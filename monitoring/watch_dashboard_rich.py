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

        # Total Profit Rate Chart
        self._render_total_profit_chart()
        console.print()

        # Today's Intraday Profit Chart
        self._render_today_intraday_chart()
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

    def _render_total_profit_chart(self):
        """
        전체 수익률 시간대별 그래프

        시뮬레이션: 시작자본 대비 현재까지의 수익률 추이
        """
        # Get current portfolio value
        portfolio_query = text("""
            SELECT cash, total_value
            FROM portfolio_summary
            LIMIT 1
        """)
        portfolio = self.db.execute(portfolio_query).fetchone()

        if not portfolio:
            return

        total_value = float(portfolio.total_value)
        initial_capital = 10_000_000
        current_pnl_pct = ((total_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0

        # Simulate daily profit history (TODO: Replace with real data from DB)
        # For now, generate sample data showing trend
        days = 30
        profit_history = []

        # Generate realistic profit progression
        for i in range(days + 1):
            # Simulate gradual profit increase with some volatility
            progress = i / days
            simulated_pnl = current_pnl_pct * progress

            # Add some random volatility (±2%)
            import random
            volatility = random.uniform(-2, 2) if i > 0 else 0
            simulated_pnl += volatility

            profit_history.append(simulated_pnl)

        # Build ASCII chart
        chart_lines = []
        chart_lines.append("")

        # Chart dimensions
        chart_height = 15
        chart_width = 70

        # Find min/max for scaling
        max_pnl = max(profit_history)
        min_pnl = min(min(profit_history), 0)  # Include 0 line
        pnl_range = max_pnl - min_pnl

        # Build chart from top to bottom
        for i in range(chart_height, -1, -1):
            pnl_level = min_pnl + pnl_range * (i / chart_height)
            line_parts = ["│"]

            # Y-axis label
            if abs(pnl_level - max_pnl) < pnl_range * 0.05:
                line_parts[0] = f"│ [green]+{max_pnl:5.1f}%[/green]"
            elif abs(pnl_level) < pnl_range * 0.05:
                line_parts[0] = f"│ [yellow] {0:5.1f}%[/yellow]"
            elif abs(pnl_level - min_pnl) < pnl_range * 0.05 and min_pnl < 0:
                line_parts[0] = f"│ [red]{min_pnl:5.1f}%[/red]"
            else:
                line_parts[0] = f"│      "

            # Plot data points
            plot_line = ""
            for day_idx in range(len(profit_history)):
                day_pnl = profit_history[day_idx]

                # Normalize to chart height
                normalized_pos = (day_pnl - min_pnl) / pnl_range * chart_height if pnl_range > 0 else 0

                # Check if this point should be plotted on this line
                if abs(normalized_pos - i) < 0.5:
                    # Plot point
                    if day_pnl > 0:
                        plot_line += "[green]●[/green]"
                    elif day_pnl < 0:
                        plot_line += "[red]●[/red]"
                    else:
                        plot_line += "[yellow]●[/yellow]"
                elif abs(normalized_pos - i) < 1.5:
                    # Draw connecting line
                    if day_pnl > 0:
                        plot_line += "[green]│[/green]"
                    elif day_pnl < 0:
                        plot_line += "[red]│[/red]"
                    else:
                        plot_line += "[yellow]│[/yellow]"
                else:
                    # Empty space
                    if abs(pnl_level) < pnl_range * 0.05:
                        plot_line += "[dim]─[/dim]"  # Zero line
                    else:
                        plot_line += " "

            line_parts.append(plot_line)
            chart_lines.append("".join(line_parts))

        # Time axis
        time_axis = "└" + "─" * 6 + "┬" + "─" * 20 + "┬" + "─" * 20 + "┬" + "─" * 20 + "▶"
        chart_lines.append(time_axis)
        chart_lines.append(f"       [dim]D-30          D-20          D-10          TODAY[/dim]")

        # Current status
        chart_lines.append("")
        status_color = "green" if current_pnl_pct >= 0 else "red"
        chart_lines.append(f"[bold {status_color}]현재 수익률: {current_pnl_pct:+.2f}% (₩{total_value:,.0f})[/bold {status_color}]")

        # Peak info
        peak_pnl = max(profit_history)
        peak_color = "green" if peak_pnl >= 0 else "red"
        chart_lines.append(f"[{peak_color}]최고 수익률: {peak_pnl:+.2f}%[/{peak_color}]")

        # Render chart panel
        chart_text = "\n".join(chart_lines)
        console.print(Panel(
            chart_text,
            title="📈 전체 수익률 추이 (30일)",
            border_style="cyan",
            subtitle="[dim]※ 시뮬레이션 데이터 (TODO: 실제 거래 내역 연동)[/dim]"
        ))

    def _render_today_intraday_chart(self):
        """
        오늘 하루 시간별 수익률 그래프 (09:00~15:30)

        장중 실시간 수익률 변화 추이
        """
        # Get current portfolio value
        portfolio_query = text("""
            SELECT cash, total_value
            FROM portfolio_summary
            LIMIT 1
        """)
        portfolio = self.db.execute(portfolio_query).fetchone()

        if not portfolio:
            return

        total_value = float(portfolio.total_value)
        initial_capital = 10_000_000
        current_pnl_pct = ((total_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0

        # Current time
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute

        # Market hours: 09:00~15:30
        market_start = 9 * 60  # 09:00 in minutes
        market_end = 15 * 60 + 30  # 15:30 in minutes
        current_time_minutes = current_hour * 60 + current_minute

        # Generate intraday profit history (TODO: Replace with real tick data from DB)
        # Simulate 5-minute intervals: 09:00, 09:05, 09:10, ..., 15:30
        time_points = []
        profit_history = []

        # Starting point
        start_pnl = current_pnl_pct - 0.5  # Assume started 0.5% lower

        for minutes in range(market_start, min(market_end + 1, current_time_minutes + 1), 5):
            hour = minutes // 60
            minute = minutes % 60
            time_str = f"{hour:02d}:{minute:02d}"
            time_points.append(time_str)

            # Simulate profit progression with volatility
            progress = (minutes - market_start) / (current_time_minutes - market_start) if current_time_minutes > market_start else 0
            simulated_pnl = start_pnl + (current_pnl_pct - start_pnl) * progress

            # Add realistic intraday volatility
            import random
            volatility = random.uniform(-0.1, 0.1)
            simulated_pnl += volatility

            profit_history.append(simulated_pnl)

        if len(profit_history) == 0:
            console.print(Panel(
                "[yellow]장 시작 전입니다. 09:00 이후 데이터가 표시됩니다.[/yellow]",
                title="⏰ 오늘 수익률 (시간별)",
                border_style="yellow"
            ))
            return

        # Build ASCII chart
        chart_lines = []
        chart_lines.append("")

        # Chart dimensions
        chart_height = 12
        chart_width = 80

        # Find min/max for scaling
        max_pnl = max(profit_history)
        min_pnl = min(profit_history)
        pnl_range = max(max_pnl - min_pnl, 0.5)  # Minimum range 0.5%

        # Build chart from top to bottom
        for i in range(chart_height, -1, -1):
            pnl_level = min_pnl + pnl_range * (i / chart_height)
            line_parts = []

            # Y-axis label
            if abs(pnl_level - max_pnl) < pnl_range * 0.1:
                line_parts.append(f"│ [green]{max_pnl:+6.2f}%[/green]")
            elif abs(pnl_level - current_pnl_pct) < pnl_range * 0.1:
                line_parts.append(f"│ [cyan]{current_pnl_pct:+6.2f}%[/cyan]")
            elif abs(pnl_level - min_pnl) < pnl_range * 0.1:
                line_parts.append(f"│ [red]{min_pnl:+6.2f}%[/red]")
            else:
                line_parts.append(f"│       ")

            # Plot data points
            plot_line = " "
            for idx, pnl in enumerate(profit_history):
                # Normalize to chart height
                normalized_pos = (pnl - min_pnl) / pnl_range * chart_height if pnl_range > 0 else 0

                # Check if this point should be plotted on this line
                if abs(normalized_pos - i) < 0.3:
                    # Plot point
                    if idx == len(profit_history) - 1:
                        # Current point (larger)
                        plot_line += "[bold cyan]●[/bold cyan]"
                    elif pnl > start_pnl:
                        plot_line += "[green]●[/green]"
                    elif pnl < start_pnl:
                        plot_line += "[red]●[/red]"
                    else:
                        plot_line += "[yellow]●[/yellow]"
                elif abs(normalized_pos - i) < 0.8:
                    # Draw connecting line
                    if pnl > start_pnl:
                        plot_line += "[green]│[/green]"
                    elif pnl < start_pnl:
                        plot_line += "[red]│[/red]"
                    else:
                        plot_line += "[yellow]│[/yellow]"
                else:
                    # Empty space
                    plot_line += " "

            line_parts.append(plot_line)
            chart_lines.append("".join(line_parts))

        # Time axis with markers
        time_markers = "└" + "─" * 7
        marker_interval = len(profit_history) // 4 if len(profit_history) > 0 else 1

        for idx in range(len(profit_history)):
            if idx % marker_interval == 0 or idx == len(profit_history) - 1:
                time_markers += "┬" + "─" * (marker_interval - 1)
            else:
                time_markers += "─"

        time_markers += "▶"
        chart_lines.append(time_markers)

        # Time labels
        time_labels = "        "
        for idx in range(0, len(time_points), max(len(time_points) // 4, 1)):
            time_labels += f"{time_points[idx]:^{marker_interval + 1}}"

        # Add current time at the end
        if len(time_points) > 0:
            padding = chart_width - len(time_labels) - len(time_points[-1]) - 2
            time_labels += " " * max(0, padding) + f"[bold cyan]{time_points[-1]}[/bold cyan]"

        chart_lines.append(time_labels)

        # Stats
        chart_lines.append("")
        open_pnl = profit_history[0]
        high_pnl = max(profit_history)
        low_pnl = min(profit_history)
        close_pnl = profit_history[-1]

        chart_lines.append(f"[bold]장 시작: [cyan]{open_pnl:+.2f}%[/cyan]  |  "
                          f"고점: [green]{high_pnl:+.2f}%[/green]  |  "
                          f"저점: [red]{low_pnl:+.2f}%[/red]  |  "
                          f"현재: [cyan]{close_pnl:+.2f}%[/cyan][/bold]")

        # Intraday change
        intraday_change = close_pnl - open_pnl
        change_color = "green" if intraday_change >= 0 else "red"
        chart_lines.append(f"[{change_color}]오늘 변화: {intraday_change:+.2f}% "
                          f"({'상승' if intraday_change >= 0 else '하락'})[/{change_color}]")

        # Market status
        if current_time_minutes < market_start:
            status = "[yellow]장 시작 전[/yellow]"
        elif current_time_minutes > market_end:
            status = "[blue]장 마감[/blue]"
        else:
            status = "[green]장중 거래[/green]"

        chart_lines.append(f"상태: {status}")

        # Render chart panel
        chart_text = "\n".join(chart_lines)
        console.print(Panel(
            chart_text,
            title=f"⏰ 오늘 수익률 (시간별) - {now.strftime('%Y-%m-%d')}",
            border_style="magenta",
            subtitle="[dim]※ 5분 간격 시뮬레이션 (TODO: 실제 틱 데이터 연동)[/dim]"
        ))

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

            # Calculate totals
            total_value = 0
            total_pnl = 0
            total_pnl_weighted = 0

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

                # Accumulate for average
                position_value = pos.quantity * pos.current_price
                total_value += position_value
                total_pnl += (pos.current_price - pos.avg_price) * pos.quantity
                total_pnl_weighted += pos.unrealized_pnl_pct * position_value

            # Add separator and average row
            table.add_row("─" * 12, "─" * 8, "─" * 10, "─" * 10, "─" * 10, "─" * 40)

            # Calculate weighted average profit rate
            avg_pnl_pct = (total_pnl_weighted / total_value) if total_value > 0 else 0
            avg_pnl_color = "green" if avg_pnl_pct >= 0 else "red"
            avg_pnl_text = f"[{avg_pnl_color}]{avg_pnl_pct:+.2f}%[/{avg_pnl_color}]"

            # Average bar graph
            avg_bar_width = 30
            avg_abs_pct = abs(avg_pnl_pct)
            avg_bar_len = min(avg_bar_width, int(avg_abs_pct / 10 * avg_bar_width))

            if avg_pnl_pct >= 0:
                avg_bar_graph = f"[green]{'█' * avg_bar_len}[/green] {avg_pnl_pct:+.2f}%"
            else:
                avg_bar_graph = f"[red]{'█' * avg_bar_len}[/red] {avg_pnl_pct:+.2f}%"

            table.add_row(
                "[bold cyan]📊 평균[/bold cyan]",
                f"[bold]{len(position_risks)}개[/bold]",
                "-",
                f"[bold]₩{total_value:,.0f}[/bold]",
                f"[bold]{avg_pnl_text}[/bold]",
                f"[bold]{avg_bar_graph}[/bold]"
            )

            console.print(table)

        else:
            console.print(Panel("보유 종목 없음", title="📈 HOLDINGS", border_style="yellow"))

    def _render_price_chart(self, position):
        """
        시간대별 가격 차트 (트레일링 스톱 시각화)

        Args:
            position: 종목 포지션 정보
        """
        # Get intraday price history (simplified - using mock data for now)
        # TODO: Fetch real intraday data from DB or API

        buy_price = position.avg_price
        current_price = position.current_price
        high_price = max(buy_price, current_price) * 1.05  # Assume 5% gain at peak
        trailing_stop_price = high_price * 0.98  # 2% trailing stop from peak

        # Determine chart state
        is_profit = current_price > buy_price
        is_trailing_active = current_price > buy_price * 1.05  # Trailing ON after 5% gain
        is_stop_hit = current_price < trailing_stop_price and is_trailing_active

        # Build ASCII chart
        chart_lines = []
        chart_lines.append(f"\n[bold cyan]📊 {position.name} 가격 차트 (트레일링 스톱)[/bold cyan]")
        chart_lines.append("")

        # Price scale
        price_range = [buy_price, current_price, high_price, trailing_stop_price]
        max_price = max(price_range)
        min_price = min(price_range)

        # Chart height
        chart_height = 12
        width = 60

        # Build chart from top to bottom
        for i in range(chart_height, -1, -1):
            price_level = min_price + (max_price - min_price) * (i / chart_height)
            line = "│"

            # Price markers
            if abs(price_level - high_price) < (max_price - min_price) * 0.05:
                line = f"│ [yellow]★ 고점 {high_price:,.0f}원[/yellow]"
            elif abs(price_level - trailing_stop_price) < (max_price - min_price) * 0.05 and is_trailing_active:
                line = f"│ [red]← 손절가 {trailing_stop_price:,.0f}원 (고점-2%)[/red]"
            elif abs(price_level - current_price) < (max_price - min_price) * 0.05:
                status = "[green]● 현재가[/green]" if is_profit else "[red]● 현재가[/red]"
                line = f"│ {status} {current_price:,.0f}원"
            elif abs(price_level - buy_price) < (max_price - min_price) * 0.05:
                line = f"│ [cyan]◆ 매수가 {buy_price:,.0f}원[/cyan]"
            else:
                # Draw trend line
                if i == chart_height // 2:
                    if is_trailing_active:
                        line = "│         [dim]트레일링 ON (+5% 도달)[/dim]"
                    else:
                        line = "│"
                else:
                    line = "│"

            chart_lines.append(line)

        # Time axis
        chart_lines.append("└" + "─" * (width - 2) + "▶ 시간")

        # Legend
        chart_lines.append("")
        chart_lines.append("[bold]범례:[/bold]")
        chart_lines.append("  [yellow]★[/yellow] 고점 (최고가)")
        chart_lines.append("  [cyan]◆[/cyan] 매수가 (진입가)")
        chart_lines.append("  [green]●[/green] 현재가 (실시간)")
        chart_lines.append("  [red]←[/red] 손절가 (트레일링 스톱)")

        # Status
        if is_stop_hit:
            chart_lines.append("\n[bold red]🚨 손절가 하회 → [SELL] 신호 발생[/bold red]")
        elif is_trailing_active:
            chart_lines.append("\n[bold green]✅ 트레일링 스톱 활성화 (+5% 돌파)[/bold green]")
        elif is_profit:
            chart_lines.append("\n[bold yellow]📈 수익 구간 (트레일링 대기)[/bold yellow]")
        else:
            chart_lines.append("\n[bold]📊 관망 구간[/bold]")

        # Render chart panel
        chart_text = "\n".join(chart_lines)
        console.print(Panel(chart_text, title=f"💹 {position.name} 트레일링 차트", border_style="cyan"))

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
