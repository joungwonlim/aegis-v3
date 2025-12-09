# WebSocket Manager 설계

> 작성일: 2025-12-09
> 상태: 설계
> Phase: 2

---

## 🎯 목표

40개 슬롯 제한 하에서 우선순위 기반 동적 구독 관리

---

## 📊 슬롯 제한 및 우선순위

### KIS WebSocket 제한

- **최대 동시 구독**: 40개 종목 (TR_ID별)
- **TR_ID 종류**:
  - H0STCNT0: 실시간 체결가
  - H0STASP0: 실시간 호가
  - H0STPGM0: 프로그램 매매
  - H0STCNI0: 체결 통보 (계좌 단위, 슬롯 소비 안함)

### 우선순위 정책

```python
Priority 1 (최우선): 보유종목
  - 항상 구독 유지
  - 매도 시점 포착 필수
  - 예: 10종목 보유 → 10 슬롯 고정

Priority 2 (중요): AI Daily Picks
  - DeepSeek R1 일일 분석 결과
  - 매수 기회 포착
  - 예: 20종목 선정 → 20 슬롯

Priority 3 (일반): 급등주/거래량 상위
  - Market Scanner 실시간 발견
  - 나머지 슬롯 활용
  - 예: 10 슬롯 (40 - 10 - 20)
```

### 슬롯 재할당 로직

```
1. 보유종목 변경 시
   - 매수 체결: 즉시 구독 추가
   - 매도 체결: 즉시 구독 해제

2. Daily Picks 갱신 시 (07:20)
   - 기존 Priority 2 전체 해제
   - 새로운 Picks 구독

3. 급등주 발견 시
   - 슬롯 여유 있으면: 즉시 추가
   - 슬롯 부족하면: Priority 3 중 가장 오래된 종목 교체
```

---

## 🏗️ 아키텍처

### 클래스 구조

```python
class WebSocketSlot:
    """단일 슬롯 정보"""
    stock_code: str
    tr_id: str  # H0STCNT0 등
    priority: int  # 1, 2, 3
    subscribed_at: datetime
    last_data_at: datetime

class KISWebSocketManager:
    """WebSocket 슬롯 관리자"""

    # 속성
    max_slots: int = 40
    slots: Dict[str, WebSocketSlot]  # key: stock_code
    ws_connection: websockets.WebSocketClientProtocol

    # 구독 관리
    async def subscribe(stock_code, priority, tr_id)
    async def unsubscribe(stock_code)
    async def resubscribe_all()

    # 우선순위 관리
    async def update_priorities()
    async def evict_lowest_priority()

    # 데이터 수신
    async def listen()
    async def handle_message(data)
```

---

## 🔧 구현 계획

### 1. WebSocketSlot 클래스

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class WebSocketSlot:
    """WebSocket 구독 슬롯"""
    stock_code: str
    stock_name: str
    tr_id: str  # H0STCNT0, H0STASP0, H0STPGM0
    priority: int  # 1=보유, 2=AI picks, 3=급등주
    subscribed_at: datetime
    last_data_at: datetime = None

    def is_stale(self, threshold_minutes: int = 30) -> bool:
        """데이터 수신이 오래되었는지 확인"""
        if not self.last_data_at:
            return False
        elapsed = (datetime.now() - self.last_data_at).total_seconds() / 60
        return elapsed > threshold_minutes
