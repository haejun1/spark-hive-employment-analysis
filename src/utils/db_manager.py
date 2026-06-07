import pymysql
import yaml


def load_config():

    with open(
        "config/config.yaml",
        "r",
        encoding="utf-8"
    ) as f:

        config = yaml.safe_load(f)

    return config["development"]


def get_db_connection():

    config = load_config()

    mysql_config = config["mysql"]

    conn = pymysql.connect(
        host=mysql_config["host"],
        port=mysql_config["port"],
        user=mysql_config["user"],
        password=mysql_config["password"],
        database=mysql_config["database"],
        charset="utf8mb4",
        autocommit=True
    )

    return conn


def insert_job(cursor, table_name, job):

    sql = f"""
    INSERT IGNORE INTO {table_name}
    (
        job_id,
        title,
        company_name,
        career,
        education,
        main_task,
        qualification,
        preferred_text,
        tech_stacks,
        raw_html,
        crawled_at
    )
    VALUES
    (
        %s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s
    )
    """

    values = (
        job["job_id"],
        job["title"],
        job["company_name"],
        job["career"],
        job["education"],
        job["main_task"],
        job["qualification"],
        job["preferred_text"],
        job["tech_stacks"],
        job["raw_html"],
        job["crawled_at"]
    )

    cursor.execute(sql, values)