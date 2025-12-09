"""
AEGIS v3.0 - Learning Models
AI 학습 및 피드백 루프를 위한 DB 모델
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, Text
from sqlalchemy.sql import func
from app.database import Base


class TrapPattern(Base):
    """
    함정 패턴 학습 테이블

    역할:
    - 각 함정 패턴의 가중치 저장
    - 정확도 추적 (맞춘 횟수 / 전체 횟수)
    - 시간에 따른 패턴 강화/약화
    """
    __tablename__ = "trap_patterns"

    id = Column(Integer, primary_key=True, index=True)
    trap_type = Column(String(50), unique=True, nullable=False, index=True)  # "fake_rise", "gap_overheat", etc.
    weight = Column(Float, nullable=False, default=0.80)  # 가중치 (0.0 ~ 1.0)
    total_count = Column(Integer, nullable=False, default=0)  # 전체 감지 횟수
    correct_count = Column(Integer, nullable=False, default=0)  # 정확히 맞춘 횟수
    accuracy = Column(Float, nullable=False, default=0.0)  # 정확도 (%)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class TradeFeedback(Base):
    """
    거래 피드백 테이블

    역할:
    - 함정 감지 → 매수 회피 → 실제 결과 기록
    - AI 학습 데이터 수집
    - 백테스트 검증
    """
    __tablename__ = "trade_feedback"

    id = Column(Integer, primary_key=True, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    stock_code = Column(String(10), nullable=False, index=True)
    stock_name = Column(String(100))

    # 감지 정보
    trap_detected = Column(Boolean, nullable=False, default=False)  # 함정 감지 여부
    trap_type = Column(String(50), index=True)  # "fake_rise", "gap_overheat", etc.
    trap_confidence = Column(Float)  # 감지 신뢰도 (0.0 ~ 1.0)
    trap_reason = Column(Text)  # 감지 이유

    # 결정 정보
    avoided_buy = Column(Boolean, nullable=False, default=False)  # 매수 회피 여부
    ai_recommendation = Column(String(20))  # "AVOID", "WAIT", "REDUCE_SIZE"

    # 실제 결과
    actual_result = Column(String(20), nullable=False)  # "CORRECT" | "WRONG"
    price_at_decision = Column(Integer)  # 결정 시점 가격
    price_after_1h = Column(Integer)  # 1시간 후 가격
    price_at_close = Column(Integer)  # 종가
    price_change_pct = Column(Float)  # 실제 가격 변화율 (%)

    # 학습 메타데이터
    learned = Column(Boolean, nullable=False, default=False)  # 학습 완료 여부
    weight_before = Column(Float)  # 학습 전 가중치
    weight_after = Column(Float)  # 학습 후 가중치

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