```

### 2. KISWebSocketManager 클래스

```python
class KISWebSocketManager:
    """
    KIS WebSocket 슬롯 관리자

    특징:
    - 40개 슬롯 제한
    - 우선순위 기반 자동 관리
    - 재연결 처리
    """

    MAX_SLOTS = 40

    def __init__(self):
        self.kis_client = kis_client
        self.slots: Dict[str, WebSocketSlot] = {}
        self.ws_connection = None
        self.is_running = False

    async def start(self):
        """WebSocket 연결 및 리스너 시작"""
        await self.kis_client.connect_websocket()
        self.ws_connection = self.kis_client.ws_connection
        self.is_running = True

        # 체결 통보 구독 (슬롯 소비 안함)
        await self.kis_client.subscribe_execution_notice()

        # 데이터 수신 루프 시작
        asyncio.create_task(self.listen())

        logger.info("✅ WebSocket Manager started")

    async def subscribe(
        self,
        stock_code: str,
        stock_name: str,
        priority: int,
        tr_id: str = "H0STCNT0"
    ) -> bool:
        """
        종목 구독

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            priority: 우선순위 (1, 2, 3)
            tr_id: TR_ID (기본: H0STCNT0 실시간 체결가)

        Returns:
            구독 성공 여부
        """
        # 이미 구독중
        if stock_code in self.slots:
            logger.debug(f"Already subscribed: {stock_code}")
            return True

        # 슬롯 부족 - 낮은 우선순위 제거
        if len(self.slots) >= self.MAX_SLOTS:
            evicted = await self.evict_lowest_priority(priority)
            if not evicted:
                logger.warning(f"⚠️  Cannot subscribe {stock_code}: slots full")
                return False

        # WebSocket 구독 메시지 전송
        try:
            subscribe_msg = {
                "header": {
                    "approval_key": self.kis_client.ws_approval_key,
                    "custtype": "P",
                    "tr_type": "1",
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": tr_id,
                        "tr_key": stock_code
                    }
                }
            }

            await self.ws_connection.send(json.dumps(subscribe_msg))

            # 슬롯 기록
            self.slots[stock_code] = WebSocketSlot(
                stock_code=stock_code,
                stock_name=stock_name,
                tr_id=tr_id,
                priority=priority,
                subscribed_at=datetime.now()
            )

            logger.info(f"📡 Subscribed: {stock_code} (priority={priority}, slots={len(self.slots)}/{self.MAX_SLOTS})")
            return True

        except Exception as e:
            logger.error(f"❌ Subscribe failed: {stock_code} - {e}")
            return False

    async def unsubscribe(self, stock_code: str) -> bool:
        """
        종목 구독 해제

        Args:
            stock_code: 종목코드

        Returns:
            해제 성공 여부
        """
        if stock_code not in self.slots:
            logger.debug(f"Not subscribed: {stock_code}")
            return True

        slot = self.slots[stock_code]

        # WebSocket 구독 해제 메시지 전송
        try:
            unsubscribe_msg = {
                "header": {
                    "approval_key": self.kis_client.ws_approval_key,
                    "custtype": "P",
                    "tr_type": "2",  # 2=해제
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": slot.tr_id,
                        "tr_key": stock_code
                    }
                }
            }

            await self.ws_connection.send(json.dumps(unsubscribe_msg))

            # 슬롯 제거
            del self.slots[stock_code]

            logger.info(f"🔕 Unsubscribed: {stock_code} (slots={len(self.slots)}/{self.MAX_SLOTS})")
            return True

        except Exception as e:
            logger.error(f"❌ Unsubscribe failed: {stock_code} - {e}")
            return False

    async def evict_lowest_priority(self, required_priority: int) -> bool:
        """
        가장 낮은 우선순위 종목 제거

        Args:
            required_priority: 필요한 우선순위

        Returns:
            제거 성공 여부
        """
        # Priority 3 중 가장 오래된 것 찾기
        priority_3_slots = [
            (code, slot) for code, slot in self.slots.items()
            if slot.priority == 3
        ]

        if not priority_3_slots:
            logger.warning("⚠️  No priority 3 slots to evict")
            return False

        # 가장 오래된 슬롯 제거
        oldest = min(priority_3_slots, key=lambda x: x[1].subscribed_at)
        await self.unsubscribe(oldest[0])

        logger.info(f"🔄 Evicted: {oldest[0]} (priority=3)")
        return True

    async def sync_with_portfolio(self):
        """
        보유종목과 동기화 (Priority 1)
        """
        # 현재 보유종목 조회
        portfolio = await portfolio_service.get_portfolio()
        portfolio_codes = {p.stock_code for p in portfolio}

        # 현재 Priority 1 슬롯
        current_priority1 = {
            code for code, slot in self.slots.items()
            if slot.priority == 1
        }

        # 추가할 종목 (보유하는데 구독 안됨)
        to_add = portfolio_codes - current_priority1
        for code in to_add:
            stock = next(p for p in portfolio if p.stock_code == code)
            await self.subscribe(code, stock.stock_name, priority=1)

        # 제거할 종목 (구독중인데 보유 안함)
        to_remove = current_priority1 - portfolio_codes
        for code in to_remove:
            await self.unsubscribe(code)

        logger.info(f"✅ Portfolio synced: +{len(to_add)}, -{len(to_remove)}")

    async def listen(self):
        """
        WebSocket 데이터 수신 루프
        """
        logger.info("👂 WebSocket listener started")

        while self.is_running:
            try:
                async for message in self.ws_connection:
                    data = json.loads(message)
                    await self.handle_message(data)

            except websockets.exceptions.ConnectionClosed:
                logger.warning("⚠️  WebSocket connection closed, reconnecting...")
                await self.reconnect()

            except Exception as e:
                logger.error(f"❌ Listener error: {e}")
                await asyncio.sleep(1)

    async def handle_message(self, data: Dict):
        """
        WebSocket 메시지 처리

        Args:
            data: WebSocket 메시지
        """
        tr_id = data.get('header', {}).get('tr_id', '')
        stock_code = data.get('body', {}).get('output', {}).get('MKSC_SHRN_ISCD', '')

        # 체결 통보 (H0STCNI0)
        if tr_id == 'H0STCNI0':
            await kis_fetcher.on_execution_notice(data)
            return

        # 실시간 시세 (H0STCNT0)
        if tr_id == 'H0STCNT0' and stock_code in self.slots:
            # last_data_at 갱신
            self.slots[stock_code].last_data_at = datetime.now()

            # TODO: 시세 데이터 DB 저장 또는 Brain 전달
            logger.debug(f"📊 Price update: {stock_code}")

        # 실시간 호가 (H0STASP0)
        elif tr_id == 'H0STASP0' and stock_code in self.slots:
            self.slots[stock_code].last_data_at = datetime.now()
            logger.debug(f"📈 Orderbook update: {stock_code}")

    async def reconnect(self):
        """WebSocket 재연결"""
        logger.info("🔄 Reconnecting WebSocket...")

        await self.kis_client.connect_websocket()
        self.ws_connection = self.kis_client.ws_connection

        # 기존 구독 전체 재구독
        await self.resubscribe_all()

        logger.info("✅ WebSocket reconnected")

    async def resubscribe_all(self):
        """모든 슬롯 재구독"""
        slots_copy = list(self.slots.items())
        self.slots.clear()

        for code, slot in slots_copy:
            await self.subscribe(
                stock_code=code,
                stock_name=slot.stock_name,
                priority=slot.priority,
                tr_id=slot.tr_id
            )

        logger.info(f"✅ Resubscribed all: {len(self.slots)} slots")

    async def stop(self):
        """WebSocket Manager 정지"""
        self.is_running = False
        await self.kis_client.close()
        logger.info("🛑 WebSocket Manager stopped")


