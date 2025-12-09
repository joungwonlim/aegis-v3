# Partial Sell (분할 매도) Specification

**작성일**: 2025-12-09 22:59:20
**작성자**: wonny
**프로젝트**: AEGIS v3.0

## 개요

수익이 발생한 종목을 단계적으로 매도하는 전략. "손실은 짧게, 수익은 길게" 원칙 구현.

## 핵심 원칙

> **"손실은 짧게(-3%), 수익은 길게(끝까지 추적)"**

- 손절은 빠르게 (-3%)
- 익절은 단계적으로 (1차 50%, 2차 100%)
- 트레일링으로 수익 극대화

## 매도 결정 플로우

### 전체 구조

```
┌─────────────────────────────────────────┐
│     보유 종목 (매 1분마다 체크)          │
└─────────────┬───────────────────────────┘
              │
              ↓
        ┌─────────┐
        │ 손익률  │
        │ 계산    │
        └────┬────┘
             │
        ┌────┴────┐
        │         │
    ≤-3%?     +3.5%?
        │         │
     [손절]   [1차 분할 50%]
        │         │
        │      +5%?
        │         │
        │   [트레일링 ON]
        │    고점 -2%
        │         │
        │     +5.5%?
        │         │
        │   [2차 익절 100%]
        │         │
        │      +8%?
        │         │
        │   [강화 트레일링]
        │    고점 -1.5%
        │         │
        └─────────┴─────────→ [계속 보유]
```

## 매도 조건 상세

### 1️⃣ 손절 (-3%) - 전량 매도

**조건**: 손익률 ≤ -3%
**수량**: 100% (전량)
**가격**: 시장가
**우선순위**: 1 (최우선)

```python
if profit_rate <= -3.0:
    return {
        'reason': f'칼손절 (Stop Loss) - {profit_rate:.2f}%',
        'reason_type': 'stop_loss',
        'sell_ratio': 1.0,  # 전량
        'price': 0,  # 시장가
        'confidence': 100
    }
```

**목적**: 손실 확대 방지

---

### 2️⃣ 1차 분할 매도 (+3.5%) - 50% 매도

**조건**: 손익률 ≥ +3.5% AND < +5.5%
**수량**: 50% (원금 회수 개념)
**가격**: 시장가
**플래그**: `partial_sold_1 = True` 설정

```python
if profit_rate >= 3.5 and profit_rate < 5.5:
    if not item.partial_sold_1:
        return {
            'reason': f'1차 분할 매도 (+{profit_rate:.2f}%)',
            'reason_type': 'partial_sell_1',
            'sell_ratio': 0.5,  # 50%
            'price': 0,
            'confidence': 85,
            'mark_partial_sold': True
        }
```

**목적**:
- 원금 회수로 심리적 안정
- 나머지 50%는 더 큰 수익 추구

**중복 방지**: `partial_sold_1` 플래그로 한 번만 실행

---

### 3️⃣ 트레일링 스탑 (+5% 이상) - 전량 매도

**조건**:
- 최고 수익률 ≥ +5% (한 번이라도 도달)
- 현재가가 고점 대비 -2% 이상 하락

**수량**: 100% (전량 또는 남은 수량)
**가격**: 시장가

#### 3-1. 일반 트레일링 (+5% ~ +8%)

```python
max_profit_rate = (highest_price - avg_price) / avg_price * 100

if max_profit_rate >= 5.0 and max_profit_rate < 8.0:
    drop_from_high = (highest_price - current_price) / highest_price * 100

    if drop_from_high >= 2.0:
        return {
            'reason': f'트레일링 스탑 (고점 대비 -{drop_from_high:.1f}%)',
            'reason_type': 'trailing_stop',
            'sell_ratio': 1.0,
            'price': 0,
            'confidence': 90
        }
```

**예시**:
- 매수: 10,000원
- 고점: 10,500원 (+5.0%)
- 현재: 10,290원 (고점 대비 -2.0%)
- **결과**: 트레일링 스탑 매도 ✅

