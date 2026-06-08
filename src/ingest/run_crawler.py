import os
import json
import time
from src.ingest.jumpit_crawler import JumpitCrawler
from src.pipeline.preprocess import normalize_job
from src.utils.db_manager import get_db_connection, insert_job, load_config
from src.ingest.kafka_producer import get_kafka_producer, send_to_kafka
from src.utils.logger import get_logger

logger = get_logger("Crawler")

def run():
    crawler = JumpitCrawler()
    config = load_config()
    if "development" in config:
        mysql_cfg = config["development"]["mysql"]
    else:
        mysql_cfg = config["mysql"]
    table_name = mysql_cfg["table_name"]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        producer = get_kafka_producer()
        logger.info("Kafka 연결 성공")
    except Exception as e:
        logger.error(f"Kafka 연결 실패 : {e}")
        producer = None

    save_path = "data/raw/jumpit_raw.json"
    all_jobs = []

    if os.path.exists(save_path):
        try:
            with open(save_path, "r", encoding="utf-8") as f:
                all_jobs = json.load(f)
                if not isinstance(all_jobs, list):
                    all_jobs = []
            logger.info(f"과거 누적 데이터 {len(all_jobs)}개를 성공적으로 불러왔습니다.")
        except Exception:
            all_jobs = []
            
    existing_ids = {str(job.get("id") or job.get("job_id")) for job in all_jobs if job}
    
    total_saved = 0
    new_scraped_count = 0
    page = 1

    logger.info("===== 크롤링 시작 =====")

    while True:
        try:
            jobs = crawler.fetch_job_list(page)
            if not jobs:
                logger.info("----마지막 페이지----")
                break

            logger.info(f"[PAGE {page}] {len(jobs)}개 발견")

            for idx, job in enumerate(jobs, start=1):
                try:
                    job_id = str(job["id"])
                    if job_id in existing_ids:
                        continue
                    detail = crawler.fetch_job_detail(job_id)
                    normalized = normalize_job(detail)
                    
                    insert_job(cursor, table_name, normalized)
                    all_jobs.append(normalized)
                    existing_ids.add(job_id)
                    
                    total_saved += 1
                    logger.info(f"[{total_saved}] 저장 완료 | page={page} | idx={idx} | id={job_id}")
                    
                    if producer:
                        try:
                            job_payload = {
                                "job_id": str(normalized.get("id", job_id)),
                                "title": normalized.get("title", ""),
                                "company_name": normalized.get("company_name", ""),
                                "education": normalized.get("education", "학력무관"),
                                "career": normalized.get("career", "경력무관"),
                                "main_task": normalized.get("main_task", ""),
                                "qualification": normalized.get("qualification", ""),
                                "preferred_text": normalized.get("preferred_text", ""),
                                "tech_stacks": str(normalized.get("tech_stacks", []))
                            }
                            send_to_kafka(producer, job_payload)
                        except Exception as k_err:
                            logger.error(f"[Kafka 전송 에러] id={job_id}: {k_err}")

                    time.sleep(0.3)
                except Exception as e:
                    logger.error(f"[ERROR] id={job_id}: {e}")

            page += 1
        except Exception as e:
            logger.error(f"[PAGE ERROR] page={page}: {e}")
            break

    conn.close()

    # 데이터 저장
    os.makedirs("data/raw", exist_ok=True)
    save_path = "data/raw/jumpit_raw.json"
    
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, ensure_ascii=False, indent=4, default=str)

    logger.info(f"===== 완료 =====")
    logger.info(f"총 저장 공고 수: {total_saved}")
    logger.info(f"백업 HDFS용 JSON 경로: {save_path}")

if __name__ == "__main__":
    run()