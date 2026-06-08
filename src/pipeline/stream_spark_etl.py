import sys
import yaml
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, from_json, regexp_replace, when
from pyspark.sql.types import StructType, StructField, StringType, ArrayType, BooleanType

def load_config():
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def create_spark_streaming_session(config):
    spark_cfg = config["development"]["spark"]
    return SparkSession.builder \
        .appName("Jumpit-Stream-ETL") \
        .master(spark_cfg.get("master", "local[*]")) \
        .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:9000") \
        .config("spark.sql.shuffle.partitions", spark_cfg.get("shuffle_partitions", "2")) \
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

def run_stream_etl():
    config = load_config()
    spark = create_spark_streaming_session(config)
    
    clean_array_udf = udf(clean_and_build_array, ArrayType(StringType()))
    ai_skill_udf = udf(check_ai_skill, BooleanType())
    trad_skill_udf = udf(check_traditional_skill, BooleanType())
    exp_udf = udf(check_experience_attr, BooleanType())
    coll_udf = udf(check_collaboration_attr, BooleanType())
    ai_rel_udf = udf(check_ai_relation_attr, BooleanType())

    kafka_cfg = config["development"]["kafka"]
    
    kafka_stream_df = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", kafka_cfg["bootstrap_servers"]) \
        .option("subscribe", kafka_cfg["topic"]) \
        .load()

    job_schema = StructType([
        StructField("job_id", StringType(), True),
        StructField("title", StringType(), True),
        StructField("company_name", StringType(), True),
        StructField("education", StringType(), True),
        StructField("career", StringType(), True),
        StructField("main_task", StringType(), True),
        StructField("qualification", StringType(), True),
        StructField("preferred_text", StringType(), True),
        StructField("tech_stacks", StringType(), True)
    ])

    parsed_df = kafka_stream_df \
        .selectExpr("CAST(value AS STRING) as json_str") \
        .select(from_json(col("json_str"), job_schema).alias("data")) \
        .select("data.*")

    clean_pattern = r"[\n•\-\t\r]"
    
    processed_df = parsed_df.select(
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

    final_stream_df = processed_df \
        .withColumn("has_ai_skill", ai_skill_udf(col("tech_stacks_array"))) \
        .withColumn("has_trad_skill", trad_skill_udf(col("tech_stacks_array"))) \
        .withColumn("has_experience_required", exp_udf(col("qualification"), col("preferred_text"))) \
        .withColumn("has_collaboration_required", coll_udf(col("qualification"), col("preferred_text"))) \
        .withColumn("has_ai_relation_required", ai_rel_udf(col("qualification"), col("preferred_text")))

    spark_cfg = config["development"]["spark"]
    
    query = final_stream_df.writeStream \
        .format("parquet") \
        .option("path", spark_cfg["parquet_path"]) \
        .option("checkpointLocation", spark_cfg["checkpoint_path"]) \
        .partitionBy("career", "education") \
        .outputMode("append") \
        .start()

    print(f"Apache Spark Structured Streaming 가동을 시작합니다. (대상 토픽: {kafka_cfg['topic']})")
    query.awaitTermination()

if __name__ == "__main__":
    run_stream_etl()