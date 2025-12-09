"""
AEGIS v3.0 - Fundamental Analysis Engine
재무 분석 엔진

Metrics:
- Profitability: ROE, ROA, 영업이익률
- Financial Health: 부채비율, 유동비율, 당좌비율
- Valuation: PER, PBR, PSR, PCR
- Growth: 매출 성장률, 영업이익 성장률

Data: DART 재무 데이터 (2,587종목)
"""
import os
import sys
import logging
from datetime import datetime, date
from typing import Dict, List, Optional
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text

logger = logging.getLogger("FundamentalAnalyzer")


@dataclass
class FundamentalSignals:
    """재무 분석 시그널"""
    code: str
    name: str

    # Profitability
    roe: Optional[float]  # ROE (자기자본이익률)
    roa: Optional[float]  # ROA (총자산이익률)
    op_margin: Optional[float]  # 영업이익률
    net_margin: Optional[float]  # 순이익률

    # Financial Health
    debt_ratio: Optional[float]  # 부채비율
    current_ratio: Optional[float]  # 유동비율
    quick_ratio: Optional[float]  # 당좌비율

    # Valuation
    per: Optional[float]  # PER (주가수익비율)
    pbr: Optional[float]  # PBR (주가순자산비율)
    psr: Optional[float]  # PSR (주가매출액비율)
    pcr: Optional[float]  # PCR (주가현금흐름비율)

    # Market Data
    market_cap: Optional[int]  # 시가총액
    current_price: Optional[float]

    # Risk
    is_deficit: bool  # 적자 여부
    last_risk_report: Optional[str]  # 최근 리스크 공시

    # Signals
    profitability_signal: str  # EXCELLENT, GOOD, FAIR, POOR
    health_signal: str  # STRONG, STABLE, WEAK, DANGER
    valuation_signal: str  # UNDERVALUED, FAIR, OVERVALUED
    risk_level: str  # LOW, MEDIUM, HIGH

    # Overall
    score: float  # 0 ~ 100
    grade: str  # A+, A, B+, B, C, D, F


