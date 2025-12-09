"""
AEGIS v3.0 - System Models (SCHEMA 5)
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base


class SystemConfig(Base):
    """시스템 설정"""
    __tablename__ = "system_config"

    key = Column(String(100), primary_key=True)
    value = Column(String(255), nullable=False)
    description = Column(Text)

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class FetcherHealthLog(Base):
    """Fetcher 상태"""
    __tablename__ = "fetcher_health_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fetcher_name = Column(String(50), nullable=False, index=True)

    status = Column(String(20), comment="OK/ERROR/SKIP")
    records_count = Column(Integer, comment="수집된 레코드 수")
    last_run = Column(DateTime(timezone=True), comment="마지막 실행 시간")
    message = Column(Text, comment="에러 메시지")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class StrategyState(Base):
    """전략 가중치"""
    __tablename__ = "strategy_states"

    strategy_name = Column(String(50), primary_key=True)

    current_weight = Column(Float, default=1.0, comment="현재 가중치 (0.5~1.5)")
    win_streak = Column(Integer, default=0, comment="연속 성공 횟수")
    loss_streak = Column(Integer, default=0, comment="연속 실패 횟수")
    is_active = Column(Boolean, default=True, comment="활성화 여부")

    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
