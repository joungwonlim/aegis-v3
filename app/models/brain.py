"""
AEGIS v3.0 - Brain Models (SCHEMA 3)
"""
from sqlalchemy import Column, String, Integer, Float, Date, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base


class DailyPick(Base):
    """일일 추천 종목"""
    __tablename__ = "daily_picks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    stock_code = Column(String(20), nullable=False)

    strategy_name = Column(String(50), comment="선정 전략")
    rank = Column(Integer, comment="우선순위 (1이 최우선)")

    quant_score = Column(Integer, comment="Quant 점수 (0~100)")
    ai_score = Column(Integer, comment="AI 점수 (0~100)")
    expected_entry_price = Column(Float, comment="예상 진입가 (원)")

    ai_comment = Column(Text, comment="AI 코멘트")
    is_executed = Column(Boolean, default=False, comment="실제 매수 여부")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DailyAnalysisLog(Base):
    """분석 파이프라인 로그"""
    __tablename__ = "daily_analysis_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    stock_code = Column(String(20), nullable=False)

    step_1_quant_score = Column(Integer, comment="1단계: Quant 점수")
    step_2_ai_score = Column(Integer, comment="2단계: AI 점수")
    step_3_risk_check = Column(String(20), comment="3단계: APPROVE/REJECT")

    final_score = Column(Integer, comment="최종 점수 (0~100)")
    final_decision = Column(String(20), comment="BUY/HOLD/WAIT")
    risk_analysis = Column(Text, comment="AI 리스크 분석")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IntelFeed(Base):
    """뉴스/공시 분석"""
    __tablename__ = "intel_feed"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    source = Column(String(20), comment="DART/NAVER/GOOGLE")
    category = Column(String(50), comment="공시유형/뉴스카테고리")
    title = Column(Text)
    stock_code = Column(String(20))

    sentiment_score = Column(Integer, comment="감성 점수 (-100~100)")
    impact_level = Column(String(20), comment="HIGH/MEDIUM/LOW")
    ai_summary = Column(Text, comment="AI 요약")


class MarketRegime(Base):
    """시장 국면"""
    __tablename__ = "market_regime"

    check_time = Column(DateTime(timezone=True), primary_key=True)

    mode = Column(String(20), comment="IRON_SHIELD/VANGUARD/NORMAL")
    vix_level = Column(Float, comment="VIX 수치")
    trend_direction = Column(String(10), comment="UP/DOWN/SIDEWAYS")