class FundamentalAnalyzer:
    """
    재무 분석 엔진

    DART 재무 데이터로:
    - 수익성 분석
    - 재무 건전성 분석
    - 밸류에이션 분석
    - 리스크 평가
    """

    def __init__(self):
        self.db = SessionLocal()
        logger.info("✅ FundamentalAnalyzer initialized")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def analyze(self, code: str) -> Optional[FundamentalSignals]:
        """
        종목 재무 분석

        Args:
            code: 종목코드

        Returns:
            FundamentalSignals or None
        """
        # Get stock data
        query = text("""
            SELECT
                code, name, market_cap, roe, debt_ratio, op_margin,
                is_deficit, last_risk_report
            FROM stocks
            WHERE code = :code
        """)

        result = self.db.execute(query, {'code': code}).fetchone()

        if not result:
            logger.warning(f"   ⚠️  {code}: 종목 정보 없음")
            return None

        # Get current price
        price_query = text("""
            SELECT close
            FROM daily_prices
            WHERE stock_code = :code
            ORDER BY date DESC
            LIMIT 1
        """)

        price_result = self.db.execute(price_query, {'code': code}).fetchone()
        current_price = float(price_result.close) if price_result else None

        # Calculate valuations
        per = self._calculate_per(code, current_price) if current_price else None
        pbr = self._calculate_pbr(code, current_price) if current_price else None
        psr = self._calculate_psr(code, current_price) if current_price else None

        # Generate signals
        profitability_signal = self._profitability_signal(
            roe=result.roe,
            op_margin=result.op_margin
        )

        health_signal = self._health_signal(
            debt_ratio=result.debt_ratio,
            is_deficit=result.is_deficit
        )

        valuation_signal = self._valuation_signal(per, pbr, psr)

        risk_level = self._risk_level(
            is_deficit=result.is_deficit,
            last_risk_report=result.last_risk_report,
            debt_ratio=result.debt_ratio
        )

        # Calculate overall score
        score = self._calculate_score(
            profitability_signal,
            health_signal,
            valuation_signal,
            risk_level
        )

        grade = self._calculate_grade(score)

        return FundamentalSignals(
            code=code,
            name=result.name,
            roe=float(result.roe) if result.roe is not None else None,
            roa=None,  # TODO: Calculate from financial data
            op_margin=float(result.op_margin) if result.op_margin is not None else None,
            net_margin=None,  # TODO
            debt_ratio=float(result.debt_ratio) if result.debt_ratio is not None else None,
            current_ratio=None,  # TODO
            quick_ratio=None,  # TODO
            per=per,
            pbr=pbr,
            psr=psr,
            pcr=None,  # TODO
            market_cap=result.market_cap,
            current_price=current_price,
            is_deficit=result.is_deficit,
            last_risk_report=result.last_risk_report,
            profitability_signal=profitability_signal,
            health_signal=health_signal,
            valuation_signal=valuation_signal,
            risk_level=risk_level,
            score=score,
            grade=grade
        )

    # ========================================
    # VALUATION CALCULATIONS
    # ========================================

    def _calculate_per(self, code: str, price: float) -> Optional[float]:
        """
        PER 계산

        PER = 현재가 / EPS
        """
        # TODO: Get EPS from financial data
        # For now, use ROE as proxy
        query = text("SELECT roe FROM stocks WHERE code = :code")
        result = self.db.execute(query, {'code': code}).fetchone()

        if result and result.roe:
            eps_proxy = price * (result.roe / 100)  # Simplified
            per = price / eps_proxy if eps_proxy > 0 else None
            return per

        return None

    def _calculate_pbr(self, code: str, price: float) -> Optional[float]:
        """
        PBR 계산

        PBR = 현재가 / BPS
        """
        # TODO: Get BPS from financial data
        # For now, return None
        return None

    def _calculate_psr(self, code: str, price: float) -> Optional[float]:
        """
        PSR 계산

        PSR = 시가총액 / 매출액
        """
        query = text("SELECT market_cap FROM stocks WHERE code = :code")
        result = self.db.execute(query, {'code': code}).fetchone()

        if result and result.market_cap:
            # TODO: Get actual sales from financial data
            # For now, return None
            return None

        return None

    # ========================================
    # SIGNAL GENERATION
    # ========================================

    def _profitability_signal(
        self,
        roe: Optional[float],
        op_margin: Optional[float]
    ) -> str:
        """수익성 시그널"""
        if roe is None or op_margin is None:
            return "UNKNOWN"

        if roe > 15 and op_margin > 10:
            return "EXCELLENT"
        elif roe > 10 and op_margin > 5:
            return "GOOD"
        elif roe > 5 and op_margin > 0:
            return "FAIR"
        else:
            return "POOR"

    def _health_signal(
        self,
        debt_ratio: Optional[float],
        is_deficit: bool
    ) -> str:
        """재무 건전성 시그널"""
        if is_deficit:
            return "DANGER"

        if debt_ratio is None:
            return "UNKNOWN"

        if debt_ratio < 100:
            return "STRONG"
        elif debt_ratio < 200:
            return "STABLE"
        elif debt_ratio < 300:
            return "WEAK"
        else:
            return "DANGER"

    def _valuation_signal(
        self,
        per: Optional[float],
        pbr: Optional[float],
        psr: Optional[float]
    ) -> str:
        """밸류에이션 시그널"""
        if per is None:
            return "UNKNOWN"

        if per < 10:
            return "UNDERVALUED"
        elif per < 20:
            return "FAIR"
        else:
            return "OVERVALUED"

    def _risk_level(
        self,
        is_deficit: bool,
        last_risk_report: Optional[str],
        debt_ratio: Optional[float]
    ) -> str:
        """리스크 레벨"""
        if is_deficit or last_risk_report:
            return "HIGH"

        if debt_ratio and debt_ratio > 300:
            return "HIGH"
        elif debt_ratio and debt_ratio > 200:
            return "MEDIUM"
        else:
            return "LOW"

    # ========================================
    # SCORING
    # ========================================

    def _calculate_score(
        self,
        profitability: str,
        health: str,
        valuation: str,
        risk: str
    ) -> float:
        """
        종합 점수 계산

        Returns:
            0 ~ 100
        """
        score = 0.0

        # Profitability (30점)
        profitability_scores = {
            "EXCELLENT": 30,
            "GOOD": 22,
            "FAIR": 15,
            "POOR": 5,
            "UNKNOWN": 10
        }
        score += profitability_scores.get(profitability, 10)

        # Health (30점)
        health_scores = {
            "STRONG": 30,
            "STABLE": 22,
            "WEAK": 12,
            "DANGER": 0,
            "UNKNOWN": 10
        }
        score += health_scores.get(health, 10)

        # Valuation (20점)
        valuation_scores = {
            "UNDERVALUED": 20,
            "FAIR": 15,
            "OVERVALUED": 5,
            "UNKNOWN": 10
        }
        score += valuation_scores.get(valuation, 10)

        # Risk penalty (최대 -20점)
        if risk == "HIGH":
            score -= 20
        elif risk == "MEDIUM":
            score -= 10

        return max(0, min(100, score))

    def _calculate_grade(self, score: float) -> str:
        """등급 계산"""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"


# ========================================
# MAIN
# ========================================

def main():
    """테스트"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    analyzer = FundamentalAnalyzer()

    # Test with 삼성전자
    signals = analyzer.analyze("005930")

    if signals:
        print("\n" + "=" * 60)
        print(f"📊 {signals.name} ({signals.code}) Fundamental Analysis")
        print("=" * 60)

        print(f"\n[Profitability]")
        print(f"  ROE: {signals.roe:.2f}%" if signals.roe else "  ROE: N/A")
        print(f"  Operating Margin: {signals.op_margin:.2f}%" if signals.op_margin else "  Operating Margin: N/A")
        print(f"  Signal: {signals.profitability_signal}")

        print(f"\n[Financial Health]")
        print(f"  Debt Ratio: {signals.debt_ratio:.2f}%" if signals.debt_ratio else "  Debt Ratio: N/A")
        print(f"  Is Deficit: {signals.is_deficit}")
        print(f"  Signal: {signals.health_signal}")

        print(f"\n[Valuation]")
        print(f"  Current Price: {signals.current_price:,.0f}" if signals.current_price else "  Current Price: N/A")
        print(f"  Market Cap: {signals.market_cap:,}" if signals.market_cap else "  Market Cap: N/A")
        print(f"  PER: {signals.per:.2f}" if signals.per else "  PER: N/A")
        print(f"  Signal: {signals.valuation_signal}")

        print(f"\n[Risk]")
        print(f"  Risk Level: {signals.risk_level}")
        print(f"  Last Risk Report: {signals.last_risk_report or 'None'}")

        print(f"\n[Overall]")
        print(f"  Score: {signals.score:.1f}/100")
        print(f"  Grade: {signals.grade}")
        print("=" * 60)


if __name__ == "__main__":
    main()
