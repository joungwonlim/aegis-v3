#!/bin/bash

# AEGIS v3.0 - 시장 수급 데이터 수집 (장 시간 실행 필수)
# 실행: bash scripts/RUN_MARKET_FLOW.sh
# 권장 시간: 15:30 (장 마감 후)

echo "============================================================"
echo "📊 시장 수급 데이터 수집"
echo "============================================================"
echo ""
echo "⚠️  주의: 이 스크립트는 장 시간(09:00-15:30)에 실행해야 합니다"
echo "         현재 시간이 장 시간이 아니면 데이터가 수집되지 않을 수 있습니다"
echo ""

# 현재 시간 확인
current_hour=$(date +%H)
current_minute=$(date +%M)
current_time="${current_hour}${current_minute}"

if [ "$current_time" -lt "0900" ] || [ "$current_time" -gt "1530" ]; then
    echo "⚠️  경고: 현재 장 시간이 아닙니다 (현재: $(date +%H:%M))"
    echo "   장 시간: 09:00-15:30"
    echo ""
    read -p "계속 진행하시겠습니까? (y/n): " confirm

    if [ "$confirm" != "y" ]; then
        echo "❌ 취소됨"
        exit 0
    fi
fi

# 프로젝트 디렉토리로 이동
cd /Users/wonny/Dev/aegis/v3

# 가상환경 활성화
source venv/bin/activate

echo ""
echo "============================================================"
echo "📊 시장 수급 데이터 수집 중..."
echo "============================================================"
echo ""
echo "수집 항목:"
echo "  1️⃣ 투자자별 순매수 (외국인/기관/개인) - KOSPI 100개"
echo "  2️⃣ 대차잔고 (전체 종목)"
echo ""
echo "⏱️  예상 소요시간: 5~10분"
echo ""

# 시장 수급 데이터 수집
python scripts/init_market_flow.py

exit_code=$?

echo ""
echo "============================================================"
if [ $exit_code -eq 0 ]; then
    echo "✅ 시장 수급 데이터 수집 완료!"
else
    echo "❌ 시장 수급 데이터 수집 실패 (에러 코드: $exit_code)"
    echo ""
    echo "💡 문제 해결:"
    echo "   1. 장 시간(09:00-15:30)에 다시 실행"
    echo "   2. 또는 장 마감 후 30분 내 실행"
    echo "   3. pykrx API가 일시적으로 불안정할 수 있음"
fi
echo "============================================================"