# Singleton Instance
ws_manager = KISWebSocketManager()
```

---

## 📋 사용 시나리오

### 1. 시스템 시작 시

```python
# main.py
async def startup():
    # WebSocket Manager 시작
    await ws_manager.start()

    # 보유종목 구독
    await ws_manager.sync_with_portfolio()

    # Daily Picks 로드 (DB에 저장된 것)
    daily_picks = await db.query(DailyPick).filter(...).all()
    for pick in daily_picks:
        await ws_manager.subscribe(pick.stock_code, pick.stock_name, priority=2)
```

### 2. 매수 체결 시

```python
# kis_fetcher.on_execution_notice()
async def on_execution_notice(data):
    # ... 기존 로직 ...

    if order_type == 'BUY':
        # 즉시 WebSocket 구독
        await ws_manager.subscribe(
            stock_code=stock_code,
            stock_name=stock_name,
            priority=1  # 보유종목
        )
```

### 3. 매도 체결 시

```python
# kis_fetcher.on_execution_notice()
async def on_execution_notice(data):
    # ... 기존 로직 ...

    if order_type == 'SELL':
        portfolio = await portfolio_service.get_stock_info(stock_code)
        if not portfolio or portfolio.quantity == 0:
            # 완전 매도 → 구독 해제
            await ws_manager.unsubscribe(stock_code)
