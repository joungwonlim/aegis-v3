# Scenario Validator: 통합 검증 시스템

> 작성일: 2025-12-09
> 상태: 완료 ✅
> Phase: 3

---

## 🎯 목표

AI 예측을 **3가지 검증 기법**으로 검증하여 리스크 최소화

```
시나리오 검증 + 백테스트 + 몬테카를로 시뮬레이션 = 신뢰도 높은 의사결정
```

---

## 📊 3가지 검증 기법

### 1️⃣ 시나리오 검증 (Scenario Analysis)

**목적**: Best/Expected/Worst case 확률적 분석

```python
Best Case: AI 예측 * 1.5 → +18% (확률 20%)
Expected Case: AI 예측 * 0.8 → +9.6% (확률 60%)  ← 보수적
Worst Case: -3% (손절 기준) (확률 20%)

기댓값 = 18% * 0.2 + 9.6% * 0.6 + (-3%) * 0.2 = +8.76%
```

**출력**:
- 3가지 시나리오별 수익률
- 각 시나리오 확률
- 시나리오 점수 (0~100)

### 2️⃣ 백테스트 (Backtest)

**목적**: 과거 3개월 유사 패턴으로 승률 계산

```python
조회: 과거 3개월 동안 유사한 패턴의 거래 내역
계산:
- 총 거래 수: 50건
- 승리: 32건 (64%)
- 패배: 18건 (36%)
- 평균 수익률: +6.5%
- 최대 수익률: +18.2%
- 최대 손실률: -4.5%

백테스트 점수 = 승률 + 평균수익률 * 3 = 64 + 6.5*3 = 83.5점
```

**출력**:
- 승률 (Win Rate)
- 평균 수익률
- 최대/최소 수익률
- 백테스트 점수 (0~100)

### 3️⃣ 몬테카를로 시뮬레이션 (Monte Carlo Simulation)

**목적**: 1000회 시뮬레이션으로 확률 분포 계산

```python
설정:
- 평균: AI 예측 * 0.7 (보수적)
- 표준편차: 4%
- 시뮬레이션: 1000회

결과:
- 평균 수익률: +8.4%
- 표준편차: 4.1%
- 수익 확률: 68%
- 손실 확률: 32%
- 5% 백분위 (최악의 5%): -2.1%
- 50% 백분위 (중앙값): +8.3%
- 95% 백분위 (최선의 5%): +18.9%

몬테카를로 점수 = 수익확률 + 평균수익률*2 = 68 + 8.4*2 = 84.8점
```

**출력**:
- 확률 분포 통계
- 수익/손실 확률
- 백분위 분석
- 몬테카를로 점수 (0~100)

---

## 🔢 통합 점수 계산

### 가중치

```python
시나리오: 30%
백테스트: 40%  ← 가장 신뢰도 높음 (실제 데이터)
몬테카를로: 30%

최종 점수 = 시나리오 * 0.3 + 백테스트 * 0.4 + 몬테카를로 * 0.3
```

### 예시

```python
시나리오 점수: 78.5
백테스트 점수: 83.5
몬테카를로 점수: 84.8

최종 점수 = 78.5 * 0.3 + 83.5 * 0.4 + 84.8 * 0.3
         = 23.55 + 33.4 + 25.44
         = 82.39점
```

---

## ✅ 승인/거부 기준

### 3단계 검증

```python
1차: 최종 점수 >= 65점
2차: 백테스트 승률 >= 55%
3차: 몬테카를로 수익 확률 >= 60%

모든 조건 통과 → ✅ 승인
하나라도 미달 → ❌ 거부
```

### 예시

| 종목 | 최종 점수 | 승률 | 수익 확률 | 결과 | 이유 |
|------|----------|------|-----------|------|------|
| A | 82.4 | 64% | 68% | ✅ 승인 | 모든 조건 통과 |
| B | 72.1 | 52% | 65% | ❌ 거부 | 승률 < 55% |
| C | 61.5 | 58% | 62% | ❌ 거부 | 최종 점수 < 65 |
| D | 68.2 | 57% | 58% | ❌ 거부 | 수익 확률 < 60% |

---

## 💰 보수적 목표가 조정

### 3가지 목표가 계산

