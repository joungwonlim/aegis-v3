"""
AEGIS v3.0 - Real-time Watch Dashboard (Rich UI)
실시간 모니터링 대시보드 with Rich library

Features:
- 포트폴리오 현황 + 목표 수익률 그래프
- 보유 종목 상세 + 수익률 막대 그래프
- 🎯 Recent Signals
- 앞으로 실행될 스케줄
- 실행중인 프로세스
- AI 시그널 모니터링
- 최근 거래 내역
- Sonnet Commander 결정 로그
- 시스템 상태

Usage:
    python monitoring/watch_dashboard_rich.py

    또는

    watch -n 3 python monitoring/watch_dashboard_rich.py  # 3초마다 갱신
"""
import os
import sys
import logging
import psutil
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text
from risk.risk_manager import RiskManager
from feedback.feedback_engine import FeedbackEngine

# Rich library imports
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import Progress, BarColumn, TextColumn
from rich.text import Text
from rich import box

logger = logging.getLogger("WatchDashboard")
console = Console()


class RichWatchDashboard:
    """Rich UI 기반 실시간 모니터링 대시보드"""

    def __init__(self):
        self.db = SessionLocal()
        self.risk_manager = RiskManager()
        self.feedback_engine = FeedbackEngine()

        # Target profit rate (목표 수익률)
        self.target_profit_rate = 10.0  # 10% 목표

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def render(self):
        """대시보드 전체 렌더링"""
        console.clear()

        # Header
        header = Panel(
            Text("🤖 AEGIS v3.0 - WATCH DASHBOARD", style="bold white", justify="center"),
            subtitle=f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
            border_style="bright_cyan"
        )
        console.print(header)
        console.print()

        # Portfolio Summary with Target Graph
        self._render_portfolio_with_target()
        console.print()

        # Holdings with Bar Charts
        self._render_holdings_bars()
        console.print()

        # Recent Signals
        self._render_recent_signals()
        console.print()

        # Schedule & Processes
        self._render_schedule_and_processes()
        console.print()

        # Recent Trades
        self._render_recent_trades()
        console.print()

        # Commander Decisions
        self._render_commander_decisions()
        console.print()

        # System Status
        self._render_system_status()

    def _render_portfolio_with_target(self):
        """포트폴리오 요약 + 목표 수익률 그래프"""
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
            initial_capital = 10_000_000
            total_pnl = total_value - initial_capital
            total_pnl_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0

            # Create table
            table = Table(title="📊 PORTFOLIO SUMMARY", box=box.ROUNDED, border_style="cyan")
            table.add_column("항목", style="cyan")
            table.add_column("금액", justify="right", style="yellow")
            table.add_column("비중", justify="right")

            table.add_row(
                "총 평가액",
                f"₩{total_value:,.0f}",
                "100.0%"
            )
            table.add_row(
                "현금",
                f"₩{cash:,.0f}",
                f"{(cash/total_value*100):.1f}%"
            )
            table.add_row(
                "주식평가",
                f"₩{stock_value:,.0f}",
                f"{(stock_value/total_value*100):.1f}%"
            )

            # Profit/Loss row with color
            pnl_icon = "🟢" if total_pnl >= 0 else "🔴"
            pnl_color = "green" if total_pnl >= 0 else "red"
            table.add_row(
                f"{pnl_icon} 총 손익",
                f"[{pnl_color}]{total_pnl:+,.0f}[/{pnl_color}]",
                f"[{pnl_color}]{total_pnl_pct:+.2f}%[/{pnl_color}]"
            )

            console.print(table)

            # Target Profit Rate Progress Bar
            console.print("\n[bold cyan]🎯 목표 수익률 달성도[/bold cyan]")

            # Calculate progress (current vs target)
            progress_pct = min(100, (total_pnl_pct / self.target_profit_rate) * 100)

            # Create progress bar using Rich
            with Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=40),
                TextColumn("[progress.percentage]{task.percentage:>3.1f}%"),
                expand=False
            ) as progress:
                task = progress.add_task(
                    f"현재: {total_pnl_pct:+.2f}% / 목표: {self.target_profit_rate:.1f}%",
                    total=100,
                    completed=progress_pct
                )

    def _render_holdings_bars(self):
        """보유 종목 + 수익률 막대 그래프"""
        position_risks, warnings = self.risk_manager.check_positions()

        if position_risks:
            table = Table(title="📈 HOLDINGS", box=box.ROUNDED, border_style="green")
            table.add_column("종목", style="cyan", width=12)
            table.add_column("수량", justify="right", width=8)
            table.add_column("평단가", justify="right", width=10)
            table.add_column("현재가", justify="right", width=10)
            table.add_column("손익률", justify="right", width=10)
            table.add_column("수익률 그래프", width=40)

            for pos in position_risks:
                # Status icon
                if pos.action == "STOP_LOSS":
                    icon = "🔴"
                elif pos.action == "TAKE_PROFIT":
                    icon = "🟢"
                elif pos.unrealized_pnl_pct > 0:
                    icon = "📈"
                else:
                    icon = "📉"

                # Profit rate color
                pnl_color = "green" if pos.unrealized_pnl_pct >= 0 else "red"
                pnl_text = f"[{pnl_color}]{pos.unrealized_pnl_pct:+.2f}%[/{pnl_color}]"

                # Create bar chart for profit rate
                bar_width = 30
                abs_pct = abs(pos.unrealized_pnl_pct)
                bar_len = min(bar_width, int(abs_pct / 10 * bar_width))  # Scale: 10% = full bar

                if pos.unrealized_pnl_pct >= 0:
                    bar_graph = f"[green]{'█' * bar_len}[/green] {pos.unrealized_pnl_pct:+.2f}%"
                else:
                    bar_graph = f"[red]{'█' * bar_len}[/red] {pos.unrealized_pnl_pct:+.2f}%"

                table.add_row(
                    f"{icon} {pos.name[:10]}",
                    f"{pos.quantity:,}",
                    f"{pos.avg_price:,.0f}",
                    f"{pos.current_price:,.0f}",
                    pnl_text,
                    bar_graph
                )

            console.print(table)
        else:
            console.print(Panel("보유 종목 없음", title="📈 HOLDINGS", border_style="yellow"))

    def _render_recent_signals(self):
        """🎯 최근 AI 시그널 (Recent 5)"""
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

            table = Table(title="🎯 RECENT SIGNALS (최근 5개)", box=box.ROUNDED, border_style="yellow")
            table.add_column("시각", style="dim")
            table.add_column("종목", style="cyan")
            table.add_column("Signal", justify="center")
            table.add_column("점수", justify="right")
            table.add_column("신뢰도", justify="right")
            table.add_column("사유", style="dim")

            for sig in signals:
                time_str = datetime.now().strftime("%H:%M")
                name = sig.get('name', 'N/A')[:10]
                action = sig.get('action', 'HOLD')
                score = sig.get('score', 0)
                confidence = sig.get('confidence', 0)
                reason = sig.get('reason', '')[:30]

                # Action color
                if action == 'BUY':
                    action_text = "[green]🟢 BUY[/green]"
                elif action == 'SELL':
                    action_text = "[red]🔴 SELL[/red]"
                else:
                    action_text = "⚪ HOLD"

                table.add_row(
                    time_str,
                    name,
                    action_text,
                    f"{score:.1f}",
                    f"{confidence:.0f}%",
                    reason
                )

            console.print(table)
        else:
            console.print(Panel("시그널 데이터 없음", title="🎯 RECENT SIGNALS", border_style="yellow"))

    def _render_schedule_and_processes(self):
        """앞으로 실행될 스케줄 + 실행중인 프로세스"""
        # Schedule Table
        schedule_table = Table(title="⏰ UPCOMING SCHEDULE", box=box.SIMPLE, border_style="magenta", width=60)
        schedule_table.add_column("시간", style="cyan")
        schedule_table.add_column("작업", style="yellow")
        schedule_table.add_column("설명")

        # Define schedule
        schedule = [
            ("07:00", "KRX 데이터", "수급 데이터 수집"),
            ("07:20", "Brain 분석", "DeepSeek-R1 심층 분석"),
            ("08:00", "Opus 브리핑", "Claude Opus 오늘 전략"),
            ("09:00", "장 시작", "자동매매 시작 (30초 주기)"),
            ("15:30", "장 마감", "일일 정산 및 피드백"),
        ]

        current_time = datetime.now().time()
        for time_str, task, desc in schedule:
            task_time = datetime.strptime(time_str, "%H:%M").time()

            # Highlight upcoming tasks
            if task_time > current_time:
                style = "bold green"
            else:
                style = "dim"

            schedule_table.add_row(
                f"[{style}]{time_str}[/{style}]",
                f"[{style}]{task}[/{style}]",
                f"[{style}]{desc}[/{style}]"
            )

        # Processes Table
        process_table = Table(title="🔄 RUNNING PROCESSES", box=box.SIMPLE, border_style="blue", width=60)
        process_table.add_column("PID", justify="right", style="cyan")
        process_table.add_column("프로세스", style="yellow")
        process_table.add_column("CPU%", justify="right")
        process_table.add_column("메모리", justify="right")

        # Get Python processes related to AEGIS
        aegis_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('aegis' in arg.lower() or 'scheduler' in arg.lower() for arg in cmdline):
                    aegis_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if aegis_processes:
            for proc_info in aegis_processes[:5]:  # Top 5
                cmdline = proc_info.get('cmdline', [])
                script_name = cmdline[-1].split('/')[-1] if cmdline else 'unknown'

                mem_mb = proc_info.get('memory_info').rss / 1024 / 1024 if proc_info.get('memory_info') else 0

                process_table.add_row(
                    str(proc_info.get('pid', 0)),
                    script_name[:30],
                    f"{proc_info.get('cpu_percent', 0):.1f}%",
                    f"{mem_mb:.0f} MB"
                )
        else:
            process_table.add_row("N/A", "프로세스 없음", "-", "-")

        # Render side by side
        console.print(schedule_table)
        console.print()
        console.print(process_table)

    def _render_recent_trades(self):
        """최근 거래 내역"""
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
            table = Table(title="💰 RECENT TRADES (최근 5건)", box=box.ROUNDED, border_style="yellow")
            table.add_column("시각", style="dim")
            table.add_column("종목", style="cyan")
            table.add_column("액션", justify="center")
            table.add_column("수량", justify="right")
            table.add_column("가격", justify="right")

            for trade in trades:
                time_str = trade.created_at.strftime("%H:%M") if trade.created_at else "N/A"

                # Get stock name
                name_query = text("SELECT name FROM stocks WHERE code = :code")
                name_result = self.db.execute(name_query, {'code': trade.stock_code}).fetchone()
                name = name_result.name[:10] if name_result else "N/A"

                action = trade.action if trade.action else "N/A"

                # Action color
                if action == 'BUY':
                    action_text = "[green]🟢 BUY[/green]"
                elif action == 'SELL':
                    action_text = "[red]🔴 SELL[/red]"
                else:
                    action_text = "⚪ " + action

                table.add_row(
                    time_str,
                    name,
                    action_text,
                    f"{trade.quantity:,}" if trade.quantity else "0",
                    f"{float(trade.price):,.0f}" if trade.price else "0"
                )

            console.print(table)
        else:
            console.print(Panel("거래 내역 없음", title="💰 RECENT TRADES", border_style="yellow"))

    def _render_commander_decisions(self):
        """Sonnet Commander 결정 로그"""
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
            table = Table(title="🧠 SONNET COMMANDER DECISIONS (최근 3건)", box=box.ROUNDED, border_style="blue")
            table.add_column("시각", style="dim")
            table.add_column("종목", style="cyan")
            table.add_column("액션", justify="center", style="yellow")
            table.add_column("사유", style="dim")
            table.add_column("신뢰도", justify="right")

            for dec in decisions:
                time_str = dec.timestamp.strftime("%H:%M") if dec.timestamp else "N/A"
                stock = dec.target_stock[:10] if dec.target_stock else "N/A"
                action = dec.action[:12] if dec.action else "N/A"
                reason = dec.reason[:40] if dec.reason else "N/A"
                confidence = f"{dec.confidence_level:.0f}%" if dec.confidence_level else "N/A"

                table.add_row(time_str, stock, action, reason, confidence)

            console.print(table)
        else:
            console.print(Panel("Commander 결정 없음", title="🧠 SONNET COMMANDER", border_style="blue"))

    def _render_system_status(self):
        """시스템 상태"""
        # Feedback Engine Status
        min_score = self.feedback_engine.current_min_score
        consecutive_losses = self.feedback_engine.check_consecutive_losses() or 0
        consecutive_wins = self.feedback_engine.check_consecutive_wins() or 0

        # Circuit Breaker
        circuit_status = "🔴 ACTIVE" if consecutive_losses >= 5 else "🟢 OFF"
        circuit_color = "red" if consecutive_losses >= 5 else "green"

        # Daily Stats
        daily_status = self.risk_manager.get_daily_risk_status()
        trades_today = daily_status['trades_today']
        max_trades = 20

        table = Table(title="⚙️ SYSTEM STATUS", box=box.ROUNDED, border_style="cyan")
        table.add_column("항목", style="cyan")
        table.add_column("값", justify="right", style="yellow")

        table.add_row("MIN_SCORE", str(min_score))
        table.add_row("연속 손절", f"{consecutive_losses}회")
        table.add_row("연속 익절", f"{consecutive_wins}회")
        table.add_row("Circuit Breaker", f"[{circuit_color}]{circuit_status}[/{circuit_color}]")
        table.add_row("오늘 거래", f"{trades_today}/{max_trades}건")

        console.print(table)

        # Warnings
        if daily_status['warnings']:
            console.print("\n[bold red]⚠️ WARNINGS:[/bold red]")
            for warning in daily_status['warnings']:
                console.print(f"  [yellow]• {warning}[/yellow]")


# ========================================
# MAIN
# ========================================

def main():
    """메인 실행"""
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        dashboard = RichWatchDashboard()
        dashboard.render()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]대시보드 종료[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
