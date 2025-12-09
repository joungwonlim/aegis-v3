"""
AEGIS v3.0 - Main Scheduler
APScheduler 기반 자동매매 스케줄러

하이브리드 동기화 전략 (WebSocket + REST API):
1. ⚡ 이벤트 기반: WebSocket 체결 알림 → 즉시 DB 반영
2. 🛡️ 주기적 동기화: 1분마다 REST API로 강제 동기화 (Safety Net)
3. 🚨 비상 동기화: WebSocket 재연결 시 즉시 동기화
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import asyncio
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers.kis_client import KISClient
from app.database import SessionLocal

logger = logging.getLogger("MainScheduler")


class MainScheduler:
    """메인 스케줄러"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self.kis = KISClient()

        logger.info("✅ MainScheduler initialized")
        logger.info("   📡 KIS Client ready")
        logger.info("   🛡️ Hybrid Sync Strategy enabled")

    def start(self):
        """스케줄러 시작"""
        print("🚀 AEGIS Scheduler Starting...")

        # ===== 데이터 수집 =====

        # 06:00 - US 시장 데이터
        self.scheduler.add_job(
            self.fetch_us_market,
            CronTrigger(hour=6, minute=0),
            id="fetch_us_market"
        )

        # 07:00 - KRX 수급 데이터
        self.scheduler.add_job(
            self.fetch_krx_data,
            CronTrigger(hour=7, minute=0),
            id="fetch_krx_data"
        )

        # 07:20 - Brain 심층 분석 (DeepSeek-R1)
        self.scheduler.add_job(
            self.brain_deep_analysis,
            CronTrigger(hour=7, minute=20),
            id="brain_deep_analysis"
        )

        # 08:00 - Opus Briefing
        self.scheduler.add_job(
            self.opus_briefing,
            CronTrigger(hour=8, minute=0),
            id="opus_briefing"
        )

        # ===== 실시간 거래 =====

        # 09:00-15:30 - 자동매매 (30초마다)
        self.scheduler.add_job(
            self.auto_trading,
            IntervalTrigger(seconds=30),
            id="auto_trading",
            start_date="09:00:00",
            end_date="15:30:00"
        )

        # ===== 🛡️ 하이브리드 동기화 (Safety Net) =====

        # 09:00-15:30 - 1분마다 계좌 잔고 강제 동기화
        self.scheduler.add_job(
            self.job_sync_account,
            CronTrigger(hour='9-15', minute='*'),  # 매분 00초마다 실행
            id="sync_account_safety"
        )

        # ===== 일일 정산 =====

        # 16:00 - 일일 정산
        self.scheduler.add_job(
            self.daily_settlement,
            CronTrigger(hour=16, minute=0),
            id="daily_settlement"
        )

        # 스케줄러 시작
        self.scheduler.start()
        print("✅ Scheduler Started")
        print("📅 Scheduled Jobs:")
        for job in self.scheduler.get_jobs():
            print(f"   - {job.id}: {job.next_run_time}")

    async def fetch_us_market(self):
        """US 시장 데이터 수집"""
        print(f"[{datetime.now()}] 📊 Fetching US Market Data...")
        # TODO: yfinance로 NASDAQ, SOX, VIX 수집

    async def fetch_krx_data(self):
        """KRX 수급 데이터 수집"""
        print(f"[{datetime.now()}] 📊 Fetching KRX Data...")
        # TODO: pykrx로 수급 데이터 수집

    async def brain_deep_analysis(self):
        """Brain 심층 분석 (DeepSeek-R1)"""
        print(f"[{datetime.now()}] 🧠 Brain Deep Analysis...")
        # TODO: DeepSeek-R1 분석 실행

    async def opus_briefing(self):
        """Opus 아침 브리핑"""
        print(f"[{datetime.now()}] 🎖️ Opus Morning Briefing...")
        # TODO: Opus에게 오늘 전략 브리핑

    async def auto_trading(self):
        """자동매매 실행"""
        print(f"[{datetime.now()}] ⚔️ Auto Trading...")
        # TODO: 포트폴리오 체크 → 매수/매도 판단 → 실행

    async def daily_settlement(self):
        """일일 정산"""
        print(f"[{datetime.now()}] 📊 Daily Settlement...")
        # TODO: 오늘 거래 정산, 피드백 반영

    async def job_sync_account(self):
        """
        🛡️ 하이브리드 동기화: 1분마다 계좌 잔고 강제 동기화 (Safety Net)

        WebSocket이 실시간 체결 알림을 주지만, 네트워크 패킷 유실이나
        연결 끊김 시 데이터 누락을 방지하기 위한 안전장치입니다.

        - 주기: 1분마다 (매분 00초)
        - TR 코드: TTTC8434R (주식잔고조회)
        - 목적: 데이터 불일치 시 최대 1분 안에 자동 복구
        """
        try:
            logger.debug("🛡️ [Safety] Synchronizing Account Balance...")

            db = SessionLocal()
            try:
                # KIS에서 최신 보유종목 조회
                holdings = self.kis.get_combined_balance()

                # 예수금 정보 조회
                token = self.kis.get_access_token()
                import requests
                url = f"{self.kis.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
                headers = {
                    "content-type": "application/json",
                    "authorization": f"Bearer {token}",
                    "appkey": self.kis.app_key,
                    "appsecret": self.kis.app_secret,
                    "tr_id": "TTTC8434R"
                }
                params = {
                    "CANO": self.kis.account_number,
                    "ACNT_PRDT_CD": self.kis.account_code,
                    "AFHR_FLPR_YN": "N",
                    "OFL_YN": "N",
                    "INQR_DVSN": "01",
                    "UNPR_DVSN": "01",
                    "FUND_STTL_ICLD_YN": "N",
                    "FNCG_AMT_AUTO_RDPT_YN": "N",
                    "PRCS_DVSN": "00",
                    "CTX_AREA_FK100": "",
                    "CTX_AREA_NK100": ""
                }

                response = requests.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    logger.error(f"❌ Sync failed: {response.text}")
                    return

                data = response.json()
                output2 = data.get("output2", [{}])[0]

                deposit = float(output2.get("dnca_tot_amt", 0))
                total_asset = float(output2.get("tot_evlu_amt", 0))

                # DB 동기화
                from sqlalchemy import text

                # stock_assets 테이블 동기화
                db.execute(text("DELETE FROM stock_assets"))

                changed_count = 0
                for stock in holdings:
                    code = stock.get("pdno", "")
                    quantity = int(stock.get("hldg_qty", 0))
                    avg_price = float(stock.get("pchs_avg_pric", 0))

                    if quantity > 0:
                        insert_query = text("""
                            INSERT INTO stock_assets (stock_code, quantity, avg_price, updated_at)
                            VALUES (:code, :quantity, :avg_price, :updated_at)
                        """)
                        db.execute(insert_query, {
                            'code': code,
                            'quantity': quantity,
                            'avg_price': avg_price,
                            'updated_at': datetime.now()
                        })
                        changed_count += 1

                # portfolio_summary 테이블 동기화
                db.execute(text("DELETE FROM portfolio_summary"))
                summary_query = text("""
                    INSERT INTO portfolio_summary (cash, total_value, updated_at)
                    VALUES (:cash, :total_value, :updated_at)
                """)
                db.execute(summary_query, {
                    'cash': deposit,
                    'total_value': total_asset,
                    'updated_at': datetime.now()
                })

                db.commit()

                # 변경사항이 있을 때만 info 로그 출력
                if changed_count > 0:
                    logger.info(f"🛡️ Sync Complete: {changed_count}개 종목, ₩{total_asset:,.0f}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ Sync Failed: {e}")
            import traceback
            traceback.print_exc()

    def stop(self):
        """스케줄러 중지"""
        self.scheduler.shutdown()
        print("🛑 Scheduler Stopped")


# Run Scheduler
if __name__ == "__main__":
    scheduler = MainScheduler()
    scheduler.start()

    # Keep running
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
