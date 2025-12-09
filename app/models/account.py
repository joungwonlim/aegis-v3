"""
AEGIS v3.0 - Account Models (SCHEMA 2)
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, BigInteger
from sqlalchemy.sql import func
from app.database import Base


class AccountSnapshot(Base):
    """계좌 히스토리"""
    __tablename__ = "account_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    deposit = Column(BigInteger, comment="예수금 (원)")
    total_asset = Column(BigInteger, comment="총 평가금액 (원)")
    net_profit_today = Column(BigInteger, comment="당일 실현손익 (원)")
    total_return_rate = Column(Float, comment="총 수익률 (%)")


class Portfolio(Base):
    """보유 종목"""
    __tablename__ = "portfolio"

    stock_code = Column(String(20), primary_key=True)
    stock_name = Column(String(100))

    # 기본 정보
    quantity = Column(Integer, comment="보유 수량 (주)")
    avg_price = Column(Float, comment="평균 매입가 (원)")
    current_price = Column(Float, comment="현재가 (원)")
    profit_rate = Column(Float, comment="수익률 (%)")
    bought_at = Column(DateTime(timezone=True), comment="최초 매수 시점")

    # 피라미딩
    pyramid_stage = Column(Integer, default=0, comment="피라미딩 단계 (0~3)")
    pyramid_target = Column(Float, comment="다음 피라미딩 목표가 (원)")
    max_price_reached = Column(Float, comment="보유 중 최고가 (원)")

    # 분할매도
    sell_stage = Column(Integer, default=0, comment="분할매도 단계 (0~2)")

    # AI 판단
    strategy_type = Column(String(50), comment="전략 유형")
    ai_action = Column(String(20), comment="AI 조언 (HOLD/SELL)")
    stop_loss_price = Column(Float, comment="손절가 (원)")
    target_price = Column(Float, comment="목표가 (원)")

    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
