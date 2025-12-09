# Event-Driven Fetcher: 감찰병 개념

> 작성일: 2025-12-09
> 중요도: ⭐⭐⭐⭐⭐
> 개념: Fetcher는 절대 쉬지 않는 감찰병

---

## 🎯 핵심 개념: "Fetcher는 잠시도 쉬면 안된다"

### ❌ 기존 개념 (스케줄만 의존)

```
09:00 - Fetcher 실행 (스케줄)
09:10 - Fetcher 실행 (스케줄)
09:20 - Fetcher 실행 (스케줄)
...

문제:
- 09:05에 중요 뉴스 발생 → 09:10까지 대기 (5분 지연!)
- 매수 체결 직후 → 다음 스케줄까지 대기
- 급등주 발견 → 다음 스케줄까지 대기
```

### ✅ 새로운 개념 (Event-driven + Schedule)

```
Fetcher = 감찰병 (Watcher + Scout)

역할:
1. 스케줄 기반 정찰 (예정된 순찰)
2. 이벤트 기반 즉시 출동 (긴급 상황)

절대 쉬지 않음:
- 24시간 대기 상태
- 이벤트 발생 시 즉시 실행
- 스케줄 시간에도 실행
```

---

## 📡 Fetcher 트리거 조건

### 1️⃣ 스케줄 기반 (Schedule-driven)

```python
# Dynamic Scheduler가 정기적으로 실행
09:00, 09:10, 09:20, ... (오전장 10분)
10:00, 11:00, 12:00, ... (점심장 60분)
13:00, 13:20, 13:40, ... (오후장 20분)
15:00, 15:10, 15:20    (막판 10분)
```

**용도**: 정기 점검, 전반적 시장 상황 파악

### 2️⃣ WebSocket 체결 통보 (Execution Notice)

```python
# KIS WebSocket H0STCNI0 체결 통보 수신 시 즉시 실행
매수 체결 발생:
├─ 체결 통보 수신 (0.1초 이내)
├─ 즉시 해당 종목 Fetcher 실행
└─ 최신 데이터 수집 (뉴스, 수급, 호가)

매도 체결 발생:
├─ 체결 통보 수신
├─ 포트폴리오 업데이트
└─ WebSocket 슬롯 해제 고려
```

**용도**: 매수 직후 즉시 모니터링 시작

### 3️⃣ 속보 뉴스 발생 (Breaking News)

```python
# Naver 속보 API 폴링 (30초마다)
속보 발견:
├─ 관련 종목 식별
├─ 즉시 해당 종목 Fetcher 실행
└─ 영향도 분석 (Brain에 전달)

예시:
- "삼성전자 3분기 실적 서프라이즈" 발견
  → 즉시 삼성전자 Fetcher 실행
  → DART 공시 확인
  → 수급 데이터 업데이트
  → Brain 분석 트리거
```

**용도**: 시장 변동성에 즉시 대응

### 4️⃣ 공시 발생 (DART Disclosure)

```python
# DART API 폴링 (5분마다)
공시 발견:
├─ 중요도 필터링 (매출, 투자, M&A 등)
├─ 즉시 해당 종목 Fetcher 실행
└─ AI 공시 분석 (DeepSeek/Gemini)

예시:
- "유상증자 공시" 발견 → 즉시 분석 → 매도 검토
- "배당 공시" 발견 → 즉시 분석 → 매수 검토
```

**용도**: 펀더멘털 변화 즉시 반영

### 5️⃣ Market Scanner 급등주 발견

```python
# Market Scanner (1분마다)
급등주 발견 (gemini 70점 이상):
├─ 즉시 해당 종목 Fetcher 실행
├─ WebSocket Priority 3 구독
└─ 실시간 모니터링 시작

예시:
- 10:05 - 카카오 +8% 급등 발견
  → 즉시 Fetcher 실행
  → 급등 원인 파악 (뉴스, 공시)
  → Brain 분석
  → 매수 검토
```

