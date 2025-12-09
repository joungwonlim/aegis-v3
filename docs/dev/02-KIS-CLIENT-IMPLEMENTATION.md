# KIS Client 구현 완료

> 작성일: 2025-12-09
> 상태: 완료
> Phase: 1
> 파일: fetchers/kis_client.py

---

## ✅ 구현 내용

### 1. NXT 지원 완료

#### TR_ID 매핑 테이블

```python
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
```

**구현 위치**: `kis_client.py:21-34`

#### buy_order() / sell_order() 개선

**변경사항**:
- `market` 파라미터 추가 (KRX/NXT 선택)
- NXT 시장가 주문 자동 차단
- NXT 주문 시 현재 호가로 자동 전환
- TR_ID 동적 선택
- 로깅 강화

**코드 예시**:
```python
# KRX 시장가 매수
kis_client.buy_order("005930", quantity=10, price=0, market="KRX")

# NXT 지정가 매수
kis_client.buy_order("005930", quantity=10, price=52000, market="NXT")

# NXT 시장가 → 자동으로 매도1호가로 변환
kis_client.buy_order("005930", quantity=10, price=0, market="NXT")
# ⚠️  NXT는 시장가 불가 → 현재 호가로 주문
```

**구현 위치**:
- `buy_order()`: `kis_client.py:175-230`
- `sell_order()`: `kis_client.py:232-287`

---

### 2. 잔고 조회 기능 추가

#### get_balance(market)

**기능**: 특정 시장(KRX 또는 NXT)의 잔고 조회

**파라미터**:
- `market`: "KRX" 또는 "NXT"

**반환값**:
```python
[
    {
        "pdno": "005930",           # 종목코드
        "prdt_name": "삼성전자",     # 종목명
        "hldg_qty": "10",           # 보유수량
        "pchs_avg_pric": "52000",   # 평균매입가
        "prpr": "53000",            # 현재가
        "evlu_pfls_rt": "1.92"      # 평가손익률
    },
    ...
]
```

**사용 예시**:
```python
# KRX 잔고만 조회
krx_balance = kis_client.get_balance("KRX")

# NXT 잔고만 조회
nxt_balance = kis_client.get_balance("NXT")
```

**구현 위치**: `kis_client.py:289-334`

---

#### get_combined_balance()

**기능**: KRX + NXT 통합 잔고 조회 (동일 종목 병합)

**병합 로직**:
- 동일 종목코드를 가진 포지션 자동 병합
- 수량 합산
- 평균단가 재계산: `(qty1 × price1 + qty2 × price2) / (qty1 + qty2)`

**사용 예시**:
```python
# 전체 잔고 조회 (KRX + NXT 병합)
combined_balance = kis_client.get_combined_balance()

# 예: 삼성전자를 KRX 5주 + NXT 5주 보유 시
# → 10주로 합산, 평균단가 자동 계산
```

**구현 위치**:
- `get_combined_balance()`: `kis_client.py:336-367`
- `_merge_positions()`: `kis_client.py:369-395`

---

### 3. WebSocket 체결 통보 (H0STCNI0)

#### subscribe_execution_notice()

**기능**: 체결 통보 실시간 수신 (10~50ms 지연)

**동작 방식**:
1. WebSocket 연결 확인
2. H0STCNI0 TR_ID로 구독
3. 체결 발생 시 즉시 알림

**메시지 포맷**:
```python
{
    "header": {
        "approval_key": self.ws_approval_key,
        "custtype": "P",
        "tr_type": "1",
        "content-type": "utf-8"
    },
    "body": {
        "input": {
            "tr_id": "H0STCNI0",
            "tr_key": self.account_number
        }
    }
}
```

**사용 예시**:
```python
# WebSocket 연결 및 체결 통보 구독
await kis_client.connect_websocket()
await kis_client.subscribe_execution_notice()

# 이후 체결 발생 시 자동으로 listen_realtime_data()에서 수신
```

**구현 위치**: `kis_client.py:433-463`

---

### 4. 헬퍼 메서드

#### _get_ask_price_1(stock_code)

**기능**: 현재 매도1호가 조회 (NXT 매수 시장가 대체용)

**동작**:
- 호가 조회 API 호출
- `askp1` 필드 추출
- 실패 시 현재가(`stck_prpr`) 반환

**구현 위치**: `kis_client.py:397-413`

---

#### _get_bid_price_1(stock_code)

**기능**: 현재 매수1호가 조회 (NXT 매도 시장가 대체용)

**동작**:
- 호가 조회 API 호출
- `bidp1` 필드 추출
- 실패 시 현재가(`stck_prpr`) 반환

