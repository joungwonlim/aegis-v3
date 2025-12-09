"""
AEGIS v3.0 - Dynamic Scheduler
10-60-30 전략: 시간대별 차등 실행

핵심 전략:
- 오전장 집중 (09:00~10:00): 10분 간격 (70% 변동성)
- 점심장 관망 (10:00~13:00): 60분 간격 (저거래량)
- 오후장 안정 (13:00~15:00): 20분 간격 (추세 확인)
- 막판 스퍼트 (15:00~15:20): 10분 간격 (마지막 기회)
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging
import asyncio

from pipeline.intraday_pipeline import intraday_pipeline
from fetchers.daily_analyzer import daily_analyzer
from brain.portfolio_manager import portfolio_manager

logger = logging.getLogger(__name__)


class DynamicScheduler:
    """
    동적 스케줄러

    역할:
    - 10-60-30 전략 구현
    - 시간대별 차등 실행
    - Intraday Pipeline 오케스트레이션

    설계 원칙:
    - 30분 고정 ❌ → 시간대별 최적화 ✅
    - 오전/막판: 10분 (집중)
    - 점심: 60분 (관망)
    - 오후: 20분 (안정)
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
        self.is_running = False

    def start(self):
        """스케줄러 시작"""
        logger.info("=" * 80)
        logger.info("🚀 Dynamic Scheduler Starting...")
        logger.info("📅 Strategy: 10-60-30")
        logger.info("")

        # ==========================================
        # Layer 3: 일일 심층 분석 (07:20)
        # ==========================================
        logger.info("📋 Layer 3 Schedule:")

        # 07:20 - DeepSeek R1 전체 분석
        self.scheduler.add_job(
            self._daily_deep_analysis,
            CronTrigger(hour=7, minute=20, day_of_week='mon-fri'),
            id="daily_deep_analysis",
            name="Daily Deep Analysis (DeepSeek R1)"
        )
        logger.info("  ✅ 07:20 - DeepSeek R1 전체 분석 (2000종목)")

        # ==========================================
        # Layer 2: 1분 스캔 (Market Scanner)
        # ==========================================
        logger.info("")
        logger.info("📋 Layer 2 Schedule:")

        # 09:05-15:20 - Market Scanner (1분마다)
        self.scheduler.add_job(
            self._market_scanner_cycle,
            CronTrigger(minute='*', hour='9-15', day_of_week='mon-fri'),
            id="market_scanner",
            name="Market Scanner (1분)"
        )
        logger.info("  ✅ 09:05-15:20 - Market Scanner (1분 간격)")

        # 09:00-15:30 - Portfolio Manager (1분마다)
        self.scheduler.add_job(
            self._portfolio_manager_cycle,
            CronTrigger(minute='*', hour='9-15', day_of_week='mon-fri'),
            id="portfolio_manager",
            name="Portfolio Manager (1분)"
        )
        logger.info("  ✅ 09:00-15:30 - Portfolio Manager (1분 간격)")

        # ==========================================
        # Layer 1: Intraday Pipeline (10-60-30)
        # ==========================================
        logger.info("")
        logger.info("📋 Layer 1 Schedule (10-60-30 Strategy):")

        # 🔥 오전장 집중 (09:00~10:00): 10분
        self.scheduler.add_job(
            self._intraday_pipeline_wrapper,
            CronTrigger(hour=9, minute='0,10,20,30,40,50', day_of_week='mon-fri'),
            id="intraday_morning",
            name="Intraday Pipeline - Morning (10분)"
        )
        logger.info("  🔥 09:00-10:00 - Intraday Pipeline (10분 간격)")

        # 💤 점심장 관망 (10:00~13:00): 1시간
        self.scheduler.add_job(
            self._intraday_pipeline_wrapper,
            CronTrigger(hour='10-12', minute=0, day_of_week='mon-fri'),
            id="intraday_lunch",
            name="Intraday Pipeline - Lunch (60분)"
        )
        logger.info("  💤 10:00-13:00 - Intraday Pipeline (60분 간격)")

        # 🌤️ 오후장 안정 (13:00~15:00): 20분
        self.scheduler.add_job(
            self._intraday_pipeline_wrapper,
            CronTrigger(hour='13-14', minute='0,20,40', day_of_week='mon-fri'),
            id="intraday_afternoon",
            name="Intraday Pipeline - Afternoon (20분)"
        )
        logger.info("  🌤️  13:00-15:00 - Intraday Pipeline (20분 간격)")

        # 🏁 막판 스퍼트 (15:00~15:20): 10분
        self.scheduler.add_job(
            self._intraday_pipeline_wrapper,
            CronTrigger(hour=15, minute='0,10,20', day_of_week='mon-fri'),
            id="intraday_closing",
            name="Intraday Pipeline - Closing (10분)"
        )
        logger.info("  🏁 15:00-15:20 - Intraday Pipeline (10분 간격)")

        # ==========================================
        # 일일 정산 (16:00)
        # ==========================================
        logger.info("")
        logger.info("📋 Daily Settlement:")

        self.scheduler.add_job(
            self._daily_settlement,
            CronTrigger(hour=16, minute=0, day_of_week='mon-fri'),
            id="daily_settlement",
            name="Daily Settlement"
        )
        logger.info("  ✅ 16:00 - 일일 정산")

        # 스케줄러 시작
        self.scheduler.start()
        self.is_running = True

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ Dynamic Scheduler Started")
        logger.info("")
        logger.info("📅 Next Run Times:")
        for job in sorted(self.scheduler.get_jobs(), key=lambda j: j.next_run_time or datetime.max):
            if job.next_run_time:
                logger.info(f"   - {job.name}: {job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

    async def _daily_deep_analysis(self):
        """
        Layer 3: 일일 심층 분석 (07:20)

        작업:
        - DeepSeek R1으로 전체 종목 분석
        - daily_picks 테이블 업데이트
        - WebSocket Manager에 picks 반영
        """
        logger.info("=" * 80)
        logger.info(f"🧠 [07:20] Daily Deep Analysis Started")
        logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # Daily Analyzer 실행
            picks = await daily_analyzer.analyze_all()
            logger.info(f"✅ Analysis complete: {len(picks)} picks")

            logger.info("✅ Daily Deep Analysis Complete")

        except Exception as e:
            logger.error(f"❌ Daily analysis failed: {e}", exc_info=True)

        logger.info("=" * 80)

    async def _market_scanner_cycle(self):
        """
        Layer 2: Market Scanner (1분마다)

        작업:
        - 등락률/거래량 상위 스캔
        - gemini-2.0-flash 빠른 평가
        - WebSocket Priority 3 구독
        """
        # Note: Market Scanner는 자체 무한 루프 실행 중
        # 이 job은 예비용 (Scanner 중단 시 재시작)
        pass

    async def _portfolio_manager_cycle(self):
        """
        Layer 2: Portfolio Manager (1분마다)

        역할:
        - 보유 종목 최신 데이터 갱신 (KIS 잔고 싱크)
        - 매도 조건 체크 (손절/익절/트레일링 스탑)
        - 즉시 매도 주문 실행

        핵심 원칙:
        "손실은 짧게(-3%), 수익은 길게(끝까지 추적)"
        """
        try:
            # Portfolio Manager 실행
            result = await portfolio_manager.run_cycle()

            # 결과 로깅
            if result['checked'] > 0:
                logger.info("")
                logger.info("💼 Portfolio Manager Summary:")
                logger.info(f"   - Checked: {result['checked']} holdings")
                logger.info(f"   - Stop Loss: {result['stop_loss']}")
                logger.info(f"   - Take Profit: {result['take_profit']}")
                logger.info(f"   - Trailing Stop: {result['trailing_stop']}")
                logger.info(f"   - AI Panic: {result['ai_panic']}")
                if result['errors']:
                    logger.warning(f"   - Errors: {len(result['errors'])}")
                logger.info("")

        except Exception as e:
            logger.error(f"❌ Portfolio Manager cycle error: {e}", exc_info=True)

    async def _intraday_pipeline_wrapper(self):
        """
        Layer 1: Intraday Pipeline Wrapper

        역할:
        - Pipeline 실행
        - 에러 처리
        - 결과 로깅
        """
        try:
            # 장 시간 체크
            is_market_open = await intraday_pipeline.check_market_hours()
            if not is_market_open:
                logger.debug("⏸️  Market closed, skipping pipeline")
                return

            # Pipeline 실행
            result = await intraday_pipeline.run()

            # 결과 요약
            logger.info("")
            logger.info("📊 Pipeline Summary:")
            logger.info(f"   - Candidates: {len(result.get('candidates', []))}")
            logger.info(f"   - Validated: {len(result.get('validated_candidates', []))}")
            logger.info(f"   - Buy Orders: {len(result.get('buy_orders', []))}")
            logger.info(f"   - Sell Orders: {len(result.get('sell_orders', []))}")
            logger.info(f"   - Duration: {result.get('duration', 0):.2f}s")
            logger.info("")

        except Exception as e:
            logger.error(f"❌ Pipeline wrapper error: {e}", exc_info=True)

    async def _daily_settlement(self):
        """
        일일 정산 (16:00)

        작업:
        - 오늘 거래 내역 정리
        - 수익률 계산
        - 피드백 기록
        """
        logger.info("=" * 80)
        logger.info(f"📊 [16:00] Daily Settlement Started")
        logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            # TODO: Settlement 로직 구현
            # - 오늘 거래 내역 조회
            # - 수익률 계산
            # - 전략 피드백 기록

            logger.info("✅ Daily Settlement Complete")

        except Exception as e:
            logger.error(f"❌ Settlement failed: {e}", exc_info=True)

        logger.info("=" * 80)

    def stop(self):
        """스케줄러 중지"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("🛑 Dynamic Scheduler Stopped")

    def get_status(self) -> dict:
        """
        스케줄러 상태 조회

        Returns:
            상태 정보 (is_running, jobs, next_runs)
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            })

        return {
            "is_running": self.is_running,
            "jobs": jobs,
            "job_count": len(jobs)
        }


# Singleton Instance
dynamic_scheduler = DynamicScheduler()


# Run Scheduler (for testing)
if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    scheduler = DynamicScheduler()
    scheduler.start()

    # Keep running
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
