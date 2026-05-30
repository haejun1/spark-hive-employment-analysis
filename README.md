# AI 시대 학과별 취업 트렌드 분석

### 1. 문제 정의
AI가 급격하게 발전하며 산업 전반에서 요구하는 직무 역량 및 채용 구조가 변화하고 있다.
AI의 발전이 학과 전공별로 취업에 어떠한 영향을 끼치는지 분석하고, 취업에 성공한 학생들의 특징을 다방면으로 파악하여 AI시대 대학 교육의 방향성을 제안하고자 한다.

{국가통계포털, 공공데이터포털, 대학알리미}를 통해 전공계열 별 취업률, 학과별 교육 여건 데이터를 수집하고, {사람인, 잡코리아, 워크넷} 취업 사이트를 통해 전공별 모집공고, 역량 요구사항을 크롤링하여 수집한다. 

### 2. 기술 스텍
데이터 수집 : Playwright, Sqoop
데이터 저장 : Hadoop HDFS
데이터 처리 : Spark, Gemini API
데이터 분석 : Hive
데이터 시각화 : Streamlit
실시간 처리 : Kafka, Spark Streaming
자동화 : shell script

### 3. 구현 계획
1️⃣데이터 수집 

- 비정형 데이터 수집
    - VS Code 환경에서 Playwright를 활용하여 {사람인, 잡코리아, 워크넷} 채용 공고문 및 요구사항 텍스트를 raw data 형태로 크롤링한다
- 정형 데이터 수집
    - {국가통계포털, 공공데이터포털, 대학알리미}의 취업 통계 csv 데이터(취업률, 전공 계열 정보 등)를 수집한다
- 데이터 적재
    - 수집 된 데이터를 GCP내 구축된 MySQL/MariaDB에 적재한다
    - Sqoop를 사용해 GCP에 저장된 데이터를 HDFS 환경으로 import한다

2️⃣ 데이터 처리

- HDFS에 적재된 데이터를 Spark로 읽어 들여 Spark DataFrame 형태로 변환한다
- Python 기반 Gemini API 호출 함수를 정의한 후 Spark UDF로 등록한다
- Prompt Engineering을 적용해 LLM이 비정형 데이터를 json 형태로변환하도록 한다
- json 데이터를 Spark DataFrame의 컬럼으로 변환한 후  Parquet 포맷으로 HDFS에 분산 저장한다

3️⃣ 데이터 분석

- HDFS에 저장된 정제된 데이터를 Hive 테이블 구조에 맞춰  정의한다
- HiveQL을 사용해 AI 상용화 시점(2023년)을 기점으로 학과별 취업률 변화 추이, 핵심 취업역량을 파악 및 계산한다

4️⃣ 데이터 시각화

- Streamlit framework를 Hive와 연동하여 취업에 관련한 interactive한 데이터를 제공한다

🔷 실시간 데이터 처리

- Playwright 크롤러가 주기적으로 채용사이트를 확인,
새로운 공고 발견 시 Kafka Producer가 처리
- Spark Streaming은 Kafka의 데이터를 실시간으로 조회하다가 데이터가 들어오면 데이터를 쪼개 Gemini UDF를 통과시켜 전처리를 수행한다

🔷파이프라인 자동화

- shell script를 활용해 크롤링부터 처리를 거쳐 시각화까지 자동으로 이어지도록 한다
