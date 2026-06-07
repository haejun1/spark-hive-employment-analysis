#!/bin/bash

export HADOOP_HOME=$HOME/hadoop
export HADOOP_CONF_DIR=$HADOOP_HOME/etc/hadoop

source venv/bin/activate

spark-submit \
  --master "local[*]" \
  --driver-memory 512m \
  --executor-memory 512m \
  src/pipeline/batch_spark_etl.py

echo "Spark ETL Batch Job Submitted Successfully!"