**용도**: 급등주 즉시 포착 및 분석

### 6️⃣ 시장 지표 급변 (Market Regime Change)

```python
# VIX, NASDAQ, SOX 등 모니터링
지표 급변 발견:
├─ 전체 Fetcher 즉시 실행
├─ 포트폴리오 리스크 재평가
└─ 손절가 조정 검토

예시:
- VIX 20 → 30 급등 (공포)
  → 전체 종목 Fetcher 실행
  → IRON_SHIELD 모드 전환
  → 매수 중단, 손절가 -3%로 강화
```

**용도**: 시장 전체 위기 대응

---

## 🔄 Event-driven Fetcher 구조

### 아키텍처

```python
┌─────────────────────────────────────────────┐
│  Event Bus (이벤트 버스)                     │
│  - WebSocket 체결 통보                       │
│  - 속보 뉴스                                  │
│  - DART 공시                                 │
│  - Market Scanner 발견                      │
│  - 시장 지표 변동                             │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│  Fetcher Dispatcher (즉시 실행 관리)         │
│  - 이벤트 우선순위 판단                       │
│  - 중복 실행 방지 (debounce)                 │
│  - 즉시 해당 Fetcher 트리거                   │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│  Stock-specific Fetcher (종목별 실행)        │
│  1. KIS API: 현재가, 호가, 수급               │
│  2. Naver: 최근 뉴스 (3시간 이내)             │
│  3. DART: 공시 (당일)                        │
│  4. pykrx: 외국인/기관 수급                  │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│  Database (즉시 업데이트)                     │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│  Brain Pipeline (즉시 분석)                  │
│  - Brain Analyzer (Quant + AI)             │
│  - Sonnet 4.5 Commander (최종 결정)          │
│  - Order Service (즉시 주문)                 │
└─────────────────────────────────────────────┘
```

---

## 💻 구현 예시

### 1. Event Bus

```python
# events/event_bus.py
import asyncio
from typing import Callable, Dict, List
from enum import Enum

class EventType(Enum):
    EXECUTION_NOTICE = "execution_notice"    # 체결 통보
    BREAKING_NEWS = "breaking_news"          # 속보
    DART_DISCLOSURE = "dart_disclosure"      # 공시
    HOT_STOCK_FOUND = "hot_stock_found"      # 급등주 발견
    MARKET_REGIME_CHANGE = "market_regime_change"  # 시장 지표 급변

class Event:
    def __init__(self, event_type: EventType, data: dict):
        self.type = event_type
        self.data = data
        self.timestamp = datetime.now()

class EventBus:
    """이벤트 버스 (Singleton)"""

    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}

    def subscribe(self, event_type: EventType, callback: Callable):
        """이벤트 구독"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    async def publish(self, event: Event):
        """이벤트 발행 (즉시 실행)"""
        if event.type in self.subscribers:
            for callback in self.subscribers[event.type]:
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"❌ Event handler error: {e}")

# Singleton
event_bus = EventBus()
```

### 2. Fetcher Dispatcher

