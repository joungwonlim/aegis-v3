#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AEGIS v3.0 - Telegram Bot (양방향)
사용자 명령어 처리 + 알림 전송

실행:
    python monitoring/telegram_bot.py
"""
import os
import sys
from datetime import datetime
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from app.database import SessionLocal
from sqlalchemy import text

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class AegisTelegramBot:
    """AEGIS 텔레그램 봇"""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.allowed_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.db = SessionLocal()

        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in .env")

        logger.info("✅ AEGIS Telegram Bot initialized")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    # ========================================
    # COMMAND HANDLERS
    # ========================================

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """도움말"""
        help_text = """
🤖 *AEGIS v3.0 명령어 목록*

📊 *포트폴리오 조회*
/balance - 계좌 잔고 및 보유 종목
/profit - 수익률 현황
/holdings - 보유 종목 상세

📈 *시장 정보*
/market - KOSPI 및 시장 현황
/top - 모멘텀 상위 종목 (Top 10)

🤖 *AI 전략*
/strategy - 최근 AI 전략 분석 결과
/signals - 매매 시그널 현황

📜 *거래 내역*
/orders - 최근 주문 내역 (5건)
/today - 오늘 거래 요약

⚙️ *시스템*
/status - 시스템 상태
/help - 이 도움말

