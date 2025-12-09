"""
AEGIS v3.0 - Analytics Models (SCHEMA 6)
"""
from sqlalchemy import Column, String, Integer, Float, Date, DateTime
from sqlalchemy.sql import func
from app.database import Base


class BacktestResult(Base):
    """백테스트 결과"""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_name = Column(String(50), nullable=False)
    run_at = Column(DateTime(timezone=True), server_default=func.now())

    start_date = Column(Date, comment="테스트 시작일")
    end_date = Column(Date, comment="테스트 종료일")

    total_return = Column(Float, comment="총 수익률 (%)")
    mdd = Column(Float, comment="최대 낙폭 (%)")
    win_rate = Column(Float, comment="승률 (%)")
    avg_return = Column(Float, comment="평균 수익률 (%)")
    sharpe_ratio = Column(Float, comment="샤프 비율")
    profit_factor = Column(Float, comment="손익비")

    grade = Column(String(10), comment="S/A/B/C/F")