#### 3-2. 강화 트레일링 (+8% 이상)

```python
if max_profit_rate >= 8.0:
    drop_from_high = (highest_price - current_price) / highest_price * 100

    if drop_from_high >= 1.5:
        return {
            'reason': f'강화 트레일링 스탑 (고점 대비 -{drop_from_high:.1f}%)',
            'reason_type': 'strong_trailing',
            'sell_ratio': 1.0,
            'price': 0,
            'confidence': 95
        }
```

**예시**:
- 매수: 10,000원
- 고점: 10,800원 (+8.0%)
- 현재: 10,638원 (고점 대비 -1.5%)
- **결과**: 강화 트레일링 매도 ✅

**목적**:
- 큰 수익 발생 시 빠르게 확정
- 고점 대비 -1.5%로 스탑 간격 축소

---

### 4️⃣ 2차 익절 (+5.5%) - 전량 매도

**조건**: 손익률 ≥ +5.5%
**수량**: 100% (전량 또는 남은 50%)
**가격**: 시장가

```python
if profit_rate >= 5.5:
    return {
        'reason': f'2차 익절 (전량) (+{profit_rate:.2f}%)',
        'reason_type': 'partial_sell_2',
        'sell_ratio': 1.0,
        'price': 0,
        'confidence': 85
    }
```

**목적**:
- 적정 수익 확정
- 트레일링 진입 전 안전판

---

## 고점 추적 (Highest Price Tracking)

매 분마다 현재가가 최고가를 갱신하면 업데이트:

```python
highest_price = item.max_price_reached or item.avg_price

if current_price > highest_price:
    item.max_price_reached = current_price
    logger.debug(f"📈 {stock_name}: 신고가 갱신 {current_price:,}원")
```

**DB 필드**: `Portfolio.max_price_reached`

---

## 매도 실행 로직

### _execute_sell() 메서드

```python
async def _execute_sell(self, item: Portfolio, decision: Dict) -> bool:
    """
    매도 주문 실행 (분할 매도 지원)

    Args:
        item: Portfolio 객체
        decision: 매도 결정 정보
            - reason: 매도 사유
            - sell_ratio: 매도 비율 (0.5 = 50%, 1.0 = 전량)
            - mark_partial_sold: 분할 매도 플래그 설정 여부
    """
    total_quantity = item.quantity
    sell_ratio = decision.get('sell_ratio', 1.0)
    mark_partial_sold = decision.get('mark_partial_sold', False)

    # 매도 수량 계산
    sell_quantity = int(total_quantity * sell_ratio)

    # 로그 출력
    if sell_ratio < 1.0:
        logger.info(f"  수량: {sell_quantity}주 / {total_quantity}주 ({sell_ratio*100:.0f}% 분할 매도)")
    else:
        logger.info(f"  수량: {sell_quantity}주 (전량)")

    # 분할 매도 플래그 설정
    if mark_partial_sold:
        item.partial_sold_1 = True
```

---

## 예시 시나리오

### 시나리오 1: 완벽한 수익 실현

```
Day 1 09:30 → 매수: 10,000원 (100주)
Day 1 14:00 → 현재가: 10,350원 (+3.5%)
              → 1차 분할 매도 50주 (수익: +17,500원)
              → 남은 수량: 50주

Day 2 10:00 → 현재가: 10,500원 (+5.0%, 고점 갱신)
              → 트레일링 스탑 ON

Day 2 11:30 → 현재가: 10,700원 (+7.0%, 고점 갱신)
              → 트레일링 스탑 갱신

Day 2 13:00 → 현재가: 10,486원 (고점 대비 -2.0%)
              → 트레일링 스탑 매도 50주 (수익: +24,300원)

총 수익: +41,800원 (+4.18%)
```

### 시나리오 2: 손절

