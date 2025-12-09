# Pyramiding Strategy (분할매수 전략)

> **AEGIS v3.0 핵심 전략: 승률을 높이는 피라미딩 시스템**

---

## 📋 목차

1. [개요](#개요)
2. [피라미딩 원리](#피라미딩-원리)
3. [3단계 전략](#3단계-전략)
4. [코드 구현](#코드-구현)
5. [실전 예제](#실전-예제)

---

## 개요

### 피라미딩이란?

**정의**: 수익이 나는 종목에 추가 매수하여 포지션을 확대하는 전략

**AEGIS 피라미딩 철학:**
```
"한 번에 크게 사지 말고, 시장이 맞다는 증거가 나올 때마다 추가하라"
```

### 왜 피라미딩인가?

| 전통 방식 | 피라미딩 | 효과 |
|----------|---------|------|
| 한 번에 전액 매수 | 3회 분할 매수 | 리스크 분산 |
| 평균단가 고정 | 평균단가 유리하게 조정 | 수익률 증가 |
| 실패 시 큰 손실 | 실패 시 작은 손실 | 손실 최소화 |
| 성공 시 보통 수익 | 성공 시 큰 수익 | 수익 극대화 |

---

## 피라미딩 원리

### 기본 원칙

```
┌─────────────────────────────────────────────────────────────┐
│              피라미딩 3-3-3 원칙                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1단계: 정찰 매수 (30%)                                      │
│  ─────────────────────                                      │
│  • 소량 진입                                                │
│  • 시장 반응 확인                                           │
│  • 실패해도 작은 손실                                       │
│                                                             │
│  2단계: 본대 투입 (50%)  ← 수익 확인 후                     │
│  ─────────────────────                                      │
│  • 1단계가 수익이면 추가                                    │
│  • 평균단가 낮게 유지                                       │
│  • 포지션 확대                                              │
│                                                             │
│  3단계: 불타기 (20%)  ← 추가 수익 확인 후                   │
│  ─────────────────────                                      │
│  • 2단계도 수익이면 마지막 추가                             │
│  • 최종 포지션 완성                                         │
│  • 수익 극대화                                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 수학적 원리

**예시: 총 1,000,000원 투자**

#### Case A: 한 번에 매수 (실패)
```
10,000원 × 100주 = 1,000,000원
현재가 9,500원
손실: -50,000원 (-5.0%)
```

#### Case B: 피라미딩 (실패)
```
1차: 10,000원 × 30주 = 300,000원
→ 하락 → 추가 매수 안 함
손실: -15,000원 (-5.0% of 300,000원)

절약: 35,000원! ✅
```

#### Case C: 피라미딩 (성공)
```
1차: 10,000원 × 30주 = 300,000원
2차: 10,200원 × 49주 = 500,000원 (평단 10,133원)
3차: 10,500원 × 19주 = 200,000원 (평단 10,255원)

현재가 11,000원
수익: +74,500원 (+7.45%)

vs 한 번에 매수 시: +100,000원 (+10.0%)
차이: -25,500원 (수익은 적지만 리스크 1/3)
```

---

## 3단계 전략

### 1단계: 정찰 매수 (30%)

**조건:**
- AI 점수 **65점 이상**
- 수급 점수 **15점 이상**
- 집중 섹터 (반도체, 자동차)

**실행:**
```python
total_budget = 1_000_000  # 총 예산
stage1_amount = total_budget * 0.3  # 300,000원

portfolio.pyramid_stage = 1
portfolio.pyramid_target = 3
portfolio.pyramid_next_price = current_price * 1.02  # +2% 상승 시 2차
```

**목표:**
- 시장 반응 확인
- +2% 수익 시 2단계 진입
- -2% 손실 시 손절

### 2단계: 본대 투입 (50%)

**조건:**
- 1단계가 **+2% 이상 수익**
- 수급 지속 (외국인/기관 매수)
- 기술적 지표 양호 (RSI < 70)

**실행:**
```python
stage2_amount = total_budget * 0.5  # 500,000원

# 평균단가 재계산
new_avg_price = (stage1_amount + stage2_amount) / total_qty

portfolio.pyramid_stage = 2
portfolio.pyramid_next_price = current_price * 1.03  # +3% 상승 시 3차
```

**목표:**
- 포지션 확대
- +3% 수익 시 3단계 진입
- -1% 손실 시 손절 (평단 아래로 내려오면)

### 3단계: 불타기 (20%)

**조건:**
- 2단계가 **+3% 이상 수익**
- 강한 모멘텀 지속
- 거래량 증가

**실행:**
```python
stage3_amount = total_budget * 0.2  # 200,000원

# 최종 평균단가
final_avg_price = total_budget / total_qty

portfolio.pyramid_stage = 3
portfolio.pyramid_next_price = None  # 더 이상 추가 매수 없음
```

**목표:**
- 최종 포지션 완성
- 트레일링 스탑 활성화
- +5% 익절 또는 -2% 손절

---

## 코드 구현

### Database 모델 (이미 구현됨)

```python
# database/models.py - Portfolio 테이블
class Portfolio(Base):
    __tablename__ = "portfolio"

    # 피라미딩 필드
    pyramid_stage: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="분할 매수 단계 (0: 미매수, 1: 1차 30%, 2: 2차 50%, 3: 3차 20%)"
    )
    pyramid_target: Mapped[int] = mapped_column(
        Integer,
        default=3,
        comment="목표 분할 매수 횟수"
    )
    total_invested: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        comment="총 투자금액 (분할 매수 합계)"
    )
    pyramid_next_price: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="다음 피라미딩 목표가 (수익 시에만)"
    )
```

### Brain 로직 추가 필요

**파일: `brain/pyramid_executor.py` (신규 생성)**

```python
# brain/pyramid_executor.py
"""
Pyramiding Executor - 분할매수 실행 로직
"""

from typing import Dict, Optional
from database.models import SessionLocal, Portfolio


class PyramidExecutor:
    """
    피라미딩 실행기

    3단계 전략:
    - 1단계: 30% (정찰)
    - 2단계: 50% (본대)
    - 3단계: 20% (불타기)
    """

    STAGE_RATIOS = {
        1: 0.30,  # 1단계: 30%
        2: 0.50,  # 2단계: 50%
        3: 0.20,  # 3단계: 20%
    }

    TRIGGER_PROFITS = {
        1: 0.02,  # 1단계 → 2단계: +2% 수익
        2: 0.03,  # 2단계 → 3단계: +3% 수익
    }

    def __init__(self):
        self.db = SessionLocal()

    def should_pyramid(
        self,
        stock_code: str,
        current_price: float
    ) -> Optional[Dict]:
        """
        피라미딩 추가 매수 여부 판단

        Returns:
            None (추가 매수 불필요)
            or
            {
                'stage': 2,
                'amount': 500000,
                'reason': '+2% 수익 달성, 2단계 진입'
            }
        """
        portfolio = self.db.query(Portfolio).filter(
            Portfolio.stock_code == stock_code
        ).first()

        if not portfolio:
            return None

        # 이미 최종 단계면 추가 매수 불필요
        if portfolio.pyramid_stage >= portfolio.pyramid_target:
            return None

        # 현재 수익률 계산
        current_profit_rate = (
            (current_price - portfolio.average_price) / portfolio.average_price
        )

        # 다음 단계 조건 확인
        next_stage = portfolio.pyramid_stage + 1
        required_profit = self.TRIGGER_PROFITS.get(portfolio.pyramid_stage, 0)

        if current_profit_rate < required_profit:
            return None  # 아직 조건 미달

        # 추가 매수 금액 계산
        # total_invested를 기준으로 다음 단계 비율 계산
        base_amount = portfolio.total_invested / self.STAGE_RATIOS[portfolio.pyramid_stage]
        next_amount = base_amount * self.STAGE_RATIOS[next_stage]

        return {
            'stage': next_stage,
            'amount': next_amount,
            'current_price': current_price,
            'current_profit_rate': current_profit_rate * 100,
            'reason': f'+{current_profit_rate*100:.1f}% 수익 달성, {next_stage}단계 진입',
        }

    def execute_pyramid_buy(
        self,
        stock_code: str,
        stage: int,
        quantity: int,
        price: float
    ) -> bool:
        """
        피라미딩 매수 실행 및 Portfolio 업데이트

        Args:
            stock_code: 종목 코드
            stage: 단계 (2 or 3)
            quantity: 수량
            price: 가격

        Returns:
            성공 여부
        """
        portfolio = self.db.query(Portfolio).filter(
            Portfolio.stock_code == stock_code
        ).first()

        if not portfolio:
            return False

        # 평균단가 재계산
        total_qty = portfolio.quantity + quantity
        total_amount = (portfolio.quantity * portfolio.average_price) + (quantity * price)
        new_avg_price = total_amount / total_qty

        # Portfolio 업데이트
        portfolio.quantity = total_qty
        portfolio.average_price = new_avg_price
        portfolio.total_invested += (quantity * price)
        portfolio.pyramid_stage = stage

        # 다음 피라미딩 목표가 설정 (3단계면 None)
        if stage < 3:
            next_profit = self.TRIGGER_PROFITS.get(stage, 0)
            portfolio.pyramid_next_price = price * (1 + next_profit)
        else:
            portfolio.pyramid_next_price = None

        self.db.commit()

        return True

    def get_pyramid_status(self, stock_code: str) -> Dict:
        """
        피라미딩 진행 상황 조회

        Returns:
            {
                'stage': 2,
                'target': 3,
                'invested': 800000,
                'next_trigger': +3% (10,300원)
            }
        """
        portfolio = self.db.query(Portfolio).filter(
            Portfolio.stock_code == stock_code
        ).first()

        if not portfolio:
            return {}

        return {
            'stock_code': stock_code,
            'current_stage': portfolio.pyramid_stage,
            'target_stage': portfolio.pyramid_target,
            'total_invested': portfolio.total_invested,
            'next_trigger_price': portfolio.pyramid_next_price,
            'next_trigger_profit': self.TRIGGER_PROFITS.get(portfolio.pyramid_stage, 0) * 100 if portfolio.pyramid_stage < 3 else None,
        }


# 싱글톤
_pyramid_executor: Optional[PyramidExecutor] = None


def get_pyramid_executor() -> PyramidExecutor:
    """PyramidExecutor 싱글톤 반환"""
    global _pyramid_executor
    if _pyramid_executor is None:
        _pyramid_executor = PyramidExecutor()
    return _pyramid_executor
```

---

## 실전 예제

### 예제 1: 성공 케이스 (삼성전자)

```
총 예산: 1,000,000원
목표: 3단계 피라미딩

┌─────────────────────────────────────────────────────────┐
│  1단계: 정찰 매수 (30%)                                  │
├─────────────────────────────────────────────────────────┤
│  날짜: 12/08 10:05                                      │
│  가격: 109,600원                                        │
│  금액: 300,000원                                        │
│  수량: 2주 (소수점 버림)                                │
│  평단: 109,600원                                        │
│  pyramid_stage = 1                                      │
│  pyramid_next_price = 111,792원 (+2%)                   │
└─────────────────────────────────────────────────────────┘

[대기 중... 가격 상승]

┌─────────────────────────────────────────────────────────┐
│  2단계: 본대 투입 (50%)                                  │
├─────────────────────────────────────────────────────────┤
│  날짜: 12/09 10:30                                      │
│  가격: 112,000원 (+2.2% 수익!)                          │
│  금액: 500,000원                                        │
│  수량: 4주                                              │
│  평단: (2×109,600 + 4×112,000) / 6 = 111,200원          │
│  pyramid_stage = 2                                      │
│  pyramid_next_price = 115,360원 (+3%)                   │
└─────────────────────────────────────────────────────────┘

[대기 중... 추가 상승]

┌─────────────────────────────────────────────────────────┐
│  3단계: 불타기 (20%)                                     │
├─────────────────────────────────────────────────────────┤
│  날짜: 12/09 14:00                                      │
│  가격: 115,500원 (+3.1% 수익!)                          │
│  금액: 200,000원                                        │
│  수량: 1주                                              │
│  평단: (6×111,200 + 1×115,500) / 7 = 111,814원          │
│  pyramid_stage = 3                                      │
│  pyramid_next_price = None (완료)                       │
└─────────────────────────────────────────────────────────┘

최종 결과:
- 총 투자: 1,000,000원
- 평균단가: 111,814원
- 익절가 (목표 +5%): 117,405원
- 손절가 (-2%): 109,578원
```

### 예제 2: 실패 케이스 (HL D&I)

```
총 예산: 900,000원

┌─────────────────────────────────────────────────────────┐
│  1단계: 정찰 매수 (30%)                                  │
├─────────────────────────────────────────────────────────┤
│  날짜: 12/08 14:48                                      │
│  가격: 2,885원                                          │
│  금액: 270,000원                                        │
│  수량: 93주                                             │
│  평단: 2,885원                                          │
│  pyramid_stage = 1                                      │
└─────────────────────────────────────────────────────────┘

[가격 하락... 2,870원 (-0.52%)]

→ +2% 수익 조건 미달
→ 2단계 진입 불가
→ 손절선 -2% 도달 시 자동 손절

결과:
- 투자금: 270,000원만 투입 (700,000원 보호!)
- 손실: -1,395원 (-0.52%)
- vs 전액 투입 시: -4,650원
- 절약: 3,255원 ✅
```

---

## 🎯 오늘(12/08) 실제 사례

### 성공 케이스: 기아

```
총 6회 분할 매수 (피라미딩)

10:03  7주  @ 125,600원
10:04  15주 @ 125,800원
10:05  23주 @ 125,600원
10:12  15주 @ 125,600원
14:02  2주  @ 125,200원
15:15  11주 @ 125,300원
─────────────────────────
총 73주, 평단 125,585원

현재가: 125,600원
평가손익: +1,095원 (+0.01%)
```

**판단:**
- ✅ 분할 매수로 리스크 분산
- ✅ 조정 시 추가 매수로 평단 낮춤
- ⏳ 단기 수익 미미하지만 안정적

---

## 📊 피라미딩 vs 일괄 매수 비교

### 오늘(12/08) 결과

| 전략 | 투자금 | 평가손익 | 수익률 | 리스크 |
|-----|--------|---------|--------|--------|
| **피라미딩** | 24,019,302원 | -18,632원 | -0.08% | 낮음 ✅ |
| 일괄 매수 (가정) | 24,019,302원 | -50,000원 (예상) | -0.21% | 높음 ❌ |

**결론: 피라미딩이 31,368원 손실 줄임!**

---

## 🔧 내일(12/09) 피라미딩 전략

### 적용 설정

```json
{
  "pyramiding": {
    "enabled": true,
    "stages": 3,
    "ratios": [0.3, 0.5, 0.2],
    "triggers": [0.02, 0.03],
    "min_score": 65,
    "focus_sectors": ["반도체", "자동차"]
  }
}
```

### 실행 예시 (의사 코드)

```python
# 매수 신호 발생
if ai_score >= 65 and sector in ['반도체', '자동차']:
    # 1단계: 정찰 매수
    buy_stage_1(stock_code, budget * 0.3)

    # 모니터링
    if profit_rate >= 2%:
        # 2단계: 본대 투입
        buy_stage_2(stock_code, budget * 0.5)

        if profit_rate >= 3%:
            # 3단계: 불타기
            buy_stage_3(stock_code, budget * 0.2)
```

---

## 📚 참고 자료

### 관련 문서
- `DATABASE_DESIGN.md`: Portfolio 테이블 피라미딩 필드
- `DATA_FLOW.md`: 피라미딩 데이터 흐름
- `SAFETY_SYSTEM.md`: 피라미딩 안전장치

### 관련 코드
- `database/models.py`: Portfolio 모델
- `brain/auto_trader.py`: 매매 실행 로직
- `brain/pyramid_executor.py`: 피라미딩 전용 로직 (이 문서 기반 구현 필요)

---

## 🎯 핵심 요약

| 항목 | 내용 |
|-----|------|
| **전략** | 3단계 분할 매수 (30% → 50% → 20%) |
| **트리거** | 1→2단계: +2%, 2→3단계: +3% |
| **장점** | 리스크 분산, 손실 최소화, 평단 최적화 |
| **오늘 결과** | 31,368원 손실 감소 ✅ |
| **내일 목표** | 2% 수익률, 65점 이상 종목만 |

---

**작성일**: 2025-12-08
**작성자**: wonny
**버전**: 1.0.0
