# AEGIS v3.0 - 프로젝트 구조

## 디렉토리 구조

```
v3/
├── app/                    # 애플리케이션 코어
│   ├── config.py          # 설정 관리
│   ├── database.py        # DB 연결
│   └── models/            # SQLAlchemy 모델
│       ├── portfolio.py   # 포트폴리오 모델
│       └── trade.py       # 거래 모델 (TradeOrder, TradeExecution)
│
├── fetchers/              # 데이터 수집 (DB Write 전담)
│   ├── kis_client.py      # KIS API 래퍼 (내부 전용)
│   ├── kis_fetcher.py     # KIS → DB 동기화
│   ├── websocket_manager.py  # 40 슬롯 WebSocket 관리
│   └── market_scanner.py  # Layer 2 스캔 (1분, gemini)
│
├── services/              # 비즈니스 로직 (DB Read only)
│   ├── portfolio_service.py  # 포트폴리오 조회
│   └── order_service.py   # 주문 실행 (예외: KIS API 직접 조회)
│
├── pipeline/              # 파이프라인 오케스트레이션
│   └── intraday_pipeline.py  # 5단계 파이프라인
│
├── scheduler/             # 스케줄러
│   ├── main_scheduler.py     # 기존 고정 스케줄러 (미사용)
│   └── dynamic_scheduler.py  # 10-60-30 Dynamic Scheduler ✅
│
├── brain/                 # AI 분석 (TODO)
│   └── (미구현)
│
├── scripts/               # 유틸리티 스크립트
├── tests/                 # 테스트
└── docs/                  # 문서
    └── dev/               # 개발 문서
        ├── 00-ROADMAP.md
        ├── 01-KIS-CLIENT.md
        ├── 02-KIS-CLIENT-IMPLEMENTATION.md
        ├── 03-PHASE1-COMPLETE.md
        ├── 04-WEBSOCKET-MANAGER.md
        ├── 05-MARKET-SCANNER.md
        ├── 06-PHASE2-PROGRESS.md
        ├── 07-PIPELINE-DESIGN.md
        └── 08-PHASE3-IMPLEMENTATION.md
```

## 핵심 파일 설명

### fetchers/kis_client.py
- KIS API 래퍼 (내부 전용, 직접 호출 금지)
- NXT/KRX TR_ID 분기
- WebSocket 구독 (H0STCNI0, H0STCNT0, H0STASP0)
- get_balance(), get_combined_balance()
- get_top_gainers(), get_top_volume()

### fetchers/kis_fetcher.py
- **유일한 DB Write 권한**
- sync_portfolio() - 잔고 동기화
- on_execution_notice() - 체결 통보 처리
- sync_execution() - 미체결 조회

### services/portfolio_service.py
- **Read only** (DB만 읽음)
- get_portfolio() - 전체 보유 종목
- get_total_asset() - 총 자산
- get_deposit() - 예수금
- get_stock_info() - 개별 종목
- get_portfolio_summary() - 요약

### services/order_service.py
- 주문 실행 (매수/매도/취소)
- **예외**: 주문 직전 KIS API 직접 잔고 확인 가능

### pipeline/intraday_pipeline.py
- 5단계 파이프라인 오케스트레이션
- Just-in-Time Data Feeding
- 순서: Fetching → Pre-processing → Brain → Validation → Execution

### scheduler/dynamic_scheduler.py
- 10-60-30 전략
- 3-Layer 스케줄 통합
- APScheduler 기반

### fetchers/websocket_manager.py
- 40 슬롯 관리
- Priority 기반 구독 (1=보유, 2=AI picks, 3=급등주)
- 자동 eviction (우선순위 낮은 것부터)

### fetchers/market_scanner.py
- Layer 2 스캔 (1분마다)
- gemini-2.0-flash 빠른 평가
- 70점 이상 → WebSocket Priority 3 구독

## 데이터베이스 모델

### Portfolio
- 보유 종목 (stock_code, quantity, avg_price)

### TradeOrder
- 주문 내역 (order_no, status, filled_qty)

### TradeExecution
- 체결 내역 (order_no, exec_qty, exec_price)

## 환경 설정

**.env 필수 항목**:
- KIS_APP_KEY, KIS_APP_SECRET
- KIS_ACCOUNT_NO
- GEMINI_API_KEY
- DATABASE_URL
