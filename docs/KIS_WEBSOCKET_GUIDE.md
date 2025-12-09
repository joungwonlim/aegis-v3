# KIS WebSocket 승인키 발급 가이드

## WebSocket이 필요한 경우

WebSocket은 **실시간 시세 수신**이 필요할 때만 사용합니다:

- ✅ 실시간 체결가 모니터링
- ✅ 실시간 호가 데이터
- ✅ 체결 통보 수신

REST API만으로도 충분한 경우:
- 📊 일반 데이터 수집 (일봉, 수급)
- 💰 매수/매도 주문
- 📈 현재가 조회 (폴링)

## 승인키 발급 방법

### 1. 한국투자증권 Open API 포털 접속

```
https://apiportal.koreainvestment.com
```

### 2. 로그인 후 마이페이지

- 좌측 메뉴: **마이페이지**
- **API 관리** 클릭

### 3. WebSocket 승인키 발급

- **실시간 시세 서비스** 신청
- 승인키 자동 발급 (즉시)
- 승인키 복사

### 4. .env에 등록

```bash
# KIS WebSocket (NXT)
KIS_WS_APPROVAL_KEY=복사한_승인키_여기에_붙여넣기
```

## 승인키 없이 개발하기

WebSocket 승인키가 없어도 **AEGIS는 정상 작동**합니다:

### REST API 사용

```python
from fetchers.kis_client import kis_client

# 현재가 조회 (REST)
price = kis_client.get_current_price("005930")

# 매수 주문 (REST)
result = kis_client.buy_order("005930", quantity=10, price=52000)

# 매도 주문 (REST)
result = kis_client.sell_order("005930", quantity=10, price=53000)
```

### 폴링 방식으로 실시간 대체

```python
import asyncio

async def polling_price(stock_code: str, interval: int = 30):
    """30초마다 현재가 조회"""
    while True:
        price = kis_client.get_current_price(stock_code)
        print(f"{stock_code}: {price}")
        await asyncio.sleep(interval)
```

## WebSocket 사용 예시

승인키 발급 후:

```python
from fetchers.kis_client import kis_client

# WebSocket 연결
await kis_client.connect_websocket()

# 실시간 시세 구독
await kis_client.subscribe_realtime_price("005930")

# 데이터 수신
async def handle_realtime_data(data):
    print(f"실시간 체결: {data}")

await kis_client.listen_realtime_data(handle_realtime_data)
```

## 주의사항

1. **WebSocket 승인키는 REST API 키와 별개**
   - APP_KEY, APP_SECRET (REST용) ≠ WS_APPROVAL_KEY (WebSocket용)

2. **발급 즉시 사용 가능**
   - 별도 승인 대기 없음

3. **무료**
   - 추가 비용 없음

4. **연결 유지 필요**
   - WebSocket은 연결이 끊어지면 재연결 필요
   - Ping/Pong으로 연결 유지 (자동 처리됨)

## FAQ

### Q1. WebSocket 없이 자동매매 가능한가요?

**A.** 네, 가능합니다. REST API로 30초마다 체크하면 충분합니다.

### Q2. WebSocket과 REST API 차이는?

**A.**
- **WebSocket**: 서버가 데이터를 푸시 (실시간)
- **REST API**: 클라이언트가 주기적으로 요청 (폴링)

### Q3. 승인키 발급이 안 돼요

**A.** 한국투자증권 고객센터: 1544-5000

---

**작성일**: 2025-12-09
**버전**: 1.0
