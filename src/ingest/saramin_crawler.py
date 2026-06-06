import os
import json
import asyncio
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from src.utils.rdb_connector import get_connection

async def extract_rec_ids_from_list(page_num):
    """
    1단계: IT개발·데이터 카테고리 목록 페이지에서 공고 번호(rec_idx)를 수집합니다.
    """
    url = f"https://www.saramin.co.kr/zf_user/jobs/list/job-category?page={page_num}&cat_mcls=2&isAjaxRequest=0&page_count=50&sort=RL"
    rec_indices = []
    
    async with async_playwright() as p:
        # 목록 페이지도 안전하게 일반 브라우저 화면을 띄워 접근
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        try:
            # 네트워크 헤더가 전송 완료되는 즉시(commit) 페이지 소스를 가로챔
            await page.goto(url, wait_until="commit", timeout=30000)
            await asyncio.sleep(3)
            html_content = await page.content()
        except Exception as e:
            print(f"-> 목록 페이지 접근 실패: {e}")
            await browser.close()
            return rec_indices
        await browser.close()

    soup = BeautifulSoup(html_content, 'html.parser')
    items = soup.select("div.list_item")
    
    for item in items:
        item_id = item.get('id', '')
        if item_id and item_id.startswith('rec-'):
            idx = item_id.replace('rec-', '').strip()
            if idx not in rec_indices:
                rec_indices.append(idx)
                
    print(f"-> 목록 {page_num}페이지에서 {len(rec_indices)}개의 공고 일련번호 추출 완료.")
    return rec_indices


