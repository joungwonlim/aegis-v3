"""
AEGIS v3.0 - Portfolio Router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.account import Portfolio

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])


@router.get("/")
async def get_portfolio(db: Session = Depends(get_db)):
    """
    보유 종목 조회

    Returns:
        - 전체 보유 종목 리스트
        - 총 평가금액, 수익률 등
    """
    try:
        holdings = db.query(Portfolio).filter(Portfolio.quantity > 0).all()

        total_value = sum(h.current_price * h.quantity for h in holdings)
        total_cost = sum(h.avg_price * h.quantity for h in holdings)
        total_profit_rate = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

        return {
            "holdings": [
                {
                    "stock_code": h.stock_code,
                    "stock_name": h.stock_name,
                    "quantity": h.quantity,
                    "avg_price": h.avg_price,
                    "current_price": h.current_price,
                    "profit_rate": h.profit_rate,
                    "strategy_type": h.strategy_type,
                    "pyramid_stage": h.pyramid_stage,
                    "ai_action": h.ai_action
                }
                for h in holdings
            ],
            "summary": {
                "total_value": total_value,
                "total_cost": total_cost,
                "total_profit_rate": round(total_profit_rate, 2),
                "position_count": len(holdings)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{stock_code}")
async def get_position(stock_code: str, db: Session = Depends(get_db)):
    """
    개별 종목 포지션 조회

    Args:
        stock_code: 종목코드 (예: 005930)
    """
    position = db.query(Portfolio).filter(Portfolio.stock_code == stock_code).first()

    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    return {
        "stock_code": position.stock_code,
        "stock_name": position.stock_name,
        "quantity": position.quantity,
        "avg_price": position.avg_price,
        "current_price": position.current_price,
        "profit_rate": position.profit_rate,
        "bought_at": position.bought_at,
        "pyramid_stage": position.pyramid_stage,
        "pyramid_target": position.pyramid_target,
        "sell_stage": position.sell_stage,
        "stop_loss_price": position.stop_loss_price,
        "target_price": position.target_price,
        "ai_action": position.ai_action
    }
