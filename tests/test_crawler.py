import json
import os
import sys

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

from src.ingest.jumpit_crawler import JumpitCrawler


def test_jumpit_crawler():

    crawler = JumpitCrawler()

    jobs = crawler.fetch_job_list(page=1)

    print(f"\n총 {len(jobs)}개 조회됨")

    assert len(jobs) > 0, "채용공고를 가져오지 못함"

    results = []

    # 5개만 테스트
    for idx, job in enumerate(jobs[:5], start=1):

        job_id = job.get("id")

        print(f"\n[{idx}/5] job_id={job_id}")

        try:
            detail = crawler.fetch_job_detail(job_id)

            results.append(detail)

        except Exception as e:
            print(f"[ERROR] {job_id}: {e}")

    # JSON 예쁘게 출력
    print("\n" + "=" * 60)
    print("크롤링 결과 (5개)")
    print("=" * 60)

    print(
        json.dumps(
            results,
            indent=4,
            ensure_ascii=False
        )
    )

    # 저장
    save_path = "data/raw/jumpit_sample.json"

    os.makedirs("data/raw", exist_ok=True)

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(
            results,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(f"\nSaved -> {save_path}")

    # 테스트 검증
    assert len(results) == 5


if __name__ == "__main__":
    test_jumpit_crawler()