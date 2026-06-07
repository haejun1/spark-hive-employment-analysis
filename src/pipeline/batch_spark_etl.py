import os
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, from_json
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
import google.generativeai as genai

# 1. 독립형 로컬 스파크 세션 시작 (MySQL 커넥터 장착)
spark = SparkSession.builder \
    .appName("SaraminGeminiLLMAndSparkETL") \
    .master("local[*]") \
    .config("spark.jars.packages", "com.mysql:mysql-connector-j:8.0.33") \
    .getOrCreate()

print("\n🚀 [데이터 처리 단계] 스파크 엔진 및 Gemini 1.5 Flash UDF 파이프라인 시동...")

# 2. 형이 제공한 인프라 설정 정보 (GCP MySQL & Gemini)
DB_HOST = "34.64.49.102"
DB_PORT = "3306"
DB_USER = "root"
DB_PASSWORD = "ZSjIYVS$x0a1ZP?i"
DB_NAME = "ai-employment"
GEMINI_KEY = "AIzaSyAdNNJrPrCRnuXqVEXFKfLuxzaXeIbbgQw"

# 3. GCP MySQL로부터 Raw 데이터 수집 및 로드 (Playwright 수집본 백업 대체)
try:
    raw_df = spark.read \
        .format("jdbc") \
        .option("url", f"jdbc:mysql://{DB_HOST}:{DB_PORT}/{DB_NAME}") \
        .option("dbtable", "saramin_raw_jobs") \
        .option("user", DB_USER) \
        .option("password", DB_PASSWORD) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .load()
    print("💾 GCP MySQL로부터 채용 공고 비정형 데이터 로딩 성공!")
except Exception as e:
    print(f"❌ DB 로드 실패: {e}")
    spark.stop()
    exit(1)

# ======================== [4번 블록 긴급 패치 버전] ========================
def analyze_job_text_with_gemini(description_text):
    if not description_text or len(description_text.strip()) < 10:
        return json.dumps({"experience_type": "미지정", "education": "미지정", "tech_stack": "", "ai_required": "N"})
    
    try:
        # 워커 노드 내부 환경 설정
        genai.configure(api_key=GEMINI_KEY)
        
        # ⚠️ 기존 genai.Model ──► genai.GenerativeModel 인터페이스로 정정!
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        
        prompt = f"""
        당신은 IT 전문 채용 분석가입니다. 아래의 채용 공고문 텍스트를 분석하여 지정된 JSON 형식으로만 응답하세요. 
        텍스트 외의 다른 설명이나 마크다운(```json)을 절대 포함하지 마십시오. 반드시 순수 JSON 스트링만 반환해야 합니다.

        [분석 기준]
        1. experience_type: '신입', '경력', '경력무관' 중 하나로 분류
        2. education: '고졸', '초대졸', '대졸(4년제)', '석박사', '학력무관' 중 하나로 분류
        3. tech_stack: 공고문에서 요구하는 기술 스택 키워드들을 쉼표(,)로 구분한 문자열 (예: 'Python, FastAPI, MySQL')
        4. ai_required: AI 모델 활용, LLM, 딥러닝, 머신러닝 스킬 요구 여부 ('Y' 또는 'N')

        [JSON 출력 포맷 예시]
        {{"experience_type": "경력", "education": "대졸(4년제)", "tech_stack": "Java, Spring, MySQL", "ai_required": "N"}}

        [분석할 채용 공고문]
        {description_text}
        """
        
        response = model.generate_content(prompt)
        result_text = response.text.replace("```json", "").replace("```", "").strip()
        return result_text
    except Exception as e:
        # 디버깅 편의를 위해 에러 메시지 역추적용 텍스트 반환 유지
        return json.dumps({"experience_type": "에러", "education": "에러", "tech_stack": str(e), "ai_required": "N"})
        
# 5. PySpark UDF(User Defined Function) 등록 ⭐️
gemini_udf = udf(analyze_job_text_with_gemini, StringType())

print("\n🤖 [LLM 전처리] Gemini 1.5 Flash API 호출 및 비정형 데이터 파싱 시작 (시간이 약간 소요될 수 있어 형!)...")

# 실습 가속화를 위해 상위 5개 데이터 샘플링해서 LLM 파싱 테스트 진행
sample_df = raw_df.limit(5)
processed_json_df = sample_df.withColumn("gemini_json", gemini_udf(col("description_text")))

# 6. JSON 파싱을 위한 스파크 스키마 정의
json_schema = StructType([
    StructField("experience_type", StringType(), True),
    StructField("education", StringType(), True),
    StructField("tech_stack", StringType(), True),
    StructField("ai_required", StringType(), True)
])

# 7. JSON 컬럼을 스파크 DataFrame 정형 컬럼들로 변환
final_structured_df = processed_json_df.withColumn("parsed_data", from_json(col("gemini_json"), json_schema)) \
    .select(
        col("rec_idx"),
        col("company_name"),
        col("job_title"),
        col("parsed_data.experience_type").alias("experience_type"),
        col("parsed_data.education").alias("education"),
        col("parsed_data.tech_stack").alias("tech_stack"),
        col("parsed_data.ai_required").alias("ai_required"),
        col("created_at")
    )

print("\n✨ Gemini LLM 파싱 완료! 정형화된 데이터프레임 구조:")
final_structured_df.show(5, truncate=False)

# 8. [최종 저장] 정제된 분석 마트 데이터를 Parquet 포맷으로 가뿐하게 분산 저장
output_path = "data/2_processed/saramin_refined_parquet"
print(f"\n💾 기획서 요구사항에 맞춰 Parquet 포맷으로 HDFS(로컬 대치) 적재 진행 ──► {output_path}")

final_structured_df.write \
    .mode("overwrite") \
    .format("parquet") \
    .save(output_path)

print("🎉 [대성공] 2단계 데이터 처리(LLM UDF 전처리 및 Parquet 저장) 마스터 완료!")
spark.stop()