async def fetch_and_parse_detail(rec_idx):
    """
    2단계: 추출한 공고 번호로 상세페이지에 접속하여 목적에 맞게 선택한 11개 필드 + 본문 전체를 긁어옵니다.
    """
    url = f"https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx={rec_idx}"
    html_content = ""
    
    async with async_playwright() as p:
        print("\n[DEBUG 1] 실제 크롬 브라우저 화면을 띄워 우회 접속 중 (Headed 모드)...")
        
        browser = await p.chromium.launch(
            headless=False, 
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--window-size=1920,1080'
            ]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            java_script_enabled=True
        )
        
        page = await context.new_page()
        
        # 자동화 봇 탐지 솔루션 무력화 스크립트 주입
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {} };
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US', 'en']});
        """)
        
        try:
            print("[DEBUG 2] 1차 검증: 사람인 메인 홈 접속 시도 중...")
            # 보안 차단을 피하기 위해 네트워크 최초 응답 시점(commit)까지만 대기하고 진입
            main_response = await page.goto("https://www.saramin.co.kr", wait_until="commit", timeout=20000)
            print(f"[DEBUG 2-1] 메인 홈 응답 코드: {main_response.status if main_response else 'No Response'}")
            
            print(f"[DEBUG 3] 2차 검증: 목표 상세페이지 이동 중 -> {url}")
            response = await page.goto(url, wait_until="commit", timeout=20000)
            print(f"[DEBUG 4] 상세페이지 서버 응답 상태 코드 수신: {response.status if response else 'No Response'}")
            
            page_title = await page.title()
            print(f"[DEBUG 5] 현재 브라우저가 읽은 페이지 제목(Title): '{page_title}'")
            
            # 렌더링 안정화를 위해 화면 조작 없이 3초 대기
            await asyncio.sleep(3)
            html_content = await page.content()
            
        except Exception as e:
            print(f"\n❌ [CRITICAL ERROR] 상세페이지 로드 타임아웃/실패: {e}")
            await browser.close()
            return None
            
        await browser.close()
        print("[DEBUG 6] 브라우저 세션 정상 종료. BeautifulSoup 파싱 시작.")

    if not html_content:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    main_section = soup.select_one("section[class^='jview-0-']") or soup.select_one("section.jview")
    if not main_section:
        print("❌ [DEBUG] HTML 파싱 실패: 공고 본문 섹션을 찾지 못했습니다.")
        return None

    job_data = {
        'rec_idx': rec_idx, 'company_name': 'N/A', 'job_title': 'N/A',
        'experience': 'N/A', 'education': 'N/A', 'job_type': 'N/A',
        'work_place': 'N/A', 'job_sectors': [], 'preferred_conditions': [],    
        'company_scale': 'N/A', 'company_industry': 'N/A', 'description_text': 'N/A'     
    }

    try:
        company_tag = main_section.select_one("a.company")
        if company_tag: job_data['company_name'] = company_tag.get_text(strip=True)
        
        title_tag = main_section.select_one("h1.tit_job")
        if title_tag: job_data['job_title'] = title_tag.get_text(strip=True)

        for dl in main_section.select("div.jv_summary div.col dl"):
            dt_tag, dd_tag = dl.select_one("dt"), dl.select_one("dd")
            if dt_tag and dd_tag:
                dt, dd = dt_tag.get_text(strip=True), dd_tag.get_text(strip=True)
                if '경력' in dt: job_data['experience'] = dd
                elif '학력' in dt: job_data['education'] = dd
                elif '근무형태' in dt: job_data['job_type'] = dd
                elif '지역' in dt or '근무지' in dt: job_data['work_place'] = dd

        preferred_div = main_section.select_one("div[id^='details-preferred-']")
        if preferred_div:
            job_data['preferred_conditions'] = [li.get_text(" ", strip=True) for li in preferred_div.select("li")]

        sector_tags = main_section.select("div.tags a")
        job_data['job_sectors'] = [tag.get_text(strip=True).replace('#', '') for tag in sector_tags]

        for dl in main_section.select("div.info_area dl"):
            dt_tag, dd_tag = dl.select_one("dt"), dl.select_one("dd")
            if dt_tag and dd_tag:
                dt = dt_tag.get_text(strip=True)
                dd_txt = dd_tag.find(text=True, recursive=False)
                dd_txt = dd_txt.strip() if dd_txt else dd_tag.get_text(strip=True)
                if '기업형태' in dt: job_data['company_scale'] = dd_txt
                elif '업종' in dt: job_data['company_industry'] = dd_txt

        welfare_content = main_section.select_one("div.jv_details")
        if welfare_content:
            job_data['description_text'] = re.sub(r'\s+', ' ', welfare_content.get_text(" ", strip=True))
    except Exception as e:
        print(f"-> 파싱 중 에러 발생: {e}")

    return job_data


def save_to_mysql(data):
    """
    3단계: 원격 GCP MySQL 테이블에 적재합니다.
    """
    if not data or data['company_name'] == 'N/A':
        return
        
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            insert_query = """
            INSERT INTO saramin_raw_jobs (
                rec_idx, company_name, job_title, experience, education, 
                job_type, work_place, job_sectors, preferred_conditions, 
                company_scale, company_industry, description_text
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                company_name=VALUES(company_name),
                job_title=VALUES(job_title),
                experience=VALUES(experience),
                education=VALUES(education),
                job_type=VALUES(job_type),
                work_place=VALUES(work_place),
                job_sectors=VALUES(job_sectors),
                preferred_conditions=VALUES(preferred_conditions),
                company_scale=VALUES(company_scale),
                company_industry=VALUES(company_industry),
                description_text=VALUES(description_text);
            """
            
            sectors_json = json.dumps(data['job_sectors'], ensure_ascii=False)
            preferred_json = json.dumps(data['preferred_conditions'], ensure_ascii=False)
            
            cursor.execute(insert_query, (
                data['rec_idx'], data['company_name'], data['job_title'], data['experience'],
                data['education'], data['job_type'], data['work_place'], sectors_json,
                preferred_json, data['company_scale'], data['company_industry'], data['description_text']
            ))
        connection.commit()
    except Exception as e:
        print(f"-> MySQL 원격 적재 에러: {e}")
    finally:
        connection.close()


async def main():
    print("=== [테스트 모드] 로컬 가동 및 원격 적재 파이프라인 ===")
    SAMPLE_REC_IDX = "53861623" 
    
    job_result = await fetch_and_parse_detail(SAMPLE_REC_IDX)
    if job_result:
        print("\n🎉 === 크롤링 및 파싱 성공! === ")
        print(json.dumps(job_result, ensure_ascii=False, indent=4))
        
        print("\n⏳ GCP MySQL 원격 저장을 시도합니다...")
        save_to_mysql(job_result)
        print("✅ DB 적재 완료 확인!")

if __name__ == "__main__":
    asyncio.run(main())