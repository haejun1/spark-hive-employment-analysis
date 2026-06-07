# src/analytics/analyze.py
import os
from pyspark.sql import SparkSession

def load_sql_queries(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    queries = []
    raw_queries = content.split(";")
    for q in raw_queries:
        clean_q = q.strip()
        if clean_q and not clean_q.startswith("--"):
            queries.append(clean_q)
    return queries

def run_hive_analysis():
    spark = SparkSession.builder \
        .appName("Jumpit-Hive-Analysis") \
        .master("local[*]") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:9000") \
        .getOrCreate()

    processed_path = "hdfs://localhost:9000/user/data/processed/jumpit_processed"
    df = spark.read.parquet(processed_path)
    df.createOrReplaceTempView("jumpit_processed_jobs")
    print("\n HDFS Parquet -> Hive\n")

    sql_file_path = "src/analytics/analyze_queries.sql"
    if not os.path.exists(sql_file_path):
        print(f"{sql_file_path} 파일이 존재하지 않습니다")
        return

    queries = load_sql_queries(sql_file_path)

    titles = [
        "[분석 1-1] IT 채용공고 별 학력 요구사항 분포",
        "[분석 1-2] IT 채용공고 별 경력 요구사항 분포 (연차별 그룹화)",
        "[분석 2-1] 전통 코딩 스킬 비중 vs AI 스킬 요구량 비교",
        "[분석 2-2-1] 전통 코딩 분야 세부 기술 스택 TOP 10",
        "[분석 2-2-2] AI 분야 세부 기술 스택 TOP 10",
        "[분석 3] IT 기업 자격요건 및 우대사항 기반 핵심 인재상 분석 (경험·협업·AI)"
    ]

    for i, query in enumerate(queries):
        if i < len(titles):
            print("\n" + "="*60)
            print(titles[i])
            print("="*60)
            
            result_df = spark.sql(query)
            
            if i == 5:
                result_df.show(5, truncate=30)
            else:
                result_df.show(20, truncate=False)      

    spark.stop()

if __name__ == "__main__":
    run_hive_analysis()