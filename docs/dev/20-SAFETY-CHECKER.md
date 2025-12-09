# Safety Checker Specification

**작성일**: 2025-12-09 22:59:20
**작성자**: wonny
**프로젝트**: AEGIS v3.0

## 개요

매수 전 안전성을 검증하는 5단계 체크 시스템. 모든 조건을 통과해야만 매수 실행.

## 핵심 원칙

> **"보수적 진입, 공격적 탈출"**

- 매수는 신중하게 (5가지 안전장치)
- 매도는 빠르게 (손절 -3%, 익절 단계별)

## 5가지 Safety Check

### 1️⃣ 보유 종목 수 체크
- **규칙**: 최대 5개 종목까지만 보유
- **임계값**: `MAX_HOLDINGS = 5`
- **이유**: 분산 투자, 집중 관리

```python
holdings_count = db.query(Portfolio).filter(Portfolio.quantity > 0).count()
passed = holdings_count < self.MAX_HOLDINGS
```

### 2️⃣ 일일 거래 횟수 체크
- **규칙**: 하루 최대 4회까지만 거래
- **임계값**: `MAX_DAILY_TRADES = 4`
- **이유**: 과도한 거래 방지, 수수료 절감

```python
trades_count = db.query(TradingHistory).filter(
    TradingHistory.trade_date == today
).count()
passed = trades_count < self.MAX_DAILY_TRADES
```

### 3️⃣ 금요일 마감 시간 체크
- **규칙**: 금요일 14:30 이후 매수 금지
- **임계값**: `FRIDAY_CUTOFF = time(14, 30)`
- **이유**: 주말 리스크 회피 (갭 하락 방지)

```python
is_friday = now.weekday() == 4
current_time = now.time()
if is_friday and current_time >= self.FRIDAY_CUTOFF:
    passed = False
```

### 4️⃣ 계좌 손실률 체크
- **규칙**: 계좌 손실률 -2% 이하 시 매수 금지
- **임계값**: `MAX_ACCOUNT_LOSS_PCT = -2.0`
- **이유**: 손실 확대 방지, 심리적 안정

```python
profit_rate = ((total_asset - deposit) / deposit) * 100
passed = profit_rate > self.MAX_ACCOUNT_LOSS_PCT
```

### 5️⃣ 종목 비중 체크
- **규칙**: 단일 종목 비중 10% 초과 금지
- **임계값**: `MAX_POSITION_WEIGHT_PCT = 10.0`
- **이유**: 집중 리스크 방지

```python
buy_amount = quantity * price
position_weight = (buy_amount / total_asset) * 100
passed = position_weight <= self.MAX_POSITION_WEIGHT_PCT
```

## API 명세

### check_buy_safety()

```python
async def check_buy_safety(
    stock_code: str,
    stock_name: str,
    quantity: int,
    price: int
) -> Dict:
    """
    매수 안전성 종합 검증

    Returns:
        {
            "approved": True/False,
            "reason": "승인/거부 이유",
            "checks": {
                "holdings_count": {"passed": True, "detail": "보유 종목 수: 3/5"},
                "daily_trades": {"passed": True, "detail": "일일 거래 횟수: 2/4"},
                "friday_cutoff": {"passed": True, "detail": "금요일 마감 시간 체크 통과"},
                "account_loss": {"passed": True, "detail": "계좌 손실률: +1.2% (기준: -2.0%)"},
                "position_weight": {"passed": True, "detail": "종목 비중: 8.5% (기준: 10.0%)"}
            }
        }
    """
```

## Integration

### Pipeline 통합

**위치**: `pipeline/intraday_pipeline.py` → `_execute_orders()`

**실행 순서**:
```
Commander 승인
    ↓
Safety Check (5단계)
    ↓
주문 실행 (KIS API)
```

**코드**:
```python
# 🛡️ Safety Check (5가지 안전성 검증)
safety_result = await safety_checker.check_buy_safety(
    stock_code=stock_code,
    stock_name=stock_name,
    quantity=estimated_quantity,
    price=current_price
)

# Safety check 실패 시 매수 스킵
if not safety_result['approved']:
    logger.warning(f"  ❌ {stock_name}: Safety check REJECTED - {safety_result['reason']}")
    continue

logger.info(f"  ✅ {stock_name}: Safety check PASSED - {safety_result['reason']}")
```

## Error Handling

### 실패 시 기본 동작

API 조회 실패 등 에러 발생 시:
- **기본값**: `passed = True` (통과 처리)
- **이유**: 매수 기회 박탈 방지
- **예외**: 명확한 위반 조건 (보유 5개, 거래 4회 등)

```python
try:
    account_info = await kis_fetcher.get_account_balance()
    # ... check logic
except Exception as e:
    logger.error(f"Account loss check error: {e}")
    # 오류 시 안전하게 통과
    return {"passed": True, "detail": f"Error (통과 처리): {str(e)}"}
```

## Logging

### 로그 레벨

- ✅ **INFO**: 체크 통과
- ❌ **WARNING**: 체크 실패
- 🚨 **ERROR**: API 조회 실패 등 예외

### 로그 예시

```
🛡️ Safety Check Started: 삼성전자 (005930)
   Quantity: 10, Price: 78,000원
   ✅ 보유 종목 수: 3/5
   ✅ 일일 거래 횟수: 2/4
   ✅ 금요일 마감 시간 체크 통과
   ✅ 계좌 손실률: +1.2% (기준: -2.0%)
   ✅ 종목 비중: 8.5% (기준: 10.0%)
   ✅ APPROVED: All safety checks passed
```

## 관련 파일

- **구현**: `brain/safety_checker.py`
- **통합**: `pipeline/intraday_pipeline.py` (line 416-428)
- **모델**: `app/models/account.py` (Portfolio, TradingHistory)

## 테스트 시나리오

### Test Case 1: 모든 조건 통과
- 보유 종목 3개
- 일일 거래 2회
- 월요일 10:00
- 계좌 수익률 +1.2%
- 종목 비중 8.5%
- **예상 결과**: APPROVED ✅

### Test Case 2: 보유 종목 초과
- 보유 종목 5개
- **예상 결과**: REJECTED ❌ ("보유 종목 수 초과")

### Test Case 3: 금요일 마감 시간 이후
- 금요일 14:35
- **예상 결과**: REJECTED ❌ ("금요일 14:30 이후 매수 금지")

### Test Case 4: 계좌 손실 과다
- 계좌 수익률 -2.5%
- **예상 결과**: REJECTED ❌ ("계좌 손실률 -2% 이하")

### Test Case 5: 종목 비중 과다
- 종목 비중 12.0%
- **예상 결과**: REJECTED ❌ ("종목 비중 10% 초과")

## 향후 개선 사항

- [ ] 동적 임계값 조정 (시장 상황에 따라)
- [ ] 개별 종목 거래 빈도 체크
- [ ] 섹터 집중도 체크
- [ ] 변동성 기반 포지션 크기 조정
- [ ] 텔레그램 알림 통합

## 참고 문서

- Buy Decision Flow: `docs/dev/BUY_SELL_DECISION_FLOW.md`
- Portfolio Manager: `docs/BACKEND_MICRO_OPT.md`
- Trading Techniques: `docs/TRADING_TECHNIQUES.md`