```

### 4. Daily Picks 갱신 시 (07:20)

```python
# daily_analyzer.py
async def analyze_all_stocks():
    # DeepSeek R1 분석 실행
    picks = await deepseek_analyze(...)

    # DB 저장
    await db.bulk_insert(DailyPick, picks)

    # WebSocket 재구독 (Priority 2 전체 교체)
    # 1. 기존 Priority 2 해제
    for code, slot in ws_manager.slots.items():
        if slot.priority == 2:
            await ws_manager.unsubscribe(code)

    # 2. 새로운 Picks 구독
    for pick in picks[:20]:  # 상위 20개
        await ws_manager.subscribe(pick.stock_code, pick.stock_name, priority=2)
```

### 5. 급등주 발견 시

```python
# market_scanner.py
async def scan_market():
    # 등락률 상위 조회
    top_gainers = await scan_top_gainers()

    for stock in top_gainers[:5]:
        # 슬롯 여유 확인 후 구독
        if len(ws_manager.slots) < ws_manager.MAX_SLOTS:
            await ws_manager.subscribe(stock.code, stock.name, priority=3)
```

---

## 🧪 테스트 계획

### 단위 테스트

```python
async def test_subscribe():
    """구독 테스트"""
    result = await ws_manager.subscribe("005930", "삼성전자", priority=1)
    assert result is True
    assert "005930" in ws_manager.slots

async def test_slot_limit():
    """슬롯 제한 테스트"""
    # 40개 채우기
    for i in range(40):
        await ws_manager.subscribe(f"{i:06d}", f"Stock{i}", priority=3)

    # 41번째 Priority 3 → 실패
    result = await ws_manager.subscribe("999999", "Stock41", priority=3)
    assert result is False

    # 41번째 Priority 1 → 성공 (Priority 3 하나 제거)
    result = await ws_manager.subscribe("999999", "Stock41", priority=1)
    assert result is True

async def test_portfolio_sync():
    """포트폴리오 동기화 테스트"""
    await ws_manager.sync_with_portfolio()

    portfolio = await portfolio_service.get_portfolio()
    for stock in portfolio:
        assert stock.stock_code in ws_manager.slots
        assert ws_manager.slots[stock.stock_code].priority == 1
```

---

## 🚨 주의사항

### 1. H0STCNI0는 슬롯 소비 안함

체결 통보(H0STCNI0)는 계좌 단위 구독이므로 40개 제한에 포함되지 않음

### 2. 재연결 시 전체 재구독 필요

WebSocket 연결이 끊어지면 모든 구독이 해제되므로 재연결 시 전체 재구독

### 3. 우선순위 변경 불가

Priority는 구독 시점에 결정되며, 변경하려면 재구독 필요

---

## 📝 다음 단계

1. ✅ WebSocketSlot 클래스 구현
2. ✅ KISWebSocketManager 클래스 구현
3. ✅ 우선순위 관리 로직
4. ✅ 재연결 처리
5. ⏳ 통합 테스트

---

**작성**: Claude Code
**상태**: 설계 완료
**다음**: WebSocket Manager 구현