```python
1. 시나리오 기준: 현재가 * (1 + Expected Case / 100)
2. 백테스트 기준: 현재가 * (1 + 평균 수익률 / 100)
3. 몬테카를로 기준: 현재가 * (1 + 중앙값 / 100)

최종 목표가 = min(시나리오, 백테스트, 몬테카를로)  ← 가장 보수적
```

### 예시

```python
AI 예측: 70,000원 → 78,750원 (+12.5%)

검증 결과:
- 시나리오 Expected: +9.6% → 76,720원
- 백테스트 평균: +6.5% → 74,550원
- 몬테카를로 중앙값: +8.3% → 75,810원

조정된 목표가 = min(76,720, 74,550, 75,810) = 74,550원
```

**결과**: AI 목표가 78,750원 → 조정 후 74,550원 (-5.3%)

---

## 📦 리스크 기반 수량 조정

### 계산 공식

```python
기본 투자 금액: 200만원

점수 조정:
- 65점: 100%
- 75점: 125%
- 85점: 150%
- 점수_계수 = 1.0 + (점수 - 65) / 100

변동성 조정:
- 변동성_계수 = 1.0 / (1 + 표준편차 / 10)

최종 금액 = 기본 * 점수_계수 * 변동성_계수
권장 수량 = 최종 금액 / 현재가
```

### 예시

```python
최종 점수: 82.4점
변동성: 4.1%
현재가: 70,000원

점수_계수 = 1.0 + (82.4 - 65) / 100 = 1.174
변동성_계수 = 1.0 / (1 + 4.1/10) = 0.709

최종 금액 = 2,000,000 * 1.174 * 0.709 = 1,664,652원
권장 수량 = 1,664,652 / 70,000 = 23주
```

---

## 🔄 전체 플로우

```
AI 예측
   ↓
Scenario Validator
   ↓
┌──────────────────────────────────────┐
│ 1️⃣ 시나리오 검증                    │
│    - Best/Expected/Worst            │
│    - 확률 분포                       │
│    - 시나리오 점수: 78.5             │
└──────────────────────────────────────┘
   ↓
┌──────────────────────────────────────┐
│ 2️⃣ 백테스트                         │
│    - 과거 3개월 패턴                 │
│    - 승률: 64%                       │
│    - 백테스트 점수: 83.5             │
└──────────────────────────────────────┘
   ↓
┌──────────────────────────────────────┐
│ 3️⃣ 몬테카를로 시뮬레이션             │
│    - 1000회 시뮬레이션               │
│    - 수익 확률: 68%                  │
│    - 몬테카를로 점수: 84.8           │
└──────────────────────────────────────┘
   ↓
┌──────────────────────────────────────┐
│ 통합 점수 계산                        │
│    최종 점수: 82.4                   │
│    조정 목표가: 74,550원             │
│    권장 수량: 23주                   │
└──────────────────────────────────────┘
   ↓
┌──────────────────────────────────────┐
│ 승인/거부 결정                        │
│    ✅ 승인 (65점 이상, 55% 이상, 60% 이상) │
│    ❌ 거부 (조건 미달)               │
└──────────────────────────────────────┘
   ↓
주문 실행 (승인 시)
```

---

## 💻 사용법

### Pipeline에서 자동 실행

```python
# pipeline/intraday_pipeline.py

async def _validate_candidates(self, candidates: List[dict]) -> List[dict]:
    """Stage 4: 시나리오 검증"""

    validated = []

    for candidate in candidates:
        # Scenario Validator 실행
        validation_result = await scenario_validator.validate(
            stock_code=candidate['stock_code'],
            stock_name=candidate['stock_name'],
            current_price=candidate['current_price'],
            ai_predicted_return=candidate['predicted_return'],
            ai_target_price=candidate['target_price']
        )

        if validation_result.approved:
            validated.append({
                **candidate,
                'adjusted_target_price': validation_result.adjusted_target_price,
                'recommended_quantity': validation_result.recommended_quantity,
                'final_score': validation_result.final_score
            })

    return validated
```

### 개별 호출

