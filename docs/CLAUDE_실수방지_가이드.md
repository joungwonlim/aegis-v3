# Claude 실수 방지 가이드

> AEGIS 시스템에서 Claude가 빠지기 쉬운 함정과 올바른 대응 방법

---

## 🚨 핵심 원칙

```
┌─────────────────────────────────────────────────────────────────┐
│  1. 직접 실행 우선 - 우회하지 말고 바로 실행                    │
│  2. 기존 도구 사용 - 새 파일/fetcher 만들지 말 것               │
│  3. 실계좌 기준 - 모의투자 아님                                 │
│  4. 필요한 것만 - 전체 재수집 금지                              │
│  5. 능동적 데이터 수집 - 보유종목 되면 자동 정보 채우기         │
└─────────────────────────────────────────────────────────────────┘
```

---

## ❌ 흔한 실수 vs ✅ 올바른 방법

### 1. 보유종목 조회

| ❌ 잘못된 방법 | ✅ 올바른 방법 |
|--------------|---------------|
| DB에서 portfolio 테이블 쿼리 | `kis.get_account_holdings()` 직접 호출 |
| 캐시된 데이터 사용 | KIS API 실시간 조회 |
| sync 스크립트 먼저 실행 | 바로 API 호출 |

```python
# ✅ 올바른 방법
from fetchers.kis import KISFetcher
kis = KISFetcher(use_virtual=False)  # 실계좌!
holdings = kis.get_account_holdings()
```

### 2. 현재가 조회

| ❌ 잘못된 방법 | ✅ 올바른 방법 |
|--------------|---------------|
| KRX 웹사이트 크롤링 | `kis.get_current_price(code)` |
| pykrx로 조회 | KIS API 직접 호출 |
| 네이버 금융 크롤링 | 실시간 API 사용 |

```python
# ✅ 올바른 방법
price = kis.get_current_price('005930')  # 삼성전자
```

### 3. 매수/매도 주문

| ❌ 잘못된 방법 | ✅ 올바른 방법 |
|--------------|---------------|
| `use_virtual=True` 모의투자 | `use_virtual=False` 실계좌 |
| `sell_stock()` (없는 메서드) | `sell_market_order()` |
| `buy_stock()` (없는 메서드) | `buy_market_order()` |

```python
# ✅ 올바른 방법
kis = KISFetcher(use_virtual=False)  # 실계좌!
kis.buy_market_order(stock_code='005930', quantity=10)
kis.sell_market_order(stock_code='005930', quantity=10)
```

### 4. 뉴스/공시 조회

| ❌ 잘못된 방법 | ✅ 올바른 방법 |
|--------------|---------------|
| 새 fetcher 파일 생성 | 기존 `DARTFetcher` 사용 |
| 웹 크롤러 작성 | 기존 API 클라이언트 사용 |
| `days=3` 파라미터 | `days_back=3` 파라미터 |

```python
# ✅ 올바른 방법
from fetchers.dart.client import DARTFetcher
dart = DARTFetcher()
disclosures = dart.get_recent_disclosures(days_back=3)
```

### 5. 데이터 채우기

| ❌ 잘못된 방법 | ✅ 올바른 방법 |
|--------------|---------------|
| 전종목 1년치 재수집 | 해당 종목만 수집 |
| DELETE 후 INSERT | UPSERT 사용 |
| 무조건 전체 갱신 | 누락분만 보충 |

```python
# ✅ 올바른 방법 - 특정 종목만
python scripts/refill_missing_data.py --code 005930

# ❌ 잘못된 방법 - 전체 재수집
python scripts/init_daily_data.py  # 시간 낭비!
```

---

## 🔋 토큰 낭비 방지

### 1. 반복 대기 금지

| ❌ 토큰 낭비 | ✅ 토큰 절약 |
|------------|-------------|
| Claude에서 `time.sleep(600)` | Python 백그라운드 스크립트 |
| 10분마다 Claude 호출 | JSON 파일 저장 → 필요시 읽기 |
| 세션 유지하며 대기 | On-demand 분석 |

```
❌ Claude 세션 유지: 6.5시간 × 토큰 = 💸💸💸
✅ Python 백그라운드 + JSON + 필요시 Claude = 90%+ 절약
```

### 2. 불필요한 탐색 금지

| ❌ 토큰 낭비 | ✅ 토큰 절약 |
|------------|-------------|
| 파일 구조 전체 탐색 | 직접 경로로 접근 |
| 여러 파일 읽어보기 | 알고 있는 파일 바로 열기 |
| 코드 분석 후 실행 | 바로 실행 |

### 3. 중복 작업 금지

| ❌ 토큰 낭비 | ✅ 토큰 절약 |
|------------|-------------|
| 매번 환경 확인 | 세션 시작시 1회만 |
| 같은 쿼리 반복 | 결과 재사용 |
| 설명 후 실행 | 바로 실행 후 간단 보고 |

---

## 🤖 능동적 시스템 동작

### 매수 시 자동 데이터 수집

**원칙: 보유종목이 되면 해당 종목 정보를 모두 채운다**

