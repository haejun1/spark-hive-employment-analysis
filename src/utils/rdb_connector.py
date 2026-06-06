import os
import pymysql
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

def get_base_connection():
    """데이터베이스 이름을 지정하지 않고 MySQL 서버 자체에 연결합니다."""
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def get_connection():
    """설정된 특정 데이터베이스에 연결합니다."""
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def init_database_tables():
    print("⏳ GCP MySQL 서버 연결 및 초기화 시작...")
    db_name = os.getenv("DB_NAME", "ai-employment")
    
    # 1. 데이터베이스 자동 생성
    try:
        base_conn = get_base_connection()
        with base_conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        base_conn.commit()
        base_conn.close()
    except Exception as e:
        print(f"❌ 데이터베이스 생성 실패: {e}")
        return

    # 2. 테이블 생성
    create_table_query = """
    CREATE TABLE IF NOT EXISTS saramin_raw_jobs (
        rec_idx VARCHAR(20) PRIMARY KEY,
        company_name VARCHAR(100),
        job_title VARCHAR(255),
        experience VARCHAR(50),
        education VARCHAR(50),
        job_type VARCHAR(50),
        work_place VARCHAR(100),
        job_sectors TEXT,
        preferred_conditions TEXT,
        company_scale VARCHAR(50),
        company_industry VARCHAR(100),
        description_text LONGTEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(create_table_query)
        conn.commit()
        conn.close()
        print(f"✅ 테이블 생성 완료!")
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")

if __name__ == "__main__":
    init_database_tables()