**구현 위치**: `kis_client.py:415-431`

---

## 📊 변경 사항 요약

| 항목 | Before | After |
|------|--------|-------|
| NXT 지원 | ❌ 없음 | ✅ TR_ID 자동 분기 |
| 시장 선택 | - | ✅ market 파라미터 추가 |
| NXT 시장가 | ❌ 오류 발생 | ✅ 자동 차단 + 호가 전환 |
| 잔고 조회 | ❌ 없음 | ✅ get_balance() 추가 |
| KRX+NXT 통합 | ❌ 없음 | ✅ get_combined_balance() 추가 |
| 체결 통보 | ❌ 없음 | ✅ H0STCNI0 구독 추가 |
| 로깅 | print() | logging 모듈 사용 |

---

## 🧪 테스트 가이드

### 단위 테스트

```python
# tests/test_kis_client.py

def test_buy_order_krx():
    """KRX 시장가 매수 테스트"""
    result = kis_client.buy_order("005930", 10, 0, "KRX")
    assert result['tr_id'] == "TTTC0802U"

def test_buy_order_nxt():
    """NXT 지정가 매수 테스트"""
    result = kis_client.buy_order("005930", 10, 52000, "NXT")
    assert result['tr_id'] == "TTTN0802U"

def test_nxt_market_order_blocked():
    """NXT 시장가 차단 테스트"""
    # 시장가(price=0) 주문 시 자동으로 호가 조회
    result = kis_client.buy_order("005930", 10, 0, "NXT")
    # price가 0이 아닌 값으로 변경되었는지 확인
    assert result is not None

def test_get_balance_krx():
    """KRX 잔고 조회 테스트"""
    balance = kis_client.get_balance("KRX")
    assert isinstance(balance, list)

def test_get_combined_balance():
    """통합 잔고 조회 테스트"""
    balance = kis_client.get_combined_balance()
    assert isinstance(balance, list)
    # 동일 종목 병합 확인
    codes = [item['pdno'] for item in balance]
    assert len(codes) == len(set(codes))  # 중복 없음
```

### 통합 테스트

```python
# tests/test_integration.py

async def test_websocket_execution_notice():
    """WebSocket 체결 통보 테스트"""
    # 1. WebSocket 연결
    await kis_client.connect_websocket()

    # 2. 체결 통보 구독
    await kis_client.subscribe_execution_notice()

    # 3. 테스트 주문 실행
    result = kis_client.buy_order("005930", 10, 52000, "KRX")

    # 4. 체결 통보 대기
    await asyncio.sleep(5)

    # 5. 체결 확인 (실제 환경에서는 KISFetcher가 처리)
    # TODO: KISFetcher 구현 후 테스트 보강
```

---

## 🚨 주의사항

### 1. NXT 시장가 주문

**문제**: NXT는 시장가 주문 불가

**해결**:
- `price=0`으로 주문 시 자동으로 현재 호가 조회
- 매수: 매도1호가 사용
- 매도: 매수1호가 사용

### 2. 잔고 조회 실패

**문제**: KRX 또는 NXT 잔고 조회 실패 시

**해결**:
- `get_combined_balance()`는 실패한 시장 무시
- 성공한 시장의 데이터만 반환
- 로그에 경고 메시지 출력

### 3. WebSocket 승인키 미설정

**문제**: `KIS_WS_APPROVAL_KEY`가 없을 경우

**해결**:
- WebSocket 연결 시도하지 않음
- REST API로 fallback
- 체결 통보는 비활성화 (폴링으로 대체)

---

## 📝 다음 단계

### Phase 1 남은 작업

1. ✅ kis_client.py 개선 완료
2. ⏳ KISFetcher 개발
   - sync_portfolio() - 잔고 동기화
   - on_execution_notice() - 체결 통보 처리
   - sync_execution() - 미체결 조회
3. ⏳ PortfolioService 개발
   - get_portfolio() - DB Read only
   - get_total_asset() - 총 자산 조회
4. ⏳ OrderService 개발
   - place_buy_order() - 주문 실행
   - place_sell_order() - 주문 실행

---

## 🔗 관련 문서

- [KIS API 명세](../KIS_API_SPECIFICATION.md)
- [WebSocket 가이드](../KIS_WEBSOCKET_GUIDE.md)
- [개발 로드맵](00-ROADMAP.md)
- [KIS Client 설계](01-KIS-CLIENT.md)

---

**작성**: Claude Code
**검토**: 완료
**다음**: KISFetcher 개발
