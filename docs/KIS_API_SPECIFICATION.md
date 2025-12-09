# AEGIS v3.2 - KIS API Specification

> 한국투자증권 API 연동 상세 명세서

---

## 0. 데이터 소스 원칙 (Source of Truth)

> **Claude/AI가 혼란스러워하지 않도록 명확히 정의**

### 0.1 핵심 원칙

```
┌─────────────────────────────────────────────────────────────┐
│                    데이터 흐름 원칙                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   KIS API ───(Write)───> PostgreSQL ───(Read)───> 모든 모듈  │
│      │                        │                              │
│      │                        │                              │
│      │                        ▼                              │
│      │               Brain, Dashboard,                       │
│      │               Telegram, Safety                        │
│      │                                                       │
│      └──(예외: 주문 직전)──> OrderService                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘

📖 읽기: 항상 DB에서
✍️ 쓰기: KIS Fetcher만 (유일한 Writer)
⚡ 예외: 주문 직전 잔고 검증만 KIS API 직접 조회
```

### 0.2 상황별 데이터 소스

| 상황 | 데이터 소스 | 이유 |
|------|-------------|------|
| 대시보드 잔고 표시 | **DB** (`portfolio`) | 속도, API 호출 제한 회피 |
| AI 분석/점수 계산 | **DB** (`daily_prices`) | 일관성, 캐시된 데이터 |
| 텔레그램 `/잔고` 명령 | **DB** (`portfolio`) | 빠른 응답 (< 100ms) |
| 리스크 체크 | **DB** (`portfolio`) | Safety Guard 실시간 모니터링 |
| **주문 직전 잔고 확인** | **KIS API** | ⚠️ 실시간 검증 필수 |
| **주문 직전 현재가 확인** | **KIS API** | ⚠️ 호가 확인 필수 |
| 체결 후 잔고 반영 | **WebSocket → DB** | 자동 업데이트 (30ms) |

### 0.3 코드 패턴

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ❌ 잘못된 패턴 (AI 혼란 발생)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_balance(use_cache=True):
    if use_cache:
        return db.query(Portfolio)...
    else:
        return kis_api.get_balance()  # 어디서?? 혼란!

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ 올바른 패턴 (역할 명확 분리)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PortfolioService:
    """
    [읽기 전용] 모든 모듈은 여기서 읽기만 함
    - Dashboard, Brain, Telegram, Safety 등
    """
    def get_portfolio(self) -> List[Portfolio]:
        return db.query(Portfolio).all()  # 항상 DB

    def get_total_asset(self) -> int:
        snapshot = db.query(AccountSnapshot).order_by(
            AccountSnapshot.timestamp.desc()
        ).first()
        return snapshot.total_asset  # 항상 DB


class KISFetcher:
    """
    [쓰기 전용] KIS API → DB 동기화 담당
    - 유일한 DB Writer
    - 주기적 실행 (장중 1분, 장외 10분)
    """
    async def sync_portfolio(self):
        # KIS API에서 가져와서
        data = await self.kis_api.get_balance()

        # DB에 업데이트 (Upsert)
        for item in data:
            db.merge(Portfolio(
                stock_code=item['pdno'],
                quantity=int(item['hldg_qty']),
                avg_price=float(item['pchs_avg_pric']),
                current_price=float(item['prpr']),
                # ...
            ))
        db.commit()


class OrderService:
    """
    [예외] 주문 시에만 KIS API 직접 조회
    - 주문 직전 실시간 잔고 검증 필수
    - 체결 후에는 WebSocket이 DB 자동 업데이트
    """
    async def place_buy_order(self, stock_code: str, qty: int, price: int):
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Step 1: 주문 직전 실시간 잔고 확인 (KIS API)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        balance = await self.kis_api.get_available_deposit()
        required = qty * price

        if balance < required:
            raise InsufficientBalanceError(
                f"잔고 부족: 필요 {required:,}원, 가용 {balance:,}원"
            )

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # Step 2: 주문 실행
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        result = await self.kis_api.place_order(
            stock_code=stock_code,
            order_type='BUY',
            qty=qty,
            price=price,
        )

        # Step 3: 주문 DB 기록
        db.add(TradeOrder(
            order_no=result['ODNO'],
            stock_code=stock_code,
            order_type='BUY',
            qty=qty,
            price=price,
            status='PENDING',
        ))
        db.commit()

        # Step 4: 체결은 WebSocket(H0STCNI0)이 자동 처리
        # → trade_orders 상태 업데이트
        # → trade_executions 기록
        # → portfolio 업데이트

        return result
```

### 0.4 동기화 주기

| Fetcher | 대상 테이블 | 장중 주기 | 장외 주기 |
|---------|-------------|-----------|-----------|
| KIS Balance | `portfolio`, `account_snapshots` | 1분 | 10분 |
| KIS Price | `portfolio.current_price` | 실시간 (WS) | - |
| KIS Execution | `trade_orders`, `trade_executions` | 실시간 (WS) | - |

### 0.5 왜 이렇게 해야 하는가?

```
┌─────────────────────────────────────────────────────────────┐
│  문제: KIS API 직접 호출의 위험성                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. API 호출 제한: 초당 10회 → 여러 모듈이 동시 호출 시 차단  │
│  2. 지연 시간: 100~300ms → 대시보드 느려짐                   │
│  3. 장애 전파: KIS 서버 다운 → 전체 시스템 다운              │
│  4. 비일관성: 모듈마다 다른 시점 데이터 → 버그 발생          │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  해결: DB를 Single Source of Truth로                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. KIS Fetcher만 API 호출 → 호출 제한 안전                  │
│  2. DB 조회 < 10ms → 빠른 응답                               │
│  3. KIS 다운 → DB 캐시로 서비스 유지                         │
│  4. 모든 모듈 동일 데이터 → 일관성 보장                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. API 유형 비교

### 1.1 REST API vs WebSocket

| 구분 | REST API | WebSocket |
|------|----------|-----------|
| **연결 방식** | 요청-응답 (Stateless) | 상시 연결 (Stateful) |
| **지연 시간** | 100~300ms | **10~50ms** |
| **용도** | 조회, 주문 | 실시간 시세, 체결 통보 |
| **호출 제한** | 초당 10회 | 제한 없음 (구독 기반) |
| **재연결** | 매 요청마다 | 끊기면 재연결 필요 |

### 1.2 사용 시나리오

```
┌─────────────────────────────────────────────────────────────┐
│                    AEGIS Trading Flow                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  [REST API]                    [WebSocket]                   │
│  ─────────                     ──────────                    │
│  • 장 시작 전 잔고 조회         • 실시간 호가 수신            │
│  • 주문 전송 (매수/매도)        • 실시간 체결가 수신          │
│  • 미체결 조회                  • ⚡ 내 주문 체결 통보        │
│  • 일별 거래내역               • 실시간 잔고 변동            │
│                                                              │
│  [100~300ms]                   [10~50ms]                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. REST API 명세

### 2.1 인증 (OAuth 2.0)

| 항목 | 값 |
|------|-----|
| Token URL | `https://openapi.koreainvestment.com:9443/oauth2/tokenP` |
| Grant Type | `client_credentials` |
| 유효 시간 | 24시간 (86400초) |

```python
# 토큰 발급 요청
POST /oauth2/tokenP
{
    "grant_type": "client_credentials",
    "appkey": "{APP_KEY}",
    "appsecret": "{APP_SECRET}"
}

# 응답
{
    "access_token": "eyJ0eXAi...",
    "token_type": "Bearer",
    "expires_in": 86400
}
```

