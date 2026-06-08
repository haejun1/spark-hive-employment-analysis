#!/bin/bash
set -e
mkdir -p logs

echo "[Step 0/5] 선행 인프라 서비스(Hadoop, Kafka) 자동 가동 및 검증"

if ! jps | grep -q "NameNode"; then
    echo "Hadoop HDFS 중지 -> 가동"
    start-dfs.sh
    sleep 3
else
    echo "Hadoop HDFS 서비스가 이미 정상 가동 중입니다."
fi

if ! jps | grep -q "QuorumPeerMain"; then
    echo "Zookeeper 중지 -> 가동"
    zookeeper-server-start.sh -daemon /usr/hdp/current/kafka-broker/config/zookeeper.properties
    sleep 2
fi

if ! jps | grep -q "Kafka"; then
    echo "Apache Kafka 중지 -> 가동"
    kafka-server-start.sh -daemon /usr/hdp/current/kafka-broker/config/server.properties
    sleep 3
else
    echo "Apache Kafka 서비스가 이미 정상 가동 중입니다."
fi

echo "현재 가동 중인 인프라 자바 프로세스 목록입니다:"
jps

echo "[Step 1/5] 클라우드 인프라망 상태 점검"
source venv/bin/activate
python3 tests/test_db_conn.py

echo "[Step 2/5] 실시간 수신을 위한 Spark Streaming 실행"
if [ -f ".stream_spark.pid" ]; then
    PID=$(cat .stream_spark.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
    fi
fi
bash scripts/submit_spark.sh stream

echo "[Step 3/5] 크롤러 구동 및 원본 데이터 생성"
python3 -m src.ingest.run_crawler

echo "[Step 4/5] 수집 완료된 Raw 데이터 HDFS로 push"
hdfs dfs -mkdir -p /user/data/raw
hdfs dfs -put -f data/raw/jumpit_raw.json /user/data/raw/jumpit_raw.json

echo "[Step 5/5] Hadoop 데이터를 Spark로 배치 ETL 처리"
bash scripts/submit_spark.sh batch

streamlit run src/visualization/app.py