import os
import json
import time
from src.ingest.jumpit_crawler import JumpitCrawler
from src.pipeline.preprocess import normalize_job
from src.utils.db_manager import get_db_connection, insert_job, load_config

def run():
    crawler = JumpitCrawler()
    config = load_config()
    table_name = config["mysql"]["table_name"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    all_jobs = []
    total_saved = 0
    page = 1

    print("\n===== 크롤링 시작 =====")

    while True:
        try:
            jobs = crawler.fetch_job_list(page)
            if not jobs:
                print("\n ----마지막 페이지----")
                break

            print(f"\n[PAGE {page}] {len(jobs)}개 발견")

            for idx, job in enumerate(jobs, start=1):
                try:
                    job_id = job["id"]
                    detail = crawler.fetch_job_detail(job_id)
                    normalized = normalize_job(detail)
                    
                    insert_job(cursor, table_name, normalized)
                    all_jobs.append(normalized)
                    
                    total_saved += 1
                    print(f"[{total_saved}] 저장 완료 | page={page} | idx={idx} | id={job_id}")
                    
                    time.sleep(0.3)
                except Exception as e:
                    print(f"[ERROR] id={job_id}: {e}")

            page += 1
        except Exception as e:
            print(f"[PAGE ERROR] page={page}: {e}")
            break

    conn.close()

    # 데이터 저장
    os.makedirs("data/raw", exist_ok=True)
    save_path = "data/raw/jumpit_raw.json"
    
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=4, default=str)

    print(f"\n===== 완료 =====\n총 저장 수: {total_saved}\nJSON 저장: {save_path}")

if __name__ == "__main__":
    run()