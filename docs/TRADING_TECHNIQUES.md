# Advanced Trading Techniques (고급 매매 기법)

> **AEGIS v3.0에 적용 가능한 체계적 매매 기법 모음**

---

## 📋 목차

1. [적립식 매매 (DCA/VA)](#1-적립식-매매)
2. [변동성 활용 (Grid/Scale)](#2-변동성-활용)
3. [자금 관리 (Kelly/Martingale)](#3-자금-관리)
4. [매도 최적화 (Trailing/Rebalancing)](#4-매도-최적화)
5. [AEGIS 적용 현황](#5-aegis-적용-현황)

---

## 1. 적립식 매매

### 1.1 DCA (Dollar Cost Averaging)

**개념:** 정해진 날짜에 정해진 금액 매수

```
┌─────────────────────────────────────────────────────────────┐
│                    DCA 전략                                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  매월 1일, 10만원씩 삼성전자 매수                            │
│                                                             │
│  1월: 100,000원 @ 70,000원 = 1.42주                         │
│  2월: 100,000원 @ 68,000원 = 1.47주                         │
│  3월: 100,000원 @ 72,000원 = 1.38주                         │
│  ...                                                        │
│  평단: 자동으로 최적화                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**장점:**
- ✅ 단순하고 명확
- ✅ 감정 배제 (기계적 매수)
- ✅ 장기 우상향 시장에 최적

**단점:**
- ❌ 하락장에서 비효율
- ❌ 타이밍 무시

**AEGIS 적용:**
```python
# 적용 가능성: ⭐⭐⭐⭐⭐
# 구현 난이도: 쉬움

def dca_strategy(
    stock_code: str,
    monthly_amount: int = 1000000,
    buy_day: int = 1  # 매월 1일
):
    """
    DCA 전략 실행

    매월 지정일에 정액 매수
    """
    from datetime import date

    if date.today().day == buy_day:
        # 정액 매수
        execute_buy(
            stock_code=stock_code,
            amount=monthly_amount,
            reason='DCA 정기 매수'
        )
```

**추천 종목:** 우량주 (삼성전자, 네이버, 카카오)

---

### 1.2 VA (Value Averaging)

**개념:** 평가액 목표치를 정하고 차액 매매

```
┌─────────────────────────────────────────────────────────────┐
│                    VA 전략                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  목표: 매월 평가액 +100만원                                  │
│                                                             │
│  1월 말: 평가액 100만원 (목표 달성)                          │
│  2월 말: 평가액 180만원 (목표 200만원)                       │
│    → 부족: 20만원 추가 매수                                  │
│                                                             │
│  3월 말: 평가액 330만원 (목표 300만원)                       │
│    → 초과: 30만원 매도                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**장점:**
- ✅ DCA보다 수익률 높음
- ✅ 자동 저가 매수/고가 매도
- ✅ 리밸런싱 효과

**단점:**
- ❌ 하락장에서 자금 소진 빠름
- ❌ 계산 복잡

**AEGIS 적용:**
```python
# 적용 가능성: ⭐⭐⭐⭐☆
# 구현 난이도: 보통

def va_strategy(
    stock_code: str,
    target_growth: int = 1000000,  # 월 100만원 성장
    current_month: int = 1
):
    """
    VA 전략 실행

    평가액 목표치 기준 매매
    """
    current_value = get_current_valuation(stock_code)
    target_value = target_growth * current_month

    diff = target_value - current_value

    if diff > 50000:
        # 부족 → 매수
        execute_buy(stock_code, amount=diff, reason='VA 목표 달성용 매수')
    elif diff < -50000:
        # 초과 → 매도
        execute_sell(stock_code, amount=abs(diff), reason='VA 수익 실현')
```

**추천 종목:** 변동성 있는 대형주

---

## 2. 변동성 활용

### 2.1 Grid Trading (그리드 트레이딩)

**개념:** 일정 간격으로 매수/매도 주문 배치

```
┌─────────────────────────────────────────────────────────────┐
│              그리드 트레이딩 (Grid Trading)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  현재가: 10,000원                                           │
│                                                             │
│  매도 주문:                                                 │
│    11,000원 → 10주 매도                                     │
│    10,500원 → 10주 매도                                     │
│  ────────────────── 현재가 (10,000원)                       │
│  매수 주문:                                                 │
│     9,500원 → 10주 매수                                     │
│     9,000원 → 10주 매수                                     │
│                                                             │
│  주가 등락할 때마다 자동 체결 → 시세 차익                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**장점:**
- ✅ 횡보장에서 수익
- ✅ 완전 자동화 가능
- ✅ 감정 배제

**단점:**
- ❌ 추세장에서 비효율
- ❌ 수수료 많이 발생

**AEGIS 적용:**
```python
# 적용 가능성: ⭐⭐⭐⭐⭐
# 구현 난이도: 보통

def grid_trading_setup(
    stock_code: str,
    center_price: float,
    grid_interval: float = 0.02,  # 2% 간격
    grid_levels: int = 5  # 위아래 5단계
):
    """
    그리드 트레이딩 주문 배치

    현재가 기준 ±2%, ±4%, ±6%, ±8%, ±10% 주문
    """
    orders = []

    for i in range(1, grid_levels + 1):
        # 매수 주문 (하단)
        buy_price = center_price * (1 - grid_interval * i)
        orders.append({
            'type': 'BUY',
            'price': buy_price,
            'quantity': 10,
            'reason': f'Grid 매수 레벨 {i}'
        })

        # 매도 주문 (상단)
        sell_price = center_price * (1 + grid_interval * i)
        orders.append({
            'type': 'SELL',
            'price': sell_price,
            'quantity': 10,
            'reason': f'Grid 매도 레벨 {i}'
        })

    return orders
```

**추천 종목:** 박스권 종목 (변동성 20% 이하)

---

### 2.2 Scale Trading (스케일 트레이딩)

**개념:** 하락할수록 매수량 증가

```
┌─────────────────────────────────────────────────────────────┐
│              스케일 트레이딩 (물타기 개선)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1차: 10,000원 → 10주 (100,000원)                           │
│  2차:  9,500원 → 20주 (190,000원) - 2배                     │
│  3차:  9,000원 → 40주 (360,000원) - 2배                     │
│                                                             │
│  총 70주, 평단 9,285원                                       │
│                                                             │
│  반등 시: 9,500원만 회복해도 +1.5% 수익!                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**장점:**
- ✅ 평단 급격히 낮춤
- ✅ 반등 시 빠른 탈출

**단점:**
- ❌ 계속 하락 시 파산 위험
- ❌ 자금 관리 필수

**AEGIS 적용:**
```python
# 적용 가능성: ⭐⭐☆☆☆ (위험)
# 구현 난이도: 쉬움

def scale_trading(
    stock_code: str,
    stages: List[float] = [-0.05, -0.10, -0.15],
    multiplier: float = 2.0
):
    """
    스케일 트레이딩

    ⚠️ 주의: 하락장에서 매우 위험!
    """
    base_qty = 10

    for i, drop_pct in enumerate(stages):
        if current_drop >= drop_pct:
            qty = base_qty * (multiplier ** i)
            execute_buy(
                stock_code=stock_code,
                quantity=qty,
                reason=f'Scale {drop_pct*100:.0f}% 매수'
            )
```

**⚠️ 비추천:** AEGIS 안전 철학과 맞지 않음

---

## 3. 자금 관리

### 3.1 Kelly Criterion (켈리 공식)

**개념:** 수학적 최적 투자 비중 계산

```
Kelly % = (승률 × 손익비 - 1) / (손익비 - 1)

예시:
승률 = 60%
손익비 = 2:1 (평균 수익 10%, 평균 손실 5%)

Kelly % = (0.6 × 2 - 1) / (2 - 1)
        = 0.2 / 1
        = 20%

→ 총 자산의 20%를 투자하는 것이 최적
```

**장점:**
- ✅ 수학적으로 검증됨
- ✅ 장기 수익 극대화
- ✅ 파산 위험 최소화

**단점:**
- ❌ 승률/손익비 정확히 알아야 함
- ❌ 실전 변동성 高

**AEGIS 적용:**
```python
# 적용 가능성: ⭐⭐⭐⭐⭐
# 구현 난이도: 쉬움

def kelly_position_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    total_asset: float
) -> float:
    """
    Kelly Criterion으로 최적 투자 비중 계산

    Args:
        win_rate: 승률 (0.0 ~ 1.0)
        avg_win: 평균 수익률 (예: 0.05 = 5%)
        avg_loss: 평균 손실률 (예: 0.02 = 2%)
        total_asset: 총 자산

    Returns:
        최적 투자 금액
    """
    if avg_loss == 0:
        return 0

    win_loss_ratio = avg_win / avg_loss
    kelly_pct = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio

    # 보수적으로 Kelly의 50%만 사용 (Half Kelly)
    safe_kelly = kelly_pct * 0.5

    # 최대 15% 제한 (AEGIS 안전 규칙)
    safe_kelly = min(safe_kelly, 0.15)

    return total_asset * safe_kelly


# 사용 예시
total_asset = 30_000_000
win_rate = 0.55  # 55% 승률
avg_win = 0.05   # 평균 5% 수익
avg_loss = 0.02  # 평균 2% 손실

optimal_amount = kelly_position_size(win_rate, avg_win, avg_loss, total_asset)
print(f"최적 투자금: {optimal_amount:,.0f}원")
# 출력: 최적 투자금: 4,500,000원 (15%)
```

**✅ AEGIS 적용 추천:** 종목별 포지션 사이즈 결정에 활용

---

### 3.2 Martingale (마틴게일) ⚠️

**개념:** 손실 시 베팅 2배 증가

```
1차: 100,000원 매수 → 손실
2차: 200,000원 매수 → 손실
3차: 400,000원 매수 → 손실
4차: 800,000원 매수 → 성공
→ 본전 회복
```

**AEGIS 적용:**
```
❌ 적용 불가
이유: 파산 위험 높음, AEGIS 안전 철학과 불일치
```

---

### 3.3 Anti-Martingale (역마틴게일) = 피라미딩

**개념:** 수익 시 베팅 증가

```
1차: 100,000원 매수 → +2% 수익 ✅
2차: 200,000원 추가 → +3% 수익 ✅
3차: 400,000원 추가 → +5% 수익 ✅
→ 수익 극대화
```

**AEGIS 적용:**
```
✅ 이미 적용 중
파일: docs/dev3/PYRAMIDING_STRATEGY.md
```

---

## 2. 변동성 활용

### 2.1 Grid Trading (그리드 트레이딩)

**전략 설계:**

```
┌─────────────────────────────────────────────────────────────┐
│          Grid Trading 주문 배치 (박스권 전용)                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  현재가: 10,000원                                           │
│  간격: 2% (200원)                                           │
│  레벨: 5단계                                                │
│                                                             │
│  [매도 주문]                                                │
│    11,000원 → 10주 매도                                     │
│    10,800원 → 10주 매도                                     │
│    10,600원 → 10주 매도                                     │
│    10,400원 → 10주 매도                                     │
│    10,200원 → 10주 매도                                     │
│  ──────────────────────────                                 │
│    10,000원 ← 현재가                                        │
│  ──────────────────────────                                 │
│  [매수 주문]                                                │
│     9,800원 → 10주 매수                                     │
│     9,600원 → 10주 매수                                     │
│     9,400원 → 10주 매수                                     │
│     9,200원 → 10주 매수                                     │
│     9,000원 → 10주 매수                                     │
│                                                             │
│  횡보할수록 수익 누적!                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**AEGIS 적용:**
```python
# 적용 가능성: ⭐⭐⭐⭐⭐
# 구현 난이도: 보통

class GridTradingExecutor:
    """
    그리드 트레이딩 실행기

    박스권 종목 전용
    """

    def __init__(
        self,
        stock_code: str,
        center_price: float,
        grid_interval: float = 0.02,
        levels: int = 5
    ):
        self.stock_code = stock_code
        self.center = center_price
        self.interval = grid_interval
        self.levels = levels

    def create_grid_orders(self):
        """그리드 주문 생성"""
        orders = []

        for i in range(1, self.levels + 1):
            # 하단 매수
            buy_price = self.center * (1 - self.interval * i)
            orders.append({
                'type': 'BUY',
                'price': int(buy_price),
                'quantity': 10,
                'condition': 'LIMIT',
                'reason': f'Grid-{i} 매수'
            })

            # 상단 매도
            sell_price = self.center * (1 + self.interval * i)
            orders.append({
                'type': 'SELL',
                'price': int(sell_price),
                'quantity': 10,
                'condition': 'LIMIT',
                'reason': f'Grid-{i} 매도'
            })

        return orders

    def monitor_and_rebalance(self):
        """
        체결 확인 및 재조정

        매수 체결되면 → 해당 레벨에 매도 주문
        매도 체결되면 → 해당 레벨에 매수 주문
        """
        executed_orders = get_executed_orders(self.stock_code)

        for order in executed_orders:
            if order['type'] == 'BUY':
                # 매수 체결 → 상단에 매도 주문
                sell_price = order['price'] * (1 + self.interval)
                place_sell_order(self.stock_code, sell_price, order['quantity'])

            elif order['type'] == 'SELL':
                # 매도 체결 → 하단에 매수 주문
                buy_price = order['price'] * (1 - self.interval)
                place_buy_order(self.stock_code, buy_price, order['quantity'])
```

**✅ AEGIS 적용 추천:**
- 대상 종목: 삼성전자, SK하이닉스 (박스권 횡보)
- 시기: 변동성 지수 VIX < 15

---

### 2.2 Scale Trading (스케일 트레이딩)

**개념:** 하락폭에 따라 매수량 증가

```
-5%:  10주 매수
-10%: 20주 매수 (2배)
-15%: 40주 매수 (2배)
-20%: 80주 매수 (2배)
```

**AEGIS 적용:**
```
❌ 비추천
이유: 파산 위험, 안전 철학 위배
대안: 피라미딩 (수익 시에만 추가 매수)
```

---

## 4. 매도 최적화

### 4.1 Trailing Stop (트레일링 스탑)

**개념:** 고점 대비 일정% 하락 시 자동 매도

```
┌─────────────────────────────────────────────────────────────┐
│              트레일링 스탑 (Trailing Stop)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  매수가: 10,000원                                           │
│  트레일링: -1.5% (고점 대비)                                │
│                                                             │
│  현재가 10,500원 (+5%) → 익절가: 10,342원 (10,500×0.985)    │
│  현재가 11,000원 (+10%) → 익절가: 10,835원 (11,000×0.985)   │
│  현재가 10,900원 (-0.9%) → 대기                             │
│  현재가 10,800원 (-1.8%) → 매도! (10,835원 이하)            │
│                                                             │
│  최종 매도가: 10,800원                                       │
│  수익: +8%                                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**AEGIS 적용:**
```python
# 적용 가능성: ⭐⭐⭐⭐⭐
# 구현 난이도: 쉬움 (이미 구현됨)

def trailing_stop_monitor(
    stock_code: str,
    current_price: float,
    max_price: float,
    trailing_pct: float = 0.015  # 1.5%
) -> bool:
    """
    트레일링 스탑 체크

    Returns:
        True: 매도 실행
        False: 대기
    """
    # 고점 대비 하락률
    drop_from_peak = (max_price - current_price) / max_price

    if drop_from_peak >= trailing_pct:
        # 트레일링 스탑 발동
        execute_sell(
            stock_code=stock_code,
            quantity='ALL',
            reason=f'트레일링 스탑 발동 (고점 대비 -{drop_from_peak*100:.1f}%)'
        )
        return True

    # 새 고점 갱신
    if current_price > max_price:
        update_max_price(stock_code, current_price)

    return False
```

**✅ AEGIS 적용 중:**
- 파일: `brain/auto_trader.py`
- 설정: +3% 수익 시 활성화, -1.5% 하락 시 매도

---

### 4.2 Rebalancing (리밸런싱)

**개념:** 포트폴리오 비중 조정

```
┌─────────────────────────────────────────────────────────────┐
│                  리밸런싱 전략                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [초기 설정]                                                │
│    반도체: 50% (1,500만원)                                  │
│    자동차: 30% (900만원)                                    │
│    2차전지: 20% (600만원)                                   │
│    총 자산: 3,000만원                                       │
│                                                             │
│  [1개월 후]                                                 │
│    반도체: 60% (2,000만원) ← 상승                           │
│    자동차: 25% (833만원)                                    │
│    2차전지: 15% (500만원)                                   │
│    총 자산: 3,333만원                                       │
│                                                             │
│  [리밸런싱 실행]                                            │
│    반도체: 500만원 매도 (60% → 50%)                         │
│    자동차: 166만원 매수 (25% → 30%)                         │
│    2차전지: 166만원 매수 (15% → 20%)                        │
│                                                             │
│  → 고점 매도 + 저점 매수 효과!                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**AEGIS 적용:**
```python
# 적용 가능성: ⭐⭐⭐⭐☆
# 구현 난이도: 보통

def sector_rebalancing(
    target_ratios: Dict[str, float],
    rebalance_threshold: float = 0.05  # 5% 벗어나면
):
    """
    섹터 리밸런싱

    Args:
        target_ratios: {'반도체': 0.5, '자동차': 0.3, '2차전지': 0.2}
        rebalance_threshold: 리밸런싱 기준 (5%)
    """
    holdings = get_holdings()
    total_value = sum(h['current_value'] for h in holdings)

    # 섹터별 현재 비중
    sector_values = {}
    for h in holdings:
        sector = h['sector']
        sector_values[sector] = sector_values.get(sector, 0) + h['current_value']

    # 리밸런싱 필요 여부 확인
    for sector, target_ratio in target_ratios.items():
        current_ratio = sector_values.get(sector, 0) / total_value
        diff = abs(current_ratio - target_ratio)

        if diff > rebalance_threshold:
            if current_ratio > target_ratio:
                # 비중 초과 → 매도
                sell_amount = (current_ratio - target_ratio) * total_value
                print(f"🔴 {sector} 매도: {sell_amount:,.0f}원")
            else:
                # 비중 부족 → 매수
                buy_amount = (target_ratio - current_ratio) * total_value
                print(f"🟢 {sector} 매수: {buy_amount:,.0f}원")
```

**✅ AEGIS 적용 추천:** 월간 리밸런싱 (매월 첫째 주)

---

## 5. AEGIS 적용 현황

### ✅ 이미 적용 중

| 기법 | 적용 | 파일 | 설명 |
|-----|------|------|------|
| **피라미딩** | ✅ | PYRAMIDING_STRATEGY.md | 3단계 (30-50-20) |
| **분할매도** | ✅ | BRAIN_SIMPLE.md | 3단계 (+3%, +5%, +8%) |
| **트레일링 스탑** | ✅ | auto_trader.py | +3% 활성화, -1.5% 매도 |
| **손절** | ✅ | auto_trader.py | -2.0% 자동 실행 |

### ⭐ 추천 추가 (구현 필요)

| 기법 | 우선순위 | 난이도 | 효과 |
|-----|---------|--------|------|
| **Kelly Criterion** | 🔥 높음 | 쉬움 | 최적 포지션 계산 |
| **Grid Trading** | 🔥 높음 | 보통 | 횡보장 수익 |
| **Rebalancing** | 중간 | 보통 | 섹터 비중 관리 |
| **DCA** | 낮음 | 쉬움 | 장기 투자 |
| **VA** | 낮음 | 어려움 | DCA 개선 |

### ❌ 적용 불가 (위험)

| 기법 | 이유 |
|-----|------|
| **Martingale** | 파산 위험 |
| **Scale Trading** | 무한 물타기 위험 |

---

## 🚀 내일(12/09) 우선 적용

### 1. Kelly Criterion (즉시 적용 가능)

```python
# brain/position_sizer.py (신규)
from brain.kelly_calculator import calculate_kelly_position

# TradeFeedback에서 승률/손익비 계산
win_rate = 0.55  # 최근 30일 승률
avg_win = 0.05
avg_loss = 0.02

optimal_size = calculate_kelly_position(
    win_rate, avg_win, avg_loss, total_asset=30_000_000
)
# → 4,500,000원 (15%)
```

### 2. Grid Trading (테스트 필요)

```python
# 대상: 삼성전자 (박스권 확인 후)
grid = GridTradingExecutor(
    stock_code='005930',
    center_price=109000,
    grid_interval=0.02,
    levels=5
)
grid.create_grid_orders()
```

---

## 📊 종합 매매 시스템

### 매수 시스템
```
1. Kelly Criterion → 최적 투자 금액 계산
2. 피라미딩 → 3단계 분할 매수
3. DCA → 우량주 정기 매수 (옵션)
```

### 매도 시스템
```
1. 손절 → -2.0% 자동 실행
2. 분할매도 → +3%, +5%, +8% 단계별
3. 트레일링 스탑 → +3% 수익 후 활성화
4. 리밸런싱 → 월간 섹터 비중 조정
```

### 횡보장 대응
```
1. Grid Trading → 박스권 종목 자동 매매
```

---

## 📁 관련 파일

### 문서
- `docs/dev3/PYRAMIDING_STRATEGY.md`: 피라미딩 상세
- `docs/dev3/BRAIN_SIMPLE.md`: Section 5 매매 전략
- `docs/dev3/TRADING_TECHNIQUES.md`: 이 문서

### 코드
- `brain/pyramid_executor.py`: 피라미딩 실행 (구현 필요)
- `brain/scale_out_executor.py`: 분할매도 실행 (구현 필요)
- `brain/kelly_calculator.py`: Kelly 계산 (구현 필요)
- `brain/grid_trader.py`: 그리드 트레이딩 (구현 필요)

### DB
- `database/models.py`: Portfolio (피라미딩 필드 있음)

---

## 🎯 다음 단계

1. **즉시 적용**: Kelly Criterion (포지션 사이즈)
2. **1주 내**: Grid Trading (박스권 종목)
3. **1개월 내**: Rebalancing (섹터 리밸런싱)

---

## 6. 미세 최적화 (0.001% 디테일)

### 주문 순간의 전술

상세 내용은 **[MICRO_OPTIMIZATION.md](./MICRO_OPTIMIZATION.md)** 참조

#### 핵심 기법 (4가지)

| 기법 | 효과 | 난이도 | 적용 |
|-----|------|--------|------|
| **호가 스프레드** | 0.12% / 건 | 쉬움 | 내일 |
| **점심시간 필터** | 0.10% / 건 | 쉬움 | 내일 |
| **체결강도** | 0.30% / 건 | 보통 | 1주 |
| **종가 베팅** | 0.20% / 건 | 쉬움 | 1주 |

**총 효과: 0.72% / 건**

#### 연간 효과
```
200회 거래 × 0.72% × 500만원
= 약 720만원 추가 수익!
```

---

## 7. 종합 매매 시스템

### 전략 레이어

```
[Layer 1] 거시 전략
  • 피라미딩 (분할매수)
  • 분할매도 (Scale Out)
  • Kelly Criterion (포지션)

[Layer 2] 전술 최적화
  • 호가 스프레드 따먹기
  • 시간대별 필터
  • 체결강도 확인
  • 종가 베팅

[Layer 3] 리스크 관리
  • 손절 (-2%)
  • 트레일링 스탑
  • Circuit Breaker
```

---

**작성일**: 2025-12-08
**작성자**: wonny
**버전**: 2.0.0 (미세 최적화 추가)