```
┌─────────────────────────────────────────────────────────────────┐
│  매수 완료                                                       │
│      ↓                                                          │
│  자동 실행 (Claude가 능동적으로):                                │
│      1. stocks 테이블에 종목 정보 확인/추가                      │
│      2. daily_prices 최근 60일 데이터 확인/보충                  │
│      3. 재무제표 데이터 확인/수집                                │
│      4. 최근 공시 확인                                          │
│      5. 뉴스/이슈 확인                                          │
│                                                                  │
│  → 분석에 필요한 모든 데이터 준비 완료                          │
└─────────────────────────────────────────────────────────────────┘
```

### 매수 후 체크리스트

```python
# 매수 완료 후 자동 실행
def post_buy_data_collection(stock_code: str):
    """매수 후 종목 데이터 자동 수집"""

    # 1. 종목 기본 정보
    ensure_stock_info(stock_code)

    # 2. 일봉 데이터 (최근 60일)
    fill_daily_prices(stock_code, days=60)

    # 3. 재무 데이터
    fetch_financials(stock_code)

    # 4. 최근 공시
    check_recent_disclosures(stock_code)

    # 5. QuantScore 계산
    calculate_quant_score(stock_code)
```

---

## 📋 명령어 직접 매핑

| 사용자 명령 | 즉시 실행 | ❌ 하지 말 것 |
|------------|----------|-------------|
| "보유종목" | `kis.get_account_holdings()` | DB 쿼리, sync 스크립트 |
| "현재가" | `kis.get_current_price(code)` | KRX 크롤링, pykrx |
| "잔고" | `kis.get_account_balance()` | DB 쿼리 |
| "매수" | `kis.buy_market_order()` | 모의투자, 새 스크립트 |
| "매도" | `kis.sell_market_order()` | 모의투자 |
| "공시" | `DARTFetcher.get_recent_disclosures()` | 새 fetcher 생성 |
| "거래내역" | `kis.get_today_trades()` | DB 쿼리 |
| "." (마침표) | 포트폴리오 즉시 체크 | 분석 스크립트 실행 |

---

## 🎯 KIS API 메서드 정리

```python
from fetchers.kis import KISFetcher

kis = KISFetcher(use_virtual=False)  # 항상 실계좌!

# 조회
kis.get_account_holdings()      # 보유종목
kis.get_account_balance()       # 계좌잔고
kis.get_current_price(code)     # 현재가
kis.get_today_trades()          # 당일체결

# 주문
kis.buy_market_order(stock_code, quantity)   # 시장가 매수
kis.sell_market_order(stock_code, quantity)  # 시장가 매도
kis.buy_limit_order(stock_code, quantity, price)   # 지정가 매수
kis.sell_limit_order(stock_code, quantity, price)  # 지정가 매도
```

---

## ⚠️ 시장가 주문 주의사항

**증거금은 상한가(+30%) 기준으로 잡힘!**

```python
# ❌ 잘못된 계산
current_price = 27725
cash = 1220125
max_qty = cash // current_price  # 44주 → 주문 실패!

# ✅ 올바른 계산
upper_limit = int(current_price * 1.30)  # 상한가
max_qty = cash // upper_limit  # 33주
safe_qty = int(max_qty * 0.9)  # 30주 (안전마진)
```

---

## 📝 세션 시작 체크리스트

```
□ 1. Serena 메모리 확인 (관련 메모리 읽기)
□ 2. 오늘 날짜/시간 확인
□ 3. 장 운영 시간 확인 (09:00-15:30)
□ 4. KIS API 연결 테스트
□ 5. 보유종목 현황 파악
```

---

## 🔄 오류 발생 시

1. **ImportError**: 클래스명/모듈명 확인 (Session → SessionLocal)
2. **AttributeError**: 메서드명 확인 (sell_stock → sell_market_order)
3. **TypeError**: 파라미터명 확인 (days → days_back)
4. **주문실패**: 상한가 기준 증거금 계산 확인
5. **KIS 500 Error**: 장 마감 전후(15:20~15:40) 서버 불안정 → 1-2분 후 재시도

---

## 🚨 KIS API 500 Error 대응

### 발생 시점
- 장 마감 전후 (15:20 ~ 15:40)
- 장 시작 직후 (09:00 ~ 09:10)
- KIS 서버 점검 시간

### 증상
```
500 Server Error: Internal Server Error for url:
https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance
```

### 대응 방법
1. **즉시 재시도 금지** - 서버 부하 가중
2. **1-2분 대기 후 재시도**
3. **3회 실패 시 수동 확인** (한투 MTS 앱)
4. **장 마감 후엔 조회 불가** - 다음 날 확인

### 예방
```python
import time
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(60))
def safe_get_holdings():
    return kis.get_account_holdings()
```

---

## 📚 관련 문서

- `docs/dev3/클로드_토큰절약.md` - 토큰 절약 상세 가이드
- `docs/dev3/DATA_INTEGRITY_RULES.md` - 데이터 무결성 정책
- `docs/KIS_COMMANDS.md` - KIS API 명령어 상세
- `.serena/memories/` - 학습된 교훈들

---

*마지막 업데이트: 2025-12-09*