```python
# fetchers/fetcher_dispatcher.py
from events.event_bus import event_bus, EventType, Event
from fetchers.stock_fetcher import stock_fetcher

class FetcherDispatcher:
    """Fetcher 즉시 실행 관리자"""

    def __init__(self):
        self.running_fetchers = set()  # 현재 실행 중인 종목

        # 이벤트 구독
        event_bus.subscribe(EventType.EXECUTION_NOTICE, self.on_execution)
        event_bus.subscribe(EventType.BREAKING_NEWS, self.on_breaking_news)
        event_bus.subscribe(EventType.HOT_STOCK_FOUND, self.on_hot_stock)

    async def on_execution(self, event: Event):
        """체결 통보 수신 시"""
        stock_code = event.data['stock_code']
        logger.info(f"🔔 Execution notice: {stock_code}, triggering Fetcher")

        # 즉시 Fetcher 실행
        await self.trigger_fetcher(stock_code, reason="execution_notice")

    async def on_breaking_news(self, event: Event):
        """속보 발견 시"""
        stock_code = event.data['stock_code']
        news_title = event.data['title']
        logger.info(f"📰 Breaking news: {news_title}, triggering Fetcher")

        # 즉시 Fetcher 실행
        await self.trigger_fetcher(stock_code, reason="breaking_news")

    async def on_hot_stock(self, event: Event):
        """급등주 발견 시"""
        stock_code = event.data['stock_code']
        logger.info(f"🔥 Hot stock found: {stock_code}, triggering Fetcher")

        # 즉시 Fetcher 실행
        await self.trigger_fetcher(stock_code, reason="hot_stock")

    async def trigger_fetcher(self, stock_code: str, reason: str):
        """
        Fetcher 즉시 실행

        중복 방지:
        - 이미 실행 중이면 스킵 (debounce)
        """
        if stock_code in self.running_fetchers:
            logger.debug(f"⏸️  Fetcher already running for {stock_code}, skipping")
            return

        try:
            self.running_fetchers.add(stock_code)

            # Stock-specific Fetcher 실행
            await stock_fetcher.fetch_single_stock(stock_code, reason=reason)

        finally:
            self.running_fetchers.discard(stock_code)

# Singleton
fetcher_dispatcher = FetcherDispatcher()
```

### 3. Stock-specific Fetcher

```python
# fetchers/stock_fetcher.py
class StockFetcher:
    """종목별 즉시 데이터 수집"""

    async def fetch_single_stock(self, stock_code: str, reason: str):
        """
        특정 종목 즉시 데이터 수집

        Args:
            stock_code: 종목 코드
            reason: 트리거 이유 (execution_notice, breaking_news 등)
        """
        logger.info(f"🔍 Fetcher triggered for {stock_code} (reason: {reason})")

        # 1️⃣ KIS API: 현재가, 호가
        try:
            current_price = await kis_client.get_current_price(stock_code)
            orderbook = await kis_client.get_orderbook(stock_code)
            logger.info(f"  ✅ KIS data fetched")
        except Exception as e:
            logger.error(f"  ❌ KIS fetch failed: {e}")

        # 2️⃣ Naver: 최근 뉴스 (3시간 이내)
        try:
            latest_news = await naver_fetcher.get_latest_news(stock_code, hours=3)
            logger.info(f"  ✅ News fetched: {len(latest_news)} items")
        except Exception as e:
            logger.error(f"  ❌ News fetch failed: {e}")

        # 3️⃣ DART: 당일 공시
        try:
            disclosures = await dart_fetcher.get_today_disclosures(stock_code)
            logger.info(f"  ✅ DART fetched: {len(disclosures)} disclosures")
        except Exception as e:
            logger.error(f"  ❌ DART fetch failed: {e}")

        # 4️⃣ DB 즉시 업데이트
        db = next(get_db())
        # ... DB 업데이트 로직
        db.commit()

        # 5️⃣ Brain Pipeline 즉시 트리거
        await self._trigger_brain_pipeline(stock_code)

        logger.info(f"✅ Fetcher complete for {stock_code}")

    async def _trigger_brain_pipeline(self, stock_code: str):
        """Brain Pipeline 즉시 실행"""
        from pipeline.intraday_pipeline import intraday_pipeline

        # 해당 종목만 분석
        await intraday_pipeline.run_single_stock(stock_code)

# Singleton
stock_fetcher = StockFetcher()
```

### 4. WebSocket 연동

```python
# websocket/kis_websocket_manager.py (기존 파일 수정)

# H0STCNI0 체결 통보 핸들러 수정
async def _on_execution_notice(self, data: dict):
    """체결 통보 수신"""
    stock_code = data['stock_code']

    # 1. 기존 로직 (DB 업데이트)
    await kis_fetcher.on_execution_notice(data)

    # 2. [NEW] 이벤트 발행 (즉시 Fetcher 트리거)
    from events.event_bus import event_bus, Event, EventType

    await event_bus.publish(Event(
        event_type=EventType.EXECUTION_NOTICE,
        data={'stock_code': stock_code, 'execution_data': data}
    ))

    logger.info(f"🔔 Execution event published for {stock_code}")
```

