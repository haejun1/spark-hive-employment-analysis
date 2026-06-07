import streamlit as st
import pandas as pd
from pyspark.sql import SparkSession

st.set_page_config(page_title="IT 채용시장 트렌드 분석", layout="wide")
st.title("IT 채용시장 트렌드 분석")
st.markdown("Hadoop HDFS 및 Spark SQL을 활용한 빅데이터 분석")

def load_sql_queries(sql_file_path):
    with open(sql_file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    lines = content.split("\n")
    clean_lines = [line for line in lines if not line.strip().startswith("--")]
    clean_content = "\n".join(clean_lines)
    
    queries = []
    raw_queries = clean_content.split(";")
    for q in raw_queries:
        clean_q = q.strip()
        if clean_q:
            queries.append(clean_q)
    return queries

@st.cache_resource
def load_data():
    spark = SparkSession.builder \
        .appName("Jumpit-Streamlit") \
        .master("local[*]") \
        .config("spark.hadoop.fs.defaultFS", "hdfs://localhost:9000") \
        .getOrCreate()
    
    processed_path = "hdfs://localhost:9000/user/data/processed/jumpit_processed"
    df = spark.read.parquet(processed_path)
    df.createOrReplaceTempView("jumpit_processed_jobs")
    return spark

spark = load_data()
sql_file_path = "src/analytics/analyze_queries.sql"
queries = load_sql_queries(sql_file_path)

st.header("1. 학력 및 경력별 채용공고 분포")
col1, col2 = st.columns(2)
with col1:
    st.subheader("학력 요구사항")
    df_edu = spark.sql(queries[0]).toPandas()
    st.dataframe(df_edu, use_container_width=True)
    st.bar_chart(data=df_edu.set_index('학력_요구사항')['job_count'])

with col2:
    st.subheader("연차별 경력 요구사항")
    df_career = spark.sql(queries[1]).toPandas()
    st.dataframe(df_career, use_container_width=True)
    st.bar_chart(data=df_career.set_index('경력_요구사항')['job_count'])

st.divider()


st.header("2-1. 기술 스택 요구량 분석 (전통 스킬 vs AI 스킬)")
df3_pandas = spark.sql(queries[2]).toPandas()
chart_data = pd.DataFrame({
    '요구 공고 수': [df3_pandas['trad_required_jobs'][0], df3_pandas['ai_required_jobs'][0]]
}, index=['전통 코딩 스킬 요구', 'AI 스킬 요구'])

col3, col4 = st.columns([1, 1])
with col3:
    st.dataframe(df3_pandas, use_container_width=True)
with col4:
    st.bar_chart(chart_data)

st.divider()

st.header("2-2 분야별 세부 기술 스택 TOP 5")
col5, col6 = st.columns(2)

with col5:
    st.subheader("전통 코딩 기술 TOP 5")
    df_trad_top10 = spark.sql(queries[3]).toPandas()
    st.dataframe(df_trad_top10, use_container_width=True)
    st.bar_chart(data=df_trad_top10.set_index('전통_기술스택')['공고_수'])

with col6:
    st.subheader("AI 기술 TOP 5")
    df_ai_top10 = spark.sql(queries[4]).toPandas()
    st.dataframe(df_ai_top10, use_container_width=True)
    st.bar_chart(data=df_ai_top10.set_index('AI_기술스택')['공고_수'])

st.divider()


st.header("3. IT 기업 자격요건 및 우대사항 기반 핵심 인재상 분석 (경험·협업·AI)")
df2_pandas = spark.sql(queries[5]).toPandas()
st.dataframe(df2_pandas, use_container_width=True)
if not df2_pandas.empty:
    ratio_chart_data = pd.DataFrame({
        '요구 비율 (%)': [
            df2_pandas['경험_요구_비율_퍼센트'][0], 
            df2_pandas['협업_요구_비율_퍼센트'][0], 
            df2_pandas['AI_요구_비율_퍼센트'][0]
        ]
    }, index=['경험 및 실무 역량', '협업 및 소통 능력', 'AI 관련 역량'])

    st.bar_chart(ratio_chart_data, use_container_width=True)

st.success(" ")