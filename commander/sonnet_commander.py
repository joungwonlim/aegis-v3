"""
AEGIS v3.0 - Claude Sonnet 4.5 Commander
최종 의사결정 시스템

⚠️ 명심: Opus 대신 Sonnet 4.5 사용

Features:
- 실시간 모니터링 (3분 간격)
- 매수/매도 최종 결정
- 포트폴리오 리밸런싱
- 위험 감지 및 긴급 대응
- KIS API 주문 실행 명령
- 피드백 즉시 수신 및 반영
"""
import os
import sys
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text
import anthropic

logger = logging.getLogger("SonnetCommander")


# ═══════════════════════════════════════════════════════════════
#                    설정값
# ═══════════════════════════════════════════════════════════════

# 모니터링
MONITORING_INTERVAL = 180       # 3분 (초)
FEEDBACK_DELAY_MAX = 3          # 피드백 수신 최대 지연 (초)

# 자동 대응
AUTO_STOP_LOSS = -3.0           # 손절 라인 (%)
AUTO_TAKE_PROFIT = 2.5          # 익절 라인 (점수 < 50인 경우)
SCORE_DROP_THRESHOLD = 30       # 점수 급락 기준 (70 → 40)

# 블랙리스트
BLACKLIST_DURATION_HOURS = 24   # 재매수 금지 기간

# Circuit Breaker
CIRCUIT_BREAKER_CONSECUTIVE = 5 # 연속 손절 횟수
CIRCUIT_BREAKER_DAILY_LOSS = -3.0  # 일일 손실 한도 (%)


@dataclass
class SonnetContext:
    """매 의사결정 시 Sonnet 4.5가 참조하는 컨텍스트"""

    # 계좌 상태
    total_balance: int           # 총 평가금액
    available_cash: int          # 주문 가능 금액
    total_profit_pct: float      # 총 손익률
    today_profit_pct: float      # 오늘 손익률

    # 포트폴리오 현황
    holdings: List[Dict]         # 보유 종목 리스트
    holding_count: int           # 보유 종목 수

    # 오늘 거래 현황
    today_trades: int            # 오늘 거래 횟수
    today_wins: int              # 오늘 익절 횟수
    today_losses: int            # 오늘 손절 횟수

    # 연속 패턴
    consecutive_losses: int      # 연속 손절 횟수
    consecutive_wins: int        # 연속 익절 횟수

    # 현재 설정값
    current_min_score: int       # 현재 MIN_SCORE
    current_quant_weight: float = 0.57  # Quant 가중치

    # 시장 상황
    market_regime: str = "neutral"           # "bullish" | "neutral" | "bearish"
    kospi_change: float = 0.0          # KOSPI 등락률

    # 최근 피드백 요약
    recent_feedback: List[Dict] = field(default_factory=list)  # 최근 5건 거래 결과

    # 블랙리스트
    blacklisted_stocks: List[str] = field(default_factory=list)  # 재매수 금지 종목


@dataclass
class SonnetDecision:
    """Sonnet 4.5 의사결정 결과"""
    decision_id: str              # UUID
    timestamp: datetime           # 결정 시각
    decision_type: str            # "buy" | "sell" | "hold" | "rebalance"

    # 결정 내용
    target_stock: Optional[str]   # 대상 종목
    action: str                   # 실행 액션
    quantity: Optional[int]       # 수량
    reason: str                   # 결정 사유

    # AI 분석
    risk_assessment: str          # 리스크 평가
    confidence_level: float       # 확신도 (0~100)

    # 실행 결과
    executed: bool = False                # 실행 여부
    execution_result: Optional[Dict] = None  # 체결 결과


