import sys
import os
import yaml
import pymysql

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_connection():
    print("GCP MySQL 데이터베이스 연결 상태 테스트")
    with open("config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    db_cfg = config['development']['mysql']
    try:
        conn = pymysql.connect(
            host=db_cfg['host'],
            port=db_cfg['port'],
            user=db_cfg['user'],
            password=db_cfg['password'],
            database=db_cfg['database'],
            connect_timeout=5
        )
        print("[성공] MySQL 서버망 및 접속 권한 인증")
        conn.close()
    except Exception as e:
        print(f"[실패] 데이터베이스 연결 실패 \n에러 내용: {str(e)}")

if __name__ == "__main__":
    test_connection()