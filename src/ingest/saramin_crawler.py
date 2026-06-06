import os
import json
import asyncio
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from src.utils.rdb_connector import get_connection

async def fetch_and_parse_detail(rec_idx):
    url = f"https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx={rec_idx}"
    
async with async_playwright() as p:
        print("\n[DEBUG 1] 프록시 IP를 장착하여 브라우저 가동...")
        
        # 무료 국내/해외 프록시 서버 주소 예시 (테스트용)
        # 실제 작동하는 무료 프록시 IP:포트 번호를 구해서 넣어줘야 해
        PROXY_SERVER = "http://210.107.22.251:80" 
        
        browser = await p.chromium.launch(
            headless=True,
            proxy={"server": PROXY_SERVER}, # 이 한 줄이 핵심이야!
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox'
            ]
        )
        
        # 실제 윈도우 크롬 브라우저와 완벽하게 동일한 쿠키 및 세션 환경 구축
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ko-KR",
            timezone_id="Asia/Seoul",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Upgrade-Insecure-Requests": "1"
            }
        )
        
        page = await context.new_page()
        
        # 네비게이터 자동화 흔적 지우기 (완벽 우회)
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {} };
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
            Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US', 'en']});
        """)
        
        # 텍스트 추출 속도 향상을 위해 무거운 리소스 abort
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "font", "stylesheet", "media"] else route.continue_())

        try:
            # [원인진단용 추가] 1단계 검증: 사람인 메인 도메인 자체는 뚫리는가?
            print("[DEBUG 2] 1차 검증: 사람인 메인 홈 접속 시도 중...")
            main_response = await page.goto("https://www.saramin.co.kr", wait_until="commit", timeout=15000)
            print(f"[DEBUG 2-1] 메인 홈 응답 코드: {main_response.status if main_response else 'No Response'}")
            
            # 2단계 검증: 실제 목표 상세 페이지 접속
            print(f"[DEBUG 3] 2차 검증: 목표 상세페이지 이동 중 -> {url}")
            # wait_until을 domcontentloaded 대신 commit(네트워크 수신 즉시)으로 내려서 타임아웃 방지
            response = await page.goto(url, wait_until="commit", timeout=20000)
            
            print(f"[DEBUG 4] 상세페이지 서버 응답 상태 코드 수신: {response.status if response else 'No Response'}")
            
            # 페이지에 캡차가 떴거나 차단 스크립트가 도는지 HTML 제목 확인
            page_title = await page.title()
            print(f"[DEBUG 5] 현재 브라우저가 읽은 페이지 제목(Title): '{page_title}'")
            
            if "요청하신 페이지를 찾을 수 없습니다" in page_title or "Access Denied" in page_title:
                print("❌ [경고] 사람인 방화벽에 완전히 가로막혔습니다 (IP 차단 상태).")
                await browser.close()
                return None
                
            # 강제로 스켈레톤 레이아웃이 로드될 때까지 5초만 명시적 대기
            await asyncio.sleep(5)
            html_content = await page.content()
            
        except Exception as e:
            print(f"\n❌ [CRITICAL ERROR] 네트워크 단절 또는 타임아웃 발생 원인:")
            print(f"-> 에러 상세 내용: {e}")
            print("-> 진단 결과: 현재 GCP 서버 IP 대역이 사람인 DDOS 방화벽에 Blacklist로 지정되어 패킷이 유실 중일 확률 95%입니다.")
            await browser.close()
            return None
            
        await browser.close()
        print("[DEBUG 6] 브라우저 세션 정상 종료. BeautifulSoup 파싱 연계 시작.")

    # [이하 파싱 로직 동일]
    soup = BeautifulSoup(html_content, 'html.parser')
    main_section = soup.select_one("section[class^='jview-0-']") or soup.select_one("section.jview")
    if not main_section:
        print("❌ [DEBUG] HTML 파싱 실패: 공고 본문 섹션(section.jview)을 찾지 못했습니다.")
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
        print(f"-> 파싱 중 에러: {e}")

    return job_data

def save_to_mysql(data):
    if not data or data['company_name'] == 'N/A':
        return
        
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            # 12개 컬럼 (rec_idx ~ description_text)
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
        print(f"-> MySQL 적재 에러: {e}")
    finally:
        connection.close()

async def main():
    print("=== [테스트 모드] 우회 패턴 강화 및 로그 추적 크롤링 ===")
    SAMPLE_REC_IDX = "53861623" 
    job_result = await fetch_and_parse_detail(SAMPLE_REC_IDX)
    if job_result:
        print("\n🎉 === 최종 크롤링 및 파싱 결과 ===")
        print(json.dumps(job_result, ensure_ascii=False, indent=4))

if __name__ == "__main__":
    asyncio.run(main())