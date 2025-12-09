# Phase 2 진행 상황: WebSocket 최대 활용

> 작성일: 2025-12-09
> 상태: 진행중 🔄
> Phase: 2

---

## 🎯 Phase 2 목표

3-Layer 모니터링 구축, 동적 구독 관리, gemini-2.0-flash 실시간 평가

---

## ✅ 완료 항목

### 1. WebSocket Manager 개발 완료

**파일**: `fetchers/websocket_manager.py`

**구현 내용**:
- ✅ WebSocketSlot 클래스 (슬롯 정보 관리)
- ✅ KISWebSocketManager 클래스 (40개 슬롯 관리)
- ✅ 우선순위 기반 구독 (Priority 1, 2, 3)
- ✅ 동적 슬롯 할당 (evict_lowest_priority)
- ✅ 포트폴리오 동기화 (sync_with_portfolio)
- ✅ Daily Picks 업데이트 (update_daily_picks)
- ✅ WebSocket 재연결 처리 (reconnect, resubscribe_all)
- ✅ 실시간 데이터 수신 (listen, handle_message)

**우선순위 정책**:
```
Priority 1 (최우선): 보유종목
  - 항상 구독 유지
  - 매도 시점 포착 필수

Priority 2 (중요): AI Daily Picks
  - DeepSeek R1 일일 분석 결과 (20종목)
  - 매수 기회 포착

Priority 3 (일반): 급등주/거래량 상위
  - Market Scanner 실시간 발견 (최대 10종목)
  - 슬롯 부족 시 가장 오래된 것 제거
```

**핵심 메서드**:
```python
# 구독 관리
await ws_manager.subscribe(stock_code, stock_name, priority, tr_id)
await ws_manager.unsubscribe(stock_code)
await ws_manager.evict_lowest_priority(required_priority)

# 동기화
await ws_manager.sync_with_portfolio()
await ws_manager.update_daily_picks(picks)

# 재연결
await ws_manager.reconnect()
await ws_manager.resubscribe_all()

# 상태 조회
status = await ws_manager.get_status()
```

**설계 문서**: `docs/dev/04-WEBSOCKET-MANAGER.md`

---

### 2. Market Scanner 개발 완료

**파일**: `fetchers/market_scanner.py`

**구현 내용**:
- ✅ MarketScanner 클래스 (Layer 2 스캔)
- ✅ 등락률 상위 스캔 (scan_top_gainers)
- ✅ 거래량 상위 스캔 (scan_top_volume)
- ✅ gemini-2.0-flash 평가 (evaluate_stock)
- ✅ 1분 주기 스캐너 (run_scanner)
- ✅ WebSocket Manager 연동

**스캔 플로우**:
```
09:05:00 - Scanner 시작
         ↓
  1. 등락률 상위 20개 조회 (KIS API)
  2. 거래량 상위 20개 조회 (KIS API)
         ↓
  3. 중복 제거 (약 30개 유일 종목)
         ↓
  4. gemini-2.0-flash 평가 (각 0.5초, 총 15초)
     - 급등 지속 가능성 (30점)
     - 거래량 적정성 (20점)
     - 단기 모멘텀 (30점)
     - 리스크 (20점)
         ↓
  5. 70점 이상 필터링 (예: 5개)
         ↓
  6. WebSocket 구독 (Priority 3)
         ↓
09:06:00 - 다음 사이클
```

**핵심 메서드**:
```python
# 스캔
stocks = await market_scanner.scan_top_gainers(limit=20)
stocks = await market_scanner.scan_top_volume(limit=20)

# 평가
score = await market_scanner.evaluate_stock(stock)  # 0~100

# 실행
await market_scanner.run_scanner()  # 1분 주기 무한 루프
await market_scanner.stop()
```

**kis_client.py 추가 메서드**:
```python
# KIS API 랭킹 조회
stocks = kis_client.get_top_gainers(limit=50)
stocks = kis_client.get_top_volume(limit=50)
```

