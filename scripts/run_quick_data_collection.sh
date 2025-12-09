#!/bin/bash

# AEGIS v3.0 - 빠른 데이터 수집 (일별 데이터 제외)
# 실행: bash scripts/run_quick_data_collection.sh

echo "============================================================"
echo "📊 AEGIS v3.0 빠른 데이터 수집 시작"
echo "============================================================"
echo ""

# 프로젝트 디렉토리로 이동
cd /Users/wonny/Dev/aegis/v3

# 가상환경 활성화
source venv/bin/activate

# 1. 글로벌 매크로 데이터 (빠름 - 1초)
echo "1️⃣ 글로벌 매크로 데이터 수집 중..."
python scripts/weekend_fueling.py
echo ""

# 2. 테마 & 뉴스 데이터 (빠름 - 2초)
echo "2️⃣ 테마 & 뉴스 데이터 수집 중..."
python scripts/init_theme_data.py
echo ""

# 3. DART 재무 데이터 (중간 - 30분~1시간)
echo "3️⃣ DART 재무 데이터 수집 중..."
echo "   (소요시간: 30분~1시간 예상)"
python scripts/init_dart_data.py
echo ""

echo "============================================================"
echo "✅ 빠른 데이터 수집 완료!"
echo "============================================================"
echo ""
echo "💡 종목 기초 데이터는 별도로 실행 중입니다."
