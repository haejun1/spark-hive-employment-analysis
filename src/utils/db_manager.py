import os
import pymysql
import yaml
from dotenv import load_dotenv

# .env 파일의 실제 인프라 정보를 로드합니다.
load_dotenv()


def load_config():
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    dev_config = config["development"]
    mysql_cfg = dev_config["mysql"]

    if mysql_cfg.get("host") == "ENV_DB_HOST":
        mysql_cfg["host"] = os.getenv("DB_HOST")
    if mysql_cfg.get("port") == "ENV_DB_PORT":
        mysql_cfg["port"] = int(os.getenv("DB_PORT", 3306))
    if mysql_cfg.get("user") == "ENV_DB_USER":
        mysql_cfg["user"] = os.getenv("DB_USER")
    if mysql_cfg.get("password") == "ENV_DB_PASSWORD":
        mysql_cfg["password"] = os.getenv("DB_PASSWORD")
    if mysql_cfg.get("database") == "ENV_DB_DATABASE":
        mysql_cfg["database"] = os.getenv("DB_DATABASE")

    return dev_config


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
        autocommit=True,
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
        job["crawled_at"],
    )

    cursor.execute(sql, values)