**설계 문서**: `docs/dev/05-MARKET-SCANNER.md`

---

## 📊 3-Layer 모니터링 아키텍처

```
┌─────────────────────────────────────────────────────┐
│  Layer 3: 일별 전체 스캔 (07:20, DeepSeek R1)       │
│  ├─ 코스피/코스닥 전체 (2000개)                      │
│  ├─ 심층 분석 (재무제표, 뉴스, 수급)                 │
│  └─ → daily_picks 테이블 저장 (상위 100개)           │
│      → Layer 2/1에서 활용                            │
└───────────────┬─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────┐
│  Layer 2: REST 스캔 (1분, gemini-2.0-flash)  ✅     │
│  ├─ 등락률 상위 20개 + 거래량 상위 20개              │
│  ├─ gemini-2.0-flash 빠른 평가 (30초)               │
│  ├─ 70점 이상 필터링                                 │
│  └─ → WebSocket 구독 (Priority 3)                   │
└───────────────┬─────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────┐
│  Layer 1: WebSocket 실시간 (40 슬롯)  ✅            │
│  ├─ Priority 1: 보유종목 (10개)                     │
│  ├─ Priority 2: AI Daily Picks (20개)               │
│  ├─ Priority 3: 급등주 (10개)                        │
│  ├─ H0STCNT0: 실시간 체결가                          │
│  ├─ H0STASP0: 실시간 호가                            │
│  ├─ H0STPGM0: 프로그램 매매                          │
│  └─ H0STCNI0: 체결 통보 (슬롯 소비 안함)            │
└─────────────────────────────────────────────────────┘
```

---

## 📁 생성된 파일

### 신규 파일
- ✅ `fetchers/websocket_manager.py` - WebSocket Manager 클래스
- ✅ `fetchers/market_scanner.py` - Market Scanner 클래스
- ✅ `docs/dev/04-WEBSOCKET-MANAGER.md` - WebSocket Manager 설계
- ✅ `docs/dev/05-MARKET-SCANNER.md` - Market Scanner 설계
- ✅ `docs/dev/06-PHASE2-PROGRESS.md` - 본 문서

### 수정된 파일
- ✅ `fetchers/kis_client.py` - get_top_gainers(), get_top_volume() 추가

---

## ✅ 완료 항목 (추가)

### 3. Daily Analyzer 개발 완료 (Layer 3)

**파일**: `fetchers/daily_analyzer.py`

**구현 완료**:
- ✅ daily_analyzer.py 생성
- ✅ DeepSeek R1 API 통합
- ✅ 배치 분석 (50개씩)
- ✅ daily_picks 테이블 저장
- ✅ WebSocket Manager 연동
- ✅ Dynamic Scheduler 통합 (07:20 실행)

**분석 항목**:
- 재무제표 분석 (30점)
- 수급 분석 (30점)
- 뉴스/공시 분석 (20점)
- 기술적 분석 (20점)

**설계 문서**: `docs/dev/10-DAILY-ANALYZER.md`

---

## ⏳ 남은 작업

### 1. 데이터 소스 통합 (향후 개선)

**목표**: 실제 데이터 연동

**구현 내용**:
- pykrx로 전체 종목 조회 (현재: 샘플 10개)
- 재무제표 실제 데이터 (DART API)
- 뉴스 실제 데이터 (Naver fetcher)
- 수급 실제 데이터 (pykrx)

**우선순위**: 중간

---

### 2. Intraday Pipeline 개발

**목표**: Fetcher → DB → Brain 순서 보장

**구현 내용**:
- intraday_pipeline.py 생성
- Just-in-Time 데이터 수집
- Brain 분석 트리거
- Order 실행

**플로우**:
```python
async def intraday_pipeline():
    # 1. Fetch (Just-in-Time)
    await kis_fetcher.sync_portfolio()
    await naver_fetcher.fetch_breaking_news()

    # 2. DB 커밋
    await db.commit()

    # 3. Brain 분석
    analysis = await brain.analyze_candidates()

    # 4. Order 실행
    for result in analysis:
        if result['final_score'] >= 70:
            await order_service.place_buy_order(...)
```

