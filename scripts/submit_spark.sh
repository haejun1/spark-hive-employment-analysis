#!/bin/bash
set -e

JOB_TYPE=$1

if [ "$JOB_TYPE" == "batch" ]; then
    echo "[Spark Submit] Apache Spark 일괄 배치(Batch) ETL 작업을 제출합니다."
    spark-submit \
        --master "local[*]" \
        --driver-memory 512m \
        --executor-memory 512m \
        src/pipeline/batch_spark_etl.py

elif [ "$JOB_TYPE" == "stream" ]; then
    echo "[Spark Submit] Apache Spark 실시간 스트리밍(Streaming) 작업을 백그라운드에서 실행합니다."
    nohup spark-submit \
        --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.8 \
        --master "local[*]" \
        src/pipeline/stream_spark_etl.py > logs/stream_spark_etl.log 2>&1 &
    echo $! > .stream_spark.pid
    echo "[Spark Submit] 스트리밍 엔진이 백그라운드에서 안전하게 가동되었습니다."

else
    echo "가동 에러: 올바른 아규먼트(batch 또는 stream)를 입력해 주세요."
    exit 1
fi