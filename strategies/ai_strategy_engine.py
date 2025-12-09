"""
AEGIS v3.0 - AI Strategy Engine
AI 매매 전략 엔진 (Claude + DeepSeek 통합)

역할:
1. DeepSeek-R1: 깊은 분석 (장 시작 전 1일 1회)
2. DeepSeek-V3: 빠른 판단 (장 중 실시간)
3. Claude Sonnet: 검증 및 리스크 체크

데이터 소스:
- 3년 일별 데이터 (1,893,659건)
- 재무 데이터 (2,587종목)
- 글로벌 48개 지표
- 시장 수급 데이터
- 테마/뉴스
"""
import os
import sys
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from dataclasses import dataclass, asdict

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text
import anthropic
import requests

logger = logging.getLogger("AIStrategyEngine")


# ========================================
# DATA MODELS
# ========================================

@dataclass
class MarketContext:
    """시장 컨텍스트"""
    date: str
    kospi: float
    kospi_change: float
    vix: float
    dollar_index: float
    foreign_futures_net: Optional[int]
    foreign_net_total: Optional[int]
    program_net: Optional[int]
    nasdaq: float
    sp500: float
    regime: str  # IRON_SHIELD, VANGUARD, GUERRILLA, STEALTH


@dataclass
class StockSignal:
    """종목 매매 시그널"""
    code: str
    name: str
    action: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 ~ 1.0
    reasoning: str
    target_price: Optional[float]
    stop_loss: Optional[float]
    position_size: Optional[float]  # 포지션 비중 (%)
    priority: int  # 1(highest) ~ 5(lowest)


@dataclass
class StrategyDecision:
    """AI 전략 결정"""
    timestamp: str
    model: str  # deepseek-r1, deepseek-v3, claude
    market_view: str  # BULLISH, BEARISH, NEUTRAL
    regime: str
    signals: List[StockSignal]
    cash_ratio: float  # 현금 비중
    risk_level: str  # LOW, MEDIUM, HIGH
    reasoning: str
    warnings: List[str]


# ========================================
# AI STRATEGY ENGINE
# ========================================