---

### 2.2 계좌 조회 API

#### 2.2.1 예수금 조회 → `account_snapshots`

| 항목 | 값 |
|------|-----|
| **TR코드** | `TTTC8434R` |
| **URL** | `/uapi/domestic-stock/v1/trading/inquire-psbl-order` |
| **용도** | 주문 가능 금액 조회 |

```python
# 요청
GET /uapi/domestic-stock/v1/trading/inquire-psbl-order
Headers:
    tr_id: TTTC8434R

# 응답 → DB 매핑
{
    "output": {
        "dnca_tot_amt": "10000000",      # → account_snapshots.deposit (원)
        "tot_evlu_amt": "15000000",      # → account_snapshots.total_asset (원)
        "nass_amt": "5000000"            # 순자산 (참고용)
    }
}
```

**DB 저장:**
```python
AccountSnapshot(
    deposit=int(response['dnca_tot_amt']),        # 예수금 (원)
    total_asset=int(response['tot_evlu_amt']),    # 총자산 (원)
    net_profit_today=calculate_daily_profit(),     # 별도 계산
)
```

---

#### 2.2.2 보유 종목 조회 → `portfolio`

| 항목 | 값 |
|------|-----|
| **TR코드** | `TTTC8434R` |
| **URL** | `/uapi/domestic-stock/v1/trading/inquire-balance` |
| **용도** | 보유 종목 및 평가 금액 |

```python
# 요청
GET /uapi/domestic-stock/v1/trading/inquire-balance
Headers:
    tr_id: TTTC8434R

# 응답 → DB 매핑
{
    "output1": [
        {
            "pdno": "005930",              # → portfolio.stock_code
            "prdt_name": "삼성전자",         # → portfolio.stock_name
            "hldg_qty": "100",              # → portfolio.quantity (주)
            "pchs_avg_pric": "52000",       # → portfolio.avg_price (원)
            "prpr": "53000",                # → portfolio.current_price (원)
            "evlu_pfls_rt": "1.92"          # → portfolio.profit_rate (%)
        }
    ]
}
```

**DB 저장:**
```python
Portfolio(
    stock_code=item['pdno'],
    stock_name=item['prdt_name'],
    quantity=int(item['hldg_qty']),           # 주 단위
    avg_price=float(item['pchs_avg_pric']),   # 원 단위
    current_price=float(item['prpr']),        # 원 단위
    profit_rate=float(item['evlu_pfls_rt']),  # % 단위
)
```

---

#### 2.2.3 주문 전송 → `trade_orders`

| 항목 | 값 |
|------|-----|
| **TR코드 (매수)** | `TTTC0802U` |
| **TR코드 (매도)** | `TTTC0801U` |
| **URL** | `/uapi/domestic-stock/v1/trading/order-cash` |

```python
# 매수 주문
POST /uapi/domestic-stock/v1/trading/order-cash
Headers:
    tr_id: TTTC0802U  # 매수

Body:
{
    "PDNO": "005930",           # 종목코드
    "ORD_DVSN": "00",           # 지정가
    "ORD_QTY": "10",            # 주문수량 (주)
    "ORD_UNPR": "52000"         # 주문가격 (원)
}

# 응답 → DB 매핑
{
    "output": {
        "ODNO": "0000123456",   # → trade_orders.order_no
        "ORD_TMD": "092530"     # 주문시간
    }
}
```

**DB 저장:**
```python
TradeOrder(
    order_no=response['ODNO'],
    stock_code=request['PDNO'],
    order_type='BUY',  # or 'SELL'
    qty=int(request['ORD_QTY']),      # 주 단위
    price=int(request['ORD_UNPR']),   # 원 단위
    status='PENDING',
    created_at=datetime.now(),
)
```

---

#### 2.2.4 미체결 조회 → `trade_orders` (status 업데이트)

| 항목 | 값 |
|------|-----|
| **TR코드** | `TTTC8036R` |
| **URL** | `/uapi/domestic-stock/v1/trading/inquire-nccs` |

```python
# 응답
{
    "output": [
        {
            "odno": "0000123456",      # 주문번호
            "ord_qty": "10",           # 주문수량
            "tot_ccld_qty": "5",       # 체결수량
            "rmn_qty": "5",            # 미체결수량
            "ord_unpr": "52000"        # 주문가격
        }
    ]
}
```

**상태 판단 로직:**
```python
if int(item['rmn_qty']) == 0:
    status = 'FILLED'      # 전량 체결
elif int(item['tot_ccld_qty']) > 0:
    status = 'PARTIAL'     # 부분 체결
else:
    status = 'PENDING'     # 미체결
```

---

### 2.3 시세 조회 API

#### 2.3.1 현재가 조회

| 항목 | 값 |
|------|-----|
| **TR코드** | `FHKST01010100` |
| **URL** | `/uapi/domestic-stock/v1/quotations/inquire-price` |

```python
# 응답 → portfolio.current_price 업데이트
{
    "output": {
        "stck_prpr": "53000",      # 현재가 (원)
        "prdy_vrss": "1000",       # 전일대비 (원)
        "prdy_ctrt": "1.92"        # 등락률 (%)
    }
}
```

---

#### 2.3.2 일별 시세 (과거) → `daily_prices`

| 항목 | 값 |
|------|-----|
| **TR코드** | `FHKST01010400` |
| **URL** | `/uapi/domestic-stock/v1/quotations/inquire-daily-price` |

```python
# 응답 → DB 매핑
{
    "output": [
        {
            "stck_bsop_date": "20241208",  # → daily_prices.date
            "stck_oprc": "52000",          # → open (원)
            "stck_hgpr": "53500",          # → high (원)
            "stck_lwpr": "51500",          # → low (원)
            "stck_clpr": "53000",          # → close (원)
            "acml_vol": "15000000"         # → volume (주)
        }
    ]
}
```

---

#### 2.3.3 KOSPI200 선물/현물 → `market_macro` (베이시스)

| 데이터 | TR코드 | 용도 |
|--------|--------|------|
| KOSPI200 현물 | `FHKUP03500100` | 베이시스 계산 |
| KOSPI200 선물 | `FHKIF03010200` | 베이시스 계산 |
| 선물 투자자별 | `FHKIF03020100` | 외국인 선물 포지션 |

```python
# 베이시스 계산 예시
basis = futures_price - spot_price
basis_rate = (basis / spot_price) * 100  # %

# DB 저장 (market_macro 확장 또는 별도 테이블)
if basis_rate < -0.5:
    regime = "BACKWARDATION"  # 매수 신호
elif basis_rate > 0.5:
    regime = "CONTANGO"       # 주의
```

---

## 3. WebSocket API 명세

### 3.1 연결 정보

| 항목 | 실전 | 모의 |
|------|------|------|
| **URL** | `ws://ops.koreainvestment.com:21000` | `ws://ops.koreainvestment.com:31000` |
| **프로토콜** | WebSocket | WebSocket |
| **인증** | approval_key (별도 발급) | approval_key |

```python
# WebSocket 인증키 발급
POST /oauth2/Approval
{
    "grant_type": "client_credentials",
    "appkey": "{APP_KEY}",
    "secretkey": "{APP_SECRET}"
}

# 응답
{
    "approval_key": "abc123..."
}
```

---

### 3.2 실시간 시세 구독

#### 3.2.1 실시간 호가 → `market_candles` (틱 데이터)

| 항목 | 값 |
|------|-----|
| **TR코드** | `H0STASP0` |
| **용도** | 실시간 호가 (10호가) |

