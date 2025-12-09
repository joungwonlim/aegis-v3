# Intraday Pipeline 설계: Just-in-Time Data Feeding

> 작성일: 2025-12-09
> 상태: 설계
> Phase: 3
> **핵심**: Fetching → Pre-processing → Brain 순서 엄수!

---

## 🎯 핵심 원칙

### ❌ 절대 금지: 뒷북 분석

```python
# ❌ 잘못된 순서 (AI가 오래된 데이터를 봄)
await brain.analyze()  # 1시간 전 데이터로 분석
await fetcher.sync()   # 지금 데이터 수집 (늦음!)
```

### ✅ 올바른 순서: Just-in-Time

```python
# ✅ 올바른 순서 (AI가 최신 데이터를 봄)
await fetcher.sync()   # 지금 당장 데이터 수집
await db.commit()      # DB 저장 완료
await brain.analyze()  # 따끈따끈한 데이터로 분석
```

---

## 🔄 Pipeline 5단계

```
┌──────────────────────────────────────────────────────┐
│  1️⃣ FETCHING (수집)                                  │
│  ├─ KIS API: 현재가, 호가, 수급                      │
│  ├─ Naver: 최신 뉴스 (방금 뜬 것)                     │
│  ├─ Pykrx: 프로그램 매매 (외국인/기관 동향)          │
│  └─ DART: 공시 (전날 대비 신규만)                    │
└──────────────┬───────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│  2️⃣ PRE-PROCESSING (가공)                           │
│  ├─ DB 저장 (Bulk Insert)                           │
│  ├─ 지표 계산 (수급 강도, 뉴스 스코어)               │
│  └─ AI 읽기 형식 변환 (JSON → Prompt)               │
└──────────────┬───────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│  3️⃣ BRAIN (AI 판단)                                 │
│  ├─ gemini-2.0-flash: 빠른 스코어링 (1~2초)         │
│  ├─ DeepSeek R1: 심층 분석 (일일 1회)               │
│  └─ 매수 후보 선정 (70점 이상)                       │
└──────────────┬───────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│  4️⃣ SCENARIO VALIDATION (검증)                      │
│  ├─ 과거 3개월 유사 패턴 검색                        │
│  ├─ 평균 최대 수익률 계산                            │
│  ├─ AI 목표가 vs 통계 목표가 대조                   │
│  └─ 보정된 목표가 산출 (Conservative)               │
└──────────────┬───────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│  5️⃣ EXECUTION (실행)                                │
│  ├─ OrderService: 매수 주문                          │
│  ├─ WebSocket 구독 추가 (Priority 1)                 │
│  └─ Telegram 알림                                    │
└──────────────────────────────────────────────────────┘
```

---

## 📊 데이터 종류별 수집 전략

### 실시간 데이터 (WebSocket)

**특징**: 초 단위 변동, 자동 수신

```python
# WebSocket이 자동으로 업데이트 (별도 fetch 불필요)
- 현재가 (H0STCNT0)
- 호가 (H0STASP0)
- 프로그램 매매 (H0STPGM0)
- 체결 통보 (H0STCNI0)
```

**전략**: Brain은 캐시된 값을 읽기만 하면 됨

---

### 분 단위 데이터 (REST API)

**특징**: 분 단위 변동, Pipeline 직전 fetch

```python
# Brain 실행 0.1초 전에 fetch
await naver_fetcher.fetch_breaking_news()      # 최신 속보
await kis_fetcher.get_program_trend()          # 집계된 수급
await pykrx_fetcher.get_sector_money_flow()    # 업종별 자금 이동
```

**전략**: `intraday_pipeline()` 함수 내에서 순차 실행

---

### 정적 데이터 (DB 캐시)

**특징**: 일/분기 단위 변동, DB에서 읽기만

```python
# DB에 저장된 것 그냥 씀 (매번 fetch 불필요)
- 재무제표 (분기별)
- 기업 정보 (연 단위)
- 과거 OHLCV (일봉)
```

**전략**: Brain이 DB 직접 조회

---

## 💻 구현: intraday_pipeline.py

