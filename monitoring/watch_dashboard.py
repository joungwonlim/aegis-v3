"""
AEGIS v3.0 - Real-time Watch Dashboard
실시간 모니터링 대시보드

Features:
- 포트폴리오 현황 (실시간 손익)
- 보유 종목 상세
- AI 시그널 모니터링
- 최근 거래 내역
- Sonnet Commander 결정 로그
- 시스템 상태

Usage:
    python monitoring/watch_dashboard.py

    또는

    watch -n 3 python monitoring/watch_dashboard.py  # 3초마다 갱신
"""
import os
import sys
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text
from risk.risk_manager import RiskManager
from feedback.feedback_engine import FeedbackEngine

logger = logging.getLogger("WatchDashboard")


class WatchDashboard:
    """실시간 모니터링 대시보드"""

    def __init__(self):
        self.db = SessionLocal()
        self.risk_manager = RiskManager()
        self.feedback_engine = FeedbackEngine()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def render(self):
        """대시보드 전체 렌더링"""
        # Clear screen
        os.system('clear' if os.name == 'posix' else 'cls')

        # Header
        self._print_header()

        # Portfolio Summary
        self._print_portfolio_summary()

        # Holdings Detail
        self._print_holdings()

        # Recent Signals
        self._print_recent_signals()

        # Recent Trades
        self._print_recent_trades()

        # Sonnet Decisions
        self._print_commander_decisions()

        # System Status
        self._print_system_status()

        # Footer
        self._print_footer()

    def _print_header(self):
        """헤더 출력"""
        now = datetime.now()

        print("╔" + "═" * 78 + "╗")
        print("║" + " " * 20 + "🤖 AEGIS v3.0 - WATCH DASHBOARD" + " " * 26 + "║")
        print("║" + " " * 78 + "║")
        print("║" + f"  실시간 모니터링 | {now.strftime('%Y-%m-%d %H:%M:%S')}".ljust(78) + "║")
        print("╚" + "═" * 78 + "╝")
        print()

    def _print_portfolio_summary(self):
        """포트폴리오 요약"""
        print("┌─────────────────────────────────────────────────────────────────────────────┐")
        print("│ 📊 PORTFOLIO SUMMARY                                                        │")
        print("├─────────────────────────────────────────────────────────────────────────────┤")

        # Get portfolio data
        portfolio_query = text("""
            SELECT cash, total_value
            FROM portfolio_summary
            LIMIT 1
        """)
        portfolio = self.db.execute(portfolio_query).fetchone()

        if portfolio:
            cash = float(portfolio.cash)
            total_value = float(portfolio.total_value)
            stock_value = total_value - cash

            # Calculate P&L
            initial_capital = 10_000_000  # TODO: Get from config
            total_pnl = total_value - initial_capital
            total_pnl_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0

            # Get today's P&L (simplified)
            today_pnl = 0  # TODO: Calculate from today's price changes
            today_pnl_pct = 0

            print(f"│ 총 평가액: {total_value:>15,.0f}원  │  현금: {cash:>15,.0f}원             │")
            print(f"│ 주식평가: {stock_value:>15,.0f}원  │  비중: {(stock_value/total_value*100):>5.1f}%                    │")
            print("├─────────────────────────────────────────────────────────────────────────────┤")

            pnl_icon = "🟢" if total_pnl >= 0 else "🔴"
            print(f"│ {pnl_icon} 총 손익: {total_pnl:>+15,.0f}원 ({total_pnl_pct:>+6.2f}%)                              │")

            today_icon = "🟢" if today_pnl >= 0 else "🔴"
            print(f"│ {today_icon} 오늘:   {today_pnl:>+15,.0f}원 ({today_pnl_pct:>+6.2f}%)                              │")
        else:
            print("│ 포트폴리오 데이터 없음                                                       │")

        print("└─────────────────────────────────────────────────────────────────────────────┘")
        print()

    def _print_holdings(self):
        """보유 종목 상세"""
        print("┌─────────────────────────────────────────────────────────────────────────────┐")
        print("│ 📈 HOLDINGS                                                                 │")
        print("├──────┬────────────┬────────┬──────────┬──────────┬──────────┬──────────────┤")
        print("│ 종목 │    이름    │ 수량   │  평단가  │  현재가  │   손익   │   액션       │")
        print("├──────┼────────────┼────────┼──────────┼──────────┼──────────┼──────────────┤")

        # Get holdings with risk analysis
        position_risks, warnings = self.risk_manager.check_positions()

        if position_risks:
            for pos in position_risks:
                # Status icon
                if pos.action == "STOP_LOSS":
                    icon = "🔴"
                    action_text = "손절 필요"
                elif pos.action == "TAKE_PROFIT":
                    icon = "🟢"
                    action_text = "익절 가능"
                elif pos.unrealized_pnl_pct > 0:
                    icon = "📈"
                    action_text = "보유중"
                else:
                    icon = "📉"
                    action_text = "보유중"

                # Format values
                code_short = pos.code[:6]
                name_short = pos.name[:8].ljust(8)
                pnl_icon = "+" if pos.unrealized_pnl_pct >= 0 else ""

                print(f"│ {code_short} │ {name_short} │ {pos.quantity:>6,} │ {pos.avg_price:>8,.0f} │ {pos.current_price:>8,.0f} │ {pnl_icon}{pos.unrealized_pnl_pct:>5.1f}% │ {icon} {action_text:<9} │")
        else:
            print("│                              보유 종목 없음                                 │")

        print("└──────┴────────────┴────────┴──────────┴──────────┴──────────┴──────────────┘")
        print()

    def _print_recent_signals(self):
        """최근 AI 시그널"""
        print("┌─────────────────────────────────────────────────────────────────────────────┐")
        print("│ 🎯 RECENT SIGNALS (최근 5개)                                                 │")
        print("├──────────┬────────────┬────────┬────────┬────────┬──────────────────────────┤")
        print("│   시각   │    종목    │ Signal │  점수  │ 신뢰도 │         사유             │")
        print("├──────────┼────────────┼────────┼────────┼────────┼──────────────────────────┤")

        # Get recent AI decisions
        signals_query = text("""
            SELECT
                timestamp,
                signals,
                model
            FROM ai_strategy_log
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        result = self.db.execute(signals_query).fetchone()

        if result and result.signals:
            signals = result.signals[:5]  # Top 5

            for sig in signals:
                time_str = datetime.now().strftime("%H:%M")
                code = sig.get('code', 'N/A')[:6]
                name = sig.get('name', 'N/A')[:8].ljust(8)
                action = sig.get('action', 'HOLD')[:4]
                score = sig.get('score', 0)
                confidence = sig.get('confidence', 0)
                reason = sig.get('reason', '')[:24]

                # Action color
                if action == 'BUY':
                    action_text = f"🟢 {action}"
                elif action == 'SELL':
                    action_text = f"🔴 {action}"
                else:
                    action_text = f"⚪ {action}"

                print(f"│ {time_str} │ {name} │ {action_text} │ {score:>6.1f} │ {confidence:>5.0f}% │ {reason:<24} │")
        else:
            print("│                            시그널 데이터 없음                                │")

        print("└──────────┴────────────┴────────┴────────┴────────┴──────────────────────────┘")
        print()

    def _print_recent_trades(self):
        """최근 거래 내역"""
        print("┌─────────────────────────────────────────────────────────────────────────────┐")
        print("│ 💰 RECENT TRADES (최근 5건)                                                  │")
        print("├──────────┬────────────┬────────┬────────┬──────────┬──────────┬─────────────┤")
        print("│   시각   │    종목    │  액션  │  수량  │   가격   │   손익   │    사유     │")
        print("├──────────┼────────────┼────────┼────────┼──────────┼──────────┼─────────────┤")

        trades_query = text("""
            SELECT
                created_at,
                stock_code,
                action,
                quantity,
                price
            FROM trade_orders
            ORDER BY created_at DESC
            LIMIT 5
        """)

        trades = self.db.execute(trades_query).fetchall()

        if trades:
            for trade in trades:
                time_str = trade.created_at.strftime("%H:%M") if trade.created_at else "N/A"
                code = trade.stock_code[:6] if trade.stock_code else "N/A"

                # Get stock name
                name_query = text("SELECT name FROM stocks WHERE code = :code")
                name_result = self.db.execute(name_query, {'code': trade.stock_code}).fetchone()
                name = name_result.name[:8].ljust(8) if name_result else "N/A".ljust(8)

                action = trade.action if trade.action else "N/A"
                quantity = trade.quantity if trade.quantity else 0
                price = float(trade.price) if trade.price else 0

                # Action color
                if action == 'BUY':
                    action_text = f"🟢 {action:<4}"
                elif action == 'SELL':
                    action_text = f"🔴 {action:<4}"
                else:
                    action_text = f"⚪ {action:<4}"

                print(f"│ {time_str} │ {name} │ {action_text} │ {quantity:>6,} │ {price:>8,.0f} │    -     │    -        │")
        else:
            print("│                            거래 내역 없음                                    │")

        print("└──────────┴────────────┴────────┴────────┴──────────┴──────────┴─────────────┘")
        print()

    def _print_commander_decisions(self):
        """Sonnet Commander 결정 로그"""
        print("┌─────────────────────────────────────────────────────────────────────────────┐")
        print("│ 🧠 SONNET COMMANDER DECISIONS (최근 3건)                                     │")
        print("├──────────┬────────────┬────────────┬──────────────────────────────────────────┤")
        print("│   시각   │    종목    │   액션     │                 사유                     │")
        print("├──────────┼────────────┼────────────┼──────────────────────────────────────────┤")

        decisions_query = text("""
            SELECT
                timestamp,
                target_stock,
                action,
                reason,
                confidence_level
            FROM sonnet_decision_log
            ORDER BY timestamp DESC
            LIMIT 3
        """)

        decisions = self.db.execute(decisions_query).fetchall()

        if decisions:
            for dec in decisions:
                time_str = dec.timestamp.strftime("%H:%M") if dec.timestamp else "N/A"
                stock = dec.target_stock[:8].ljust(8) if dec.target_stock else "N/A".ljust(8)
                action = dec.action[:10].ljust(10) if dec.action else "N/A".ljust(10)
                reason = dec.reason[:38] if dec.reason else "N/A"

                print(f"│ {time_str} │ {stock} │ {action} │ {reason:<38} │")
        else:
            print("│                         Commander 결정 없음                                  │")

        print("└──────────┴────────────┴────────────┴──────────────────────────────────────────┘")
        print()

    def _print_system_status(self):
        """시스템 상태"""
        print("┌─────────────────────────────────────────────────────────────────────────────┐")
        print("│ ⚙️  SYSTEM STATUS                                                            │")
        print("├─────────────────────────────────────────────────────────────────────────────┤")

        # Feedback Engine Status
        min_score = self.feedback_engine.current_min_score
        consecutive_losses = self.feedback_engine.check_consecutive_losses() or 0
        consecutive_wins = self.feedback_engine.check_consecutive_wins() or 0

        # Circuit Breaker
        circuit_breaker = "🔴 ACTIVE" if consecutive_losses >= 5 else "🟢 OFF"

        print(f"│ MIN_SCORE: {min_score:>3}  │  연속 손절: {consecutive_losses}회  │  연속 익절: {consecutive_wins}회                  │")
        print(f"│ Circuit Breaker: {circuit_breaker}                                                   │")

        # Daily Stats
        daily_status = self.risk_manager.get_daily_risk_status()
        trades_today = daily_status['trades_today']
        max_trades = 20

        print(f"│ 오늘 거래: {trades_today}/{max_trades}건                                                          │")

        # Warnings
        if daily_status['warnings']:
            print("├─────────────────────────────────────────────────────────────────────────────┤")
            print("│ ⚠️  WARNINGS:                                                                │")
            for warning in daily_status['warnings']:
                print(f"│   {warning:<73} │")

        print("└─────────────────────────────────────────────────────────────────────────────┘")
        print()

    def _print_footer(self):
        """푸터"""
        print("┌─────────────────────────────────────────────────────────────────────────────┐")
        print("│ 🔄 Auto-refresh: watch -n 3 python monitoring/watch_dashboard.py            │")
        print("│ 📊 Full Dashboard: python monitoring/watch_dashboard.py                     │")
        print("│ 🛑 Stop: Ctrl+C                                                             │")
        print("└─────────────────────────────────────────────────────────────────────────────┘")


# ========================================
# MAIN
# ========================================

def main():
    """메인 실행"""
    logging.basicConfig(
        level=logging.WARNING,  # Only show warnings/errors
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        dashboard = WatchDashboard()
        dashboard.render()
    except KeyboardInterrupt:
        print("\n\n대시보드 종료")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