---

## 📊 실행 흐름 예시

### Case 1: 매수 체결 발생

```
09:05:23.456 - 삼성전자 매수 체결 (100주)
   ↓ (0.1초 이내)
09:05:23.500 - WebSocket H0STCNI0 수신
   ↓ (즉시)
09:05:23.501 - Event Bus 발행 (EXECUTION_NOTICE)
   ↓ (즉시)
09:05:23.502 - Fetcher Dispatcher 트리거
   ↓ (즉시)
09:05:23.503 - Stock Fetcher 실행 (삼성전자)
   ├─ KIS API: 현재가 78,500원
   ├─ Naver: 최근 뉴스 5건
   ├─ DART: 공시 없음
   └─ DB 업데이트
   ↓ (3초)
09:05:26.500 - Brain Pipeline 트리거
   ├─ Brain Analyzer: Final Score 82
   ├─ Sonnet 4.5 Commander: "HOLD, 단기 과열"
   └─ 결정: 추가 매수 보류
   ↓ (2초)
09:05:28.500 - 완료

총 소요 시간: 5초
```

### Case 2: 속보 뉴스 발견

```
10:15:00 - Naver 속보 크롤링
   ↓
"SK하이닉스 HBM3 독점 공급 계약 체결" 발견
   ↓ (즉시)
10:15:00.100 - Event Bus 발행 (BREAKING_NEWS)
   ↓ (즉시)
10:15:00.101 - Fetcher Dispatcher 트리거
   ↓ (즉시)
10:15:00.102 - Stock Fetcher 실행 (SK하이닉스)
   ├─ KIS API: 현재가 151,000원 (+3%)
   ├─ Naver: 뉴스 상세 분석
   ├─ DART: 공시 확인
   └─ DB 업데이트
   ↓ (3초)
10:15:03.100 - Brain Pipeline 트리거
   ├─ Brain Analyzer: Final Score 88
   ├─ Sonnet 4.5 Commander: "BUY, 펀더멘털 강화"
   └─ 결정: 즉시 매수 (200만원)
   ↓ (2초)
10:15:05.100 - 주문 체결

총 소요 시간: 5초 (뉴스 발생 → 매수 완료)
```

---

## 🎯 핵심 원칙

### 1. 절대 쉬지 않는다
```
Fetcher는 24시간 대기 상태:
- 스케줄 시간: 정기 실행
- 이벤트 발생: 즉시 실행
- 동시에 두 가지 모두 작동
```

### 2. 즉시 실행 (No Polling)
```
❌ 1분마다 확인 (Polling)
✅ 이벤트 즉시 수신 및 실행 (Event-driven)
```

### 3. 중복 방지 (Debounce)
```
같은 종목 Fetcher가 이미 실행 중이면:
- 새 요청 무시
- 실행 중인 Fetcher 완료 대기
```

### 4. 우선순위
```
1. 체결 통보 (최우선)
2. 속보 뉴스
3. DART 공시
4. 급등주 발견
5. 스케줄 (정기)
```

---

## 📋 구현 완료 체크리스트

```
Phase 4.5: Event-driven Fetcher

⏳ Event Bus 구현
⏳ Fetcher Dispatcher 구현
⏳ Stock Fetcher (종목별) 구현
⏳ WebSocket 연동 (체결 통보 → 이벤트)
⏳ Naver 속보 폴링 → 이벤트
⏳ DART 공시 폴링 → 이벤트
⏳ Market Scanner 연동
⏳ Pipeline 즉시 실행 메서드
```

---

**작성**: Claude Code
**개념**: Fetcher = 절대 쉬지 않는 감찰병
**다음**: 실제 구현 시작