class SonnetCommander:
    """
    Claude Sonnet 4.5 Commander

    ⚠️ 중요: Opus 대신 Sonnet 4.5 사용!

    역할:
    1. 실시간 모니터링 (3분 간격)
    2. 매수/매도 최종 결정
    3. 포트폴리오 리밸런싱
    4. 위험 감지 및 긴급 대응
    5. 피드백 즉시 수신 및 반영
    """

    def __init__(self):
        self.db = SessionLocal()
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        if not self.anthropic_api_key:
            logger.warning("⚠️ ANTHROPIC_API_KEY not found - running in mock mode")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=self.anthropic_api_key)

        # Circuit Breaker 상태
        self.circuit_breaker_active = False

        logger.info("✅ SonnetCommander initialized (Claude Sonnet 4.5)")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def monitor_and_decide(self) -> List[SonnetDecision]:
        """
        실시간 모니터링 및 의사결정

        Returns:
            List of SonnetDecision
        """
        logger.info("🧠 Sonnet Commander monitoring...")

        # Build context
        context = self._build_context()

        # Check circuit breaker
        if self.circuit_breaker_active:
            logger.warning("🚨 Circuit Breaker ACTIVE - No new trades")
            return []

        # Get Sonnet 4.5 decision
        decisions = self._call_sonnet(context)

        # Log decisions
        for decision in decisions:
            self._log_decision(decision, context)

        return decisions

    def process_feedback(
        self,
        stock_code: str,
        return_pct: float,
        exit_reason: str
    ):
        """
        매도 피드백 즉시 수신

        Args:
            stock_code: 종목코드
            return_pct: 수익률
            exit_reason: 청산 사유
        """
        logger.info(f"📊 Feedback received: {stock_code} ({return_pct:+.2f}%)")

        # Update blacklist (손절 시 24시간 재매수 금지)
        if return_pct <= -2.0:
            self._add_to_blacklist(stock_code)

        # Check circuit breaker
        self._check_circuit_breaker()

    # ========================================
    # CONTEXT BUILDING
    # ========================================

    def _build_context(self) -> SonnetContext:
        """컨텍스트 생성"""
        # Get account status
        cash, total_value = self._get_account_status()

        # Get holdings
        holdings = self._get_holdings()

        # Get today's trades
        today_trades, today_wins, today_losses = self._get_today_trades()

        # Get consecutive patterns
        consecutive_losses, consecutive_wins = self._get_consecutive_patterns()

        # Get current settings
        min_score = self._get_current_min_score()

        # Get market status
        market_regime, kospi_change = self._get_market_status()

        # Get recent feedback
        recent_feedback = self._get_recent_feedback()

        # Get blacklist
        blacklisted_stocks = self._get_blacklist()

        # Calculate metrics
        total_profit_pct = 0.0  # TODO: Calculate from holdings
        today_profit_pct = 0.0  # TODO: Calculate from today's trades

        return SonnetContext(
            total_balance=int(total_value),
            available_cash=int(cash),
            total_profit_pct=total_profit_pct,
            today_profit_pct=today_profit_pct,
            holdings=holdings,
            holding_count=len(holdings),
            today_trades=today_trades,
            today_wins=today_wins,
            today_losses=today_losses,
            consecutive_losses=consecutive_losses,
            consecutive_wins=consecutive_wins,
            current_min_score=min_score,
            market_regime=market_regime,
            kospi_change=kospi_change,
            recent_feedback=recent_feedback,
            blacklisted_stocks=blacklisted_stocks
        )

    def _get_account_status(self) -> Tuple[float, float]:
        """계좌 상태 조회"""
        query = text("SELECT cash, total_value FROM portfolio_summary LIMIT 1")
        result = self.db.execute(query).fetchone()

        if result:
            return float(result.cash), float(result.total_value or result.cash)
        else:
            return 0.0, 0.0

    def _get_holdings(self) -> List[Dict]:
        """보유 종목 조회"""
        query = text("""
            SELECT
                s.code,
                s.name,
                sa.quantity,
                sa.avg_price,
                dp.close as current_price
            FROM stock_assets sa
            JOIN stocks s ON sa.stock_code = s.code
            LEFT JOIN LATERAL (
                SELECT close FROM daily_prices
                WHERE stock_code = sa.stock_code
                ORDER BY date DESC LIMIT 1
            ) dp ON true
            WHERE sa.quantity > 0
        """)

        results = self.db.execute(query).fetchall()

        holdings = []
        for r in results:
            holdings.append({
                'code': r.code,
                'name': r.name,
                'quantity': r.quantity,
                'avg_price': float(r.avg_price),
                'current_price': float(r.current_price) if r.current_price else float(r.avg_price),
                'profit_pct': ((float(r.current_price or r.avg_price) - float(r.avg_price)) / float(r.avg_price) * 100)
            })

        return holdings

    def _get_today_trades(self) -> Tuple[int, int, int]:
        """오늘 거래 현황"""
        today = date.today()

        query = text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN result_category = 'SUCCESS' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result_category = 'FAILURE' THEN 1 ELSE 0 END) as losses
            FROM trade_feedback
            WHERE DATE(created_at) = :today
        """)

        result = self.db.execute(query, {'today': today}).fetchone()

        if result:
            return result.total or 0, result.wins or 0, result.losses or 0
        else:
            return 0, 0, 0

    def _get_consecutive_patterns(self) -> Tuple[int, int]:
        """연속 패턴 조회"""
        query = text("""
            SELECT result_category
            FROM trade_feedback
            ORDER BY created_at DESC
            LIMIT 10
        """)

        results = self.db.execute(query).fetchall()

        # Count consecutive losses
        consecutive_losses = 0
        for r in results:
            if r.result_category == "FAILURE":
                consecutive_losses += 1
            else:
                break

        # Count consecutive wins
        consecutive_wins = 0
        for r in results:
            if r.result_category == "SUCCESS":
                consecutive_wins += 1
            else:
                break

        return consecutive_losses, consecutive_wins

    def _get_current_min_score(self) -> int:
        """현재 MIN_SCORE 조회"""
        query = text("""
            SELECT new_min_score
            FROM score_adjustment_history
            ORDER BY adjustment_date DESC
            LIMIT 1
        """)

        result = self.db.execute(query).fetchone()

        return result.new_min_score if result else 70

    def _get_market_status(self) -> Tuple[str, float]:
        """시장 상황 조회"""
        query = text("""
            SELECT close, change_rate
            FROM daily_prices
            WHERE stock_code = '001'
            ORDER BY date DESC
            LIMIT 1
        """)

        result = self.db.execute(query).fetchone()

        if not result:
            return "neutral", 0.0

        kospi_change = float(result.change_rate or 0)

        # Determine regime
        if kospi_change > 1.0:
            regime = "bullish"
        elif kospi_change < -1.0:
            regime = "bearish"
        else:
            regime = "neutral"

        return regime, kospi_change

    def _get_recent_feedback(self) -> List[Dict]:
        """최근 피드백 조회 (5건)"""
        query = text("""
            SELECT stock_code, return_pct, result_category, result_detail
            FROM trade_feedback
            ORDER BY created_at DESC
            LIMIT 5
        """)

        results = self.db.execute(query).fetchall()

        feedback = []
        for r in results:
            feedback.append({
                'stock_code': r.stock_code,
                'return_pct': float(r.return_pct),
                'category': r.result_category,
                'detail': r.result_detail
            })

        return feedback

    def _get_blacklist(self) -> List[str]:
        """블랙리스트 조회 (24시간 재매수 금지)"""
        cutoff = datetime.now() - timedelta(hours=BLACKLIST_DURATION_HOURS)

        query = text("""
            SELECT DISTINCT stock_code
            FROM trade_feedback
            WHERE result_category = 'FAILURE'
              AND created_at >= :cutoff
        """)

        results = self.db.execute(query, {'cutoff': cutoff}).fetchall()

        return [r.stock_code for r in results]

    # ========================================
    # SONNET 4.5 DECISION
    # ========================================

    def _call_sonnet(self, context: SonnetContext) -> List[SonnetDecision]:
        """
        Claude Sonnet 4.5 호출하여 의사결정

        ⚠️ 중요: Opus 대신 Sonnet 4.5 사용!
        """
        if not self.client:
            logger.warning("Mock mode - returning empty decisions")
            return []

        prompt = self._build_decision_prompt(context)

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",  # ⚠️ Sonnet 4.5 모델!
                max_tokens=4096,
                temperature=0.3,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response = message.content[0].text

            # Parse response
            decisions = self._parse_sonnet_response(response)

            logger.info(f"   Sonnet returned {len(decisions)} decisions")

            return decisions

        except Exception as e:
            logger.error(f"Sonnet call failed: {e}")
            return []

    def _build_decision_prompt(self, context: SonnetContext) -> str:
        """Sonnet 4.5 프롬프트 생성"""
        # Holdings summary
        holdings_text = ""
        for h in context.holdings[:5]:
            holdings_text += f"- {h['name']}: {h['quantity']}주 ({h['profit_pct']:+.2f}%)\n"

        # Recent feedback summary
        feedback_text = ""
        for f in context.recent_feedback:
            feedback_text += f"- {f['stock_code']}: {f['return_pct']:+.2f}% ({f['category']})\n"

        # Blacklist
        blacklist_text = ", ".join(context.blacklisted_stocks) if context.blacklisted_stocks else "없음"

        return f"""
