import sys
import os
import json

# 프로젝트 최상위 경로를 파이썬 시스템 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.rdb_connector import get_connection

def check_inserted_data():
    print("⏳ GCP MySQL 데이터베이스 창고를 열어 실물 데이터를 조회합니다...")
    
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            # saramin_raw_jobs 테이블에 쌓인 데이터 다 긁어오기
            sql = "SELECT rec_idx, company_name, job_title, work_place, created_at FROM saramin_raw_jobs;"
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            if not rows:
                print("\n❌ 창고가 텅 비어있습니다. 데이터가 아직 안 들어갔거나 유실되었습니다.")
                return
                
            print(f"\n🎉 === 현재 GCP MySQL 적재 완료 데이터 (총 {len(rows)}건) ===")
            print("-" * 80)
            
            # DictCursor 형식에 맞춰 이쁘게 출력
            for idx, row in enumerate(rows, start=1):
                r_idx = row.get('rec_idx') or row[0]
                c_name = row.get('company_name') or row[1]
                title = row.get('job_title') or row[2]
                place = row.get('work_place') or row[3]
                date = row.get('created_at') or row[4]
                
                print(f"[{idx}] 공고번호: {r_idx}")
                print(f"    🏢 회사명: {c_name}")
                print(f"    💼 공고명: {title}")
                print(f"    📍 근무지: {place}")
                print(f"    ⏰ 수집일시: {date}")
                print("-" * 80)
                
    except Exception as e:
        print(f"❌ 데이터 조회 실패: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    check_inserted_data()