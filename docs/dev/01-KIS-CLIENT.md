# KIS Client 재개발 상세

> 작성일: 2025-12-09
> 상태: 진행중
> Phase: 1

---

## 🎯 목표

v2의 KIS Client 문제점을 해결하고, Write/Read only 규칙을 준수하는 새로운 구조 구축

---

## 📊 현재 상태 분석

### 기존 kis_client.py 문제점

```python
# ❌ 현재 구조 (v2)
class KISClient:
    def get_current_price()  # 누구나 호출 가능
    def buy_order()          # 누구나 호출 가능
    def sell_order()         # 누구나 호출 가능

# 문제:
# 1. Dashboard, Brain, Telegram이 모두 직접 호출 가능
# 2. DB Write 책임 불명확
# 3. 데이터 불일치 발생 (캐시 vs 실시간)
# 4. NXT 미지원
# 5. WebSocket 체결 통보 없음
```

---

## ✅ 새로운 구조

### 계층 분리

```
┌─────────────────────────────────────────────────┐
│  [KIS API]                                      │
│      ↓                                          │
│  ┌────────────────────────────────────────┐    │
│  │  kis_client.py                         │    │
│  │  (내부 전용, API 래퍼)                 │    │
│  │  • get_access_token()                  │    │
│  │  • get_balance() ← 신규               │    │
│  │  • get_current_price()                 │    │
│  │  • buy_order()                         │    │
│  │  • sell_order()                        │    │
│  │  • connect_websocket()                 │    │
│  │  • subscribe_execution() ← 신규       │    │
│  └────────────┬───────────────────────────┘    │
│               ↓                                 │
│  ┌────────────────────────────────────────┐    │
│  │  fetchers/kis_fetcher.py               │    │
│  │  (Write only to DB)                    │    │
│  │  • sync_portfolio() ← 신규            │    │
│  │  • on_execution_notice() ← 신규       │    │
│  │  • sync_execution() ← 신규            │    │
│  └────────────┬───────────────────────────┘    │
│               ↓                                 │
│  ┌────────────────────────────────────────┐    │
│  │  PostgreSQL                            │    │
│  │  • portfolio                           │    │
│  │  • trade_orders                        │    │
│  │  • trade_executions                    │    │
│  │  • account_snapshots                   │    │
│  └────────────┬───────────────────────────┘    │
│               ↓                                 │
│  ┌────────────────────────────────────────┐    │
│  │  services/portfolio_service.py         │    │
│  │  (Read only from DB)                   │    │
│  │  • get_portfolio() ← 신규             │    │
│  │  • get_total_asset() ← 신규           │    │
│  │  • get_stock_info() ← 신규            │    │
│  └────────────┬───────────────────────────┘    │
│               ↓                                 │
│  ┌────────────────────────────────────────┐    │
│  │  Dashboard, Brain, Telegram, Safety    │    │
│  │  (모두 PortfolioService만 사용)        │    │
│  └────────────────────────────────────────┘    │
│                                                 │
│  ┌────────────────────────────────────────┐    │
│  │  services/order_service.py             │    │
│  │  (예외: 주문 직전만 kis_client 사용)   │    │
│  │  • place_buy_order() ← 신규           │    │
│  │  • place_sell_order() ← 신규          │    │
│  └────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

---

## 🛠️ 개발 작업

### 1. kis_client.py 개선

#### 1.1 NXT 지원

```python
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
    order_type: str = "LIMIT",
    market: str = "KRX"  # ← 추가
) -> dict:
    # NXT 시장가 차단
    if market == "NXT" and order_type == "MARKET":
        logger.warning("NXT는 시장가 불가 → 지정가로 변환")
        order_type = "LIMIT"
        if price == 0:
            price = self._get_ask_price_1(stock_code)

    # TR_ID 선택
    tr_id = self.TR_ID_MAP[market]["buy"]

    # 주문 실행
    return self._execute_order(...)
