"""
AEGIS v3.0 - Automated Trading Scheduler
자동 매매 스케줄러

Flow:
1. Python 실무자: 데이터 수집 및 분석 (Quant + DeepSeek)
2. Sonnet 지휘관: 최종 결재 (BUY/WAIT/SELL)
3. Python 실행자: KIS API 주문 전송
4. Feedback 루프: 결과 피드백 → 다음 결정에 반영

Schedule:
- 09:00 - Pre-market analysis
- 09:05 - Market open monitoring
- Every 3 minutes - Real-time monitoring & decisions
- 15:30 - Day end summary
"""
import os
import sys
import logging
import time
from datetime import datetime, date
from typing import List, Dict, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.signal_generator import SignalGenerator
from risk.risk_manager import RiskManager
from feedback.feedback_engine import FeedbackEngine
from commander.sonnet_commander import SonnetCommander, SonnetContext
from app.database import SessionLocal
from sqlalchemy import text

logger = logging.getLogger("AutoTrader")


class AutoTrader:
    """
    자동 매매 시스템

    역할 분담:
    - Python (실무자): 데이터 수집, Quant 점수 계산, DeepSeek 검증
    - Sonnet (지휘관): 최종 결재 (BUY/WAIT/SELL)
    - Python (실행자): 주문 전송 및 체결 확인
    - Feedback Engine: 매도 후 즉시 피드백 → 다음 결정 반영
    """

    def __init__(self):
        self.db = SessionLocal()

        # Components
        self.signal_generator = SignalGenerator()
        self.risk_manager = RiskManager()
        self.feedback_engine = FeedbackEngine()
        self.commander = SonnetCommander()

        # State
        self.trading_enabled = True
        self.today_trades = 0
        self.max_daily_trades = 20

        logger.info("✅ AutoTrader initialized")
        logger.info("   Python 실무자: SignalGenerator")
        logger.info("   Sonnet 지휘관: SonnetCommander")
        logger.info("   실행자: KIS API (TODO)")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def run_cycle(self):
        """
        3분 주기 실행 사이클

        1. [Python 실무자] 현황 보고서 작성
        2. [Sonnet 지휘관] 최종 결재
        3. [Python 실행자] 주문 전송
        4. [Feedback] 결과 피드백
        """
        cycle_start = datetime.now()

        logger.info("=" * 70)
        logger.info(f"🔄 Trading Cycle Start: {cycle_start.strftime('%H:%M:%S')}")
        logger.info("=" * 70)

        # Check circuit breaker
        consecutive_losses = self.feedback_engine.check_consecutive_losses()
        if consecutive_losses and consecutive_losses >= 5:
            logger.error("🚨 CIRCUIT BREAKER ACTIVE - Trading halted")
            return

        # ========================================
        # Phase 1: Python 실무자 - 보고서 작성
        # ========================================
        logger.info("\n[Phase 1] 📊 Python 실무자 - 데이터 분석 및 보고서 작성")

        # Build context for Sonnet
        context = self._build_context()

        logger.info(f"   Portfolio: ₩{context.total_balance:,}")
        logger.info(f"   Cash: ₩{context.available_cash:,}")
        logger.info(f"   Today P&L: {context.today_profit_pct:+.2f}%")
        logger.info(f"   Consecutive Losses: {context.consecutive_losses}")
        logger.info(f"   Current MIN_SCORE: {context.current_min_score}")

        # ========================================
        # Phase 2: Sonnet 지휘관 - 최종 결재
        # ========================================
        logger.info("\n[Phase 2] 🧠 Sonnet 지휘관 - 최종 결재")

        decisions = self.commander.monitor_and_decide()

        if not decisions:
            logger.info("   결재 결과: 관망 (No actions needed)")
            return

        logger.info(f"   결재 승인: {len(decisions)}건")

        # ========================================
        # Phase 3: Python 실행자 - 주문 전송
        # ========================================
        logger.info("\n[Phase 3] 🚀 Python 실행자 - 주문 전송")

        for decision in decisions:
            logger.info(f"\n   종목: {decision.target_stock}")
            logger.info(f"   지시: {decision.action}")
            logger.info(f"   수량: {decision.quantity or 0}")
            logger.info(f"   사유: {decision.reason}")
            logger.info(f"   신뢰도: {decision.confidence_level:.0f}%")

            # Execute order
            success = self._execute_order(decision)

            if success:
                logger.info(f"   ✅ 주문 성공")
                self.today_trades += 1

                # Log to DB
                self._log_decision(decision, executed=True)
            else:
                logger.error(f"   ❌ 주문 실패")
                self._log_decision(decision, executed=False)

        # ========================================
        # Phase 4: Feedback 처리
        # ========================================
        logger.info("\n[Phase 4] 📈 Feedback 처리")

        # Check for exits (stop-loss, take-profit)
        position_risks, warnings = self.risk_manager.check_positions()

        for pos in position_risks:
            if pos.action in ["STOP_LOSS", "TAKE_PROFIT"]:
                logger.info(f"   청산 발생: {pos.name} ({pos.action})")

                # Process feedback
                try:
                    feedback = self.feedback_engine.process_trade_exit(
                        stock_code=pos.code,
                        buy_date=date.today(),  # TODO: Get actual buy date
                        sell_date=date.today(),
                        buy_price=pos.avg_price,
                        sell_price=pos.current_price,
                        exit_reason=pos.action,
                        buy_scores={'quant': 70, 'deepseek': 70, 'final': 70}  # TODO: Get actual scores
                    )

                    logger.info(f"   피드백 완료: {feedback.result_category}")
                    logger.info(f"   조정 MIN_SCORE: {self.feedback_engine.current_min_score}")

                except Exception as e:
                    logger.error(f"   피드백 실패: {e}")

        cycle_end = datetime.now()
        duration = (cycle_end - cycle_start).total_seconds()

        logger.info("\n" + "=" * 70)
        logger.info(f"✅ Cycle Complete ({duration:.1f}s)")
        logger.info(f"   Today Trades: {self.today_trades}/{self.max_daily_trades}")
        logger.info("=" * 70)

    def _build_context(self) -> SonnetContext:
        """현재 상황을 Sonnet에게 보고할 컨텍스트 구성"""

        # Get portfolio summary
        portfolio_query = text("SELECT cash, total_value FROM portfolio_summary LIMIT 1")
        portfolio = self.db.execute(portfolio_query).fetchone()

        cash = float(portfolio.cash) if portfolio else 5000000
        total_value = float(portfolio.total_value) if portfolio else 10000000

        # Get holdings
        holdings_query = text("""
            SELECT
                sa.stock_code,
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

        holdings_rows = self.db.execute(holdings_query).fetchall()
        holdings = [
            {
                'code': r.stock_code,
                'name': r.name,
                'quantity': r.quantity,
                'avg_price': float(r.avg_price),
                'current_price': float(r.current_price) if r.current_price else float(r.avg_price),
                'profit_pct': ((float(r.current_price) - float(r.avg_price)) / float(r.avg_price) * 100) if r.current_price else 0
            }
            for r in holdings_rows
        ]

        # Get today's stats
        today_trades = self.today_trades

        # Calculate today P&L (simplified)
        today_profit_pct = sum(h['profit_pct'] * h['quantity'] * h['avg_price'] for h in holdings) / total_value if total_value > 0 else 0

        # Get consecutive stats
        consecutive_losses = self.feedback_engine.check_consecutive_losses() or 0
        consecutive_wins = self.feedback_engine.check_consecutive_wins() or 0

        # Get blacklist (TODO: Implement in FeedbackEngine)
        blacklist = []

        # Get KOSPI change (simplified)
        kospi_query = text("""
            SELECT change_rate
            FROM daily_prices
            WHERE stock_code = '005930'
            ORDER BY date DESC LIMIT 1
        """)
        kospi_result = self.db.execute(kospi_query).fetchone()
        kospi_change = float(kospi_result.change_rate) if kospi_result else 0.0

        return SonnetContext(
            total_balance=int(total_value),
            available_cash=int(cash),
            total_profit_pct=((total_value - 10000000) / 10000000 * 100) if total_value > 0 else 0,
            today_profit_pct=today_profit_pct,
            holdings=holdings,
            holding_count=len(holdings),
            today_trades=today_trades,
            today_wins=0,  # TODO: Calculate from today's closed positions
            today_losses=0,
            consecutive_losses=consecutive_losses,
            consecutive_wins=consecutive_wins,
            current_min_score=self.feedback_engine.current_min_score,
            market_regime="NORMAL",  # TODO: Get from AI strategy
            kospi_change=kospi_change,
            recent_feedback=[],  # TODO: Get recent feedback
            blacklisted_stocks=blacklist
        )

    def _execute_order(self, decision) -> bool:
        """
        주문 실행 (현재는 Mock)

        TODO: KIS API 연동
        - kis.send_order(code, action, qty, price)
        """
        logger.info(f"   [Mock] Order sent: {decision.action} {decision.target_stock}")
        return True

    def _save_order_to_db(self, stock_code: str, action: str, quantity: int, 
                          price: float, order_number: str):
        """주문을 trade_orders 테이블에 저장"""
        try:
            order_query = text("""
                INSERT INTO trade_orders (
                    stock_code, action, quantity, price, 
                    order_number, created_at
                ) VALUES (
                    :stock_code, :action, :quantity, :price,
                    :order_number, :created_at
                )
            """)

            self.db.execute(order_query, {
                'stock_code': stock_code,
                'action': action,
                'quantity': quantity,
                'price': price,
                'order_number': order_number,
                'created_at': datetime.now()
            })
            self.db.commit()

            logger.debug(f"   💾 주문 DB 저장 완료: {order_number}")

        except Exception as e:
            logger.error(f"   ❌ 주문 DB 저장 실패: {e}")
            self.db.rollback()

    def _log_decision(self, decision, executed: bool):
        """결정 로그 저장"""
        try:
            log_query = text("""
                INSERT INTO sonnet_decision_log (
                    timestamp, decision_type, context_json,
                    target_stock, action, quantity, reason,
                    confidence_level, executed
                ) VALUES (
                    :timestamp, :decision_type, :context_json::jsonb,
                    :target_stock, :action, :quantity, :reason,
                    :confidence, :executed
                )
            """)

            self.db.execute(log_query, {
                'timestamp': datetime.now(),
                'decision_type': 'TRADE',
                'context_json': '{}',  # TODO: Add full context
                'target_stock': decision.target_stock,
                'action': decision.action,
                'quantity': decision.quantity,
                'reason': decision.reason,
                'confidence': decision.confidence_level,
                'executed': executed
            })
            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to log decision: {e}")


# ========================================
# MAIN
# ========================================

def main():
    """메인 실행"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    trader = AutoTrader()

    print("\n" + "=" * 70)
    print("🤖 AEGIS v3.0 - Automated Trading System")
    print("=" * 70)
    print("\n역할 분담:")
    print("  📊 Python 실무자: 데이터 수집, Quant 분석, DeepSeek 검증")
    print("  🧠 Sonnet 지휘관: 최종 결재 (BUY/WAIT/SELL)")
    print("  🚀 Python 실행자: KIS API 주문 전송")
    print("  📈 Feedback Engine: 매도 후 즉시 피드백 → 학습")
    print("\n" + "=" * 70)

    # Run one cycle for demonstration
    trader.run_cycle()

    print("\n" + "=" * 70)
    print("✅ Demo Complete")
    print("\nNext steps:")
    print("  1. KIS API 연동 (_execute_order)")
    print("  2. 실시간 스케줄러 (APScheduler)")
    print("  3. Telegram 알림 연동")
    print("=" * 70)


if __name__ == "__main__":
    main()
