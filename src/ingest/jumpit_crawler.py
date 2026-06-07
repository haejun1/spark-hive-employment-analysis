import requests
from bs4 import BeautifulSoup

class JumpitCrawler:
    def __init__(self):
        self.base_url = "https://www.jumpit.co.kr"
        self.api_url = "https://jumpit-api.saramin.co.kr/api/positions"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def fetch_job_list(self, page=1):
        params = {"sort": "reg_dt", "highlight": "false", "page": page}
        response = requests.get(self.api_url, params=params, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        return data.get("result", {}).get("positions", [])

    def fetch_job_detail(self, job_id):
        url = f"{self.base_url}/position/{job_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. 제목 및 회사명
        job_title = soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else "Unknown"
        company_tag = soup.find("a", class_="name")
        if company_tag and "company_nm=" in company_tag.get("href", ""):
            company_name = company_tag.get("href").split("company_nm=")[1].split("&")[0]
        else:
            company_name = "Unknown"
        
        # 2. 기술 스택
        tech_stacks = []

        tech_stack_dt = soup.find("dt", string=lambda x:x and "기술스택" in x)
        if tech_stack_dt:
            tech_stack_dd = (tech_stack_dt.find_next_sibling("dd"))
            if tech_stack_dd:
                tech_stacks = [
                    img.get("alt").strip()
                    for img in tech_stack_dd.find_all("img")
                    if img.get("alt")
                ]

        # 3. 상세 섹션
        details = {}
        for dt in soup.find_all("dt"):
            dt_text = dt.get_text(strip=True)
            if dt_text in ["주요업무", "자격요건", "우대사항"]:
                dd = dt.find_next_sibling("dd")
                if dd:
                    details[dt_text] = dd.get_text(strip=True)

        # 4. 경력/학력
        meta_info = {}
        for dt in soup.find_all("dt"):
            dt_text = dt.get_text(strip=True)
            if dt_text in ["경력", "학력"]:
                dd = dt.find_next_sibling("dd")
                if dd:
                    meta_info[dt_text] = dd.get_text(strip=True)
        
        return {
            "job_id": job_id,
            "job_title": job_title,
            "company_name": company_name,
            "tech_stacks": tech_stacks, 
            "details": details, 
            "meta_info": meta_info,
            "raw_html": html 
        }