```python
# 구독 요청
{
    "header": {
        "approval_key": "{APPROVAL_KEY}",
        "tr_type": "1",          # 1: 등록, 2: 해제
        "content-type": "utf-8"
    },
    "body": {
        "input": {
            "tr_id": "H0STASP0",
            "tr_key": "005930"   # 종목코드
        }
    }
}

# 수신 데이터 (10ms 간격)
{
    "ASKP1": "53100",   # 매도 1호가
    "BIDP1": "53000",   # 매수 1호가
    "ASKP_RSQN1": "1000",  # 매도 1호가 잔량
    "BIDP_RSQN1": "2000"   # 매수 1호가 잔량
}
```

---

#### 3.2.2 실시간 체결가 → `market_candles`

| 항목 | 값 |
|------|-----|
| **TR코드** | `H0STCNT0` |
| **용도** | 실시간 체결 (틱) |

```python
# 수신 데이터
{
    "STCK_PRPR": "53000",      # 체결가 (원)
    "CNTG_VOL": "100",         # 체결량 (주)
    "STCK_CNTG_HOUR": "093015" # 체결시간
}
```

**DB 저장 (1분봉 집계):**
```python
# 1분 단위로 집계하여 market_candles에 저장
candle = MarketCandle(
    time=current_minute,
    symbol='005930',
    interval='1m',
    open=first_tick_price,
    high=max(tick_prices),
    low=min(tick_prices),
    close=last_tick_price,
    volume=sum(tick_volumes),
)
```

---

### 3.3 ⚡ 실시간 체결 통보 (핵심)

> **내 주문이 체결되면 즉시 알림 → 10~50ms 반응**

| 항목 | 값 |
|------|-----|
| **TR코드** | `H0STCNI0` (실전) / `H0STCNI9` (모의) |
| **용도** | 내 주문 체결 통보 |
| **지연 시간** | **10~50ms** |

```python
# 구독 요청
{
    "header": {
        "tr_type": "1"
    },
    "body": {
        "input": {
            "tr_id": "H0STCNI0",
            "tr_key": "{HTS_ID}"  # 사용자 ID
        }
    }
}

# ⚡ 체결 통보 수신 (즉시)
{
    "ODNO": "0000123456",      # 주문번호
    "SELN_BYOV_CLS": "02",     # 01:매도, 02:매수
    "PDNO": "005930",          # 종목코드
    "CNTG_QTY": "10",          # 체결수량 (주)
    "CNTG_UNPR": "52500",      # 체결가격 (원)
    "STCK_CNTG_HOUR": "093025" # 체결시간
}
```

**즉시 처리 로직:**
```python
async def on_execution_notice(data):
    """체결 통보 수신 시 즉시 처리"""

    # 1. trade_orders 상태 업데이트
    order = db.query(TradeOrder).filter(
        TradeOrder.order_no == data['ODNO']
    ).first()
    order.status = 'FILLED'

    # 2. trade_executions 기록
    execution = TradeExecution(
        order_no=data['ODNO'],
        stock_code=data['PDNO'],
        exec_qty=int(data['CNTG_QTY']),
        exec_price=int(data['CNTG_UNPR']),
        executed_at=parse_time(data['STCK_CNTG_HOUR']),
    )
    db.add(execution)

    # 3. portfolio 업데이트 (매수 시)
    if data['SELN_BYOV_CLS'] == '02':  # 매수
        update_portfolio_on_buy(data)

    # 4. 텔레그램 알림
    await send_telegram(f"✅ 체결: {data['PDNO']} {data['CNTG_QTY']}주 @ {data['CNTG_UNPR']}원")

    db.commit()
```

---

### 3.4 실시간 잔고 변동

| 항목 | 값 |
|------|-----|
| **TR코드** | `H0STCNI0` (체결통보에 포함) |
| **용도** | 체결 후 잔고 변동 |

```python
# 체결 통보에 포함된 잔고 정보
{
    "TOT_CCLD_QTY": "10",      # 총 체결 수량
    "TOT_CCLD_AMT": "525000",  # 총 체결 금액 (원)
    "PCHS_AVG_PRIC": "52500"   # 평균 매입가 (원)
}
```

---

## 4. REST vs WebSocket 속도 비교

### 4.1 주문 → 체결 확인 시나리오

```
┌─────────────────────────────────────────────────────────────┐
│  [REST API 방식] - 폴링                                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  주문 전송 ──(100ms)──> KIS 서버                             │
│                           │                                  │
│  (1초 대기)               │ 체결 처리                        │
│                           │                                  │
│  미체결 조회 ──(150ms)──> │                                  │
│                           │                                  │
│  (1초 대기)               │                                  │
│                           │                                  │
│  미체결 조회 ──(150ms)──> "체결 완료!"                       │
│                                                              │
│  📊 총 소요 시간: 2,400ms (2.4초)                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  [WebSocket 방식] - 푸시                                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  주문 전송 ──(100ms)──> KIS 서버                             │
│                           │                                  │
│  (WebSocket 상시 연결)    │ 체결 처리                        │
│          ↑                │                                  │
│          │                ↓                                  │
│          └──(30ms)────── 체결 통보 푸시!                     │
│                                                              │
│  📊 총 소요 시간: 130ms (0.13초)                             │
│                                                              │
│  ⚡ 18배 빠름!                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 속도 차이가 중요한 이유

| 시나리오 | REST (폴링) | WebSocket (푸시) | 영향 |
|----------|-------------|------------------|------|
| **손절 실행** | 2~3초 지연 | 0.1초 반응 | 추가 손실 방지 |
| **익절 실행** | 가격 변동 | 목표가 정확 체결 | 수익 극대화 |
| **피라미딩** | 기회 놓침 | 즉시 2차 매수 | 평단가 최적화 |
| **잔고 확인** | 다음 주문 지연 | 즉시 다음 주문 | 기회 포착 |

---

## 5. API → DB 매핑 총정리

### 5.1 REST API 매핑

| TR코드 | API | DB 테이블 | 주기 |
|--------|-----|-----------|------|
| `TTTC8434R` | 예수금/잔고 조회 | `account_snapshots`, `portfolio` | 장 시작 전 |
| `TTTC0802U` | 매수 주문 | `trade_orders` | 이벤트 |
| `TTTC0801U` | 매도 주문 | `trade_orders` | 이벤트 |
| `TTTC8036R` | 미체결 조회 | `trade_orders` (상태 업데이트) | 1분 |
| `FHKST01010100` | 현재가 | `portfolio.current_price` | 실시간 |
| `FHKST01010400` | 일별 시세 | `daily_prices` | 장 마감 |
| `FHKUP03500100` | KOSPI200 현물 | `market_macro` | 실시간 |
| `FHKIF03010200` | KOSPI200 선물 | `market_macro` | 실시간 |

### 5.2 WebSocket 매핑

| TR코드 | 데이터 | DB 테이블 | 지연 |
|--------|--------|-----------|------|
| `H0STASP0` | 실시간 호가 | `market_candles` | 10ms |
| `H0STCNT0` | 실시간 체결 | `market_candles` | 10ms |
| `H0STCNI0` | **체결 통보** | `trade_orders`, `trade_executions`, `portfolio` | **30ms** |

---

## 6. 구현 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                     AEGIS KIS Integration                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐                      │
│  │  REST Client │     │   WS Client  │                      │
│  │  (httpx)     │     │  (websockets)│                      │
│  └──────┬───────┘     └──────┬───────┘                      │
│         │                    │                               │
│         │    ┌───────────────┤                               │
│         │    │               │                               │
│         ▼    ▼               ▼                               │
│  ┌─────────────────────────────────────┐                    │
│  │           KIS Fetcher               │                    │
│  │  ┌─────────────────────────────┐   │                    │
│  │  │  • get_balance()            │   │                    │
│  │  │  • place_order()            │   │                    │
│  │  │  • subscribe_execution()    │   │                    │
│  │  │  • on_execution_callback()  │   │                    │
│  │  └─────────────────────────────┘   │                    │
│  └──────────────────┬──────────────────┘                    │
│                     │                                        │
│                     ▼                                        │
│  ┌─────────────────────────────────────┐                    │
│  │            PostgreSQL               │                    │
│  │  ┌─────────┐ ┌─────────┐ ┌───────┐ │                    │
│  │  │portfolio│ │trade_   │ │market_│ │                    │
│  │  │         │ │orders   │ │candles│ │                    │
│  │  └─────────┘ └─────────┘ └───────┘ │                    │
│  └─────────────────────────────────────┘                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. 에러 처리 및 재연결

### 7.1 REST API 에러 코드

| 코드 | 의미 | 대응 |
|------|------|------|
| `EGW00123` | 토큰 만료 | 토큰 재발급 |
| `EGW00201` | 호출 한도 초과 | 1초 대기 후 재시도 |
| `40100000` | 주문 실패 | 주문 조건 재확인 |
| `40900000` | 잔고 부족 | 주문 수량 조정 |

### 7.2 WebSocket 재연결 로직

```python
class KISWebSocket:
    def __init__(self):
        self.reconnect_delay = 1  # 초
        self.max_reconnect_delay = 60

    async def connect_with_retry(self):
        while True:
            try:
                await self.connect()
                self.reconnect_delay = 1  # 성공 시 리셋
                await self.listen()
            except ConnectionClosed:
                logger.warning(f"WS 끊김. {self.reconnect_delay}초 후 재연결...")
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(
                    self.reconnect_delay * 2,
                    self.max_reconnect_delay
                )