```

**체크리스트**:
- [ ] TR_ID 매핑 테이블 구현
- [ ] buy_order() market 파라미터 추가
- [ ] sell_order() market 파라미터 추가
- [ ] NXT 시장가 차단 로직
- [ ] 수수료 계산 분기
- [ ] 단위 테스트

#### 1.2 get_balance() 추가

```python
def get_balance(self, market: str = "KRX") -> List[dict]:
    """
    잔고 조회 (REST API)

    Args:
        market: KRX or NXT

    Returns:
        잔고 리스트
    """
    if not self.access_token:
        self.get_access_token()

    tr_id = self.TR_ID_MAP[market]["balance"]

    url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {self.access_token}",
        "appkey": self.app_key,
        "appsecret": self.app_secret,
        "tr_id": tr_id
    }
    params = {
        "CANO": self.account_number,
        "ACNT_PRDT_CD": self.account_code,
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
    if response.status_code == 200:
        data = response.json()
        return data.get("output1", [])
    else:
        raise Exception(f"Failed to get balance: {response.text}")

def get_combined_balance(self) -> List[dict]:
    """
    통합 잔고 조회 (KRX + NXT)
    """
    krx_balance = self.get_balance("KRX")
    nxt_balance = self.get_balance("NXT")

    # 동일 종목 병합
    combined = {}
    for item in krx_balance + nxt_balance:
        code = item["pdno"]
        if code in combined:
            # 수량 합산, 평균단가 재계산
            combined[code] = self._merge_positions(
                combined[code], item
            )
        else:
            combined[code] = item

    return list(combined.values())
```

**체크리스트**:
- [ ] get_balance() 구현
- [ ] get_combined_balance() 구현
- [ ] _merge_positions() 헬퍼 함수
- [ ] 단위 테스트

#### 1.3 WebSocket 체결 통보 (H0STCNI0)

```python
async def subscribe_execution_notice(self):
    """
    체결 통보 구독 (H0STCNI0)

    내 주문 체결 시 즉시 알림 (10~50ms)
    """
    if not self.ws_connection:
        await self.connect_websocket()

    # 체결 통보 구독
    subscribe_msg = {
        "header": {
            "approval_key": self.ws_approval_key,
            "custtype": "P",
            "tr_type": "1",
            "content-type": "utf-8"
        },
        "body": {
            "input": {
                "tr_id": "H0STCNI0",  # 실전
                "tr_key": settings.kis_hts_id  # HTS ID!
            }
        }
    }

    await self.ws_connection.send(json.dumps(subscribe_msg))
    logger.info("📡 Subscribed to execution notice (H0STCNI0)")

async def on_execution_notice(self, data: dict):
    """
    체결 통보 처리 (콜백)

    이 함수는 KISFetcher에서 구현됨
    kis_client는 WebSocket만 담당
    """
    # KISFetcher.on_execution_notice()로 전달
    pass
```

**체크리스트**:
- [ ] subscribe_execution_notice() 구현
- [ ] HTS_ID 환경변수 추가
- [ ] WebSocket 메시지 파싱
- [ ] 단위 테스트

---

### 2. KISFetcher 신규 개발

#### 2.1 sync_portfolio() - 잔고 동기화

```python
# fetchers/kis_fetcher.py

class KISFetcher:
    """
    KIS API → DB 동기화 전담
    유일한 DB Writer
    """

    def __init__(self):
        self.kis_client = kis_client

    async def sync_portfolio(self):
        """
        KIS API → DB 잔고 동기화

        실행 주기:
        - 장중: 1분마다
        - 장외: 10분마다
        """
        try:
            # 1. KIS API에서 잔고 조회 (KRX + NXT)
            balance_data = self.kis_client.get_combined_balance()

            # 2. DB 업데이트 (Upsert)
            for item in balance_data:
                portfolio = await db.query(Portfolio).filter(
                    Portfolio.stock_code == item['pdno']
                ).first()

                if portfolio:
                    # 기존 종목 업데이트
                    portfolio.quantity = int(item['hldg_qty'])
                    portfolio.avg_price = float(item['pchs_avg_pric'])
                    portfolio.current_price = float(item['prpr'])
                    portfolio.profit_rate = float(item['evlu_pfls_rt'])
                    portfolio.updated_at = datetime.now()
                else:
                    # 신규 종목 추가
                    new_portfolio = Portfolio(
                        stock_code=item['pdno'],
                        stock_name=item['prdt_name'],
                        quantity=int(item['hldg_qty']),
                        avg_price=float(item['pchs_avg_pric']),
                        current_price=float(item['prpr']),
                        profit_rate=float(item['evlu_pfls_rt'])
                    )
                    db.add(new_portfolio)

            # 3. 수량 0인 종목 삭제
            await db.query(Portfolio).filter(
                Portfolio.quantity == 0
            ).delete()

            await db.commit()

            logger.info(f"✅ Portfolio synced: {len(balance_data)} stocks")

        except Exception as e:
            logger.error(f"❌ Portfolio sync failed: {e}")
            await db.rollback()
            raise
```

**체크리스트**:
- [ ] sync_portfolio() 구현
- [ ] Upsert 로직
- [ ] 에러 처리
- [ ] 단위 테스트

#### 2.2 on_execution_notice() - 체결 통보 처리

```python
async def on_execution_notice(self, data: dict):
    """
    체결 통보 수신 시 즉시 처리

    WebSocket H0STCNI0에서 호출됨
    """
    try:
        # 1. trade_orders 상태 업데이트
        order = await db.query(TradeOrder).filter(
            TradeOrder.order_no == data['ODNO']
        ).first()

        if not order:
            logger.warning(f"Order not found: {data['ODNO']}")
            return

        order.status = 'FILLED'
        order.executed_at = datetime.now()

        # 2. trade_executions 기록
        execution = TradeExecution(
            order_no=data['ODNO'],
            stock_code=data['PDNO'],
            exec_qty=int(data['CNTG_QTY']),
            exec_price=int(data['CNTG_UNPR']),
            executed_at=self._parse_time(data['STCK_CNTG_HOUR'])
        )
        db.add(execution)

        # 3. portfolio 업데이트
        if data['SELN_BYOV_CLS'] == '02':  # 매수
            await self._update_portfolio_on_buy(data)
        else:  # 매도
            await self._update_portfolio_on_sell(data)

        # 4. 텔레그램 알림
        await send_telegram(
            f"✅ 체결: {data['PDNO']} "
            f"{data['CNTG_QTY']}주 @ {data['CNTG_UNPR']:,}원"
        )

        await db.commit()

        logger.info(f"✅ Execution processed: {data['ODNO']}")

    except Exception as e:
        logger.error(f"❌ Execution processing failed: {e}")
        await db.rollback()
        raise
```

**체크리스트**:
- [ ] on_execution_notice() 구현
- [ ] _update_portfolio_on_buy() 구현
- [ ] _update_portfolio_on_sell() 구현
- [ ] 텔레그램 알림
- [ ] 단위 테스트

---

### 3. PortfolioService 신규 개발

```python
# services/portfolio_service.py

class PortfolioService:
    """
    Portfolio 조회 전담 (Read only)

    모든 모듈은 이 서비스만 사용
    """

    async def get_portfolio(self) -> List[Portfolio]:
        """
        전체 보유종목 조회
        """
        return await db.query(Portfolio).filter(
            Portfolio.quantity > 0
        ).all()

    async def get_total_asset(self) -> int:
        """
        총 자산 조회
        """
        snapshot = await db.query(AccountSnapshot).order_by(
            AccountSnapshot.timestamp.desc()
        ).first()

        return snapshot.total_asset if snapshot else 0

    async def get_stock_info(self, stock_code: str) -> Optional[Portfolio]:
        """
        개별 종목 정보 조회
        """
        return await db.query(Portfolio).filter(
            Portfolio.stock_code == stock_code
        ).first()

# Singleton
portfolio_service = PortfolioService()
```

**체크리스트**:
- [ ] PortfolioService 클래스 구현
- [ ] get_portfolio() 구현
- [ ] get_total_asset() 구현
- [ ] get_stock_info() 구현
- [ ] 단위 테스트

---

### 4. OrderService 신규 개발

```python
# services/order_service.py

class OrderService:
    """
    주문 전담 서비스

    예외: 주문 직전만 kis_client 직접 조회
    """

    async def place_buy_order(
        self,
        stock_code: str,
        quantity: int,
        price: int,
        market: str = "KRX"
    ):
        """
        매수 주문

        주문 직전 실시간 잔고 확인 필수!
        """
        # 1. 주문 직전 실시간 잔고 확인 (KIS API 직접)
        balance = await kis_client.get_available_deposit()
        required = quantity * price

        if balance < required:
            raise InsufficientBalanceError(
                f"잔고 부족: 필요 {required:,}원, 가용 {balance:,}원"
            )

        # 2. 주문 실행
        result = kis_client.buy_order(
            stock_code=stock_code,
            quantity=quantity,
            price=price,
            market=market
        )

        # 3. 주문 DB 기록
        order = TradeOrder(
            order_no=result['ODNO'],
            stock_code=stock_code,
            order_type='BUY',
            qty=quantity,
            price=price,
            status='PENDING',
            market=market
        )
        db.add(order)
        await db.commit()

        # 4. 체결은 WebSocket(H0STCNI0)이 자동 처리

        return result

# Singleton
order_service = OrderService()
```

**체크리스트**:
- [ ] OrderService 클래스 구현
- [ ] place_buy_order() 구현
- [ ] place_sell_order() 구현
- [ ] 잔고 검증 로직
- [ ] 단위 테스트

---

## 📝 테스트 계획

### 단위 테스트

```python
# tests/test_kis_client.py
def test_buy_order_nxt():
    """NXT 주문 테스트"""
    result = kis_client.buy_order(
        stock_code="005930",
        quantity=10,
        price=52000,
        market="NXT"
    )
    assert result['tr_id'] == "TTTN0802U"

def test_combined_balance():
    """통합 잔고 조회 테스트"""
    balance = kis_client.get_combined_balance()
    assert isinstance(balance, list)
```

### 통합 테스트

```python
# tests/test_integration.py
async def test_execution_flow():
    """체결 플로우 테스트"""
    # 1. 주문
    result = await order_service.place_buy_order(...)

    # 2. WebSocket 체결 통보 대기
    await asyncio.sleep(5)

    # 3. DB 확인
    portfolio = await portfolio_service.get_stock_info("005930")
    assert portfolio.quantity == 10
```

---

## 🚀 다음 단계

1. kis_client.py 개선 완료
2. KISFetcher 개발 완료
3. PortfolioService 개발 완료
4. OrderService 개발 완료
5. 통합 테스트
6. Phase 2 진행

---

**작성**: Claude Code
**상태**: 작성 완료
**다음**: kis_client.py 개발 시작
