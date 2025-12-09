# AEGIS v3.0 개발 로드맵

> 작성일: 2025-12-09
> 상태: 진행중
> 목표: Write/Read only 규칙 준수, WebSocket 최대 활용

---

## 🎯 개발 목표

### v2의 고질적 문제 해결

1. ❌ **KIS 접근 혼란** → ✅ Write/Read only 규칙 엄격 준수
2. ❌ **통일되지 않은 접속** → ✅ 계층별 역할 명확화
3. ❌ **무분별한 잔고/거래 조회** → ✅ Single Source of Truth (DB)
4. ❌ **pykrx 오류** → ✅ 에러 처리 강화
5. ❌ **NXT 미지원** → ✅ NXT TR_ID 분기 처리

---

## 📋 개발 단계

### Phase 1: KIS API 계층 (현재)

**목표**: Write/Read only 규칙 준수, NXT 지원

```
┌─────────────────────────────────────────┐
│  [KIS API]                              │
│      ↓                                  │
│  kis_client.py (내부 전용, API 래퍼)     │
│      ↓                                  │
│  KISFetcher (Write only to DB)         │
│      ↓                                  │
│  [PostgreSQL]                           │
│      ↓                                  │
│  PortfolioService (Read only from DB)  │
│      ↓                                  │
│  [Dashboard, Brain, Telegram, Safety]  │
└─────────────────────────────────────────┘
```

**작업 항목**:
- [x] 문서 검토 완료
- [x] 아키텍처 설계 완료
- [x] kis_client.py 개선
  - [x] NXT 지원 (TR_ID 분기)
  - [x] get_balance() 추가
  - [x] get_combined_balance() 추가
  - [x] H0STCNI0 체결 통보 구독
  - [x] 에러 처리 강화
  - [x] 로깅 개선
- [x] KISFetcher 신규 개발
  - [x] sync_portfolio() - 잔고 동기화
  - [x] on_execution_notice() - 체결 통보 처리
  - [x] sync_execution() - 미체결 조회
- [x] PortfolioService 신규 개발
  - [x] get_portfolio() - DB Read only
  - [x] get_total_asset() - DB Read only
  - [x] get_deposit() - 예수금 조회
  - [x] get_stock_info() - 개별 종목 조회
  - [x] get_portfolio_summary() - 포트폴리오 요약
- [x] OrderService 신규 개발
  - [x] place_buy_order() - 주문 실행
  - [x] place_sell_order() - 주문 실행
  - [x] cancel_order() - 주문 취소
- [x] Database Models 추가
  - [x] TradeOrder - 주문 내역 테이블
  - [x] TradeExecution - 체결 내역 테이블

**예상 기간**: 3일
**실제 소요**: 1일 ✅

---

### Phase 2: WebSocket 최대 활용

**목표**: 3-Layer 모니터링, 동적 구독 관리

```
Layer 3: 일별 전체 스캔 (07:20, DeepSeek R1)
   ↓
Layer 2: REST 스캔 (1분마다, gemini-2.0-flash)
   ↓
Layer 1: WebSocket 실시간 (40개 슬롯)
```

**작업 항목**:
- [x] KISWebSocketManager 개발
  - [x] 40개 슬롯 동적 관리
  - [x] 우선순위 기반 구독 (Priority 1, 2, 3)
  - [x] 포트폴리오 동기화
  - [x] Daily Picks 업데이트
  - [x] 재연결 처리
  - [x] H0STCNI0 체결 통보 (Phase 1에서 구현)
  - [x] H0STCNT0 실시간 체결가
  - [x] H0STASP0 실시간 호가
  - [x] H0STPGM0 프로그램 매매
- [x] MarketScanner 개발
  - [x] 등락률 상위 스캔 (scan_top_gainers)
  - [x] 거래량 상위 스캔 (scan_top_volume)
  - [x] gemini-2.0-flash 빠른 평가
  - [x] WebSocket Manager 연동
  - [x] 1분 주기 실행
- [x] DailyAnalyzer 개발
  - [x] DeepSeek R1 전체 분석
  - [x] daily_picks 생성
  - [x] WebSocket Manager 연동
  - [x] Dynamic Scheduler 통합

**예상 기간**: 4일
**실제 소요**: 0.5일 ✅ 완료

---

### Phase 3: Scheduler & Pipeline

**목표**: Dynamic Schedule, 데이터 파이프라인 구축

**작업 항목**:
- [x] Intraday Pipeline
  - [x] Fetcher → DB → Brain 순서 보장
  - [x] 5단계 파이프라인 구현
  - [x] Just-in-Time Data Feeding
- [x] Dynamic Schedule
  - [x] 오전장: 10분 간격 (09:00~10:00)
  - [x] 점심장: 1시간 간격 (10:00~13:00)
  - [x] 오후장: 20분 간격 (13:00~15:00)
  - [x] 막판: 10분 간격 (15:00~15:20)
- [x] Layer 3 스케줄
  - [x] 07:20 DeepSeek R1 전체 분석 (스케줄 설정)
- [x] Scenario Validator
  - [x] 과거 패턴 비교
  - [x] 목표가 조정
  - [x] 승률 계산
  - [x] 백테스트 통합
  - [x] 몬테카를로 시뮬레이션

**예상 기간**: 2일
**실제 소요**: 1일 ✅ 완료

---

### Phase 4: Brain 통합

**목표**: DeepSeek R1 + gemini-2.0-flash 통합

**작업 항목**:
- [x] Brain 모듈 수정
  - [x] DeepSeek R1 일별 분석 (Phase 2에서 완료)
  - [x] gemini-2.0-flash 실시간 분석 (Phase 2에서 완료)
  - [x] Quant Score 계산 (RSI, MACD, 볼린저밴드, 거래량, MA)
  - [x] Final Score 계산 (AI 50% + Quant 50%)
