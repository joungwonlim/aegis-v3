"""
AEGIS v3.0 - Health Check Router
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    시스템 상태 체크

    - **db**: 데이터베이스 연결 상태
    - **ai_trading**: AI 자동매매 활성화 여부
    """
    try:
        # DB 연결 테스트
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "version": settings.app_version,
        "database": db_status,
        "ai_trading": settings.ai_trading_enabled
    }


@router.get("/ping")
async def ping():
    """간단한 핑 체크"""
    return {"message": "pong"}
