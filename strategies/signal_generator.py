"""
AEGIS v3.0 - Unified Signal Generator
통합 매매 시그널 생성 엔진

Input:
- AI Strategy (DeepSeek-R1 + Claude)
- Technical Analysis (RSI, MACD, Bollinger Bands, etc.)
- Fundamental Analysis (ROE, Debt Ratio, PER, etc.)

Output:
- BUY / SELL / HOLD signal
- Signal strength (0-100)
- Risk level
- Position size recommendation
"""
import os
import sys
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text
from strategies.ai_strategy_engine import AIStrategyEngine, StrategyDecision
from analyzers.technical_analyzer import TechnicalAnalyzer, TechnicalSignals
from analyzers.fundamental_analyzer import FundamentalAnalyzer, FundamentalSignals

logger = logging.getLogger("SignalGenerator")


@dataclass
class TradingSignal:
    """통합 매매 시그널"""
    code: str
    name: str

    # Signal
    signal: str  # BUY, SELL, HOLD
    strength: float  # 0-100 (신호 강도)
    confidence: float  # 0-100 (신뢰도)

    # Position
    position_size: float  # 0-1 (포트폴리오 비중)
    max_position: float  # 최대 허용 비중

    # Price
    current_price: float
    target_price: Optional[float]
    stop_loss: Optional[float]

    # Risk
    risk_level: str  # LOW, MEDIUM, HIGH
    risk_score: float  # 0-100

    # Components
    ai_signal: str
    ai_score: float
    technical_signal: str
    technical_score: float
    fundamental_signal: str
    fundamental_score: float

    # Reasoning
    ai_model: str  # AI 모델명 (deepseek-r1, deepseek-v3, claude)
    ai_reasoning: str  # AI 분석 근거
    reasoning: str
    warnings: List[str]

    # Metadata
    timestamp: datetime