```

---

## 8. 보안 주의사항

```python
# ❌ 절대 금지
APP_KEY = "실제키값"  # 코드에 하드코딩

# ✅ 환경변수 사용
APP_KEY = os.getenv("KIS_APP_KEY")
APP_SECRET = os.getenv("KIS_APP_SECRET")
ACCOUNT_NO = os.getenv("KIS_ACCOUNT_NUMBER")
```

**환경변수 (.env):**
```bash
KIS_APP_KEY=PSxxxxxxxx
KIS_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KIS_ACCOUNT_NUMBER=12345678-01
KIS_HTS_ID=myid123
```

---

## 9. 스마트 주문 시스템

> **슬리피지 최소화를 위한 호가 오프셋 주문**

### 9.1 호가 단위 (Tick Size) 규정

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    한국거래소 호가 단위 규정                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   가격대              호가 단위       예시                               │
│   ─────────────────────────────────────────────────────────────────     │
│   2,000원 미만           1원         1,999 → 1,998                      │
│   2,000원 ~ 5,000원      5원         4,500 → 4,495                      │
│   5,000원 ~ 20,000원    10원        15,000 → 14,990                     │
│   20,000원 ~ 50,000원   50원        35,000 → 34,950                     │
│   50,000원 ~ 200,000원 100원        80,000 → 79,900                     │
│   200,000원 ~ 500,000원 500원      350,000 → 349,500                    │
│   500,000원 이상      1,000원      800,000 → 799,000                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.2 호가 단위 계산 함수

```python
def get_tick_size(price: int) -> int:
    """
    가격대별 호가 단위 반환

    Args:
        price: 현재 가격 (원)

    Returns:
        해당 가격대의 호가 단위 (원)
    """
    if price < 2000:
        return 1
    elif price < 5000:
        return 5
    elif price < 20000:
        return 10
    elif price < 50000:
        return 50
    elif price < 200000:
        return 100
    elif price < 500000:
        return 500
    else:
        return 1000