💡 *Tip*: 모든 명령어는 / 없이도 사용 가능합니다.
예: balance, profit, market 등
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """잔고 조회"""
        try:
            # 현금
            cash_query = text("SELECT cash FROM portfolio_summary LIMIT 1")
            cash_result = self.db.execute(cash_query).fetchone()
            cash = float(cash_result.cash) if cash_result else 0.0

            # 보유 종목
            holdings_query = text("""
                SELECT
                    s.name,
                    sa.quantity,
                    sa.avg_price,
                    dp.close as current_price,
                    (dp.close - sa.avg_price) / sa.avg_price * 100 as profit_rate
                FROM stock_assets sa
                JOIN stocks s ON sa.stock_code = s.code
                LEFT JOIN LATERAL (
                    SELECT close FROM daily_prices
                    WHERE stock_code = sa.stock_code
                    ORDER BY date DESC LIMIT 1
                ) dp ON true
                WHERE sa.quantity > 0
                ORDER BY sa.avg_price * sa.quantity DESC
                LIMIT 5
            """)
            holdings = self.db.execute(holdings_query).fetchall()

            stock_value = sum(h.current_price * h.quantity for h in holdings if h.current_price)
            total_value = cash + stock_value

            message = f"""
💼 *계좌 잔고*

💰 총 자산: `{total_value:,.0f}` 원
💵 현금: `{cash:,.0f}` 원
📈 주식: `{stock_value:,.0f}` 원

📊 *보유 종목* ({len(holdings)}개)
"""
            for h in holdings:
                profit_emoji = "🟢" if h.profit_rate > 0 else "🔴" if h.profit_rate < 0 else "⚪"
                message += f"\n{profit_emoji} {h.name}: {h.quantity:,}주 ({h.profit_rate:+.2f}%)"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Balance command error: {e}")
            await update.message.reply_text(f"❌ 오류: {str(e)}")

    async def profit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """수익률 현황"""
        try:
            query = text("""
                SELECT
                    SUM((dp.close - sa.avg_price) * sa.quantity) as total_profit,
                    SUM(sa.avg_price * sa.quantity) as total_investment
                FROM stock_assets sa
                LEFT JOIN LATERAL (
                    SELECT close FROM daily_prices
                    WHERE stock_code = sa.stock_code
                    ORDER BY date DESC LIMIT 1
                ) dp ON true
                WHERE sa.quantity > 0
            """)
            result = self.db.execute(query).fetchone()

            total_profit = float(result.total_profit or 0)
            total_investment = float(result.total_investment or 0)
            profit_rate = (total_profit / total_investment * 100) if total_investment > 0 else 0

            emoji = "🟢" if total_profit > 0 else "🔴" if total_profit < 0 else "⚪"

            message = f"""
{emoji} *수익률 현황*

총 수익: `{total_profit:+,.0f}` 원
수익률: `{profit_rate:+.2f}%`

투자금액: `{total_investment:,.0f}` 원

📅 조회 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Profit command error: {e}")
            await update.message.reply_text(f"❌ 오류: {str(e)}")

    async def market_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시장 현황"""
        try:
            # KOSPI
            kospi_query = text("""
                SELECT close, change_rate
                FROM daily_prices
                WHERE stock_code = '001'
                ORDER BY date DESC LIMIT 1
            """)
            kospi = self.db.execute(kospi_query).fetchone()

            # 외국인 선물
            kis_query = text("""
                SELECT foreign_futures_net, program_net
                FROM market_flow
                ORDER BY date DESC LIMIT 1
            """)
            kis = self.db.execute(kis_query).fetchone()

            kospi_emoji = "🟢" if kospi.change_rate > 0 else "🔴" if kospi.change_rate < 0 else "⚪"

            message = f"""
📈 *시장 현황*

{kospi_emoji} KOSPI: `{kospi.close:,.2f}` ({kospi.change_rate:+.2f}%)
"""
            if kis and kis.foreign_futures_net:
                message += f"\n🌏 외국인 선물: `{kis.foreign_futures_net:,}` 계약"

            if kis and kis.program_net:
                message += f"\n💻 프로그램: `{kis.program_net:,}` 백만원"

            message += f"\n\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Market command error: {e}")
            await update.message.reply_text(f"❌ 오류: {str(e)}")

    async def top_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """모멘텀 상위 종목"""
        try:
            query = text("""
                SELECT
                    s.name,
                    AVG(dp.change_rate) * 100 as momentum_score,
                    dp_latest.close as current_price
                FROM stocks s
                JOIN daily_prices dp ON s.code = dp.stock_code
                LEFT JOIN LATERAL (
                    SELECT close FROM daily_prices
                    WHERE stock_code = s.code
                    ORDER BY date DESC LIMIT 1
                ) dp_latest ON true
                WHERE dp.date >= CURRENT_DATE - INTERVAL '20 days'
                  AND s.market IN ('KOSPI', 'KOSDAQ')
                GROUP BY s.code, s.name, dp_latest.close
                HAVING AVG(dp.change_rate) > 0
                ORDER BY AVG(dp.change_rate) DESC
                LIMIT 10
            """)
            results = self.db.execute(query).fetchall()

            message = "🚀 *모멘텀 상위 종목* (20일 기준)\n\n"

            for i, r in enumerate(results, 1):
                message += f"{i}. {r.name}\n"
                message += f"   모멘텀: `{r.momentum_score:.2f}%` | 현재가: `{r.current_price:,.0f}`원\n\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Top command error: {e}")
            await update.message.reply_text(f"❌ 오류: {str(e)}")

    async def strategy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """최근 AI 전략"""
        try:
            query = text("""
                SELECT timestamp, model, market_view, regime, cash_ratio, risk_level, reasoning
                FROM ai_strategy_log
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            result = self.db.execute(query).fetchone()

            if not result:
                await update.message.reply_text("🤖 아직 AI 전략 분석 결과가 없습니다.")
                return

            view_emoji = {
                "BULLISH": "🟢",
                "BEARISH": "🔴",
                "NEUTRAL": "⚪"
            }.get(result.market_view, "⚪")

            message = f"""
🤖 *AI 전략 분석*

{view_emoji} 시장 전망: `{result.market_view}`
🎯 Regime: `{result.regime}`
💰 현금 비중: `{result.cash_ratio}%`
⚠️ 리스크: `{result.risk_level}`

📝 분석:
{result.reasoning[:200]}...

🤖 Model: {result.model}
📅 {result.timestamp.strftime('%Y-%m-%d %H:%M')}
"""
            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Strategy command error: {e}")
            await update.message.reply_text(f"❌ 오류: {str(e)}")

    async def orders_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """최근 주문 내역"""
        try:
            query = text("""
                SELECT
                    s.name,
                    o.action,
                    o.quantity,
                    o.price,
                    o.status,
                    o.created_at
                FROM trade_orders o
                JOIN stocks s ON o.stock_code = s.code
                ORDER BY o.created_at DESC
                LIMIT 5
            """)
            results = self.db.execute(query).fetchall()

            if not results:
                await update.message.reply_text("📜 최근 주문 내역이 없습니다.")
                return

            message = "📜 *최근 주문 내역*\n\n"

            for r in results:
                action_emoji = "🔵" if r.action == "BUY" else "🟢"
                status_emoji = "✅" if r.status == "FILLED" else "⏳"

                message += f"{action_emoji} {r.name}\n"
                message += f"   {r.action} {r.quantity:,}주 @ {r.price:,.0f}원 {status_emoji}\n"
                message += f"   {r.created_at.strftime('%m/%d %H:%M')}\n\n"

            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Orders command error: {e}")
            await update.message.reply_text(f"❌ 오류: {str(e)}")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시스템 상태"""
        try:
            # DB 연결 확인
            self.db.execute(text("SELECT 1"))

            # 데이터 현황
            stocks_count = self.db.execute(text("SELECT COUNT(*) FROM stocks")).scalar()
            prices_count = self.db.execute(text("SELECT COUNT(*) FROM daily_prices")).scalar()
            holdings_count = self.db.execute(text("SELECT COUNT(*) FROM stock_assets WHERE quantity > 0")).scalar()

            message = f"""
⚙️ *시스템 상태*

✅ 시스템: 정상 작동
✅ DB 연결: 정상

📊 *데이터 현황*
종목: {stocks_count:,}개
일별 데이터: {prices_count:,}건
보유 종목: {holdings_count}개

📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            await update.message.reply_text(message, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"Status command error: {e}")
            await update.message.reply_text(f"❌ 시스템 오류: {str(e)}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """시작 메시지"""
        message = """
🤖 *AEGIS v3.0에 오신 것을 환영합니다!*

AI 기반 자동매매 시스템이 준비되었습니다.

📋 명령어 목록을 보려면 /help 를 입력하세요.
"""
        await update.message.reply_text(message, parse_mode='Markdown')

    # ========================================
    # BOT SETUP
    # ========================================

    def run(self):
        """봇 실행"""
        application = Application.builder().token(self.bot_token).build()

        # 명령어 핸들러 등록
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("balance", self.balance_command))
        application.add_handler(CommandHandler("profit", self.profit_command))
        application.add_handler(CommandHandler("market", self.market_command))
        application.add_handler(CommandHandler("top", self.top_command))
        application.add_handler(CommandHandler("strategy", self.strategy_command))
        application.add_handler(CommandHandler("orders", self.orders_command))
        application.add_handler(CommandHandler("status", self.status_command))

        logger.info("🤖 AEGIS Telegram Bot 시작...")
        logger.info("명령어 대기 중... (Ctrl+C로 종료)")

        # 봇 시작
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """메인 함수"""
    try:
        bot = AegisTelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("\n봇 종료")
    except Exception as e:
        logger.error(f"오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
