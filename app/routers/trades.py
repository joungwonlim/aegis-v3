"""
AEGIS v3.0 - Trades Router
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime
from typing import Optional
from app.database import get_db
from app.models.trade import TradeLog

router = APIRouter(prefix="/api/trades", tags=["Trades"])


@router.get("/today")
async def get_today_trades(db: Session = Depends(get_db)):
    """
    오늘 거래 내역 조회

    Returns:
        - 오늘 매수/매도 내역
        - 실현 손익
    """
    today = date.today()

    trades = db.query(TradeLog).filter(
        func.date(TradeLog.executed_at) == today
    ).order_by(TradeLog.executed_at.desc()).all()

    buy_count = sum(1 for t in trades if t.trade_type == "BUY")
    sell_count = sum(1 for t in trades if t.trade_type == "SELL")
    realized_profit = sum(
        (t.sell_price - t.buy_price) * t.quantity
        for t in trades if t.trade_type == "SELL" and t.sell_price and t.buy_price
    )

    return {
        "date": today,
        "trades": [
            {
                "id": t.id,
                "stock_code": t.stock_code,
                "trade_type": t.trade_type,
                "price": t.sell_price if t.trade_type == "SELL" else t.buy_price,
                "quantity": t.quantity,
                "profit_rate": t.profit_rate,
                "reason": t.reason,
                "model_used": t.model_used,
                "executed_at": t.executed_at
            }
            for t in trades
        ],
        "summary": {
            "buy_count": buy_count,
            "sell_count": sell_count,
            "realized_profit": realized_profit,
            "total_trades": len(trades)
        }
    }


@router.get("/")
async def get_trades(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    stock_code: Optional[str] = None,
    trade_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """
    거래 내역 조회 (페이지네이션)

    Args:
        page: 페이지 번호 (1부터 시작)
        page_size: 페이지당 항목 수 (최대 100)
        stock_code: 종목코드 필터
        trade_type: 거래 유형 (BUY/SELL)
        start_date: 시작 날짜
        end_date: 종료 날짜
    """
    query = db.query(TradeLog)

    # 필터 적용
    if stock_code:
        query = query.filter(TradeLog.stock_code == stock_code)
    if trade_type:
        query = query.filter(TradeLog.trade_type == trade_type)
    if start_date:
        query = query.filter(func.date(TradeLog.executed_at) >= start_date)
    if end_date:
        query = query.filter(func.date(TradeLog.executed_at) <= end_date)

    # 총 개수
    total = query.count()

    # 페이지네이션
    offset = (page - 1) * page_size
    trades = query.order_by(TradeLog.executed_at.desc()).offset(offset).limit(page_size).all()

    return {
        "data": [
            {
                "id": t.id,
                "stock_code": t.stock_code,
                "trade_type": t.trade_type,
                "buy_price": t.buy_price,
                "sell_price": t.sell_price,
                "quantity": t.quantity,
                "profit_rate": t.profit_rate,
                "reason": t.reason,
                "strategy": t.strategy,
                "model_used": t.model_used,
                "executed_at": t.executed_at
            }
            for t in trades
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }


@router.get("/{trade_id}")
async def get_trade_detail(trade_id: int, db: Session = Depends(get_db)):
    """
    거래 상세 조회

    Args:
        trade_id: 거래 ID
    """
    trade = db.query(TradeLog).filter(TradeLog.id == trade_id).first()

    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    return {
        "id": trade.id,
        "stock_code": trade.stock_code,
        "trade_type": trade.trade_type,
        "buy_price": trade.buy_price,
        "sell_price": trade.sell_price,
        "quantity": trade.quantity,
        "profit_rate": trade.profit_rate,
        "reason": trade.reason,
        "strategy": trade.strategy,
        "ai_score": trade.ai_score,
        "decision_context": trade.decision_context,
        "pyramid_stage": trade.pyramid_stage,
        "market_regime": trade.market_regime,
        "confidence_score": trade.confidence_score,
        "model_used": trade.model_used,
        "executed_at": trade.executed_at
    }
