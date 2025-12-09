"""
AEGIS v3.0 - Analysis Router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.database import get_db
from app.models.brain import DailyPick

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.get("/picks")
async def get_daily_picks(target_date: date = None, db: Session = Depends(get_db)):
    """
    AI 추천 종목 조회

    Args:
        target_date: 조회 날짜 (기본값: 오늘)

    Returns:
        - AI가 추천한 종목 리스트
        - Quant 점수, AI 점수, 최종 점수
    """
    if not target_date:
        target_date = date.today()

    picks = db.query(DailyPick).filter(
        DailyPick.date == target_date
    ).order_by(DailyPick.rank).all()

    return {
        "date": target_date,
        "picks": [
            {
                "rank": p.rank,
                "stock_code": p.stock_code,
                "strategy_name": p.strategy_name,
                "quant_score": p.quant_score,
                "ai_score": p.ai_score,
                "expected_entry_price": p.expected_entry_price,
                "ai_comment": p.ai_comment,
                "is_executed": p.is_executed
            }
            for p in picks
        ],
        "total_picks": len(picks)
    }


@router.get("/stock/{stock_code}")
async def analyze_stock(stock_code: str, db: Session = Depends(get_db)):
    """
    종목 분석 (실시간)

    Args:
        stock_code: 종목코드

    Note:
        실제 구현 시 Brain 모듈 호출
    """
    # TODO: Brain 모듈과 연동
    return {
        "stock_code": stock_code,
        "message": "실시간 분석 기능은 Brain 모듈 구현 후 활성화됩니다",
        "quant_score": 0,
        "ai_score": 0,
        "final_score": 0,
        "recommendation": "WAIT"
    }


@router.post("/execute")
async def execute_analysis():
    """
    AI 분석 수동 실행

    Note:
        스케줄러가 자동으로 실행하지만, 수동 트리거도 가능
    """
    # TODO: Brain 분석 파이프라인 실행
    return {
        "message": "Analysis started",
        "status": "pending"
    }