```python
"""
AEGIS v3.0 - Intraday Pipeline
Fetching → Pre-processing → Brain → Validation → Execution
"""
import asyncio
from datetime import datetime
import logging

from fetchers.kis_fetcher import kis_fetcher
from fetchers.naver_fetcher import naver_fetcher
from fetchers.pykrx_fetcher import pykrx_fetcher
from brain.screener import screener
from brain.scenario_validator import scenario_validator
from services.order_service import order_service
from fetchers.websocket_manager import ws_manager
from app.database import SessionLocal

logger = logging.getLogger(__name__)


async def intraday_pipeline():
    """
    Intraday Analysis Pipeline

    순서 엄수:
    1. Fetching (최신 데이터 수집)
    2. Pre-processing (DB 저장 및 가공)
    3. Brain (AI 분석)
    4. Validation (시나리오 검증)
    5. Execution (주문 실행)

    실행 주기:
    - 오전장: 10분 (09:00~10:00)
    - 점심장: 60분 (10:00~13:00)
    - 오후장: 20분 (13:00~15:00)
    - 막판: 10분 (15:00~15:20)
    """

    logger.info("=" * 70)
    logger.info("🔄 Intraday Pipeline Started")
    logger.info("=" * 70)

    db = SessionLocal()

    try:
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 1️⃣ FETCHING (수집) - Just-in-Time
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        logger.info("📡 [Step 1/5] Fetching Latest Data...")

        # A. 포트폴리오 동기화 (KIS API → DB)
        logger.info("  ├─ Syncing portfolio (KIS API)...")
        await kis_fetcher.sync_portfolio()

        # B. 최신 뉴스 크롤링 (Naver)
        logger.info("  ├─ Fetching breaking news (Naver)...")
        latest_news = await naver_fetcher.fetch_breaking_news()

        # C. 프로그램 매매 동향 (KIS API)
        logger.info("  ├─ Fetching program trading trend (KIS)...")
        program_trend = await kis_fetcher.get_program_trend()

        # D. 업종별 자금 흐름 (Pykrx)
        logger.info("  ├─ Fetching sector money flow (Pykrx)...")
        sector_flow = await pykrx_fetcher.get_sector_money_flow()

        logger.info("  └─ ✅ Fetching complete")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2️⃣ PRE-PROCESSING (가공)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        logger.info("🔧 [Step 2/5] Pre-processing...")

        # DB 커밋 (Fetcher가 저장한 데이터 확정)
        await db.commit()
        logger.info("  └─ ✅ DB commit complete")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 3️⃣ BRAIN (AI 판단)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        logger.info("🧠 [Step 3/5] Brain Analysis...")

        # Market Scanner의 급등주 + Daily Picks 결합
        # Screener가 70점 이상 필터링
        candidates = await screener.run(
            program_net_buy=program_trend['net_buy'],
            sector_flow=sector_flow,
            news_score=latest_news['score']
        )

        logger.info(f"  └─ ✅ Found {len(candidates)} candidates (score >= 70)")

        if not candidates:
            logger.info("⏭️  No candidates found. Skipping execution.")
            return

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 4️⃣ SCENARIO VALIDATION (검증)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        logger.info("🔍 [Step 4/5] Scenario Validation...")

        validated_candidates = []

        for candidate in candidates:
            # 과거 3개월 유사 패턴 검증
            validation = await scenario_validator.validate(
                stock_code=candidate['stock_code'],
                ai_target_pct=candidate['target_return'],
                current_pattern=candidate['pattern']
            )

            if validation['approved']:
                # 목표가 보정
                candidate['adjusted_target'] = validation['adjusted_target']
                candidate['confidence'] = validation['confidence']
                validated_candidates.append(candidate)

                logger.info(
                    f"  ✅ {candidate['stock_name']}: "
                    f"AI {candidate['target_return']:.1f}% → "
                    f"Adjusted {validation['adjusted_return']:.1f}% "
                    f"(Confidence: {validation['confidence']:.0f}%)"
                )
            else:
                logger.warning(
                    f"  ⚠️  {candidate['stock_name']}: "
                    f"Rejected (Win rate: {validation['win_rate']:.0f}%)"
                )

        logger.info(f"  └─ ✅ {len(validated_candidates)}/{len(candidates)} validated")

        if not validated_candidates:
            logger.info("⏭️  No validated candidates. Skipping execution.")
            return

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 5️⃣ EXECUTION (실행)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        logger.info("🚀 [Step 5/5] Order Execution...")

        for candidate in validated_candidates[:3]:  # 최대 3개만 매수
            try:
                # 매수 주문
                result = await order_service.place_buy_order(
                    stock_code=candidate['stock_code'],
                    stock_name=candidate['stock_name'],
                    quantity=candidate['quantity'],
                    price=candidate['entry_price'],
                    market=candidate.get('market', 'KRX')
                )

                # WebSocket 구독 추가 (Priority 1: 보유종목)
                await ws_manager.subscribe(
                    stock_code=candidate['stock_code'],
                    stock_name=candidate['stock_name'],
                    priority=1
                )

                logger.info(
                    f"  ✅ Buy order placed: {candidate['stock_name']} "
                    f"{candidate['quantity']}주 @ {candidate['entry_price']:,}원"
                )

            except Exception as e:
                logger.error(f"  ❌ Order failed: {candidate['stock_name']} - {e}")

        logger.info("=" * 70)
        logger.info("✅ Intraday Pipeline Complete")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Pipeline error: {e}")
        await db.rollback()
        raise

    finally:
        db.close()
```

