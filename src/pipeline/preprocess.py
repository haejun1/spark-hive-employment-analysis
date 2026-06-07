from datetime import datetime


def normalize_job(raw_job):
    return {
        "job_id":
            raw_job.get("job_id"),
        "title":
            raw_job.get("job_title"),
        "company_name":
            raw_job.get("company_name"),
        "career":
            raw_job.get("meta_info", {})
            .get("경력"),
        "education":
            raw_job.get("meta_info", {})
            .get("학력"),
        "main_task":
            raw_job.get("details", {})
            .get("주요업무"),
        "qualification":
            raw_job.get("details", {})
            .get("자격요건"),
        "preferred_text":
            raw_job.get("details", {})
            .get("우대사항"),
        "tech_stacks":
            ",".join(
                raw_job.get("tech_stacks", [])
            ),
        "raw_html": raw_job.get("raw_html"),
        "crawled_at": datetime.now()
    }