def adjust_price_to_tick(price: int, direction: str = "down") -> int:
    """
    가격을 호가 단위에 맞게 조정

    Args:
        price: 조정할 가격
        direction: "down" (내림) 또는 "up" (올림)

    Returns:
        호가 단위에 맞춘 가격
    """
    tick = get_tick_size(price)

    if direction == "down":
        return (price // tick) * tick
    else:  # up
        return ((price + tick - 1) // tick) * tick
```

### 9.3 스마트 주문 메서드

#### 9.3.1 현재 구현 (1호가)

```python
# ═══════════════════════════════════════════════════════════════
#                    기존 스마트 주문 (1호가)
# ═══════════════════════════════════════════════════════════════

def buy_smart_order(stock_code: str, qty: int) -> Dict:
    """
    스마트 매수: 매도 1호가로 지정가 주문

    장점: 시장가보다 슬리피지 -0.2~0.5% 절감
    단점: 급등 시 미체결 가능
    """
    orderbook = get_orderbook(stock_code)
    buy_price = orderbook["ask_price_1"]  # 매도 1호가

    return place_order(
        stock_code=stock_code,
        order_type="buy",
        price=buy_price,
        qty=qty,
        order_dvsn="00"  # 지정가
    )


def sell_smart_order(stock_code: str, qty: int) -> Dict:
    """
    스마트 매도: 매수 1호가로 지정가 주문

    장점: 급락 시 터무니없이 싼 가격 방지
    단점: 급락 시 미체결 가능
    """
    orderbook = get_orderbook(stock_code)
    sell_price = orderbook["bid_price_1"]  # 매수 1호가

    return place_order(
        stock_code=stock_code,
        order_type="sell",
        price=sell_price,
        qty=qty,
        order_dvsn="00"  # 지정가
    )
```

#### 9.3.2 확장 구현 (N호가 오프셋)

```python
# ═══════════════════════════════════════════════════════════════
#                    호가 오프셋 주문 (신규)
# ═══════════════════════════════════════════════════════════════

def buy_offset_order(
    stock_code: str,
    qty: int,
    tick_offset: int = -2
) -> Dict:
    """
    오프셋 매수: 현재가 대비 N틱 아래로 지정가 주문

    Args:
        stock_code: 종목코드
        qty: 주문 수량
        tick_offset: 틱 오프셋 (음수 = 싸게, 양수 = 비싸게)
                     -2 = 현재가보다 2틱 아래

    Returns:
        주문 결과 (order_no, price, qty, status)

    Example:
        현재가 50,000원, tick_offset=-2
        → 호가단위 100원
        → 주문가: 50,000 + (-2 × 100) = 49,800원
    """
    # 1. 현재가 조회
    current_price = get_current_price(stock_code)

    # 2. 호가 단위 계산
    tick_size = get_tick_size(current_price)

    # 3. 오프셋 적용
    target_price = current_price + (tick_offset * tick_size)

    # 4. 호가 단위 정렬 (매수는 내림)
    order_price = adjust_price_to_tick(target_price, direction="down")

    # 5. 가격 검증 (너무 낮으면 미체결 위험)
    min_price = current_price * 0.97  # 현재가 대비 -3% 한도
    order_price = max(order_price, adjust_price_to_tick(int(min_price), "up"))

    logger.info(f"📈 오프셋 매수: {stock_code} 현재가={current_price:,} "
                f"오프셋={tick_offset}틱 → 주문가={order_price:,}")

    return place_order(
        stock_code=stock_code,
        order_type="buy",
        price=order_price,
        qty=qty,
        order_dvsn="00"
    )


def sell_offset_order(
    stock_code: str,
    qty: int,
    tick_offset: int = +3
) -> Dict:
    """
    오프셋 매도: 현재가 대비 N틱 위로 지정가 주문

    Args:
        stock_code: 종목코드
        qty: 주문 수량
        tick_offset: 틱 오프셋 (양수 = 비싸게, 음수 = 싸게)
                     +3 = 현재가보다 3틱 위

    Returns:
        주문 결과

    Example:
        현재가 50,000원, tick_offset=+3
        → 호가단위 100원
        → 주문가: 50,000 + (3 × 100) = 50,300원
    """
    # 1. 현재가 조회
    current_price = get_current_price(stock_code)

    # 2. 호가 단위 계산
    tick_size = get_tick_size(current_price)

    # 3. 오프셋 적용
    target_price = current_price + (tick_offset * tick_size)

    # 4. 호가 단위 정렬 (매도는 올림)
    order_price = adjust_price_to_tick(target_price, direction="up")

    # 5. 가격 검증 (너무 높으면 미체결 위험)
    max_price = current_price * 1.03  # 현재가 대비 +3% 한도
    order_price = min(order_price, adjust_price_to_tick(int(max_price), "down"))

    logger.info(f"📉 오프셋 매도: {stock_code} 현재가={current_price:,} "
                f"오프셋={tick_offset}틱 → 주문가={order_price:,}")

    return place_order(
        stock_code=stock_code,
        order_type="sell",
        price=order_price,
        qty=qty,
        order_dvsn="00"
    )
```

### 9.4 스마트 주문 전략 매트릭스

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    상황별 스마트 주문 전략                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────┬────────────────┬────────────────┬─────────────────┐ │
│  │    상황        │    매수 전략    │    매도 전략    │     이유        │ │
│  ├───────────────┼────────────────┼────────────────┼─────────────────┤ │
│  │ 일반 매수      │ tick_offset=-2 │       -        │ 2틱 싸게 매수   │ │
│  │ (시간 여유)    │                │                │ 슬리피지 절감   │ │
│  ├───────────────┼────────────────┼────────────────┼─────────────────┤ │
│  │ 급등 종목      │ tick_offset=0  │       -        │ 1호가 즉시 체결 │ │
│  │ (빠른 진입)    │ (매도1호가)    │                │                 │ │
│  ├───────────────┼────────────────┼────────────────┼─────────────────┤ │
│  │ 일반 매도      │       -        │ tick_offset=+2 │ 2틱 비싸게 매도 │ │
│  │ (익절)         │                │                │ 수익 극대화     │ │
│  ├───────────────┼────────────────┼────────────────┼─────────────────┤ │
│  │ 손절 매도      │       -        │ tick_offset=0  │ 1호가 즉시 체결 │ │
│  │ (빠른 탈출)    │                │ (매수1호가)    │ 미체결 방지     │ │
│  ├───────────────┼────────────────┼────────────────┼─────────────────┤ │
│  │ 급락 종목      │       -        │ tick_offset=-1 │ 현재가 아래로   │ │
│  │ (긴급 탈출)    │                │                │ 확실한 체결     │ │
│  └───────────────┴────────────────┴────────────────┴─────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.5 주문 타입 코드 (KIS API)

```python
# ═══════════════════════════════════════════════════════════════
#                    KIS 주문 구분 코드
# ═══════════════════════════════════════════════════════════════

ORDER_DVSN = {
    "00": "지정가",           # 스마트 주문에서 사용
    "01": "시장가",           # 즉시 체결 (슬리피지 위험)
    "02": "조건부지정가",      # 장 마감 시 시장가 전환
    "03": "최유리지정가",      # 즉시 체결 가능 최유리 가격
    "04": "최우선지정가",      # 최우선 호가
    "05": "장전시간외",        # 08:30~08:40
    "06": "장후시간외",        # 15:40~16:00
    "07": "시간외단일가",      # 16:00~18:00
}

# 스마트 주문 권장 설정
SMART_ORDER_CONFIG = {
    "buy_normal": {"dvsn": "00", "offset": -2},     # 일반 매수
    "buy_urgent": {"dvsn": "00", "offset": 0},      # 급등 매수
    "sell_profit": {"dvsn": "00", "offset": +2},    # 익절 매도
    "sell_stop": {"dvsn": "00", "offset": 0},       # 손절 매도
    "sell_emergency": {"dvsn": "00", "offset": -1}, # 긴급 매도
}
```

### 9.6 미체결 대응 로직

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    미체결 자동 대응 플로우                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  주문 전송                                                               │
│      │                                                                  │
│      ▼                                                                  │
│  ┌────────────────┐                                                     │
│  │  30초 대기     │                                                     │
│  └───────┬────────┘                                                     │
│          │                                                              │
│          ▼                                                              │
│  ┌────────────────────┐                                                 │
│  │  체결 확인         │                                                 │
│  └─────────┬──────────┘                                                 │
│            │                                                            │
│     ┌──────┴──────┐                                                     │
│     │             │                                                     │
│   [전량 체결]   [미체결]                                                 │
│     │             │                                                     │
│     ▼             ▼                                                     │
│  ┌──────┐   ┌────────────────────┐                                      │
│  │ 완료 │   │ 주문 취소          │                                      │
│  └──────┘   └─────────┬──────────┘                                      │
│                       │                                                 │
│                       ▼                                                 │
│             ┌────────────────────┐                                      │
│             │  재주문 (offset 조정)│                                     │
│             │                     │                                     │
│             │  매수: offset +1    │  (더 비싸게)                         │
│             │  매도: offset -1    │  (더 싸게)                           │
│             └─────────┬──────────┘                                      │
│                       │                                                 │
│                       ▼                                                 │
│             ┌────────────────────┐                                      │
│             │  3회 재시도 후     │                                       │
│             │  시장가 전환       │                                       │
│             └────────────────────┘                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.7 슬리피지 절감 효과 예상

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    슬리피지 절감 효과 분석                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  예시: 삼성전자 (005930) - 현재가 80,000원                              │
│                                                                         │
│  ┌────────────────────┬────────────────┬────────────────────────────┐  │
│  │      주문 방식      │    체결 예상가  │         비고              │  │
│  ├────────────────────┼────────────────┼────────────────────────────┤  │
│  │ 시장가 (01)         │ 80,100원       │ +0.125% 슬리피지          │  │
│  │ 스마트 1호가        │ 80,000원       │ 0% (매도1호가)            │  │
│  │ 오프셋 -2틱         │ 79,800원       │ -0.25% 절감               │  │
│  │ 오프셋 -3틱         │ 79,700원       │ -0.375% 절감 (미체결 위험)│  │
│  └────────────────────┴────────────────┴────────────────────────────┘  │
│                                                                         │
│  연간 절감 효과 (일 4회 거래, 회당 100만원 가정):                        │
│                                                                         │
│  • 시장가 대비 스마트: 0.125% × 4 × 250일 × 100만원 = 125만원/년        │
│  • 스마트 대비 오프셋: 0.25% × 4 × 250일 × 100만원 = 250만원/년         │
│                                                                         │
│  ⚠️ 단, 오프셋이 클수록 미체결 확률 증가                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.8 설정값 요약

```python
# ═══════════════════════════════════════════════════════════════
#                    스마트 주문 설정값
# ═══════════════════════════════════════════════════════════════

# 기본 오프셋
DEFAULT_BUY_OFFSET = -2          # 매수: 2틱 아래
DEFAULT_SELL_OFFSET = +2         # 매도: 2틱 위

# 상황별 오프셋
URGENT_BUY_OFFSET = 0            # 급등 매수: 1호가
STOP_LOSS_OFFSET = 0             # 손절 매도: 1호가
EMERGENCY_SELL_OFFSET = -1       # 긴급 매도: 1틱 아래

# 가격 한도
MAX_OFFSET_PERCENT = 3.0         # 현재가 대비 최대 오프셋 (±3%)

# 미체결 대응
UNFILLED_WAIT_SECONDS = 30       # 미체결 대기 시간
MAX_RETRY_COUNT = 3              # 최대 재시도 횟수
RETRY_OFFSET_ADJUST = 1          # 재시도 시 오프셋 조정 (틱)

# 시장가 전환 조건
FORCE_MARKET_AFTER_RETRY = True  # 재시도 초과 시 시장가 전환
```

---

## 11. NXT 시장 연동 (Next Trading System)

> **NXT**: K-OTC Next - 한국투자증권 대체거래소 시스템

### 11.1 NXT vs KRX 비교

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       KRX vs NXT 비교표                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────┐     ┌─────────────────────────┐            │
│  │         KRX             │     │         NXT             │            │
│  │   (한국거래소)           │     │   (대체거래소)           │            │
│  ├─────────────────────────┤     ├─────────────────────────┤            │
│  │ 운영시간                 │     │ 운영시간                 │            │
│  │ 09:00 ~ 15:30           │     │ 08:00 ~ 20:00           │            │
│  │                         │     │ (프리마켓 + 애프터마켓)   │            │
│  ├─────────────────────────┤     ├─────────────────────────┤            │
│  │ 수수료                   │     │ 수수료                   │            │
│  │ 0.0140527%              │     │ 0.0139527%              │            │
│  │                         │     │ (약간 저렴)              │            │
│  ├─────────────────────────┤     ├─────────────────────────┤            │
│  │ 거래세                   │     │ 거래세                   │            │
│  │ 0.15%                   │     │ 0.15%                   │            │
│  │ (동일)                   │     │ (동일)                   │            │
│  ├─────────────────────────┤     ├─────────────────────────┤            │
│  │ 주문유형                 │     │ 주문유형                 │            │
│  │ 지정가, 시장가, 조건부   │     │ 지정가만 (시장가 없음)   │            │
│  │                         │     │                         │            │
│  ├─────────────────────────┤     ├─────────────────────────┤            │
│  │ 호가 단위                │     │ 호가 단위                │            │
│  │ KRX 표준                 │     │ KRX 동일                 │            │
│  └─────────────────────────┘     └─────────────────────────┘            │
│                                                                         │
│  📌 핵심 차이점:                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│  1. 운영시간 확장 (08:00~20:00)                                          │
│  2. 시장가 주문 불가 → 지정가만 가능                                      │
│  3. 수수료 약간 저렴 (-0.0001%)                                          │
│  4. 유동성 낮음 → 대형주 위주 거래                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.2 NXT API 엔드포인트

| 기능 | KRX API | NXT API | 차이점 |
|-----|---------|---------|--------|
| **매수 주문** | TTTC0802U | **TTTN0802U** | TR_ID 변경 |
| **매도 주문** | TTTC0801U | **TTTN0801U** | TR_ID 변경 |
| **잔고 조회** | TTTC8434R | **TTTN8434R** | TR_ID 변경 |
| **미체결 조회** | TTTC8036R | **TTTN8036R** | TR_ID 변경 |
| **호가 조회** | FHKST01010200 | **동일** | 변경 없음 |

### 11.3 NXT 주문 구현 요구사항

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      NXT 주문 시스템 요구사항                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  🚨 필수 구현 사항                                                       │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  1. TR_ID 분기 처리                                                      │
│     ─────────────────                                                   │
│     if market == "NXT":                                                 │
│         tr_id = "TTTN0802U"  # NXT 매수                                 │
│     else:                                                               │
│         tr_id = "TTTC0802U"  # KRX 매수                                 │
│                                                                         │
│  2. 시장가 주문 차단                                                     │
│     ─────────────────                                                   │
│     if market == "NXT" and order_type == "MARKET":                      │
│         raise ValueError("NXT는 시장가 주문 불가")                       │
│         # 또는 자동으로 지정가로 변환                                    │
│                                                                         │
│  3. 운영시간 확인                                                        │
│     ─────────────────                                                   │
│     KRX: 09:00 ~ 15:30                                                  │
│     NXT: 08:00 ~ 20:00                                                  │
│                                                                         │
│  4. 수수료 계산 분기                                                     │
│     ─────────────────                                                   │
│     KRX_FEE_RATE = 0.0140527%                                           │
│     NXT_FEE_RATE = 0.0139527%                                           │
│                                                                         │
│  5. 잔고 조회 통합                                                       │
│     ─────────────────                                                   │
│     KRX 잔고 + NXT 잔고 = 통합 잔고                                      │
│     (TR_ID: TTTC8434R + TTTN8434R)                                      │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.4 NXT 수수료 설정 (.env)

```bash
# ═══════════════════════════════════════════════════════════════
#              NXT 수수료 설정 (.env 파일)
# ═══════════════════════════════════════════════════════════════

# KRX (정규장)
KIS_FEE_RATE=0.0140527          # 증권사 수수료 (%)
KIS_TAX_TOTAL=0.15              # 거래세 (%)

# NXT (대체거래소)
KIS_NXT_FEE_RATE=0.0139527      # NXT 증권사 수수료 (%)
KIS_NXT_TAX_TOTAL=0.15          # NXT 거래세 (%)
```

### 11.5 NXT 구현 코드 설계

```python
# ═══════════════════════════════════════════════════════════════
#              NXT 지원 KIS Fetcher 설계
# ═══════════════════════════════════════════════════════════════

class KISFetcher:
    """한국투자증권 API 래퍼 (KRX + NXT 지원)"""

    # TR_ID 매핑
    TR_ID_MAP = {
        "KRX": {
            "buy": "TTTC0802U",
            "sell": "TTTC0801U",
            "balance": "TTTC8434R",
            "unfilled": "TTTC8036R",
        },
        "NXT": {
            "buy": "TTTN0802U",
            "sell": "TTTN0801U",
            "balance": "TTTN8434R",
            "unfilled": "TTTN8036R",
        }
    }

    def buy_order(
        self,
        stock_code: str,
        quantity: int,
        price: int = 0,
        order_type: str = "LIMIT",  # LIMIT or MARKET
        market: str = "KRX"         # KRX or NXT
    ) -> dict:
        """
        매수 주문

        Args:
            stock_code: 종목코드
            quantity: 수량
            price: 가격 (지정가 시)
            order_type: LIMIT(지정가) or MARKET(시장가)
            market: KRX or NXT

        Returns:
            주문 결과
        """
        # NXT 시장가 차단
        if market == "NXT" and order_type == "MARKET":
            logger.warning("NXT는 시장가 불가 → 지정가로 변환")
            order_type = "LIMIT"
            if price == 0:
                price = self._get_ask_price_1(stock_code)  # 매도1호가

        # TR_ID 선택
        tr_id = self.TR_ID_MAP[market]["buy"]

        # 주문 실행
        return self._execute_order(
            tr_id=tr_id,
            stock_code=stock_code,
            quantity=quantity,
            price=price,
            order_type=order_type
        )

    def get_combined_balance(self) -> List[dict]:
        """
        통합 잔고 조회 (KRX + NXT)

        Returns:
            KRX 잔고 + NXT 잔고 통합 리스트
        """
        krx_balance = self._get_balance("KRX")
        nxt_balance = self._get_balance("NXT")

        # 동일 종목 병합
        combined = {}
        for item in krx_balance + nxt_balance:
            code = item["stock_code"]
            if code in combined:
                # 수량 합산, 평균단가 재계산
                combined[code] = self._merge_positions(
                    combined[code], item
                )
            else:
                combined[code] = item

        return list(combined.values())

    def _get_balance(self, market: str) -> List[dict]:
        """시장별 잔고 조회"""
        tr_id = self.TR_ID_MAP[market]["balance"]
        # API 호출...

    def calc_fee(self, amount: int, market: str = "KRX") -> dict:
        """
        수수료 계산

        Args:
            amount: 거래금액
            market: KRX or NXT

        Returns:
            {fee: 수수료, tax: 거래세, total: 합계}
        """
        if market == "NXT":
            fee_rate = float(os.getenv("KIS_NXT_FEE_RATE", "0.0139527"))
            tax_rate = float(os.getenv("KIS_NXT_TAX_TOTAL", "0.15"))
        else:
            fee_rate = float(os.getenv("KIS_FEE_RATE", "0.0140527"))
            tax_rate = float(os.getenv("KIS_TAX_TOTAL", "0.15"))

        fee = int(amount * fee_rate / 100)
        tax = int(amount * tax_rate / 100)

        return {"fee": fee, "tax": tax, "total": fee + tax}
```

### 11.6 NXT 운영시간 처리

```python
# ═══════════════════════════════════════════════════════════════
#              NXT 운영시간 체크
# ═══════════════════════════════════════════════════════════════

def is_market_open(market: str = "KRX") -> bool:
    """
    시장 운영시간 확인

    Args:
        market: KRX or NXT

    Returns:
        운영 중 여부
    """
    now = datetime.now()
    weekday = now.weekday()

    # 주말 제외
    if weekday >= 5:
        return False

    current_time = now.time()

    if market == "NXT":
        # NXT: 08:00 ~ 20:00
        market_open = time(8, 0)
        market_close = time(20, 0)
    else:
        # KRX: 09:00 ~ 15:30
        market_open = time(9, 0)
        market_close = time(15, 30)

    return market_open <= current_time <= market_close


def get_available_market() -> str:
    """
    현재 이용 가능한 시장 반환

    Returns:
        "KRX", "NXT", or None
    """
    now = datetime.now().time()

    # 08:00 ~ 09:00: NXT 프리마켓
    if time(8, 0) <= now < time(9, 0):
        return "NXT"

    # 09:00 ~ 15:30: KRX 정규장 (우선)
    if time(9, 0) <= now <= time(15, 30):
        return "KRX"

    # 15:30 ~ 20:00: NXT 애프터마켓
    if time(15, 30) < now <= time(20, 0):
        return "NXT"

    return None
```

### 11.7 NXT 구현 체크리스트

- [ ] TR_ID 매핑 테이블 구현
- [ ] `buy_order()` market 파라미터 추가
- [ ] `sell_order()` market 파라미터 추가
- [ ] NXT 시장가 주문 차단 로직
- [ ] `get_combined_balance()` KRX+NXT 통합
- [ ] 수수료 계산 분기 (`calc_fee`)
- [ ] 운영시간 체크 함수 (`is_market_open`)
- [ ] .env 파일 NXT 설정 추가
- [ ] 단위 테스트 작성

### 11.8 NXT 주의사항

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         NXT 주의사항                                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ⚠️ 반드시 숙지해야 할 사항                                              │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  1. 시장가 주문 불가                                                     │
│     - NXT는 지정가만 가능                                                │
│     - 시장가 요청 시 자동으로 매도1호가 지정가로 변환                     │
│                                                                         │
│  2. 유동성 제한                                                          │
│     - 대형주 위주로 거래                                                 │
│     - 소형주는 체결 어려움                                               │
│     - 호가 스프레드 넓을 수 있음                                         │
│                                                                         │
│  3. 잔고 조회 주의                                                       │
│     - KRX와 NXT 잔고 별도 조회 필요                                      │
│     - 통합 잔고 = KRX 잔고 + NXT 잔고                                    │
│     - 동일 종목 보유 시 합산 처리                                        │
│                                                                         │
│  4. 시간대별 전략                                                        │
│     - 08:00~09:00: NXT 프리마켓 (갭 대응)                                │
│     - 09:00~15:30: KRX 우선 (유동성)                                     │
│     - 15:30~20:00: NXT 애프터마켓 (미국장 대응)                           │
│                                                                         │
│  5. 수수료 계산                                                          │
│     - KRX/NXT 별도 수수료율 적용 필수                                    │
│     - 거래세는 동일 (0.15%)                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 12. 오늘의 운영 이슈 (2024-12-08)

> 실제 운영 중 발생한 문제와 원인 분석

### 12.1 한국전력 매수 이슈

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      🚨 한국전력 매수 문제                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  📋 상황                                                                 │
│  ─────────────────────────────────────────────────────────────────────  │
│  - 예상치 못한 한국전력(015760) 매수 발생                                │
│  - AI 분석 점수가 높게 나옴                                              │
│                                                                         │
│  🔍 원인 분석                                                            │
│  ─────────────────────────────────────────────────────────────────────  │
│  1. Screener 필터링 미흡                                                 │
│     - 시가총액/섹터 필터 없음                                            │
│     - 공기업/유틸리티 섹터 제외 안됨                                     │
│                                                                         │
│  2. AI 점수 맹신                                                         │
│     - 수급 데이터만으로 높은 점수                                        │
│     - 펀더멘털/섹터 특성 미반영                                          │
│                                                                         │
│  3. 블랙리스트 미적용                                                    │
│     - 회피 종목 리스트 없음                                              │
│                                                                         │
│  🛠️ 해결방안                                                             │
│  ─────────────────────────────────────────────────────────────────────  │
│  1. Screener에 섹터 필터 추가                                            │
│     excluded_sectors = ["유틸리티", "공기업"]                             │
│                                                                         │
│  2. 종목 블랙리스트 구현                                                 │
│     BLACKLIST = ["015760", ...]  # 한전, 가스공사 등                     │
│                                                                         │
│  3. AI 프롬프트에 섹터 제외 조건 추가                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 12.2 잔고 불일치 이슈

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      🚨 잔고 불일치 문제                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  📋 상황                                                                 │
│  ─────────────────────────────────────────────────────────────────────  │
│  - 대시보드 잔고 ≠ 실제 HTS/MTS 잔고                                    │
│  - 특정 종목이 누락되거나 수량 불일치                                    │
│                                                                         │
│  🔍 원인 분석                                                            │
│  ─────────────────────────────────────────────────────────────────────  │
│  1. KRX만 조회, NXT 잔고 누락                                            │
│     - TTTC8434R (KRX)만 호출                                            │
│     - TTTN8434R (NXT) 미호출                                            │
│                                                                         │
│  2. 동기화 타이밍 이슈                                                   │
│     - 체결 후 DB 반영 지연                                               │
│     - WebSocket 미연결 시 누락                                           │
│                                                                         │
│  3. 수동 매매 미반영                                                     │
│     - MTS에서 직접 매매한 건 미동기화                                    │
│                                                                         │
│  🛠️ 해결방안                                                             │
│  ─────────────────────────────────────────────────────────────────────  │
│  1. KRX + NXT 통합 잔고 조회                                             │
│     combined = get_krx_balance() + get_nxt_balance()                     │
│                                                                         │
│  2. 정기 강제 동기화 (10분마다)                                          │
│     - API 직접 조회 → DB 업데이트                                        │
│                                                                         │
│  3. WebSocket 재연결 감시 강화                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 12.3 NXT 미구현 이슈

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      🚨 NXT 미구현 문제                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  📋 상황                                                                 │
│  ─────────────────────────────────────────────────────────────────────  │
│  - NXT 거래 기록이 시스템에 미반영                                       │
│  - 프리마켓/애프터마켓 거래 불가                                         │
│                                                                         │
│  🔍 원인 분석                                                            │
│  ─────────────────────────────────────────────────────────────────────  │
│  1. TR_ID 미분기                                                         │
│     - 모든 주문이 KRX TR_ID 사용                                         │
│     - NXT TR_ID (TTTN****) 미구현                                        │
│                                                                         │
│  2. 운영시간 체크 누락                                                   │
│     - 08:00~09:00, 15:30~20:00 고려 안됨                                 │
│                                                                         │
│  3. 수수료 계산 미분기                                                   │
│     - NXT 수수료율 적용 안됨                                             │
│                                                                         │
│  🛠️ 해결방안                                                             │
│  ─────────────────────────────────────────────────────────────────────  │
│  → Section 11 (NXT 시장 연동) 구현 참조                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 12.4 이슈 해결 우선순위

| 순위 | 이슈 | 긴급도 | 영향도 | 예상 공수 |
|-----|------|-------|-------|----------|
| 1 | 잔고 불일치 (NXT 통합) | 🔴 긴급 | 🔴 높음 | 4시간 |
| 2 | 한전 류 종목 필터 | 🟡 보통 | 🟡 중간 | 2시간 |
| 3 | NXT 주문 구현 | 🟢 낮음 | 🟡 중간 | 8시간 |

---

## 13. 체크리스트

### 13.1 REST API 구현

- [ ] OAuth 토큰 발급 및 자동 갱신
- [ ] 예수금/잔고 조회 (TTTC8434R)
- [ ] 매수/매도 주문 (TTTC0802U/0801U)
- [ ] 미체결 조회 (TTTC8036R)
- [ ] 에러 핸들링 및 재시도 로직

### 13.2 WebSocket 구현

- [ ] approval_key 발급
- [ ] 실시간 호가 구독 (H0STASP0)
- [ ] 실시간 체결 구독 (H0STCNT0)
- [ ] **체결 통보 구독 (H0STCNI0)** ⚡
- [ ] 자동 재연결 로직

### 13.3 DB 연동

- [ ] trade_orders INSERT (주문 시)
- [ ] trade_orders UPDATE (체결 시)
- [ ] trade_executions INSERT (체결 시)
- [ ] portfolio UPDATE (체결 시)
- [ ] account_snapshots INSERT (정기)

---

*Last Updated: 2024-12-08*
*Version: 4.0 (AEGIS v3.0) - NXT 시장 연동 및 운영 이슈 문서화*


[참고용]

한국투자증권(KIS) **WebSocket(실시간)**에서 사용하는 코드는 REST API의 `TTTC...` 스타일이 아니라, **`H0...` (Real-time TR)** 스타일을 사용합니다. **AEGIS 시스템 구축에 필요한 모든 실시간 TR 코드**를 중요도 순으로 정리해 드립니다. --- ### 🚨 핵심 차이점 (먼저 확인!) * **REST API (요청/응답):** `TTTC8434R` (잔고조회) 등 → **내가 물어봐야 대답함.** * **WebSocket (실시간 푸시):** `H0STCNT0` (주식체결) 등 → **연결해두면 알아서 계속 보냄.** --- ### 1. 📢 계좌 관련 (가장 중요) 주문이 체결되었을 때 즉시 알림을 받는 코드입니다. (자동매매 필수) | TR ID | 이름 | Key 값 | 제공 정보 | 비고 | | :--- | :--- | :--- | :--- | :--- | | **`H0STCNI0`** | **주식 체결 통보 (실전)** | **HTS ID** | 주문번호, 체결시간, 체결가, 체결수량, 매수/매도구분 | **실전 필수** | | **`H0STCNI9`** | **주식 체결 통보 (모의)** | **HTS ID** | (위와 동일) | **모의 필수** | > **주의:** 이 코드는 종목코드(`005930`)가 아니라 **사용자 ID(HTS ID)**를 `tr_key`에 넣어야 합니다. --- ### 2. 📈 국내 주식 시세 (필수) 차트와 호가창을 구성하고 단타 로직을 돌리는 데 쓰입니다. | TR ID | 이름 | Key 값 | 제공 정보 | 활용처 | | :--- | :--- | :--- | :--- | :--- | | **`H0STCNT0`** | **주식 체결가** | 종목코드 | 현재가, 등락률, 거래량, 누적거래대금, 시/고/저 | **Type-V(VWAP), 기본 시세** | | **`H0STASP0`** | **주식 호가** | 종목코드 | 매도 1~10호가/잔량, 매수 1~10호가/잔량, 총매도/매수잔량 | **Type-S(호가 스캘핑), 스마트 주문** | | **`H0STCTI0`** | 주식 체결 강도 | 종목코드 | 체결강도, 매수체결량, 매도체결량 | 단타 모멘텀 판단 | --- ### 3. 🧠 고급 분석용 (Alpha 전략용) 기관/외국인의 움직임이나 시장 경보를 포착합니다. | TR ID | 이름 | Key 값 | 제공 정보 | 활용처 | | :--- | :--- | :--- | :--- | :--- | | **`H0STPGM0`** | **프로그램 매매** | 종목코드 | 프로그램 순매수(차익/비차익), 증감 | **Type-D(수급), Alpha 전략** | | **`H1VI`** | **VI 발동 해제** | (None) | VI종류(정적/동적), 발동가격, 해제예상가 | **Type-N(뉴스/급등주), Safety** | | **`H0UPCNT0`** | 업종 지수 | 업종코드 | 코스피/코스닥 지수, 등락률, 거래량 | **MarketGuard (폭락장 감지)** | | `H0STNV` | 예상 체결가 | 종목코드 | (장전/장마감) 예상체결가, 예상수량 | **Morning Gap (시초가 공략)** | --- ### 4. 🇺🇸 해외 주식 (참고용) 미국장 데이터를 실시간으로 받고 싶을 때 사용합니다. | TR ID | 이름 | Key 값 | 제공 정보 | | :--- | :--- | :--- | :--- | | **`HDFSCNT0`** | 미국 체결가 | 티커(D+티커) | 현재가, 체결수량 | | **`HDFSASP0`** | 미국 호가 | 티커(D+티커) | 매수/매도 호가 및 잔량 | --- ### 🛠️ AEGIS 시스템 적용 가이드 사용자님의 시스템(`fetchers/realtime_client.py`)에 **반드시 등록해야 할 리스트**는 다음과 같습니다. 1. **`H0STCNI0` (또는 `9`):** 내 주문 체결 확인용. (DB 동기화) 2. **`H0STCNT0`:** 감시 중인 종목의 현재가 업데이트. (Stop Loss 감시) 3. **`H0STASP0`:** 매수 주문 직전, '최우선 매도호가' 파악용. (SOR 지정가 주문) 4. **`H0STPGM0`:** 프로그램 수급이 들어오는지 확인용. (Type-D 가중치) **[팁]** `H0STCNT0` (체결가) 데이터만 받아도 **가격, 거래량, 등락률, 시/고/저**가 다 들어오므로, 데이터 비용을 아끼려면 호가(`H0STASP0`)는 매매 시점에만 잠깐 REST API로 조회하는 것도 방법입니다. (단타 위주면 호가도 소켓으로 받아야 합니다.)