[AEGIS Commander - 의사결정 요청]

⚠️ 당신은 Claude Sonnet 4.5 Commander입니다.

현재 상황:
- 계좌 잔고: {context.total_balance:,}원
- 가용 현금: {context.available_cash:,}원
- 오늘 손익: {context.today_profit_pct:+.2f}%
- 보유 종목: {context.holding_count}개
- 오늘 거래: {context.today_trades}회 (익절 {context.today_wins}, 손절 {context.today_losses})
- 연속 손절: {context.consecutive_losses}회

보유 종목:
{holdings_text}

최근 피드백:
{feedback_text}

현재 설정:
- MIN_SCORE: {context.current_min_score}
- Quant 가중치: {context.current_quant_weight}

시장 상황:
- Regime: {context.market_regime}
- KOSPI: {context.kospi_change:+.2f}%

블랙리스트 (24시간 재매수 금지):
{blacklist_text}

위 상황을 종합하여 다음을 결정해주세요:

1. 보유 종목 중 매도할 종목 (손절/익절 조건 충족 시)
2. 리밸런싱 필요 여부
3. 설정 조정 필요 여부

JSON 형식으로 응답:
{{
  "decisions": [
    {{
      "action": "sell",
      "stock_code": "005930",
      "reason": "손절 조건 도달 (-3.2%)",
      "confidence": 95
    }}
  ],
  "overall_assessment": "시장 분석 및 전략..."
}}
"""

    def _parse_sonnet_response(self, response: str) -> List[SonnetDecision]:
        """Sonnet 응답 파싱"""
        import json

        try:
            # Extract JSON
            start = response.find('{')
            end = response.rfind('}') + 1

            if start < 0 or end <= start:
                return []

            json_str = response[start:end]
            data = json.loads(json_str)

            decisions = []

            for d in data.get('decisions', []):
                decision = SonnetDecision(
                    decision_id=str(uuid.uuid4()),
                    timestamp=datetime.now(),
                    decision_type=d.get('action', 'hold'),
                    target_stock=d.get('stock_code'),
                    action=d.get('action', 'hold'),
                    quantity=d.get('quantity'),
                    reason=d.get('reason', ''),
                    risk_assessment=data.get('overall_assessment', ''),
                    confidence_level=float(d.get('confidence', 50))
                )

                decisions.append(decision)

            return decisions

        except Exception as e:
            logger.error(f"Failed to parse Sonnet response: {e}")
            return []

    # ========================================
    # BLACKLIST & CIRCUIT BREAKER
    # ========================================

    def _add_to_blacklist(self, stock_code: str):
        """블랙리스트 추가"""
        logger.warning(f"⚠️ Adding {stock_code} to blacklist for {BLACKLIST_DURATION_HOURS}h")

    def _check_circuit_breaker(self):
        """Circuit Breaker 체크"""
        consecutive_losses, _ = self._get_consecutive_patterns()

        if consecutive_losses >= CIRCUIT_BREAKER_CONSECUTIVE:
            self.circuit_breaker_active = True
            logger.critical(f"🚨 Circuit Breaker ACTIVATED - {consecutive_losses} consecutive losses!")

    # ========================================
    # LOGGING
    # ========================================

    def _log_decision(self, decision: SonnetDecision, context: SonnetContext):
        """의사결정 로그 저장"""
        query = text("""
            INSERT INTO sonnet_decision_log
            (id, timestamp, decision_type, context_json, target_stock,
             action, quantity, reason, risk_assessment, confidence_level, executed)
            VALUES
            (:id, :timestamp, :type, :context, :stock, :action, :quantity,
             :reason, :risk, :confidence, :executed)
        """)

        self.db.execute(query, {
            'id': decision.decision_id,
            'timestamp': decision.timestamp,
            'type': decision.decision_type,
            'context': str(context.__dict__),  # Simplified
            'stock': decision.target_stock,
            'action': decision.action,
            'quantity': decision.quantity,
            'reason': decision.reason,
            'risk': decision.risk_assessment,
            'confidence': decision.confidence_level,
            'executed': decision.executed
        })
        self.db.commit()


# ========================================
# MAIN
# ========================================

def main():
    """테스트"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    commander = SonnetCommander()

    # Test monitoring
    decisions = commander.monitor_and_decide()

    print("\n" + "=" * 70)
    print("🧠 Sonnet Commander Decisions")
    print("=" * 70)

    if decisions:
        for d in decisions:
            print(f"\n[{d.decision_type.upper()}]")
            print(f"  Stock: {d.target_stock}")
            print(f"  Action: {d.action}")
            print(f"  Reason: {d.reason}")
            print(f"  Confidence: {d.confidence_level:.1f}%")
    else:
        print("\nNo decisions (Mock mode or no actions needed)")

    print("=" * 70)


if __name__ == "__main__":
    main()
