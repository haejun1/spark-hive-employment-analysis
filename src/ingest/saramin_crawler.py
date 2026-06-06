import os
import json
import asyncio
import re
import random
import sys
import time
from datetime import datetime
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from src.utils.rdb_connector import get_connection

def write_log(message):
    """과정 추적용 실시간 로그 파일 기록"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}\n"
    print(message)
    with open("crawler_marathon.log", "a", encoding="utf-8") as f:
        f.write(log_line)

def check_already_exists(rec_idx):
    """[무적 필터] 타임아웃 터져도 죽지 않고 3번까지 재시도 후 스킵 결정"""
    for attempt in range(1, 4):
        try:
            connection = get_connection()
            with connection.cursor() as cursor:
                sql = "SELECT 1 FROM saramin_raw_jobs WHERE rec_idx = %s LIMIT 1;"
                cursor.execute(sql, (rec_idx,))
                return cursor.fetchone() is not None
        except Exception as e:
            if attempt == 3:
                write_log(f"   ❌ [체크 에러] DB 연결 최종 실패 (안전을 위해 스킵 패스): {e}")
                return False
            time.sleep(5)
        finally:
            try: connection.close()
            except: pass
    return False

async def extract_jobs_from_list(page_num):
    """1단계: IT 목록에서 공고 번호와 기본 정보를 스캔합니다."""
    url = f"https://www.saramin.co.kr/zf_user/jobs/list/job-category?page={page_num}&cat_mcls=2&isAjaxRequest=0&page_count=50&sort=RL"
    job_list = []
    
    async with async_playwright() as p:
        # 💡 모니터 바깥 좌표 (2500, 2500)로 창을 완전히 추방
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--window-size=200,150',
                '--window-position=2500,2500',
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox'
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.set_viewport_size({"width": 200, "height": 150})
        
        try:
            await page.goto(url, wait_until="commit", timeout=30000)
            await asyncio.sleep(2)
            html_content = await page.content()
        except Exception as e:
            write_log(f"   ⚠️ [{page_num}페이지] 목록 페이지 접근 타임아웃/실패 (스킵) : {e}")
            await browser.close()
            return job_list
        await browser.close()

    soup = BeautifulSoup(html_content, 'html.parser')
    items = soup.select("div.list_item")
    for item in items:
        item_id = item.get('id', '')
        if item_id and item_id.startswith('rec-'):
            idx = item_id.replace('rec-', '').strip()
            corp_tag = item.select_one("a.str_tit") or item.select_one("div.col_corp a")
            title_tag = item.select_one("a.job_tit") or item.select_one("div.job_tit a")
            corp_name = corp_tag.get_text(strip=True) if corp_tag else "N/A"
            job_title = title_tag.get_text(strip=True) if title_tag else "N/A"
            
            if idx not in [j['rec_idx'] for j in job_list]:
                job_list.append({'rec_idx': idx, 'list_company': corp_name, 'list_title': job_title})
    return job_list

async def fetch_and_parse_detail_heavy(job_meta):
    """2단계: 상세페이지 원문 전체를 화면 밖 꼼수로 고속 스크랩합니다."""
    rec_idx = job_meta['rec_idx']
    url = f"https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx={rec_idx}"
    html_content = ""
    
    async with async_playwright() as p:
        # 상세페이지도 화면 바깥 좌표 (2500, 2500)로 완벽 격리 조치
        browser = await p.chromium.launch(
            headless=False, 
            args=[
                '--window-size=200,150',
                '--window-position=2500,2500',
                '--disable-blink-features=AutomationControlled', 
                '--no-sandbox'
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await page.set_viewport_size({"width": 200, "height": 150})
        
        try:
            await page.goto(url, wait_until="commit", timeout=20000)
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 1000);")
                await asyncio.sleep(0.3)
            html_content = await page.content()
        except Exception as e:
            await browser.close()
            return None
        await browser.close()

    job_data = {
        'rec_idx': rec_idx, 'company_name': job_meta['list_company'], 'job_title': job_meta['list_title'],
        'experience': '경력무관', 'education': '학력무관', 'job_type': '정규직', 'work_place': '근무지 미지정',
        'job_sectors': [], 'preferred_conditions': [], 'company_scale': '중소기업', 'company_industry': 'IT·웹·통신',
        'description_text': ''
    }

    if not html_content:
        return job_data

    soup = BeautifulSoup(html_content, 'html.parser')
    all_text_elements = soup.find_all(['p', 'div', 'li', 'span', 'th', 'td'])
    heavy_text_pool = []
    
    for elem in all_text_elements:
        text = elem.get_text(" ", strip=True)
        if len(text) > 15 and text not in heavy_text_pool:
            heavy_text_pool.append(text)
            
    job_data['description_text'] = re.sub(r'\s+', ' ', " ".join(heavy_text_pool))
    
    main_section = soup.select_one("section[class^='jview-0-']") or soup.select_one("section.jview")
    if main_section:
        try:
            sector_tags = main_section.select("div.tags a")
            job_data['job_sectors'] = [tag.get_text(strip=True).replace('#', '') for tag in sector_tags]
            for dl in main_section.select("div.jv_summary div.col dl"):
                dt_tag, dd_tag = dl.select_one("dt"), dl.select_one("dd")
                if dt_tag and dd_tag:
                    dt, dd = dt_tag.get_text(strip=True), dd_tag.get_text(strip=True)
                    if '경력' in dt: job_data['experience'] = dd
                    elif '학력' in dt: job_data['education'] = dd
        except:
            pass

    return job_data

def save_to_mysql(data):
    """3단계: GCP 세션 다운 시 죽지 않고 10초 대기 후 무한 재시도하는 적재 로직"""
    if not data or data['company_name'] == 'N/A':
        return False
        
    for attempt in range(1, 4):
        try:
            connection = get_connection()
            with connection.cursor() as cursor:
                insert_query = """
                INSERT INTO saramin_raw_jobs (
                    rec_idx, company_name, job_title, experience, education, 
                    job_type, work_place, job_sectors, preferred_conditions, 
                    company_scale, company_industry, description_text
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    company_name=VALUES(company_name), job_title=VALUES(job_title), description_text=VALUES(description_text);
                """
                sectors_json = json.dumps(data['job_sectors'], ensure_ascii=False)
                preferred_json = json.dumps(data['preferred_conditions'], ensure_ascii=False)
                cursor.execute(insert_query, (
                    data['rec_idx'], data['company_name'], data['job_title'], data['experience'],
                    data['education'], data['job_type'], data['work_place'], sectors_json,
                    preferred_json, data['company_scale'], data['company_industry'], data['description_text']
                ))
            connection.commit()
            return True
        except Exception as e:
            if attempt == 3:
                write_log(f"   ❌ GCP MySQL 적재 최종 실패 (스킵 조치) : {e}")
                return False
            write_log(f"   ⚠️ GCP DB 세션 지연 터짐. 안전하게 10초 후 자동 재연결 들어갑니다... ({attempt}/3)")
            time.sleep(10)
        finally:
            try: connection.close()
            except: pass
    return False

async def main():
    write_log("================================================================")
    write_log("🏁 [최종 마스터본] 커넥션 풀 + 화면 밖 격리 크롤러 마라톤 엔진 가동")
    write_log("================================================================")
    
    START_PAGE = 1
    TOTAL_PAGES = 200  
    
    global_success_count = 0
    estimated_total_bytes = 0
    
    for current_page in range(START_PAGE, START_PAGE + TOTAL_PAGES):
        write_log(f"\n🔄 [페이지 진입] 현재 {current_page} / {START_PAGE + TOTAL_PAGES - 1} 페이지 수집 중...")
        
        jobs = await extract_jobs_from_list(current_page)
        if not jobs:
            write_log(f"   ⚠️ {current_page}페이지 일시적 지연 감지. 5초 대기 후 다음으로 우회.")
            await asyncio.sleep(5)
            continue
            
        page_success = 0
        skip_count = 0
        
        for idx, job_meta in enumerate(jobs, start=1):
            if check_already_exists(job_meta['rec_idx']):
                skip_count += 1
                global_success_count += 1
                continue
            
            await asyncio.sleep(random.uniform(0.8, 1.4))
            job_data = await fetch_and_parse_detail_heavy(job_meta)
            if job_data:
                success = save_to_mysql(job_data)
                if success:
                    page_success += 1
                    global_success_count += 1
                    
                    data_bytes = len(job_data['description_text'].encode('utf-8'))
                    estimated_total_bytes += data_bytes
                    
                    if global_success_count % 10 == 0:
                        mb_size = estimated_total_bytes / (1024 * 1024)
                        print(f"   📈 [실시간 메트릭스] 누적 수집: {global_success_count}건 | 추정 확보 용량: {mb_size:.2f} MB")
                        
        if skip_count > 0:
            print(f"    ⏩ [{current_page}페이지] 이미 수집된 기존 공고 {skip_count}개 초고속 스킵 완료!")
        if page_success > 0:
            write_log(f"📊 [중간 리포트] {current_page}페이지 신규 데이터 {page_success}개 적재 성공")
        
        await asyncio.sleep(2)

    write_log("\n================================================================")
    write_log(f"🏆 [마라톤 수집 완료] 최종 누적량: {global_success_count}건 안착 완료!")
    write_log(f"💾 최종 확보 용량: {estimated_total_bytes / (1024 * 1024):.2f} MB")
    write_log("================================================================")

if __name__ == "__main__":
    asyncio.run(main())