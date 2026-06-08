#!/bin/bash
set -e

echo "[Setup] 파이썬 가상환경 및 데이터 파이프라인 필수 패키지 설치"

# 가상환경 존재 여부 검사 및 생성
if [ ! -d "venv" ]; then
    echo "가상환경이 존재하지 않아 새로 생성합니다."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[Setup] 필수 의존성 패키지 설치 완료"

echo "[Setup] 크롤러 구동을 위한 Playwright 시스템 브라우저를 설치합니다."
python3 -m playwright install --with-deps