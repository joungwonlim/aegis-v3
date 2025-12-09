#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AEGIS v3.0 - Real-time Portfolio Monitor
실시간 포트폴리오 모니터링 (설정 가능한 갱신 주기)

실행:
    python monitoring/realtime_monitor.py [interval]

    interval: 갱신 주기(초), 기본 10초

예시:
    python monitoring/realtime_monitor.py 10   # 10초마다 갱신
    python monitoring/realtime_monitor.py 30   # 30초마다 갱신
"""
import os
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich import box
from rich.text import Text

from app.database import SessionLocal
from sqlalchemy import text

console = Console()

# 설정
TARGET_RATE = 2.0  # 목표 수익률 +2%
STOPLOSS_RATE = -2.0  # 손절선 -2%


class RealtimeMonitor:
    """실시간 포트폴리오 모니터"""

    def __init__(self, interval: int = 10):
        self.db = SessionLocal()
        self.interval = interval
        self.previous_data = {
            'total_value': None,
            'holdings': {}
        }

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def get_portfolio_summary(self) -> Dict:
        """포트폴리오 요약 조회"""

        # 보유 종목
        holdings_query = text("""
            SELECT
                s.code,
                s.name,
                sa.quantity,
                sa.avg_price,
                dp.close as current_price,
                dp.change_rate as price_change_rate,
                (dp.close - sa.avg_price) / sa.avg_price * 100 as profit_rate,
                (dp.close - sa.avg_price) * sa.quantity as profit_amount,
                dp.close * sa.quantity as current_value
            FROM stock_assets sa
            JOIN stocks s ON sa.stock_code = s.code
            LEFT JOIN LATERAL (
                SELECT close, change_rate
                FROM daily_prices
                WHERE stock_code = sa.stock_code
                ORDER BY date DESC
                LIMIT 1
            ) dp ON true
            WHERE sa.quantity > 0
            ORDER BY current_value DESC NULLS LAST
        """)

        holdings = self.db.execute(holdings_query).fetchall()

        # 현금
        cash_query = text("SELECT cash FROM portfolio_summary LIMIT 1")
        cash_result = self.db.execute(cash_query).fetchone()
        cash = float(cash_result.cash) if cash_result else 0.0

        # 계산
        stock_value = sum(float(h.current_value or 0) for h in holdings)
        total_value = cash + stock_value
        total_investment = sum(float(h.avg_price * h.quantity) for h in holdings)
        total_profit = sum(float(h.profit_amount or 0) for h in holdings)
        total_profit_rate = (total_profit / total_investment * 100) if total_investment > 0 else 0.0

        return {
            'cash': cash,
            'stock_value': stock_value,
            'total_value': total_value,
            'total_investment': total_investment,
            'total_profit': total_profit,
            'total_profit_rate': total_profit_rate,
            'holdings': holdings,
            'holding_count': len(holdings)
        }

    def get_market_status(self) -> Dict:
        """시장 상태 조회"""

        # KOSPI
        kospi_query = text("""
            SELECT close, change_rate
            FROM daily_prices
            WHERE stock_code = '001'
            ORDER BY date DESC
            LIMIT 1
        """)
        kospi = self.db.execute(kospi_query).fetchone()

        # 외국인 선물
        kis_query = text("""
            SELECT foreign_futures_net, program_net
            FROM market_flow
            ORDER BY date DESC
            LIMIT 1
        """)
        kis = self.db.execute(kis_query).fetchone()

        return {
            'kospi': float(kospi.close) if kospi else None,
            'kospi_change': float(kospi.change_rate) if kospi else None,
            'foreign_futures': kis.foreign_futures_net if kis else None,
            'program_net': kis.program_net if kis else None
        }

    def create_header_panel(self, market: Dict) -> Panel:
        """헤더 패널 생성"""

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        kospi_text = ""
        if market['kospi']:
            kospi_color = "green" if market['kospi_change'] > 0 else "red" if market['kospi_change'] < 0 else "white"
            kospi_text = f"KOSPI: [{kospi_color}]{market['kospi']:,.2f} ({market['kospi_change']:+.2f}%)[/{kospi_color}]"

        header = Text()
        header.append("AEGIS v3.0 - 실시간 포트폴리오 모니터", style="bold cyan")
        header.append(f"\n{now}", style="dim")
        if kospi_text:
            header.append(f" | {kospi_text}")

        return Panel(header, border_style="cyan", box=box.ROUNDED)

    def create_summary_table(self, summary: Dict) -> Table:
        """요약 테이블 생성"""

        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("항목", style="cyan", width=20)
        table.add_column("값", justify="right", width=25)

        # 총 자산
        table.add_row(
            "💰 총 자산",
            f"[bold]{summary['total_value']:,.0f}[/bold] 원"
        )

        # 현금
        table.add_row(
            "   💵 현금",
            f"{summary['cash']:,.0f} 원"
        )

        # 주식 평가액
        table.add_row(
            "   📈 주식",
            f"{summary['stock_value']:,.0f} 원"
        )

        table.add_row("", "")  # 공백

        # 총 수익
        profit_color = "green" if summary['total_profit'] > 0 else "red" if summary['total_profit'] < 0 else "white"
        table.add_row(
            "📊 총 수익",
            f"[{profit_color}]{summary['total_profit']:+,.0f}[/{profit_color}] 원"
        )

        # 수익률
        rate_color = "green" if summary['total_profit_rate'] > 0 else "red" if summary['total_profit_rate'] < 0 else "white"
        table.add_row(
            "   수익률",
            f"[{rate_color}]{summary['total_profit_rate']:+.2f}%[/{rate_color}]"
        )

        # 목표 달성률
        target_progress = summary['total_profit_rate'] / TARGET_RATE * 100 if TARGET_RATE > 0 else 0
        table.add_row(
            "   목표 달성",
            f"{target_progress:.1f}% (목표: {TARGET_RATE:+.1f}%)"
        )

        table.add_row("", "")  # 공백

        # 보유 종목 수
        table.add_row(
            "🏢 보유 종목",
            f"{summary['holding_count']}개"
        )

        return table

    def create_holdings_table(self, holdings: List) -> Table:
        """보유 종목 테이블 생성"""

        table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")

        table.add_column("종목", style="cyan", width=12)
        table.add_column("수량", justify="right", width=8)
        table.add_column("평균가", justify="right", width=12)
        table.add_column("현재가", justify="right", width=12)
        table.add_column("등락", justify="right", width=10)
        table.add_column("수익률", justify="right", width=10)
        table.add_column("평가액", justify="right", width=12)
        table.add_column("신호", justify="center", width=6)

        for h in holdings:
            # 색상 결정
            profit_rate = float(h.profit_rate or 0)

            if profit_rate >= TARGET_RATE:
                signal = "🎯"  # 목표 달성
                row_style = "green"
            elif profit_rate <= STOPLOSS_RATE:
                signal = "⚠️"  # 손절선
                row_style = "red"
            elif profit_rate > 0:
                signal = "✅"  # 수익
                row_style = "green"
            elif profit_rate < 0:
                signal = "📉"  # 손실
                row_style = "red"
            else:
                signal = "➖"  # 보합
                row_style = "white"

            price_change_color = "green" if h.price_change_rate > 0 else "red" if h.price_change_rate < 0 else "white"

            table.add_row(
                h.name,
                f"{h.quantity:,}",
                f"{h.avg_price:,.0f}",
                f"{h.current_price:,.0f}" if h.current_price else "N/A",
                f"[{price_change_color}]{h.price_change_rate:+.2f}%[/{price_change_color}]" if h.price_change_rate is not None else "N/A",
                f"[{row_style}]{profit_rate:+.2f}%[/{row_style}]",
                f"{h.current_value:,.0f}" if h.current_value else "N/A",
                signal,
                style=row_style if profit_rate >= TARGET_RATE or profit_rate <= STOPLOSS_RATE else None
            )

        return table

    def create_layout(self) -> Layout:
        """레이아웃 생성"""

        market = self.get_market_status()
        summary = self.get_portfolio_summary()

        layout = Layout()

        # 헤더
        header = self.create_header_panel(market)

        # 요약
        summary_table = self.create_summary_table(summary)
        summary_panel = Panel(summary_table, title="📊 포트폴리오 요약", border_style="cyan")

        # 보유 종목
        if summary['holdings']:
            holdings_table = self.create_holdings_table(summary['holdings'])
            holdings_panel = Panel(holdings_table, title="🏢 보유 종목", border_style="cyan")
        else:
            holdings_panel = Panel("[dim]보유 종목 없음[/dim]", title="🏢 보유 종목", border_style="cyan")

        # 푸터
        footer_text = Text()
        footer_text.append(f"갱신 주기: {self.interval}초", style="dim")
        footer_text.append(" | ", style="dim")
        footer_text.append("종료: Ctrl+C", style="dim")
        footer = Panel(footer_text, border_style="dim")

        # 레이아웃 구성
        layout.split_column(
            Layout(header, size=5),
            Layout(summary_panel, size=12),
            Layout(holdings_panel),
            Layout(footer, size=3)
        )

        return layout

    def run(self):
        """모니터링 실행"""

        console.clear()
        console.print(f"\n[bold cyan]AEGIS v3.0 실시간 모니터 시작[/bold cyan]")
        console.print(f"[dim]갱신 주기: {self.interval}초 | 종료: Ctrl+C[/dim]\n")

        time.sleep(2)

        try:
            with Live(self.create_layout(), console=console, refresh_per_second=1) as live:
                while True:
                    time.sleep(self.interval)
                    live.update(self.create_layout())

        except KeyboardInterrupt:
            console.print("\n\n[yellow]모니터링 종료[/yellow]")


def main():
    """메인 함수"""

    parser = argparse.ArgumentParser(description="AEGIS v3.0 실시간 포트폴리오 모니터")
    parser.add_argument(
        'interval',
        type=int,
        nargs='?',
        default=10,
        help='갱신 주기(초), 기본값: 10초'
    )

    args = parser.parse_args()

    if args.interval < 1:
        console.print("[red]갱신 주기는 1초 이상이어야 합니다.[/red]")
        sys.exit(1)

    if args.interval > 300:
        console.print("[yellow]⚠️  갱신 주기가 5분을 초과합니다. 계속하시겠습니까? (y/n)[/yellow]", end=" ")
        response = input().lower()
        if response != 'y':
            sys.exit(0)

    monitor = RealtimeMonitor(interval=args.interval)
    monitor.run()


if __name__ == "__main__":
    main()