```python
from brain.scenario_validator import scenario_validator

# 검증 실행
result = await scenario_validator.validate(
    stock_code="005930",
    stock_name="삼성전자",
    current_price=70000,
    ai_predicted_return=12.5,
    ai_target_price=78750
)

# 결과 확인
if result.approved:
    print(f"✅ 승인: {result.reason}")
    print(f"   최종 점수: {result.final_score:.1f}")
    print(f"   조정 목표가: {result.adjusted_target_price:,}원")
    print(f"   권장 수량: {result.recommended_quantity}주")
else:
    print(f"❌ 거부: {result.reason}")
```

---

## 📊 검증 결과 구조

### ValidationResult

```python
@dataclass
class ValidationResult:
    stock_code: str
    stock_name: str
    ai_predicted_return: float     # AI 예측 수익률
    ai_target_price: int           # AI 목표가

    # 3가지 검증 결과
    scenario: ScenarioResult
    backtest: BacktestResult
    montecarlo: MonteCarloResult

    # 통합 점수
    final_score: float             # 최종 점수 (0~100)
    adjusted_target_price: int     # 조정된 목표가
    recommended_quantity: int      # 권장 수량

    # 최종 결정
    approved: bool                 # 승인 여부
    reason: str                    # 승인/거부 이유
```

---

## 🧪 테스트 케이스

### 1. 고득점 종목 (승인)

```python
AI 예측: +12.5%

검증 결과:
- 시나리오: 78.5점
- 백테스트: 83.5점 (승률 64%)
- 몬테카를로: 84.8점 (수익확률 68%)

최종 점수: 82.4점
결과: ✅ 승인
```

### 2. 낮은 승률 (거부)

```python
AI 예측: +10.2%

검증 결과:
- 시나리오: 72.1점
- 백테스트: 68.3점 (승률 52%)  ← 기준 미달 (55% 이하)
- 몬테카를로: 75.2점 (수익확률 65%)

최종 점수: 71.9점
결과: ❌ 거부 (승률 부족)
```

### 3. 낮은 수익 확률 (거부)

```python
AI 예측: +8.5%

검증 결과:
- 시나리오: 65.2점
- 백테스트: 72.1점 (승률 57%)
- 몬테카를로: 63.8점 (수익확률 58%)  ← 기준 미달 (60% 이하)

최종 점수: 68.2점
결과: ❌ 거부 (수익 확률 부족)
```

---

## 🔮 향후 개선 사항

### 1. 실제 DB 연동

**현재**: 임시 값 사용
**개선**: 실제 DB에서 과거 거래 내역 조회

```python
async def _backtest_analysis(self, stock_code: str, ...):
    # DB에서 과거 3개월 데이터 조회
    historical_trades = db.query(TradeExecution).filter(
        TradeExecution.stock_code == stock_code,
        TradeExecution.created_at >= datetime.now() - timedelta(days=90)
    ).all()

    # 실제 승률 계산
    ...
```

### 2. 패턴 유사도 매칭

**현재**: 전체 과거 데이터 사용
**개선**: 현재 상황과 유사한 패턴만 필터링

```python
# 급등 후 조정 vs 하락 후 반등 → 다른 패턴
# 현재 패턴과 유사한 과거만 백테스트
```

### 3. 실시간 변동성 계산

**현재**: 고정 표준편차 (4%)
**개선**: 실시간 변동성 계산

```python
# 최근 20일 변동성 계산
volatility = calculate_volatility(stock_code, days=20)
```

### 4. 리스크 한도 관리

**개선**: 포트폴리오 전체 리스크 고려

```python
# 현재 포트폴리오 VaR (Value at Risk)
# 신규 종목 추가 시 VaR 변화
# 리스크 한도 초과 시 수량 조정
```

---

## 📈 기대 효과

### 1. 리스크 최소화

- 3가지 검증으로 신뢰도 ↑
- 보수적 목표가 조정
- 변동성 기반 수량 조정

### 2. 승률 향상

- 낮은 승률 종목 필터링
- 백테스트 기반 검증
- 역사적 패턴 활용

### 3. 수익률 안정화

- 과도한 예측 방지
- 시나리오 기반 리스크 분석
- 확률적 의사결정

---

**작성**: Claude Code
**상태**: Scenario Validator 완료 ✅
**다음**: Daily Analyzer 개발
