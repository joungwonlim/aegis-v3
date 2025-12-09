"""
AEGIS v3.0 - Trade Models (SCHEMA 4)
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, Text, JSON, BigInteger
from sqlalchemy.sql import func
from app.database import Base


class TradeOrder(Base):
    """주문 내역 (실시간 추적)"""
    __tablename__ = "trade_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(20), unique=True, nullable=False, index=True, comment="주문번호")
    stock_code = Column(String(20), nullable=False, index=True, comment="종목코드")
    stock_name = Column(String(100), comment="종목명")

    order_type = Column(String(10), nullable=False, comment="BUY/SELL")
    market = Column(String(10), default="KRX", comment="KRX/NXT")
    order_qty = Column(Integer, nullable=False, comment="주문 수량")
    order_price = Column(Integer, nullable=False, comment="주문 가격")

    status = Column(String(20), default="PENDING", comment="PENDING/FILLED/PARTIALLY_FILLED/CANCELLED")
    filled_qty = Column(Integer, default=0, comment="체결 수량")
    avg_filled_price = Column(Float, default=0, comment="평균 체결가")

    ordered_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    executed_at = Column(DateTime(timezone=True), comment="체결 완료 시각")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TradeExecution(Base):
    """체결 내역 (개별 체결)"""
    __tablename__ = "trade_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_no = Column(String(20), nullable=False, index=True, comment="주문번호")
    stock_code = Column(String(20), nullable=False, index=True, comment="종목코드")

    exec_qty = Column(Integer, nullable=False, comment="체결 수량")
    exec_price = Column(Integer, nullable=False, comment="체결 가격")
    exec_amount = Column(BigInteger, comment="체결 금액")

    executed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TradeLog(Base):
    """매매 기록 (통합)"""
    __tablename__ = "trade_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_code = Column(String(20), nullable=False, index=True)
    trade_type = Column(String(10), comment="BUY/SELL")

    buy_price = Column(Float, comment="매수가 (원)")
    sell_price = Column(Float, comment="매도가 (원)")
    quantity = Column(Integer, comment="수량 (주)")
    profit_rate = Column(Float, comment="수익률 (%)")

    reason = Column(Text, comment="AI 매수/매도 이유")
    strategy = Column(String(50), comment="매매 전략")
    ai_score = Column(Integer, comment="매수 시점 AI 점수 (0~100)")
    decision_context = Column(JSON, comment="AI 판단 컨텍스트")

    pyramid_stage = Column(Integer, comment="피라미딩 단계 (0~3)")
    market_regime = Column(String(20), comment="시장 국면")
    confidence_score = Column(Float, comment="AI 확신도 (0~100)")

    # v3.0 필수
    model_used = Column(String(50), comment="사용된 AI 모델 (opus/sonnet/deepseek)")

    executed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class TradeFeedback(Base):
    """매매 피드백"""
    __tablename__ = "trade_feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_log_id = Column(Integer, nullable=False, index=True)
    stock_code = Column(String(20), nullable=False)

    is_success = Column(String(10), comment="수익 여부")
    actual_profit_rate = Column(Float, comment="실제 수익률 (%)")
    holding_days = Column(Integer, comment="보유 기간 (일)")

    buy_reason_valid = Column(String(20), comment="매수 이유 유효성")
    sell_timing_score = Column(Integer, comment="매도 타이밍 점수 (1~10)")

    market_condition_at_buy = Column(String(50), comment="매수 시점 시장 상황")
    market_condition_at_sell = Column(String(50), comment="매도 시점 시장 상황")

    lessons_learned = Column(Text, comment="배운 점")
    improvement_suggestions = Column(Text, comment="개선 제안")

    optimal_sell_price = Column(Float, comment="최적 매도가 (원)")
    missed_profit_rate = Column(Float, comment="놓친 수익률 (%)")
    risk_reward_ratio = Column(Float, comment="리스크/리워드 비율")

    ai_analysis = Column(JSON, comment="AI 거래 피드백")

    # v3.0 필수
    feedback_applied = Column(Integer, comment="점수 보정값 (+3, -2 등)")

    analyzed_at = Column(DateTime(timezone=True), server_default=func.now())
