"""
AEGIS v3.0 - Market Data Models (SCHEMA 1)
"""
from sqlalchemy import Column, String, Integer, Float, Date, DateTime, BigInteger, Boolean
from sqlalchemy.sql import func
from app.database import Base


class Stock(Base):
    """종목 마스터"""
    __tablename__ = "stocks"

    code = Column(String(20), primary_key=True, comment="종목코드")
    name = Column(String(100), nullable=False, comment="종목명")
    market = Column(String(10), comment="KOSPI/KOSDAQ")
    sector = Column(String(100), comment="업종")
    market_cap = Column(BigInteger, comment="시가총액 (원)")
    is_kosdaq150 = Column(Boolean, default=False, comment="코스닥150 편입")
    theme_tags = Column(String(255), comment="AI 테마 태그")
    overhang_ratio = Column(Float, comment="CB/BW 희석 비율 (0~1)")
    is_active = Column(Boolean, default=True, comment="거래 가능")

    # 재무 펀더멘털 데이터 (DART API)
    debt_ratio = Column(Float, comment="부채비율 (%)")
    roe = Column(Float, comment="자기자본이익률 ROE (%)")
    op_margin = Column(Float, comment="영업이익률 (%)")
    is_deficit = Column(Boolean, default=False, comment="영업적자 여부")

    # 리스크 데이터
    last_risk_report = Column(String(255), comment="최근 악재 공시 제목")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DailyPrice(Base):
    """일별 시세 + 수급"""
    __tablename__ = "daily_prices"

    stock_code = Column(String(20), primary_key=True)
    date = Column(Date, primary_key=True)

    # OHLCV
    open = Column(Integer, comment="시가 (원)")
    high = Column(Integer, comment="고가 (원)")
    low = Column(Integer, comment="저가 (원)")
    close = Column(Integer, comment="종가 (원)")
    volume = Column(BigInteger, comment="거래량 (주)")
    change_rate = Column(Float, comment="등락률 (%)")

    # 수급 데이터 (주 단위!)
    foreigner_net_buy = Column(BigInteger, comment="외국인 순매수 (주)")
    institution_net_buy = Column(BigInteger, comment="기관계 순매수 (주)")
    pension_net_buy = Column(BigInteger, comment="연기금 순매수 (주)")
    financial_invest_net = Column(BigInteger, comment="금융투자 순매수 (주)")
    insurance_net_buy = Column(BigInteger, comment="보험 순매수 (주)")
    trust_net_buy = Column(BigInteger, comment="투신 순매수 (주)")
    program_net_buy = Column(BigInteger, comment="프로그램 순매수 (주)")
    corporate_net_buy = Column(BigInteger, comment="기타법인 순매수 (주)")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MarketCandle(Base):
    """분봉 데이터 (TimescaleDB Hypertable)"""
    __tablename__ = "market_candles"

    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), primary_key=True)
    interval = Column(String(5), primary_key=True, comment="1m, 5m, 15m, 1h, 1d")

    open = Column(Float, comment="시가 (원)")
    high = Column(Float, comment="고가 (원)")
    low = Column(Float, comment="저가 (원)")
    close = Column(Float, comment="종가 (원)")
    volume = Column(BigInteger, comment="거래량 (주)")


class MarketMacro(Base):
    """매크로 지표"""
    __tablename__ = "market_macro"

    date = Column(Date, primary_key=True)

    us_krw = Column(Float, comment="환율 (원/달러)")
    nasdaq = Column(Float, comment="나스닥 종합")
    sox = Column(Float, comment="필라델피아 반도체")
    vix = Column(Float, comment="VIX 공포지수")
    fear_greed = Column(Integer, comment="CNN Fear & Greed (0~100)")

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FinancialStatement(Base):
    """재무제표 데이터 (DART API)"""
    __tablename__ = "financial_statements"

    stock_code = Column(String(20), primary_key=True)
    quarter = Column(String(10), primary_key=True, comment="2024Q3")

    # 손익계산서
    revenue = Column(BigInteger, comment="매출액 (원)")
    operating_profit = Column(BigInteger, comment="영업이익 (원)")
    net_income = Column(BigInteger, comment="당기순이익 (원)")

    # 재무상태표
    total_assets = Column(BigInteger, comment="총자산 (원)")
    total_liabilities = Column(BigInteger, comment="총부채 (원)")
    total_equity = Column(BigInteger, comment="총자본 (원)")

    # 비율 지표
    debt_ratio = Column(Float, comment="부채비율 (%)")
    roe = Column(Float, comment="ROE (%)")
    roa = Column(Float, comment="ROA (%)")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Disclosure(Base):
    """공시 정보 (DART API)"""
    __tablename__ = "disclosures"

    rcept_no = Column(String(20), primary_key=True, comment="접수번호")
    stock_code = Column(String(20), index=True)

    corp_name = Column(String(100), comment="회사명")
    report_nm = Column(String(255), comment="보고서명")
    rcept_dt = Column(Date, comment="접수일자")
    flr_nm = Column(String(100), comment="공시제출인명")

    # 분류
    category = Column(String(50), comment="공시 카테고리")
    importance = Column(String(10), comment="중요도 (high/medium/low)")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