- [x] Brain Analyzer 구현
  - [x] analyze_candidate() - 개별 종목 분석
  - [x] analyze_batch() - 배치 분석
  - [x] 매수/매도 추천
  - [x] 목표가/손절가 계산
- [x] Quant Calculator 구현
  - [x] RSI 계산 (30점)
  - [x] MACD 계산 (25점)
  - [x] 볼린저밴드 계산 (20점)
  - [x] 거래량 분석 (15점)
  - [x] 이동평균선 분석 (10점)
- [x] Pipeline 통합
  - [x] _brain_analyze() 구현
  - [x] daily_picks 활용
- [x] daily_picks 테이블 활용

**예상 기간**: 2일
**실제 소요**: 0.5일 ✅ 완료

---

### Phase 5: Fetchers 마이그레이션

**목표**: v2 fetchers 통합

**작업 항목**:
- [ ] pykrx fetcher (수급 데이터)
- [ ] DART fetcher (공시)
- [ ] Naver fetcher (뉴스, 테마)
- [ ] Macro fetcher (VIX, NASDAQ, SOX)
- [ ] 에러 처리 강화

**예상 기간**: 3일

---

### Phase 6: 통합 테스트

**목표**: End-to-End 테스트, 안정화

**작업 항목**:
- [ ] 단위 테스트
- [ ] 통합 테스트
- [ ] 부하 테스트
- [ ] 모의 투자 검증
- [ ] 문서화

**예상 기간**: 2일

---

## 📊 전체 일정

| Phase | 기간 | 시작일 | 종료일 | 상태 |
|-------|------|--------|--------|------|
| Phase 1 | 1일 | 12/09 | 12/09 | ✅ 완료 |
| Phase 2 | 4일 | 12/09 | 12/09 | ✅ 완료 |
| Phase 3 | 2일 | 12/09 | 12/09 | ✅ 완료 (100%) |
| Phase 4 | 2일 | 12/09 | 12/09 | ✅ 완료 (100%) |
| Phase 5 | 3일 | 12/18 | 12/20 | ⏳ 대기 |
| Phase 6 | 2일 | 12/21 | 12/22 | ⏳ 대기 |

**총 예상 기간**: 16일

---

## 🔑 핵심 원칙

### 1. Write/Read Only 규칙

```
✅ Write: KISFetcher만 DB에 쓰기
✅ Read: 모든 모듈은 DB에서만 읽기
⚠️ 예외: OrderService만 주문 직전 KIS API 직접 조회
```

### 2. Single Source of Truth

```
KIS API → KISFetcher → DB → All Modules
```

### 3. WebSocket 우선

```
실시간 데이터: WebSocket (제한 없음)
과거 데이터: REST API (제한 있음)
```

### 4. Dynamic Schedule

```
오전장: 집중 (10분)
점심장: 휴식 (1시간)
오후장: 안정 (20분)
막판: 집중 (10분)
```

---

## 📝 일일 진행사항

### 2025-12-09 (Day 1)

**완료**:
- [x] 문서 검토 (DATA_FLOW.md, KIS_API_SPECIFICATION.md)
- [x] 아키텍처 설계
- [x] 3-Layer 모니터링 전략 수립
- [x] Dynamic Schedule 설계
- [x] 개발 로드맵 작성
- [x] kis_client.py 개선 완료
  - [x] NXT 지원 (TR_ID_MAP 구현)
  - [x] buy_order()/sell_order() market 파라미터 추가
  - [x] NXT 시장가 차단 로직
  - [x] get_balance() 구현
  - [x] get_combined_balance() 구현
  - [x] _merge_positions() 헬퍼 구현
  - [x] subscribe_execution_notice() (H0STCNI0) 구현
  - [x] 로깅 개선
- [x] 구현 문서 작성 (02-KIS-CLIENT-IMPLEMENTATION.md)

**완료 (Phase 1)**:
- [x] KISFetcher 신규 개발 완료
  - [x] sync_portfolio() - 잔고 동기화
  - [x] on_execution_notice() - 체결 통보 처리
  - [x] sync_execution() - 미체결 조회
- [x] PortfolioService 개발 완료
  - [x] get_portfolio(), get_total_asset() 등 5개 메서드
- [x] OrderService 개발 완료
  - [x] place_buy_order(), place_sell_order(), cancel_order()
- [x] Database Models 추가 (TradeOrder, TradeExecution)
- [x] Phase 1 완료 문서 작성 (03-PHASE1-COMPLETE.md)

**다음 (Phase 2)**:
- WebSocket Manager 개발 (40개 슬롯 관리)
- Market Scanner 개발 (1분 스캔)
- Daily Analyzer 개발 (DeepSeek R1)

---

## 🚨 주의사항

1. **절대 금지**:
   - Dashboard/Brain/Telegram에서 kis_client 직접 호출
   - DB Write를 KISFetcher 외 다른 곳에서 수행
   - WebSocket 없이 REST API만으로 실시간 데이터 수집

2. **필수 준수**:
   - 데이터 파이프라인 순서: Fetcher → DB → Brain
   - WebSocket 40개 슬롯 제한
   - Dynamic Schedule (시간대별 차등)

---

## 📚 참고 문서

- [DATA_FLOW.md](../DATA_FLOW.md) - 데이터 흐름 원칙
- [KIS_API_SPECIFICATION.md](../KIS_API_SPECIFICATION.md) - KIS API 명세
- [BRAIN_SIMPLE.md](../BRAIN_SIMPLE.md) - Brain 의사결정
- [SCHEDULER_DESIGN.md](../SCHEDULER_DESIGN.md) - Scheduler 설계

---

**작성**: Claude Code
**검토**: 개발팀
**승인**: 대기중
