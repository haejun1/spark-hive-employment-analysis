## **AI 시대 IT 직군 채용 트렌드 분석**

### **1. 문제 정의**

- AI가 급격하게 발전하며 IT산업에서 요구하는 기술스택, 직무 역량 및 채용 구조가 변화하고 있다.
- IT 기업의 채용 공고문(점핏 사이트)을 분석하여 직무 역량의 변화를 파악하고자 한다.

### **2. 기술 스텍**

- 데이터 수집 : Playwright, Sqoop
- 데이터 저장 : Hadoop HDFS, GCP(MySQL/MariaDB)
- 데이터 처리 : Spark
- 데이터 분석 : Hive
- 데이터 시각화 : Streamlit
- 실시간 처리 : Kafka, Spark Streaming
- 자동화 : Shell Script

### **3. 구현 계획**

1️⃣데이터 수집 

- 데이터 수집
    - VS Code 환경에서 Playwright를 활용하여 {점핏} 사이트의 채용 공고문 데이터를 수집한다
    - 수집 시 기존의 data의 공고id를 확인하여 수집된 공고는 skip하고 새로운 공고문을 누적해서 수집한다
- 데이터 적재
    - 수집 된 데이터를 GCP내 구축된 MySQL/MariaDB에 적재 및 JSON raw 백업 데이터를 구축한다
    - 백업된 raw 데이터를 Hadoop File System을 통해 HDFS에 import한다

2️⃣ 데이터 처리

- HDFS에 적재된 데이터를 Spark로 읽어 들여 Spark DataFrame 형태로 변환한다
- 수집된 json 데이터를 1차 분리한다(preprocess.py)
- 특수문자, 줄바꿈 등을 바꾸는 cleansing을 수행한다
- 분석목적에 맞게UDF로 데이터를 처리한다
    - 데이터 종류 및 도메인을 파악할 때 LLM으로 1차 파악한 후 도출된 핵심 키워드를 전처리에 활용한다
- Parquet 포맷으로 HDFS에 분산 저장한다.

3️⃣ 데이터 분석

- HDFS에 저장된 정제된  Parquet 데이터를 Hive 테이블 구조에 맞춰 정의하고 HiveQL 연산을 수행한다
- 분석 1 :  IT 채용 공고별 경력, 학력 비교
- 분석 2 : 기술스택 : 전통 코딩 스킬 vs AI 스킬 요구사항 분석
- 분석 3 : IT기업 요구 자격요건, 우대사항 기반 인재상 (경험 - 협업 - AI)

4️⃣ 데이터 시각화

- Streamlit framework를 Hive와 연동하여 취업에 관련한 interactive한 데이터를 제공한다

🔷 실시간 데이터 처리

- 기존과 공고id가 중복되지 않는 새로운 공고 발견 시 Kafka Producer가 처리하여 json으로 형태로 방출한다
- Spark Streaming은 Kafka의 데이터를 실시간으로 조회하다가 데이터가 들어오면 전처리하여 가공하여 분석에 사용할 수 있도록 처리하여 시각화까지 이어준다

🔷파이프라인 자동화

- shell script를 활용해 데이터 수집→처리→분석→시각화까지 run_all.sh로 한번에 진행되도록 한다
    - gcp 연결 상태를 확인한다
    - 크롤링을 한다
    - 수집된 데이터를 hdfs로 보낸다
    - 데이터를 처리하여 최종 저장한다
    - 데이터를 분석하는 HiveQL을 수행하고 시각화하여 화면에 띄워준다

### 실행 가이드

❗Hadoop, Kafka가 설치된 Linux 가상환경 기준으로 작동합니다

#### 1️⃣ 가상환경 및 의존성 패키지 일괄 설치

```python
# 1. 쉘 스크립트 가동 권한 부여
chmod +x scripts/*.sh

# 2. 통합 환경 설정 스크립트 실행 (최초 1회)
bash scripts/setup_env.sh
```

#### 2️⃣ 사용자 환경 변수 설정

```python
# 1. 템플릿 파일을 복사하여 .env 생성
cp .env.example .env

# 2. 텍스트 에디터로 .env 파일을 열어 DB 정보 입력
nano .env
```

#### 3️⃣ 실행

```python
# 통합 자동화 쉘 스크립트 가동
./scripts/run_all.sh
```