---

## ⏰ Dynamic Scheduler (10-60-30 전략)

```python
"""
AEGIS v3.0 - Dynamic Scheduler
시간대별 차등 실행: 거래 활발한 시간에 집중
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

from pipeline.intraday_pipeline import intraday_pipeline
from brain.daily_analyzer import daily_analyzer

logger = logging.getLogger(__name__)


class DynamicScheduler:
    """
    Dynamic Scheduler (10-60-30 전략)

    시간대별 실행 주기:
    - 09:00~10:00: 10분 (오전장 집중)
    - 10:00~13:00: 60분 (점심장 휴식)
    - 13:00~15:00: 20분 (오후장 안정)
    - 15:00~15:20: 10분 (막판 스퍼트)
    - 07:20: DeepSeek R1 전체 분석 (일일 1회)
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """스케줄러 시작"""

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Layer 3: Daily Analysis (07:20)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        self.scheduler.add_job(
            daily_analyzer.analyze_all,
            CronTrigger(hour=7, minute=20, day_of_week='mon-fri'),
            id="daily_analysis"
        )
        logger.info("📅 Scheduled: Daily Analysis (07:20)")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Layer 2: Intraday Pipeline (Dynamic)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        # 🔥 오전장 집중 (09:00~10:00): 10분 간격
        self.scheduler.add_job(
            intraday_pipeline,
            CronTrigger(hour=9, minute='0,10,20,30,40,50', day_of_week='mon-fri'),
            id="intraday_morning"
        )
        logger.info("📅 Scheduled: Morning Rush (09:00~10:00, 10min)")

        # 💤 점심장 관망 (10:00~13:00): 1시간 간격
        self.scheduler.add_job(
            intraday_pipeline,
            CronTrigger(hour='10-12', minute=0, day_of_week='mon-fri'),
            id="intraday_lunch"
        )
        logger.info("📅 Scheduled: Lunch Watch (10:00~13:00, 60min)")

        # 🌤️ 오후장 안정 (13:00~15:00): 20분 간격
        self.scheduler.add_job(
            intraday_pipeline,
            CronTrigger(hour='13-14', minute='0,20,40', day_of_week='mon-fri'),
            id="intraday_afternoon"
        )
        logger.info("📅 Scheduled: Afternoon Stable (13:00~15:00, 20min)")

        # 🏁 막판 스퍼트 (15:00~15:20): 10분 간격
        self.scheduler.add_job(
            intraday_pipeline,
            CronTrigger(hour=15, minute='0,10,20', day_of_week='mon-fri'),
            id="intraday_closing"
        )
        logger.info("📅 Scheduled: Closing Sprint (15:00~15:20, 10min)")

        # 스케줄러 시작
        self.scheduler.start()
        logger.info("✅ Dynamic Scheduler started")

    def stop(self):
        """스케줄러 정지"""
        self.scheduler.shutdown()
        logger.info("🛑 Dynamic Scheduler stopped")


# Singleton Instance
scheduler = DynamicScheduler()
```

---

## 🎯 핵심 요약

### 1. 순서가 생명

```
Fetcher → DB → Brain
(절대 Brain → Fetcher 순서 안 됨!)
```

### 2. Just-in-Time Data Feeding

- AI 실행 **0.1초 전**에 데이터 수집
- WebSocket은 자동, 뉴스/수급은 fetch 필요

### 3. Dynamic Schedule (10-60-30)

- 거래 활발한 시간에 집중
- 점심시간에는 휴식 (비용 절감)

### 4. Scenario Validation

- AI 목표가를 과거 통계로 검증
- 보수적 보정 (Conservative)

---

**작성**: Claude Code
**상태**: 설계 완료
**다음**: 구현 시작