class SignalGenerator:
    """
    통합 시그널 생성 엔진

    3가지 분석을 통합하여 최종 매매 시그널 생성:
    1. AI Strategy (50% weight) - 시장 전망, 리짐 감지
    2. Technical Analysis (30% weight) - 추세, 모멘텀, 변동성
    3. Fundamental Analysis (20% weight) - 재무 건전성, 밸류에이션
    """

    def __init__(self):
        self.db = SessionLocal()
        self.ai_engine = AIStrategyEngine()
        self.technical_analyzer = TechnicalAnalyzer()
        self.fundamental_analyzer = FundamentalAnalyzer()

        # Weights
        self.AI_WEIGHT = 0.50
        self.TECHNICAL_WEIGHT = 0.30
        self.FUNDAMENTAL_WEIGHT = 0.20

        logger.info("✅ SignalGenerator initialized")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def generate_signal(
        self,
        code: str,
        name: str,
        ai_decision: Optional[StrategyDecision] = None
    ) -> Optional[TradingSignal]:
        """
        종목에 대한 통합 매매 시그널 생성

        Args:
            code: 종목코드
            name: 종목명
            ai_decision: AI 전략 결정 (없으면 최신 것 사용)

        Returns:
            TradingSignal or None
        """
        logger.info(f"🎯 Generating signal for {name} ({code})")

        # 1. Get AI Strategy
        if ai_decision is None:
            ai_decision = self._get_latest_ai_decision()

        if ai_decision is None:
            logger.warning(f"   ⚠️  No AI strategy available")
            return None

        # 2. Technical Analysis
        technical = self.technical_analyzer.analyze(code, name)

        if technical is None:
            logger.warning(f"   ⚠️  Technical analysis failed")
            return None

        # 3. Fundamental Analysis
        fundamental = self.fundamental_analyzer.analyze(code)

        # 4. Calculate Scores
        ai_score = self._ai_score(ai_decision, code)
        technical_score = technical.score  # -100 ~ 100
        fundamental_score = fundamental.score if fundamental else 50.0  # 0 ~ 100

        # 5. Weighted Combined Score
        combined_score = self._combine_scores(
            ai_score,
            technical_score,
            fundamental_score
        )

        # 6. Generate Signal
        signal, strength = self._determine_signal(combined_score)

        # 7. Calculate Confidence
        confidence = self._calculate_confidence(
            ai_decision,
            technical,
            fundamental
        )

        # 8. Position Sizing
        position_size, max_position = self._calculate_position_size(
            signal,
            strength,
            confidence,
            ai_decision.cash_ratio
        )

        # 9. Price Targets
        current_price = technical.sma_20  # Use SMA as proxy
        target_price, stop_loss = self._calculate_price_targets(
            current_price,
            signal,
            technical
        )

        # 10. Risk Assessment
        risk_level, risk_score = self._assess_risk(
            ai_decision,
            technical,
            fundamental
        )

        # 11. Reasoning
        reasoning = self._build_reasoning(
            ai_decision,
            technical,
            fundamental,
            signal,
            combined_score
        )

        # 12. Warnings
        warnings = self._generate_warnings(
            ai_decision,
            technical,
            fundamental,
            risk_level
        )

        return TradingSignal(
            code=code,
            name=name,
            signal=signal,
            strength=strength,
            confidence=confidence,
            position_size=position_size,
            max_position=max_position,
            current_price=current_price,
            target_price=target_price,
            stop_loss=stop_loss,
            risk_level=risk_level,
            risk_score=risk_score,
            ai_signal=self._ai_signal_name(ai_decision, code),
            ai_score=ai_score,
            ai_model=ai_decision.model if ai_decision else "unknown",
            ai_reasoning=ai_decision.reasoning if ai_decision else "",
            technical_signal=technical.signal,
            technical_score=technical_score,
            fundamental_signal=fundamental.grade if fundamental else "N/A",
            fundamental_score=fundamental_score,
            reasoning=reasoning,
            warnings=warnings,
            timestamp=datetime.now()
        )

    def generate_signals_for_universe(
        self,
        stock_codes: List[str],
        ai_decision: Optional[StrategyDecision] = None
    ) -> List[TradingSignal]:
        """
        종목 유니버스에 대한 시그널 생성

        Args:
            stock_codes: 종목코드 리스트
            ai_decision: AI 전략 결정

        Returns:
            List of TradingSignal
        """
        signals = []

        for code in stock_codes:
            # Get stock name
            query = text("SELECT name FROM stocks WHERE code = :code")
            result = self.db.execute(query, {'code': code}).fetchone()

            if not result:
                continue

            name = result.name

            signal = self.generate_signal(code, name, ai_decision)

            if signal:
                signals.append(signal)

        # Sort by strength (descending)
        signals.sort(key=lambda x: x.strength, reverse=True)

        return signals

    # ========================================
    # SCORING
    # ========================================

    def _ai_score(self, ai_decision: StrategyDecision, code: str) -> float:
        """
        AI 전략 점수 계산

        Returns:
            -100 ~ 100
        """
        # Check if stock is in AI signals
        if not ai_decision.signals:
            return 0.0

        for signal in ai_decision.signals:
            if signal.get('code') == code:
                action = signal.get('action', 'HOLD')

                if action == 'BUY':
                    return 80.0
                elif action == 'SELL':
                    return -80.0
                else:
                    return 0.0

        # Not in signals - neutral
        return 0.0

    def _combine_scores(
        self,
        ai_score: float,
        technical_score: float,
        fundamental_score: float
    ) -> float:
        """
        가중 평균 점수 계산

        Returns:
            -100 ~ 100
        """
        # Normalize fundamental score to -100 ~ 100
        fundamental_normalized = (fundamental_score - 50) * 2

        combined = (
            ai_score * self.AI_WEIGHT +
            technical_score * self.TECHNICAL_WEIGHT +
            fundamental_normalized * self.FUNDAMENTAL_WEIGHT
        )

        return max(-100, min(100, combined))

    def _determine_signal(self, combined_score: float) -> Tuple[str, float]:
        """
        종합 점수로 시그널 결정

        Returns:
            (signal, strength)
        """
        if combined_score > 40:
            return "BUY", min(100, abs(combined_score))
        elif combined_score < -40:
            return "SELL", min(100, abs(combined_score))
        else:
            return "HOLD", abs(combined_score)

    def _calculate_confidence(
        self,
        ai_decision: StrategyDecision,
        technical: TechnicalSignals,
        fundamental: Optional[FundamentalSignals]
    ) -> float:
        """
        시그널 신뢰도 계산

        Returns:
            0-100
        """
        confidence = 50.0

        # AI + Technical agreement
        ai_bullish = ai_decision.market_view == "BULLISH"
        tech_bullish = technical.signal == "BUY"

        if ai_bullish and tech_bullish:
            confidence += 30
        elif ai_bullish or tech_bullish:
            confidence += 15

        # Fundamental quality
        if fundamental:
            if fundamental.grade in ["A+", "A"]:
                confidence += 20
            elif fundamental.grade in ["B+", "B"]:
                confidence += 10

        return min(100, confidence)

    def _calculate_position_size(
        self,
        signal: str,
        strength: float,
        confidence: float,
        cash_ratio: float
    ) -> Tuple[float, float]:
        """
        포지션 크기 계산

        Returns:
            (position_size, max_position)
        """
        if signal == "HOLD":
            return 0.0, 0.0

        # Base position (최대 10%)
        base_position = 0.10

        # Adjust by strength
        strength_factor = strength / 100.0

        # Adjust by confidence
        confidence_factor = confidence / 100.0

        # Adjust by cash ratio
        cash_factor = (100 - cash_ratio) / 100.0

        position_size = base_position * strength_factor * confidence_factor * cash_factor

        # Max position (최대 15%)
        max_position = 0.15

        return round(position_size, 4), max_position

    def _calculate_price_targets(
        self,
        current_price: float,
        signal: str,
        technical: TechnicalSignals
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        목표가 및 손절가 계산

        Returns:
            (target_price, stop_loss)
        """
        if signal == "BUY":
            # Target: +5% or Bollinger Upper
            target_price = max(
                current_price * 1.05,
                technical.bb_upper
            )

            # Stop loss: -3% or Bollinger Lower
            stop_loss = min(
                current_price * 0.97,
                technical.bb_lower
            )

            return round(target_price, 0), round(stop_loss, 0)

        elif signal == "SELL":
            # Already holding - set stop loss
            stop_loss = current_price * 0.97
            return None, round(stop_loss, 0)

        else:
            return None, None

    def _assess_risk(
        self,
        ai_decision: StrategyDecision,
        technical: TechnicalSignals,
        fundamental: Optional[FundamentalSignals]
    ) -> Tuple[str, float]:
        """
        리스크 평가

        Returns:
            (risk_level, risk_score)
        """
        risk_score = 0.0

        # AI risk
        if ai_decision.risk_level == "HIGH":
            risk_score += 40
        elif ai_decision.risk_level == "MEDIUM":
            risk_score += 20

        # Technical volatility
        if technical.volatility_signal == "HIGH":
            risk_score += 30
        elif technical.volatility_signal == "MEDIUM":
            risk_score += 15

        # Fundamental risk
        if fundamental:
            if fundamental.risk_level == "HIGH":
                risk_score += 30
            elif fundamental.risk_level == "MEDIUM":
                risk_score += 15

        # Determine level
        if risk_score > 60:
            risk_level = "HIGH"
        elif risk_score > 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return risk_level, min(100, risk_score)

    # ========================================
    # HELPERS
    # ========================================

    def _get_latest_ai_decision(self) -> Optional[StrategyDecision]:
        """최신 AI 전략 결정 조회"""
        query = text("""
            SELECT timestamp, model, market_view, regime, signals, cash_ratio, risk_level, reasoning, warnings
            FROM ai_strategy_log
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        result = self.db.execute(query).fetchone()

        if not result:
            return None

        return StrategyDecision(
            timestamp=result.timestamp.isoformat() if result.timestamp else datetime.now().isoformat(),
            model=result.model or "unknown",
            market_view=result.market_view,
            regime=result.regime,
            signals=result.signals or [],
            cash_ratio=float(result.cash_ratio) if result.cash_ratio else 30.0,
            risk_level=result.risk_level,
            reasoning=result.reasoning or "(From DB)",
            warnings=result.warnings or []
        )

    def _ai_signal_name(self, ai_decision: StrategyDecision, code: str) -> str:
        """AI 시그널 이름"""
        if not ai_decision.signals:
            return "NEUTRAL"

        for signal in ai_decision.signals:
            if signal.get('code') == code:
                return signal.get('action', 'HOLD')

        return "NEUTRAL"

    def _build_reasoning(
        self,
        ai_decision: StrategyDecision,
        technical: TechnicalSignals,
        fundamental: Optional[FundamentalSignals],
        signal: str,
        score: float
    ) -> str:
        """시그널 근거 작성"""
        reasoning = f"Signal: {signal} (Score: {score:.1f})\n\n"

        reasoning += f"AI: {ai_decision.market_view} regime, {ai_decision.regime}\n"
        reasoning += f"Technical: {technical.trend_signal} trend, RSI {technical.rsi_14:.1f}\n"

        if fundamental:
            reasoning += f"Fundamental: Grade {fundamental.grade}, ROE {fundamental.roe:.1f}%\n"

        return reasoning

    def _generate_warnings(
        self,
        ai_decision: StrategyDecision,
        technical: TechnicalSignals,
        fundamental: Optional[FundamentalSignals],
        risk_level: str
    ) -> List[str]:
        """경고 메시지 생성"""
        warnings = []

        if risk_level == "HIGH":
            warnings.append("⚠️ High risk level detected")

        if technical.rsi_14 > 70:
            warnings.append("⚠️ RSI overbought (>70)")
        elif technical.rsi_14 < 30:
            warnings.append("⚠️ RSI oversold (<30)")

        if technical.volatility_signal == "HIGH":
            warnings.append("⚠️ High volatility")

        if fundamental and fundamental.is_deficit:
            warnings.append("⚠️ Company in deficit")

        if ai_decision.risk_level == "HIGH":
            warnings.append("⚠️ AI detected high market risk")

        return warnings


# ========================================
# MAIN
# ========================================

def main():
    """테스트"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    generator = SignalGenerator()

    # Test with 삼성전자
    signal = generator.generate_signal("005930", "삼성전자")

    if signal:
        print("\n" + "=" * 70)
        print(f"🎯 {signal.name} ({signal.code}) Trading Signal")
        print("=" * 70)

        print(f"\n[SIGNAL]")
        print(f"  Action: {signal.signal}")
        print(f"  Strength: {signal.strength:.1f}/100")
        print(f"  Confidence: {signal.confidence:.1f}/100")

        print(f"\n[POSITION]")
        print(f"  Size: {signal.position_size*100:.2f}% (max {signal.max_position*100:.1f}%)")

        print(f"\n[PRICE]")
        print(f"  Current: {signal.current_price:,.0f}")
        if signal.target_price:
            print(f"  Target: {signal.target_price:,.0f} (+{(signal.target_price/signal.current_price-1)*100:.1f}%)")
        if signal.stop_loss:
            print(f"  Stop Loss: {signal.stop_loss:,.0f} ({(signal.stop_loss/signal.current_price-1)*100:.1f}%)")

        print(f"\n[RISK]")
        print(f"  Level: {signal.risk_level}")
        print(f"  Score: {signal.risk_score:.1f}/100")

        print(f"\n[COMPONENTS]")
        print(f"  AI: {signal.ai_signal} ({signal.ai_score:.1f}) - Model: {signal.ai_model}")
        print(f"  Technical: {signal.technical_signal} ({signal.technical_score:.1f})")
        print(f"  Fundamental: {signal.fundamental_signal} ({signal.fundamental_score:.1f})")

        print(f"\n[AI REASONING]")
        print(f"{signal.ai_reasoning[:300]}..." if len(signal.ai_reasoning) > 300 else signal.ai_reasoning)

        print(f"\n[REASONING]")
        print(f"{signal.reasoning}")

        if signal.warnings:
            print(f"\n[WARNINGS]")
            for warning in signal.warnings:
                print(f"  {warning}")

        print("=" * 70)


if __name__ == "__main__":
    main()
