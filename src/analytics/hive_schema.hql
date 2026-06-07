CREATE EXTERNAL TABLE IF NOT EXISTS jumpit_processed_jobs (
    job_id STRING,
    title STRING,
    company_name STRING,
    main_task STRING,
    qualification STRING,
    preferred_text STRING,
    has_ai_skill BOOLEAN,
    has_trad_skill BOOLEAN
)
PARTITIONED BY (career STRING, education STRING)
STORED AS PARQUET
LOCATION '/user/data/processed/jumpit_processed';

MSCK REPAIR TABLE jumpit_processed_jobs;