```
Day 1 09:30 → 매수: 10,000원 (100주)
Day 1 14:00 → 현재가: 9,700원 (-3.0%)
              → 칼손절 100주 (손실: -30,000원)
```

### 시나리오 3: 강화 트레일링

```
Day 1 09:30 → 매수: 10,000원 (100주)
Day 1 10:00 → 현재가: 10,350원 (+3.5%)
              → 1차 분할 매도 50주

Day 2 11:00 → 현재가: 10,800원 (+8.0%, 고점 갱신)
              → 강화 트레일링 ON (고점 -1.5%)

Day 2 13:00 → 현재가: 10,638원 (고점 대비 -1.5%)
              → 강화 트레일링 매도 50주

총 수익: +49,400원 (+4.94%)
```

---

## 로그 예시

```
🔍 Portfolio Manager: Checking holdings...
  📋 보유 종목: 3개

  🔍 삼성전자: 현재 78,500원 (+3.8%)
  📈 삼성전자: 신고가 갱신 78,500원
  🟡 삼성전자: 1차 분할 매도 (+3.8%, 50% 매도)

📉 매도 신호 발생!
  종목: 삼성전자 (005930)
  수량: 5주 / 10주 (50% 분할 매도)
  사유: 1차 분할 매도 (+3.8%)
  ⚠️  매도 주문 실행 (TODO: KIS API 연동 필요)
  ✅ 분할 매도 플래그 설정 완료

✅ Portfolio Manager cycle complete
```

---

## 관련 파일

- **구현**: `brain/portfolio_manager.py`
- **모델**: `app/models/portfolio.py` (Portfolio.max_price_reached, Portfolio.partial_sold_1)
- **스케줄러**: `scheduler/dynamic_scheduler.py` (1분마다 실행)

---

## DB 스키마 변경 필요

### Portfolio 테이블

```sql
ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS max_price_reached INTEGER;
ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS partial_sold_1 BOOLEAN DEFAULT FALSE;
```

**필드 설명**:
- `max_price_reached`: 보유 중 달성한 최고가 (트레일링 스탑용)
- `partial_sold_1`: 1차 분할 매도 완료 여부 (중복 방지)

---

## 테스트 시나리오

### Test Case 1: 손절
- 매수: 10,000원
- 현재: 9,700원 (-3.0%)
- **예상**: 전량 매도 ✅

### Test Case 2: 1차 분할 매도
- 매수: 10,000원, 100주
- 현재: 10,350원 (+3.5%)
- **예상**: 50주 매도 ✅, partial_sold_1 = True

### Test Case 3: 1차 분할 후 2차 익절
- 매수: 10,000원, 100주
- 1차: 10,350원에 50주 매도
- 현재: 10,550원 (+5.5%)
- **예상**: 남은 50주 전량 매도 ✅

### Test Case 4: 트레일링 스탑
- 매수: 10,000원
- 고점: 10,500원 (+5.0%)
- 현재: 10,290원 (고점 -2.0%)
- **예상**: 전량 매도 ✅

### Test Case 5: 강화 트레일링
- 매수: 10,000원
- 고점: 10,800원 (+8.0%)
- 현재: 10,638원 (고점 -1.5%)
- **예상**: 전량 매도 ✅

---

## 향후 개선 사항

- [ ] 변동성 기반 스탑 간격 동적 조정
- [ ] 개별 종목 특성 반영 (성장주 vs 가치주)
- [ ] 시장 상황에 따른 분할 매도 비율 조정
- [ ] AI 기반 최적 매도 타이밍 추천
- [ ] 백테스트 결과 반영

---

## 참고 문서

- Sell Decision Flow: `docs/dev/BUY_SELL_DECISION_FLOW.md`
- Portfolio Manager: `docs/BACKEND_MICRO_OPT.md`
- Trading Techniques: `docs/TRADING_TECHNIQUES.md`
- Trailing Stop Logic: `docs/MICRO_OPTIMIZATION.md`
