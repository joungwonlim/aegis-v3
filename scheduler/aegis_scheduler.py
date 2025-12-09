"""
AEGIS v3.0 - 상세 스케줄러
SCHEDULER_DESIGN.md 기반 완전 구현
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from datetime import datetime
import asyncio
import logging
from functools import wraps

logger = logging.getLogger("AEGISScheduler")


def job_wrapper(func):
    """모든 잡에 적용되는 에러 핸들러"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            logger.info(f"🔄 [{func.__name__}] 시작")
            result = await func(*args, **kwargs)
            logger.info(f"✅ [{func.__name__}] 완료")
            return result
        except Exception as e:
            logger.error(f"❌ [{func.__name__}] 실패: {e}")
            # TODO: Telegram 알림
            # notify_telegram(f"❌ Job 실패: {func.__name__}\n{e}")
    return wrapper


class AEGISScheduler:
    """AEGIS 메인 스케줄러"""

    def __init__(self):
        """스케줄러 초기화"""
        self.scheduler = AsyncIOScheduler(
            jobstores={'default': MemoryJobStore()},
            job_defaults={
                'coalesce': True,           # 누락된 잡 병합
                'max_instances': 1,         # 동시 실행 방지
                'misfire_grace_time': 60,   # 60초 지연 허용
            },
            timezone="Asia/Seoul"
        )

    def start(self):
        """스케줄러 시작 및 모든 Job 등록"""
        logger.info("=" * 60)
        logger.info("🚀 AEGIS Scheduler Starting...")
        logger.info("=" * 60)

        # ===== PRE-MARKET PHASE (07:00-09:00) =====
        self._register_premarket_jobs()

        # ===== MARKET PREP PHASE (08:00-09:00) =====
        self._register_market_prep_jobs()

        # ===== TRADING PHASE (09:00-15:30) =====
        self._register_trading_jobs()

        # ===== POST-MARKET PHASE (15:30-20:00) =====
        self._register_postmarket_jobs()

        # ===== WEEKEND JOBS =====
        self._register_weekend_jobs()

        # 스케줄러 시작
        self.scheduler.start()
        logger.info("✅ Scheduler Started")
        logger.info("📅 Scheduled Jobs:")
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "N/A"
            logger.info(f"   - {job.id}: {next_run}")

    # ========================================
    # PRE-MARKET PHASE (07:00-09:00)
    # ========================================

    def _register_premarket_jobs(self):
        """프리마켓 잡 등록"""

        # 07:00 - Fetcher 상태 점검
        self.scheduler.add_job(
            self.job_fetcher_health_check,
            CronTrigger(hour=7, minute=0, day_of_week='mon-fri'),
            id="fetcher_health_check"
        )

        # 07:20 - 심층 분석 (DeepSeek-R1)
        self.scheduler.add_job(
            self.job_morning_deep_analysis,
            CronTrigger(hour=7, minute=20, day_of_week='mon-fri'),
            id="morning_deep_analysis"
        )

        # 07:30 - 글로벌 선행지표
        self.scheduler.add_job(
            self.job_global_leader_morning,
            CronTrigger(hour=7, minute=30, day_of_week='mon-fri'),
            id="global_leader_morning"
        )

        # 07:30 - 매크로 데이터 수집
        self.scheduler.add_job(
            self.job_macro_update,
            CronTrigger(hour=7, minute=30, day_of_week='mon-fri'),
            id="macro_update"
        )

    # ========================================
    # MARKET PREP PHASE (08:00-09:00)
    # ========================================

    def _register_market_prep_jobs(self):
        """장 준비 잡 등록"""

        # 08:00 - 매크로 모니터링 (매 1시간)
        self.scheduler.add_job(
            self.job_macro_monitoring,
            CronTrigger(hour='8-20', minute=0, day_of_week='mon-fri'),
            id="macro_monitoring"
        )

        # 08:00 - 월요일 최종 체크
        self.scheduler.add_job(
            self.job_monday_final_check,
            CronTrigger(hour=8, minute=0, day_of_week='mon'),
            id="monday_final_check"
        )

        # 08:30 - 갭 스캔
        self.scheduler.add_job(
            self.job_alpha_morning_gap,
            CronTrigger(hour=8, minute=30, day_of_week='mon-fri'),
            id="alpha_morning_gap"
        )

        # 08:30 - 월요일 전략 결정
        self.scheduler.add_job(
            self.job_monday_strategy,
            CronTrigger(hour=8, minute=30, day_of_week='mon'),
            id="monday_strategy"
        )

        # 08:30 - 외국인 선물 체크
        self.scheduler.add_job(
            self.job_derivative_monitoring,
            CronTrigger(hour=8, minute=30, day_of_week='mon-fri'),
            id="derivative_monitoring_morning"
        )

        # 08:50 - 장 시작 준비
        self.scheduler.add_job(
            self.job_market_open,
            CronTrigger(hour=8, minute=50, day_of_week='mon-fri'),
            id="market_open"
        )

        # 08:55 - 오케스트레이터 리셋
        self.scheduler.add_job(
            self.job_orchestrator_reset,
            CronTrigger(hour=8, minute=55, day_of_week='mon-fri'),
            id="orchestrator_reset"
        )

    # ========================================
    # TRADING PHASE (09:00-15:30)
    # ========================================

    def _register_trading_jobs(self):
        """거래 시간 잡 등록 - Dynamic Schedule 적용"""

        # === 핵심 매매 잡 (고빈도) ===

        # 포트폴리오 동기화 (1분마다)
        self.scheduler.add_job(
            self.job_portfolio_sync,
            CronTrigger(hour='9-15', minute='*', day_of_week='mon-fri'),
            id="portfolio_sync"
        )

        # 손절/익절 감시 (1분마다)
        self.scheduler.add_job(
            self.job_portfolio_watchdog,
            CronTrigger(hour='9-15', minute='*', day_of_week='mon-fri'),
            id="portfolio_watchdog"
        )

        # 자동 매매 실행 (30초마다)
        self.scheduler.add_job(
            self.job_auto_trading,
            CronTrigger(hour='9-15', minute='*', second='*/30', day_of_week='mon-fri'),
            id="auto_trading"
        )

        # === Dynamic Schedule: 장중 AI 분석 ===

        # 🔥 오전장 (09:00-10:00): 10분 간격
        self.scheduler.add_job(
            self.job_intraday_analysis,
            CronTrigger(hour=9, minute='0,10,20,30,40,50', day_of_week='mon-fri'),
            id="intraday_morning"
        )

        # 💤 점심장 (10:00-13:00): 1시간 간격
        self.scheduler.add_job(
            self.job_intraday_analysis,
            CronTrigger(hour='10-12', minute=0, day_of_week='mon-fri'),
            id="intraday_lunch"
        )

        # 🌤️ 오후장 (13:00-15:00): 20분 간격
        self.scheduler.add_job(
            self.job_intraday_analysis,
            CronTrigger(hour='13-14', minute='0,20,40', day_of_week='mon-fri'),
            id="intraday_afternoon"
        )

        # 🏁 막판 (15:00-15:20): 10분 간격
        self.scheduler.add_job(
            self.job_intraday_analysis,
            CronTrigger(hour=15, minute='0,10,20', day_of_week='mon-fri'),
            id="intraday_closing"
        )

        # === 시장 국면 체크 (5분마다) ===
        self.scheduler.add_job(
            self.job_market_regime_check,
            CronTrigger(hour='9-15', minute='*/5', day_of_week='mon-fri'),
            id="market_regime_check"
        )

        # === 수급 데이터 수집 (10분마다) ===
        self.scheduler.add_job(
            self.job_supply_data_sync,
            CronTrigger(hour='9-15', minute='*/10', day_of_week='mon-fri'),
            id="supply_data_sync"
        )

        # === 헷지 관리 (10분마다) ===
        self.scheduler.add_job(
            self.job_hedge_management,
            CronTrigger(hour='9-15', minute='*/10', day_of_week='mon-fri'),
            id="hedge_management"
        )

        # === 오케스트레이터 실행 (10분마다) ===
        self.scheduler.add_job(
            self.job_orchestrator_execute,
            CronTrigger(hour='9-15', minute='*/10', day_of_week='mon-fri'),
            id="orchestrator_execute"
        )

        # === DART 공시 스캔 (15분마다) ===
        self.scheduler.add_job(
            self.job_dart_disclosure_scan,
            CronTrigger(hour='9-15', minute='*/15', day_of_week='mon-fri'),
            id="dart_disclosure_scan"
        )

        # === 섹터 순환 체크 (20분마다) ===
        self.scheduler.add_job(
            self.job_alpha_sector_rotation,
            CronTrigger(hour='9-15', minute='*/20', day_of_week='mon-fri'),
            id="alpha_sector_rotation"
        )

        # === 테마 스캔 (30분마다) ===
        self.scheduler.add_job(
            self.job_naver_theme_scan,
            CronTrigger(hour='9-15', minute='*/30', day_of_week='mon-fri'),
            id="naver_theme_scan"
        )

        # === 데이터 융합 분석 (30분마다) ===
        self.scheduler.add_job(
            self.job_data_fusion_scan,
            CronTrigger(hour='9-15', minute='*/30', day_of_week='mon-fri'),
            id="data_fusion_scan"
        )

        # === 시스템 상태 로그 (30분마다) ===
        self.scheduler.add_job(
            self.job_system_health_log,
            CronTrigger(hour='9-15', minute='*/30', day_of_week='mon-fri'),
            id="system_health_log"
        )

        # === 특정 시간 잡 ===

        # 09:05 - 현금 확보 체크
        self.scheduler.add_job(
            self.job_morning_cash_check,
            CronTrigger(hour=9, minute=5, day_of_week='mon-fri'),
            id="morning_cash_check"
        )

        # 09:05 - 일일 상태 로그
        self.scheduler.add_job(
            self.job_daily_status_log,
            CronTrigger(hour=9, minute=5, day_of_week='mon-fri'),
            id="daily_status_log"
        )

        # 09:05 - 페어 트레이딩 분석
        self.scheduler.add_job(
            self.job_pair_trading_morning,
            CronTrigger(hour=9, minute=5, day_of_week='mon-fri'),
            id="pair_trading_morning"
        )

        # 10:00 - 페어 트레이딩 체크
        self.scheduler.add_job(
            self.job_pair_trading_midmorning,
            CronTrigger(hour=10, minute=0, day_of_week='mon-fri'),
            id="pair_trading_midmorning"
        )

        # 10:30 - 아시아 선행지표
        self.scheduler.add_job(
            self.job_global_leader_asia,
            CronTrigger(hour=10, minute=30, day_of_week='mon-fri'),
            id="global_leader_asia"
        )

        # 10:30 - AI 리밸런싱 1차
        self.scheduler.add_job(
            self.job_ai_rebalancing,
            CronTrigger(hour=10, minute=30, day_of_week='mon-fri'),
            id="ai_rebalancing_1st"
        )

        # 14:00 - AI 리밸런싱 2차
        self.scheduler.add_job(
            self.job_ai_rebalancing,
            CronTrigger(hour=14, minute=0, day_of_week='mon-fri'),
            id="ai_rebalancing_2nd"
        )

        # 14:00 - 페어 트레이딩 마감
        self.scheduler.add_job(
            self.job_pair_trading_afternoon,
            CronTrigger(hour=14, minute=0, day_of_week='mon-fri'),
            id="pair_trading_afternoon"
        )

        # 15:20 - 현금 파킹
        self.scheduler.add_job(
            self.job_cash_optimization,
            CronTrigger(hour=15, minute=20, day_of_week='mon-fri'),
            id="cash_optimization"
        )

    # ========================================
    # POST-MARKET PHASE (15:30-20:00)
    # ========================================

    def _register_postmarket_jobs(self):
        """장 마감 후 잡 등록"""

        # 15:45 - 일봉 데이터 수집
        self.scheduler.add_job(
            self.job_daily_price_sync,
            CronTrigger(hour=15, minute=45, day_of_week='mon-fri'),
            id="daily_price_sync"
        )

        # 16:00 - 수급 컨센서스 수집
        self.scheduler.add_job(
            self.job_supply_consensus_sync,
            CronTrigger(hour=16, minute=0, day_of_week='mon-fri'),
            id="supply_consensus_sync"
        )

        # 16:10 - 세분화 투자자 데이터
        self.scheduler.add_job(
            self.job_detailed_investors_sync,
            CronTrigger(hour=16, minute=10, day_of_week='mon-fri'),
            id="detailed_investors_sync"
        )

        # 16:30 - 외국인 선물 마감 체크
        self.scheduler.add_job(
            self.job_derivative_monitoring,
            CronTrigger(hour=16, minute=30, day_of_week='mon-fri'),
            id="derivative_monitoring_closing"
        )

        # 16:30 - 일일 DB 백업
        self.scheduler.add_job(
            self.job_db_backup_daily,
            CronTrigger(hour=16, minute=30, day_of_week='mon-fri'),
            id="db_backup_daily"
        )

        # 18:00 - 유럽 선행지표
        self.scheduler.add_job(
            self.job_global_leader_europe,
            CronTrigger(hour=18, minute=0, day_of_week='mon-fri'),
            id="global_leader_europe"
        )

        # 20:10 - 일일 마감 처리
        self.scheduler.add_job(
            self.job_daily_closing,
            CronTrigger(hour=20, minute=10, day_of_week='mon-fri'),
            id="daily_closing"
        )

        # 21:00 - 저녁 심층 분석
        self.scheduler.add_job(
            self.job_evening_deep_analysis,
            CronTrigger(hour=21, minute=0, day_of_week='mon-fri'),
            id="evening_deep_analysis"
        )

    # ========================================
    # WEEKEND JOBS
    # ========================================

    def _register_weekend_jobs(self):
        """주말 잡 등록"""

        # === 토요일 ===

        # 03:00 - 주간 Full DB 백업
        self.scheduler.add_job(
            self.job_db_backup_weekly,
            CronTrigger(hour=3, minute=0, day_of_week='sat'),
            id="db_backup_weekly"
        )

        # 07:00 - 미국장 전체 스캔
        self.scheduler.add_job(
            self.job_weekend_full_scan,
            CronTrigger(hour=7, minute=0, day_of_week='sat'),
            id="weekend_full_scan"
        )

        # 08:00 - 미국장 마감 데이터
        self.scheduler.add_job(
            self.job_weekend_us_market,
            CronTrigger(hour=8, minute=0, day_of_week='sat'),
            id="weekend_us_market"
        )

        # 09:00 - 일봉 데이터 백필
        self.scheduler.add_job(
            self.job_weekend_backfill,
            CronTrigger(hour=9, minute=0, day_of_week='sat'),
            id="weekend_backfill"
        )

        # 10:00 - GARCH 변동성 업데이트
        self.scheduler.add_job(
            self.job_weekend_volatility,
            CronTrigger(hour=10, minute=0, day_of_week='sat'),
            id="weekend_volatility"
        )

        # 10:30 - 주말 뉴스 수집
        self.scheduler.add_job(
            self.job_saturday_news,
            CronTrigger(hour=10, minute=30, day_of_week='sat'),
            id="saturday_news"
        )

        # 11:00 - AI 주간 전략
        self.scheduler.add_job(
            self.job_ai_weekly_strategy,
            CronTrigger(hour=11, minute=0, day_of_week='sat'),
            id="ai_weekly_strategy"
        )

        # === 일요일 ===

        # 18:00 - 주간 리포트 생성
        self.scheduler.add_job(
            self.job_weekend_weekly_report,
            CronTrigger(hour=18, minute=0, day_of_week='sun'),
            id="weekend_weekly_report"
        )

        # 19:00 - 주말 뉴스 AI 분석
        self.scheduler.add_job(
            self.job_sunday_news_analysis,
            CronTrigger(hour=19, minute=0, day_of_week='sun'),
            id="sunday_news_analysis"
        )

        # 22:00 - 미국 선물 체크
        self.scheduler.add_job(
            self.job_sunday_premarket_check,
            CronTrigger(hour=22, minute=0, day_of_week='sun'),
            id="sunday_premarket_check"
        )

    # ========================================
    # JOB IMPLEMENTATIONS (순서: 데이터 수집 → AI 분석 → 실행)
    # ========================================

    # === PRE-MARKET ===

    @job_wrapper
    async def job_fetcher_health_check(self):
        """Fetcher 상태 점검"""
        # TODO: KIS/DART/Naver Fetcher 상태 체크
        pass

    @job_wrapper
    async def job_morning_deep_analysis(self):
        """심층 분석 (DeepSeek-R1)"""
        # TODO: DeepSeek-R1으로 심층 분석
        pass

    @job_wrapper
    async def job_global_leader_morning(self):
        """글로벌 선행지표"""
        # TODO: 미국 선물, 아시아 지수 체크
        pass

    @job_wrapper
    async def job_macro_update(self):
        """매크로 데이터 수집"""
        # TODO: YFinance로 글로벌 매크로 수집
        pass

    # === MARKET PREP ===

    @job_wrapper
    async def job_macro_monitoring(self):
        """매크로 모니터링"""
        # TODO: VIX, DXY, TNX 변화 감지
        pass

    @job_wrapper
    async def job_monday_final_check(self):
        """월요일 최종 체크"""
        # TODO: 주말 뉴스, 미국장 영향 분석
        pass

    @job_wrapper
    async def job_alpha_morning_gap(self):
        """갭 스캔"""
        # TODO: 갭상승/갭하락 종목 스캔
        pass

    @job_wrapper
    async def job_monday_strategy(self):
        """월요일 전략 결정"""
        # TODO: 주간 전략 최종 결정
        pass

    @job_wrapper
    async def job_derivative_monitoring(self):
        """외국인 선물 체크"""
        # TODO: 외국인 선물 포지션 모니터링
        pass

    @job_wrapper
    async def job_market_open(self):
        """장 시작 준비"""
        # TODO: 시스템 최종 체크, Telegram 알림
        pass

    @job_wrapper
    async def job_orchestrator_reset(self):
        """오케스트레이터 리셋"""
        # TODO: 전략 상태 초기화
        pass

    # === TRADING ===

    @job_wrapper
    async def job_portfolio_sync(self):
        """포트폴리오 동기화"""
        # TODO: KIS API 잔고 조회 → DB 동기화
        pass

    @job_wrapper
    async def job_portfolio_watchdog(self):
        """손절/익절 감시"""
        # TODO: 손절선(-2%), 익절선(+5.5%) 체크 → 자동 매도
        pass

    @job_wrapper
    async def job_auto_trading(self):
        """
        자동 매매 실행
        중요: 최신 데이터 수집 후 AI 실행
        """
        # Step 1: 데이터 갱신 (Just-in-Time Data Feeding)
        # - KIS: 현재가/호가 스냅샷
        # - Naver: 최신 뉴스
        # - KIS: 프로그램 매매 동향

        # Step 2: AI 분석
        # - DeepSeek-V3로 매수/매도 시그널 생성

        # Step 3: 매매 실행
        # - KIS API로 주문 전송
        pass

    @job_wrapper
    async def job_intraday_analysis(self):
        """장중 AI 분석 (Dynamic Schedule 적용)"""
        # Step 1: 최신 데이터 수집
        # Step 2: DeepSeek-V3 분석
        # Step 3: 시그널 DB 저장
        pass

    @job_wrapper
    async def job_market_regime_check(self):
        """시장 국면 판단"""
        # TODO: IRON_SHIELD/VANGUARD/GUERRILLA/STEALTH 판단
        pass

    @job_wrapper
    async def job_supply_data_sync(self):
        """수급 데이터 수집"""
        # TODO: 외국인/기관 순매수 상위 종목
        pass

    @job_wrapper
    async def job_hedge_management(self):
        """헷지 관리"""
        # TODO: 인버스 ETF 비중 조절
        pass

    @job_wrapper
    async def job_orchestrator_execute(self):
        """오케스트레이터 실행"""
        # TODO: 통합 전략 실행
        pass

    @job_wrapper
    async def job_dart_disclosure_scan(self):
        """DART 공시 스캔"""
        # TODO: 실시간 공시 크롤링, 호재/악재 분류
        pass

    @job_wrapper
    async def job_alpha_sector_rotation(self):
        """섹터 순환 체크"""
        # TODO: 섹터별 수익률 분석
        pass

    @job_wrapper
    async def job_naver_theme_scan(self):
        """테마 스캔"""
        # TODO: 네이버 테마 크롤링
        pass

    @job_wrapper
    async def job_data_fusion_scan(self):
        """데이터 융합 분석"""
        # TODO: 복합 데이터 분석
        pass

    @job_wrapper
    async def job_system_health_log(self):
        """시스템 상태 로그"""
        # TODO: CPU/메모리/API 호출 횟수 로깅
        pass

    @job_wrapper
    async def job_morning_cash_check(self):
        """현금 확보 체크"""
        # TODO: 현금 비중 확인
        pass

    @job_wrapper
    async def job_daily_status_log(self):
        """일일 상태 로그"""
        # TODO: 시스템 상태 종합 로그
        pass

    @job_wrapper
    async def job_pair_trading_morning(self):
        """페어 트레이딩 분석"""
        # TODO: 페어 트레이딩 기회 탐색
        pass

    @job_wrapper
    async def job_pair_trading_midmorning(self):
        """페어 트레이딩 체크"""
        pass

    @job_wrapper
    async def job_global_leader_asia(self):
        """아시아 선행지표"""
        # TODO: 일본/중국 시장 체크
        pass

    @job_wrapper
    async def job_ai_rebalancing(self):
        """AI 리밸런싱 (DeepSeek-R1)"""
        # TODO: 포트폴리오 최적화
        pass

    @job_wrapper
    async def job_pair_trading_afternoon(self):
        """페어 트레이딩 마감"""
        pass

    @job_wrapper
    async def job_cash_optimization(self):
        """현금 파킹"""
        # TODO: 여유 현금 단기 ETF 투자
        pass

    # === POST-MARKET ===

    @job_wrapper
    async def job_daily_price_sync(self):
        """일봉 데이터 수집"""
        # TODO: FinanceDataReader로 당일 OHLCV 수집
        pass

    @job_wrapper
    async def job_supply_consensus_sync(self):
        """수급 컨센서스 수집"""
        # TODO: pykrx로 최종 수급 데이터 수집
        pass

    @job_wrapper
    async def job_detailed_investors_sync(self):
        """세분화 투자자 데이터"""
        # TODO: 연기금/보험/신탁 등 세부 투자자
        pass

    @job_wrapper
    async def job_db_backup_daily(self):
        """일일 DB 백업"""
        # TODO: PostgreSQL 백업
        pass

    @job_wrapper
    async def job_global_leader_europe(self):
        """유럽 선행지표"""
        # TODO: 유럽 시장 체크
        pass

    @job_wrapper
    async def job_daily_closing(self):
        """일일 마감 처리"""
        # TODO: 오늘 거래 정산, Telegram 리포트
        pass

    @job_wrapper
    async def job_evening_deep_analysis(self):
        """저녁 심층 분석 (DeepSeek-R1)"""
        # TODO: 오늘 복기 + 내일 전략
        pass

    # === WEEKEND ===

    @job_wrapper
    async def job_db_backup_weekly(self):
        """주간 DB 백업"""
        pass

    @job_wrapper
    async def job_weekend_full_scan(self):
        """미국장 전체 스캔"""
        pass

    @job_wrapper
    async def job_weekend_us_market(self):
        """미국장 마감 데이터"""
        pass

    @job_wrapper
    async def job_weekend_backfill(self):
        """일봉 데이터 백필"""
        pass

    @job_wrapper
    async def job_weekend_volatility(self):
        """GARCH 변동성 업데이트"""
        pass

    @job_wrapper
    async def job_saturday_news(self):
        """주말 뉴스 수집"""
        pass

    @job_wrapper
    async def job_ai_weekly_strategy(self):
        """AI 주간 전략 (DeepSeek-R1)"""
        pass

    @job_wrapper
    async def job_weekend_weekly_report(self):
        """주간 리포트 생성"""
        pass

    @job_wrapper
    async def job_sunday_news_analysis(self):
        """주말 뉴스 AI 분석 (DeepSeek-V3)"""
        pass

    @job_wrapper
    async def job_sunday_premarket_check(self):
        """미국 선물 체크"""
        pass

    # ========================================
    # UTILITY
    # ========================================

    def get_scheduler_status(self):
        """스케줄러 상태 조회"""
        jobs = self.scheduler.get_jobs()
        return {
            "total_jobs": len(jobs),
            "jobs": [
                {
                    "id": j.id,
                    "next_run": j.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if j.next_run_time else None,
                }
                for j in jobs
            ]
        }

    def stop(self):
        """스케줄러 중지"""
        self.scheduler.shutdown()
        logger.info("🛑 Scheduler Stopped")


# ========================================
# MAIN
# ========================================

async def main():
    """메인 실행 함수"""
    scheduler = AEGISScheduler()
    scheduler.start()

    try:
        # 무한 대기
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # asyncio 실행
    asyncio.run(main())