class AIStrategyEngine:
    """
    AI 매매 전략 엔진

    Strategy:
    1. Morning Deep Analysis (DeepSeek-R1)
       - 전날 데이터 심층 분석
       - 오늘의 전략 수립
       - 관심 종목 선정

    2. Intraday Analysis (DeepSeek-V3)
       - 실시간 시장 변화 감지
       - 빠른 매매 판단
       - 포지션 조정

    3. Risk Verification (Claude Sonnet)
       - AI 결정 검증
       - 리스크 평가
       - 최종 승인/거부
    """

    def __init__(self):
        self.db = SessionLocal()

        # API Keys
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        if not self.deepseek_api_key:
            logger.warning("⚠️  DEEPSEEK_API_KEY not found")

        if not self.anthropic_api_key:
            logger.warning("⚠️  ANTHROPIC_API_KEY not found")

        # Claude client
        if self.anthropic_api_key:
            self.claude = anthropic.Anthropic(api_key=self.anthropic_api_key)

        logger.info("✅ AIStrategyEngine initialized")

    def __del__(self):
        """세션 종료"""
        if hasattr(self, 'db'):
            self.db.close()

    # ========================================
    # DATA COLLECTION
    # ========================================

    def get_market_context(self, target_date: Optional[date] = None) -> MarketContext:
        """
        시장 컨텍스트 조회

        Args:
            target_date: 조회 날짜 (None이면 최근 거래일)

        Returns:
            MarketContext
        """
        if target_date is None:
            target_date = date.today()

        # KOSPI 지수
        kospi_query = text("""
            SELECT close, change_rate
            FROM daily_prices
            WHERE stock_code = '001' AND date <= :date
            ORDER BY date DESC
            LIMIT 1
        """)
        kospi_result = self.db.execute(kospi_query, {'date': target_date}).fetchone()

        # 글로벌 매크로
        macro_query = text("""
            SELECT vix, dollar_index, nasdaq, sp500
            FROM market_macro
            WHERE date <= :date
            ORDER BY date DESC
            LIMIT 1
        """)
        macro_result = self.db.execute(macro_query, {'date': target_date}).fetchone()

        # KIS 시장 데이터
        kis_query = text("""
            SELECT foreign_futures_net, program_net
            FROM market_flow
            WHERE date <= :date
            ORDER BY date DESC
            LIMIT 1
        """)
        kis_result = self.db.execute(kis_query, {'date': target_date}).fetchone()

        # 외국인 순매수 합계
        foreign_query = text("""
            SELECT SUM(foreign_net) as total
            FROM investor_net_buying
            WHERE date = :date
        """)
        foreign_result = self.db.execute(foreign_query, {'date': target_date}).fetchone()

        # Market regime detection (simple version)
        regime = self._detect_market_regime(
            vix=macro_result.vix if macro_result else 15.0,
            kospi_change=kospi_result.change_rate if kospi_result else 0.0,
            foreign_net=foreign_result.total if foreign_result else 0
        )

        return MarketContext(
            date=target_date.strftime("%Y-%m-%d"),
            kospi=float(kospi_result.close) if kospi_result else 2500.0,
            kospi_change=float(kospi_result.change_rate) if kospi_result else 0.0,
            vix=float(macro_result.vix) if macro_result and macro_result.vix is not None else 15.0,
            dollar_index=float(macro_result.dollar_index) if macro_result and macro_result.dollar_index is not None else 104.0,
            foreign_futures_net=kis_result.foreign_futures_net if kis_result else None,
            foreign_net_total=int(foreign_result.total) if foreign_result and foreign_result.total is not None else None,
            program_net=kis_result.program_net if kis_result else None,
            nasdaq=float(macro_result.nasdaq) if macro_result and macro_result.nasdaq is not None else 15000.0,
            sp500=float(macro_result.sp500) if macro_result and macro_result.sp500 is not None else 4500.0,
            regime=regime
        )

    def _detect_market_regime(self, vix: float, kospi_change: float, foreign_net: int) -> str:
        """
        시장 regime 감지

        Regimes:
        - IRON_SHIELD: 방어 (VIX 높음)
        - VANGUARD: 공격 (상승장 + 외국인 유입)
        - GUERRILLA: 기회 포착 (변동성 중간)
        - STEALTH: 현금 대기 (악재)
        """
        if vix > 25:
            return "IRON_SHIELD"  # 방어

        if kospi_change > 1.0 and foreign_net > 0:
            return "VANGUARD"  # 공격

        if kospi_change < -2.0:
            return "STEALTH"  # 현금 대기

        return "GUERRILLA"  # 기회 포착

    def get_top_stocks_by_momentum(self, limit: int = 50) -> List[Dict]:
        """
        모멘텀 상위 종목 조회

        Returns:
            List of {code, name, momentum_score, volume_score}
        """
        query = text("""
            WITH recent_performance AS (
                SELECT
                    stock_code,
                    AVG(change_rate) as avg_change,
                    AVG(volume) as avg_volume,
                    STDDEV(change_rate) as volatility
                FROM daily_prices
                WHERE date >= CURRENT_DATE - INTERVAL '20 days'
                GROUP BY stock_code
            )
            SELECT
                s.code,
                s.name,
                rp.avg_change * 100 as momentum_score,
                rp.avg_volume / 1000000.0 as volume_score,
                rp.volatility as volatility
            FROM stocks s
            JOIN recent_performance rp ON s.code = rp.stock_code
            WHERE s.market IN ('KOSPI', 'KOSDAQ')
              AND rp.avg_change > 0
              AND rp.avg_volume > 100000
            ORDER BY rp.avg_change DESC
            LIMIT :limit
        """)

        results = self.db.execute(query, {'limit': limit}).fetchall()

        return [
            {
                'code': r.code,
                'name': r.name,
                'momentum_score': float(r.momentum_score) if r.momentum_score is not None else 0.0,
                'volume_score': float(r.volume_score) if r.volume_score is not None else 0.0,
                'volatility': float(r.volatility) if r.volatility is not None else 0.0
            }
            for r in results
        ]

    # ========================================
    # DEEP ANALYSIS (DeepSeek-R1)
    # ========================================

    def morning_deep_analysis(self) -> StrategyDecision:
        """
        장 시작 전 심층 분석 (DeepSeek-R1)

        Process:
        1. 시장 컨텍스트 수집
        2. 모멘텀 종목 선정
        3. DeepSeek-R1로 전략 수립
        4. Claude로 검증

        Returns:
            StrategyDecision
        """
        logger.info("=" * 60)
        logger.info("🧠 Morning Deep Analysis (DeepSeek-R1)")
        logger.info("=" * 60)

        # 1. 데이터 수집
        market = self.get_market_context()
        top_stocks = self.get_top_stocks_by_momentum(limit=30)

        # 2. DeepSeek-R1 분석
        prompt = self._build_deep_analysis_prompt(market, top_stocks)

        logger.info("   📊 Calling DeepSeek-R1...")
        deepseek_response = self._call_deepseek_r1(prompt)

        # 3. Parse response
        decision = self._parse_strategy_response(
            deepseek_response,
            model="deepseek-r1",
            market=market
        )

        # 4. Claude verification
        logger.info("   ✅ Verifying with Claude...")
        verified_decision = self._claude_verify(decision, market)

        return verified_decision

    def _build_deep_analysis_prompt(self, market: MarketContext, stocks: List[Dict]) -> str:
        """DeepSeek-R1용 심층 분석 프롬프트"""
        return f"""
당신은 한국 주식 시장의 전문 퀀트 트레이더입니다.

# 시장 상황
- 날짜: {market.date}
- KOSPI: {market.kospi:.2f} ({market.kospi_change:+.2f}%)
- VIX: {market.vix:.2f}
- 달러 인덱스: {market.dollar_index:.2f}
- Nasdaq: {market.nasdaq:.2f}
- S&P 500: {market.sp500:.2f}
- 외국인 선물: {market.foreign_futures_net} 계약
- 외국인 순매수: {market.foreign_net_total} 원
- 프로그램 순매수: {market.program_net} 원
- Market Regime: {market.regime}

# 모멘텀 상위 종목 (20일 기준)
{self._format_stocks_table(stocks[:10])}

# 분석 요청
1. 시장 전망 (BULLISH/BEARISH/NEUTRAL)
2. 매수 추천 종목 (최대 5개)
   - 종목코드, 종목명
   - 매수 근거
   - 목표가 및 손절가
   - 포지션 비중 (%)
3. 현금 비중 추천
4. 리스크 요인

JSON 형식으로 답변:
{{
  "market_view": "BULLISH|BEARISH|NEUTRAL",
  "signals": [
    {{
      "code": "종목코드",
      "name": "종목명",
      "action": "BUY",
      "confidence": 0.8,
      "reasoning": "매수 근거",
      "target_price": 50000,
      "stop_loss": 45000,
      "position_size": 10,
      "priority": 1
    }}
  ],
  "cash_ratio": 30,
  "risk_level": "MEDIUM",
  "reasoning": "전체 전략 설명",
  "warnings": ["리스크 요인1", "리스크 요인2"]
}}
"""

    def _format_stocks_table(self, stocks: List[Dict]) -> str:
        """종목 리스트 테이블 포맷"""
        lines = ["| 코드 | 종목명 | 모멘텀 | 거래량 | 변동성 |", "|------|--------|--------|--------|--------|"]
        for s in stocks:
            lines.append(
                f"| {s['code']} | {s['name']} | {s['momentum_score']:.2f}% | "
                f"{s['volume_score']:.1f}M | {s['volatility']:.2f}% |"
            )
        return "\n".join(lines)

    def _call_deepseek_r1(self, prompt: str) -> str:
        """
        DeepSeek-R1 API 호출

        TODO: DeepSeek API 엔드포인트 확인 필요
        """
        if not self.deepseek_api_key:
            logger.warning("   ⚠️  DEEPSEEK_API_KEY not set, using mock response")
            return self._mock_deepseek_response()

        try:
            # DeepSeek API 호출 (예시)
            # headers = {
            #     "Authorization": f"Bearer {self.deepseek_api_key}",
            #     "Content-Type": "application/json"
            # }
            # data = {
            #     "model": "deepseek-r1",
            #     "messages": [{"role": "user", "content": prompt}],
            #     "temperature": 0.7
            # }
            # response = requests.post(
            #     "https://api.deepseek.com/v1/chat/completions",
            #     headers=headers,
            #     json=data
            # )
            # return response.json()["choices"][0]["message"]["content"]

            # Mock response for now
            return self._mock_deepseek_response()

        except Exception as e:
            logger.error(f"   ❌ DeepSeek API error: {e}")
            return self._mock_deepseek_response()

    def _mock_deepseek_response(self) -> str:
        """Mock DeepSeek response for testing"""
        return json.dumps({
            "market_view": "NEUTRAL",
            "signals": [
                {
                    "code": "005930",
                    "name": "삼성전자",
                    "action": "BUY",
                    "confidence": 0.75,
                    "reasoning": "반도체 업황 개선 전망, 외국인 순매수 지속",
                    "target_price": 75000,
                    "stop_loss": 68000,
                    "position_size": 15,
                    "priority": 1
                }
            ],
            "cash_ratio": 40,
            "risk_level": "MEDIUM",
            "reasoning": "시장이 중립적이므로 보수적 접근. 우량주 중심 매수",
            "warnings": ["VIX 상승 주의", "달러 강세 리스크"]
        })

    def _parse_strategy_response(
        self,
        response: str,
        model: str,
        market: MarketContext
    ) -> StrategyDecision:
        """AI 응답 파싱"""
        try:
            data = json.loads(response)

            signals = [
                StockSignal(**signal_data)
                for signal_data in data.get("signals", [])
            ]

            return StrategyDecision(
                timestamp=datetime.now().isoformat(),
                model=model,
                market_view=data["market_view"],
                regime=market.regime,
                signals=signals,
                cash_ratio=data["cash_ratio"],
                risk_level=data["risk_level"],
                reasoning=data["reasoning"],
                warnings=data.get("warnings", [])
            )

        except Exception as e:
            logger.error(f"   ❌ Failed to parse response: {e}")
            # Return safe default
            return StrategyDecision(
                timestamp=datetime.now().isoformat(),
                model=model,
                market_view="NEUTRAL",
                regime=market.regime,
                signals=[],
                cash_ratio=100.0,
                risk_level="HIGH",
                reasoning=f"Parse error: {e}",
                warnings=["Failed to parse AI response"]
            )

    def _claude_verify(
        self,
        decision: StrategyDecision,
        market: MarketContext
    ) -> StrategyDecision:
        """
        Claude로 전략 검증

        Returns:
            Verified StrategyDecision (수정 가능)
        """
        if not self.anthropic_api_key:
            logger.warning("   ⚠️  Claude API key not set, skipping verification")
            return decision

        try:
            prompt = f"""
당신은 리스크 관리 전문가입니다. 아래 AI 매매 전략을 검증하세요.

# 시장 상황
- Regime: {market.regime}
- KOSPI: {market.kospi} ({market.kospi_change:+.2f}%)
- VIX: {market.vix}

# AI 전략
{json.dumps(asdict(decision), indent=2, ensure_ascii=False)}

# 검증 항목
1. 포지션 비중이 과도하지 않은가?
2. 리스크가 적절히 관리되는가?
3. 시장 상황과 전략이 일치하는가?

검증 결과를 JSON으로:
{{
  "approved": true/false,
  "modified_cash_ratio": 40,
  "filtered_signals": ["필터링된 종목코드"],
  "additional_warnings": ["추가 경고"]
}}
"""

            message = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            verification = json.loads(message.content[0].text)

            # Apply verification results
            if not verification["approved"]:
                logger.warning("   ⚠️  Claude rejected strategy")
                decision.warnings.append("Strategy rejected by Claude verification")

            if verification.get("modified_cash_ratio"):
                decision.cash_ratio = verification["modified_cash_ratio"]

            if verification.get("filtered_signals"):
                decision.signals = [
                    s for s in decision.signals
                    if s.code not in verification["filtered_signals"]
                ]

            decision.warnings.extend(verification.get("additional_warnings", []))

            logger.info("   ✅ Claude verification complete")
            return decision

        except Exception as e:
            logger.error(f"   ❌ Claude verification failed: {e}")
            decision.warnings.append(f"Claude verification error: {e}")
            return decision

    # ========================================
    # INTRADAY ANALYSIS (DeepSeek-V3)
    # ========================================

    def intraday_analysis(self) -> StrategyDecision:
        """
        장 중 실시간 분석 (DeepSeek-V3)

        빠른 판단이 필요한 경우:
        - 급격한 시장 변화
        - 포지션 조정
        - 손절/익절 판단

        Returns:
            StrategyDecision
        """
        logger.info("⚡ Intraday Analysis (DeepSeek-V3)")

        # TODO: Implement DeepSeek-V3 integration
        # For now, return simple decision

        market = self.get_market_context()

        return StrategyDecision(
            timestamp=datetime.now().isoformat(),
            model="deepseek-v3",
            market_view="NEUTRAL",
            regime=market.regime,
            signals=[],
            cash_ratio=50.0,
            risk_level="MEDIUM",
            reasoning="Intraday analysis not yet implemented",
            warnings=[]
        )

    # ========================================
    # UTILITIES
    # ========================================

    def save_decision(self, decision: StrategyDecision) -> None:
        """전략 결정 DB 저장"""
        try:
            query = text("""
                INSERT INTO ai_strategy_log
                (timestamp, model, market_view, regime, signals, cash_ratio, risk_level, reasoning, warnings)
                VALUES
                (:timestamp, :model, :market_view, :regime, :signals, :cash_ratio, :risk_level, :reasoning, :warnings)
            """)

            self.db.execute(query, {
                'timestamp': decision.timestamp,
                'model': decision.model,
                'market_view': decision.market_view,
                'regime': decision.regime,
                'signals': json.dumps([asdict(s) for s in decision.signals], ensure_ascii=False),
                'cash_ratio': decision.cash_ratio,
                'risk_level': decision.risk_level,
                'reasoning': decision.reasoning,
                'warnings': json.dumps(decision.warnings, ensure_ascii=False)
            })

            self.db.commit()
            logger.info("   💾 Strategy decision saved to DB")

        except Exception as e:
            logger.error(f"   ❌ Failed to save decision: {e}")
            self.db.rollback()


# ========================================
# MAIN
# ========================================

def main():
    """메인 함수"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    engine = AIStrategyEngine()

    # Morning deep analysis
    decision = engine.morning_deep_analysis()

    print("\n" + "=" * 60)
    print("📊 AI Strategy Decision")
    print("=" * 60)
    print(f"Model: {decision.model}")
    print(f"Market View: {decision.market_view}")
    print(f"Regime: {decision.regime}")
    print(f"Cash Ratio: {decision.cash_ratio}%")
    print(f"Risk Level: {decision.risk_level}")
    print(f"\nSignals: {len(decision.signals)}")
    for signal in decision.signals:
        print(f"  - {signal.name} ({signal.code}): {signal.action} "
              f"({signal.confidence:.0%} confidence, {signal.position_size}% position)")
    print(f"\nReasoning: {decision.reasoning}")
    if decision.warnings:
        print(f"\n⚠️  Warnings:")
        for w in decision.warnings:
            print(f"  - {w}")
    print("=" * 60)

    # Save to DB
    engine.save_decision(decision)


if __name__ == "__main__":
    main()
