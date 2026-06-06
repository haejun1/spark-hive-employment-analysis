import os
import requests
import json
from dotenv import load_dotenv

# .env 파일의 환경변수 로드
load_dotenv()

def call_gemini_api(prompt_text):
    """
    Python 3.8 환경을 위해 requests 통신으로 Gemini 1.5 Flash API를 호출합니다.
    공고 비정형 텍스트를 문맥 분석하여 정형 데이터로 변환하는 핵심 엔진입니다.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")
    
    if not api_key:
        return {"error": "API Key가 설정되지 않았습니다. .env 파일을 확인하세요."}

    # 구글 생성형 AI 공식 API 엔드포인트 주소
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # 구글 API 규격에 맞는 페이로드 구조화
    payload = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }
    
    try:
        # API 서버로 POST 요청 전송
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            response_json = response.json()
            # 구글 응답 JSON에서 텍스트 결과물만 파싱 추출
            result_text = response_json['candidates'][0]['content']['parts'][0]['text']
            return result_text
        else:
            return f"❌ API Error [{response.status_code}]: {response.text}"
            
    except Exception as e:
        return f"❌ Connection Fail: {str(e)}"

# 코드가 잘 돌아가는지 단독 테스트해보기 위한 블록
if __name__ == "__main__":
    print("🤖 Gemini 1.5 Flash 커넥션 테스트 시작...")
    test_prompt = "대한민국 IT 취업 시장에서 백엔드 개발자에게 Node.js와 FastAPI 중 무엇이 더 뜨고 있는지 한 줄로 요약해줘."
    
    result = call_gemini_api(test_prompt)
    print("\n[Gemini 답변]:")
    print(result)