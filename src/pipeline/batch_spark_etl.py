import sys
import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, lower, regexp_replace, split, array_contains, when, lit
from pyspark.sql.types import ArrayType, StringType, BooleanType

def create_spark_session():
    return SparkSession.builder \
        .appName("Jumpit-Batch-ETL") \
        .master("local[*]") \
        .config("spark.sql.warehouse.dir", "/user/hive/warehouse") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:9000") \
        .config("spark.hadoop.fs.hdfs.impl", "org.apache.hadoop.hdfs.DistributedFileSystem") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .config("spark.driver.memory", "512m") \
        .config("spark.executor-memory", "512m") \
        .enableHiveSupport() \
        .getOrCreate()

def clean_and_build_array(tech_string):
    if not tech_string: return []
    cleaned = str(tech_string).replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    return [t.strip().lower() for t in cleaned.split(",") if t.strip()]

def check_ai_skill(tech_list):
    if not tech_list: return False
    ai_keywords = ['ai/인공지능', '머신러닝', '딥러닝', 'ai', 'artificial intelligence', 'deep learning', 'machine learning', 'nlp', 'vision', 'llm', 'generative ai', 'pytorch', 'tensorflow', 'scikit-learn', 'keras', 'opencv', 'huggingface', 'langchain', 'data analysis']
    return any(kw in tech_list for kw in ai_keywords)

def check_traditional_skill(tech_list):
    if not tech_list: return False
    trad_keywords = ['r', 'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'c', 'go', 'kotlin', 'swift', 'php', 'html', 'css', 'spring', 'spring boot', 'react', 'node.js', 'vue.js', 'next.js', 'express', 'django', 'fastapi', 'flask', 'wpf', 'mysql', 'postgresql', 'oracle', 'mariadb', 'mongodb', 'redis', 'aws', 'docker', 'kubernetes', 'linux', 'git', 'github']
    return any(kw in tech_list for kw in trad_keywords)

def check_experience_attr(q, p):
    text = (str(q) + " " + str(p)).lower()
    keywords = ['실무 경험', '현장 개발', '운영 경험', '구축 프로젝트', '상용 서비스', '시스템 통합', '유경험자', '개발 경험', '구현 경험', '설계 경험']
    return any(kw in text for kw in keywords)

def check_collaboration_attr(q, p):
    text = (str(q) + " " + str(p)).lower()
    keywords = ['의사소통', '커뮤니케이션', '원활한', '소통과 협업', '팀워크', '협업 능력', '원만한']
    return any(kw in text for kw in keywords)

def check_ai_relation_attr(q, p):
    text = (str(q) + " " + str(p)).lower()
    keywords = ['ai', '인공지능', '머신러닝', '딥러닝', '알고리즘 개발', '모델 개발', 'ai 추론', '추론 모델', 'ai 도구', 'ai를 활용', '업무 효율']
    return any(kw in text for kw in keywords)

def run_etl():
    spark = create_spark_session()
    clean_array_udf = udf(clean_and_build_array, ArrayType(StringType()))
    ai_skill_udf = udf(check_ai_skill, BooleanType())
    trad_skill_udf = udf(check_traditional_skill, BooleanType())
    
    exp_udf = udf(check_experience_attr, BooleanType())
    coll_udf = udf(check_collaboration_attr, BooleanType())
    ai_rel_udf = udf(check_ai_relation_attr, BooleanType())

    print("\n===== 1. HDFS로부터 Raw 데이터 로드 =====")
    input_path = "hdfs://localhost:9000/user/data/raw/jumpit_raw.json"
    raw_df = spark.read.option("multiline", "true").json(input_path)

    print("\n===== 2. 데이터 정제 및 정형화 =====")
    clean_pattern = r"[\n•\-\t\r]"
    
    processed_df = raw_df.select(
        col("job_id").cast("string"),
        col("title"),
        col("company_name"),
        when(col("education").isNull(), "학력무관").otherwise(col("education")).alias("education"),
        when(col("career").isNull(), "경력무관").otherwise(col("career")).alias("career"),
        regexp_replace(col("main_task"), clean_pattern, " ").alias("main_task"),
        regexp_replace(col("qualification"), clean_pattern, " ").alias("qualification"),
        regexp_replace(col("preferred_text"), clean_pattern, " ").alias("preferred_text"),
        clean_array_udf(col("tech_stacks")).alias("tech_stacks_array")
    )

    print("\n===== 3. 핵심 도메인 분석용 파생 변수 생성 =====")
    final_df = processed_df \
        .withColumn("has_ai_skill", ai_skill_udf(col("tech_stacks_array"))) \
        .withColumn("has_trad_skill", trad_skill_udf(col("tech_stacks_array"))) \
        .withColumn("has_experience_required", exp_udf(col("qualification"), col("preferred_text"))) \
        .withColumn("has_collaboration_required", coll_udf(col("qualification"), col("preferred_text"))) \
        .withColumn("has_ai_relation_required", ai_rel_udf(col("qualification"), col("preferred_text")))

    print("\n===== 4. 정제된 데이터를 HDFS에 Parquet 포맷으로 분산 저장 =====")
    output_path = "hdfs://localhost:9000/user/data/processed/jumpit_processed"
    
    final_df.write \
        .mode("overwrite") \
        .partitionBy("career", "education") \
        .parquet(output_path)

    print(f"Parquet 분산 저장 완료: {output_path}")
    
    final_df.show(5, truncate=True)
    spark.stop()

if __name__ == "__main__":
    run_etl()