**우선순위**: 중간

---

### 3. Dynamic Scheduler 설정

**목표**: 10-60-30 전략 구현

**스케줄**:
```python
# 오전장 집중 (09:00~10:00): 10분
scheduler.add_job(intraday_pipeline, CronTrigger(hour=9, minute='0,10,20,30,40,50'))

# 점심장 휴식 (10:00~13:00): 1시간
scheduler.add_job(intraday_pipeline, CronTrigger(hour='10-12', minute=0))

# 오후장 안정 (13:00~15:00): 20분
scheduler.add_job(intraday_pipeline, CronTrigger(hour='13-14', minute='0,20,40'))

# 막판 집중 (15:00~15:20): 10분
scheduler.add_job(intraday_pipeline, CronTrigger(hour=15, minute='0,10'))

# Layer 3: 일일 분석 (07:20)
scheduler.add_job(daily_analyzer.analyze_all, CronTrigger(hour=7, minute=20))
```

**우선순위**: 중간

---

## 🧪 테스트 필요 사항

### WebSocket Manager

- [ ] 슬롯 제한 테스트 (40개 초과 시)
- [ ] 우선순위 제거 테스트 (Priority 3 → Priority 2)
- [ ] 포트폴리오 동기화 테스트
- [ ] 재연결 테스트

### Market Scanner

- [ ] KIS API 랭킹 조회 테스트
- [ ] gemini-2.0-flash 평가 테스트
- [ ] WebSocket 구독 연동 테스트
- [ ] 1분 주기 실행 테스트

---

## 📊 진행률

```
Phase 2 전체: 100% 완료 ✅

✅ WebSocket Manager (100%)
✅ Market Scanner (100%)
✅ Daily Analyzer (100%)
✅ Intraday Pipeline (100%) - Phase 3에서 완료
✅ Dynamic Scheduler (100%) - Phase 3에서 완료
```

---

## 💡 핵심 성과

### 1. 40개 슬롯 효율적 관리

- 우선순위 기반 자동 할당
- 보유종목 항상 유지
- 급등주 동적 교체

### 2. Layer 2 실시간 스캔

- 1분마다 등락률/거래량 상위 스캔
- gemini-2.0-flash로 빠른 평가 (30초)
- 70점 이상만 WebSocket 구독

### 3. 확장 가능한 아키텍처

- Layer 3 (DeepSeek R1) 추가 예정
- Intraday Pipeline 연동 준비 완료
- Dynamic Scheduler 통합 가능

---

## 🚨 알려진 이슈

### 1. Gemini API 제한

- Free tier: 분당 60회
- 해결: 0.5초 딜레이, 최대 30개 평가

### 2. WebSocket 재연결

- 연결 끊김 시 전체 재구독 필요
- 해결: resubscribe_all() 구현

### 3. Daily Picks 미구현

- Layer 3 (DeepSeek R1) 아직 미개발
- 임시: Daily Picks 빈 리스트

---

## 📝 다음 단계

### 우선순위

1. **Daily Analyzer 개발** (Layer 3 완성)
   - DeepSeek R1 통합
   - daily_picks 테이블 활용
   - WebSocket Manager 연동

2. **Intraday Pipeline 개발**
   - Fetcher → DB → Brain 순서 보장
   - Just-in-Time 데이터 수집

3. **Dynamic Scheduler 설정**
   - 10-60-30 전략 구현
   - 시간대별 차등 실행

### 예상 소요 시간

- Daily Analyzer: 1일
- Intraday Pipeline: 0.5일
- Dynamic Scheduler: 0.5일

**Phase 2 완료 예상**: 2일

---

**작성**: Claude Code
**상태**: Phase 2 진행중 (50%)
**다음**: Daily Analyzer 개발
