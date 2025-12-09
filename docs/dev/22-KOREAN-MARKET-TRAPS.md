# Korean Market Trap Detection System

**작성일**: 2025-12-09 22:59:20
**작성자**: wonny
**단계**: Phase 4.6 - AI Learning & Feedback Loop

---

## 📌 배경

### 실전 사례: 2025-12-09 삼성전자/SK하이닉스 최고점 매수

**상황**:
- 전날 미국장 호재 (엔비디아 상승)
- 아침 시초가 갭상승 (+2~3%)
- AI (Opus) 판단: "미국장 호재 + 갭상승 = 매수!"
- **CEO 만류했으나 외국인 수급 좋다는 이유로 최고점 풀매수**

**결과**:
- 시초가 이후 외국인/기관 **차익 실현 물량** 쏟아냄
- 주가 질질 흘러내려 **음봉 마감**
- 전형적인 **"전강후약(Gap Up & Die)"** 패턴

**문제**:
- AI는 미국장 호재만 보고 매수 판단
- 한국 시장 특유의 **"갭상승 = 차익 실현 기회"** 패턴 학습 안 됨
- 수급 이탈 (외국인/기관 매도) 실시간 감지 실패

---

## 🎯 목적

### 핵심 목표

1. **한국 시장 10대 함정 패턴 감지**
2. **실시간 수급 이탈 감지 (Fake Rise)**
3. **AI 학습 피드백 루프 구축 (실패 → 학습 → 개선)**

### 기대 효과

- 고질적 실수 방지 (갭상승 추격 매수)
- 외국인/기관 매도 시 즉시 감지
- 시간이 갈수록 정확도 상승 (Self-Learning)

---

## 🛠️ 10가지 함정 패턴

### 1️⃣ 수급 이탈 (Fake Rise) ⭐ 최우선

**조건**:
- 주가 상승 (+1% 이상)
- 외국인/기관 순매수 음수(-) (둘 다 매도 중)
- 개미만 사고 있는 상황

**위험도**: CRITICAL (95% 신뢰도)
**권장**: AVOID (매수 금지)

**로그 예시**:
```
🚨 [005930] FAKE RISE: 주가 상승(+2.3%) BUT 수급 이탈!
   외국인 -15,000주 매도, 기관 -8,000주 매도.
   개미 유인 함정(Ant-Luring) 감지.
```

---

### 2️⃣ 갭 과열 (Gap Overheat)

**조건**:
- 시초가가 전일 대비 +3.5% 이상

**위험도**: HIGH (90% 신뢰도)
**권장**: WAIT (눌림목 대기)

**배경**:
- 미국장 호재 → 한국 시초가 갭상승
- 외국인/기관이 그 갭을 이용해 차익 실현
- "너무 높게 시작하면 먹을 게 없다"

**로그 예시**:
```
⚠️  [005930] GAP OVERHEAT: 갭 과열 (+3.8%).
   미국장 호재에 갭상승 → 차익 실현 위험.
   '전강후약' 패턴 전조.
```

---

### 3️⃣ 프로그램 매도 가속 (Program Dump)

**조건**:
- 프로그램 순매수 음수(-)
- 매도 기울기 가파름 (< -0.3)

**위험도**: HIGH (85% 신뢰도)
**권장**: AVOID

**배경**: 오후장 폭락 전조

---

### 4️⃣ 뉴스 후 음봉 (Sell on News)

**조건**:
- 호재 뉴스 발생
- 거래량 급증 (2배 이상)
- 현재가 < 시초가

**위험도**: MEDIUM (80% 신뢰도)
**권장**: AVOID

**배경**: 재료 소멸 패턴

---

### 5️⃣ 거래량 없는 상승 (Hollow Rise)

**조건**:
- 주가 +3% 이상 상승
- 거래량 < 전일 대비 50%

**위험도**: MEDIUM (75% 신뢰도)
**권장**: REDUCE_SIZE

**배경**: 적은 돈으로 가격만 올려놓은 상태, 툭 치면 무너짐

---

### 6️⃣ 매도벽 (Resistance Wall)

**조건**:
- 1~2호가에 평소 거래량의 5배 매도 물량

**위험도**: MEDIUM (70% 신뢰도)
**권장**: WAIT

**배경**: 돌파 불가능, 모멘텀 차단

---

### 7️⃣ 섹터 디커플링 (Sector Decouple)

**조건**:
- 내 종목 +3% 상승
- 섹터 지수 -1% 하락 (괴리 2%p 이상)

**위험도**: MEDIUM (65% 신뢰도)
**권장**: WAIT

**배경**: 곧 따라 내려감 (회귀)

---

### 8️⃣ 환율 쇼크 (FX Impact)

**조건**:
- 원/달러 환율 +0.5% 이상 급등

**위험도**: MEDIUM (60% 신뢰도)
**권장**: REDUCE_SIZE

**배경**: 외국인 프로그램 매도 유발

---

### 9️⃣ 장기 이평선 저항 (MA Resistance)

**조건**:
- 현재가가 120일선 or 200일선에 근접 (±1%)

**위험도**: LOW (55% 신뢰도)
**권장**: WAIT

**배경**: 한국 시장 80% 여기서 맞고 떨어짐

---

### 🔟 오버행 상장 (Dilution Day)

**조건**:
- 오늘이 CB/BW/신주 상장일

**위험도**: CRITICAL (90% 신뢰도)
**권장**: AVOID

**배경**: 물량 공급 쇼크 임박

---

## 🔄 AI 학습 피드백 루프

### 학습 프로세스

```
1. 함정 감지
   └─→ 매수 회피 (AVOID/WAIT/REDUCE_SIZE)
         └─→ 실제 결과 수집 (1시간 후, 종가)
               └─→ 판단 결과 (CORRECT / WRONG)
                     └─→ 가중치 조정
                           ├─ CORRECT: weight += 0.01 (최대 0.99)
                           └─ WRONG: weight -= 0.02 (최소 0.30)
```

### DB 스키마

#### trap_patterns 테이블

| Column | Type | 설명 |
|--------|------|------|
| trap_type | String | 함정 타입 ("fake_rise", "gap_overheat"...) |
| weight | Float | 가중치 (0.0 ~ 1.0) |
| total_count | Integer | 전체 감지 횟수 |
| correct_count | Integer | 정확히 맞춘 횟수 |
| accuracy | Float | 정확도 (%) |

#### trade_feedback 테이블

| Column | Type | 설명 |
|--------|------|------|
| trade_date | Date | 거래일 |
| stock_code | String | 종목 코드 |
| trap_detected | Boolean | 함정 감지 여부 |
| trap_type | String | 감지된 함정 타입 |
| avoided_buy | Boolean | 매수 회피 여부 |
| actual_result | String | "CORRECT" / "WRONG" |
| price_change_pct | Float | 실제 가격 변화율 |

---

## 📊 통합 지점

### 1️⃣ Analyzer 통합

**파일**: `brain/analyzer.py`

**위치**: `analyze()` 메서드 - Quant Score 계산 후, DeepSeek V3 호출 전

```python
# 한국 시장 함정 감지
from brain.korean_market_traps import korean_trap_detector

traps = await korean_trap_detector.detect_traps(
    stock_code=stock_code,
    stock_name=stock_name,
    current_price=current_price,
    market_data=market_data,
    realtime_data=realtime_data
)

# 함정 감지 시 AI 점수 대폭 삭감
if traps:
    critical_traps = [t for t in traps if t.severity == "CRITICAL"]
    if critical_traps:
        # CRITICAL 함정 → AI 점수 0점 처리
        ai_score = 0
        ai_comment = f"TRAP DETECTED: {critical_traps[0].reason}"
    else:
        # HIGH/MEDIUM 함정 → AI 점수 감점
        penalty = sum(t.confidence * 20 for t in traps)
        ai_score = max(0, ai_score - penalty)
```

### 2️⃣ Commander 통합

**파일**: `brain/commander.py`

**위치**: `decide()` 메서드 - Prompt 구성 시

```python
# Prompt에 함정 정보 추가
if traps:
    trap_info = "\n".join([
        f"- [{t.severity}] {t.trap_type}: {t.reason}"
        for t in traps
    ])
    prompt += f"\n\n[Korean Market Traps Detected]\n{trap_info}\n"
```

### 3️⃣ Portfolio Manager 통합

**파일**: `brain/portfolio_manager.py`

**위치**: `run_cycle()` 메서드 - 보유 종목 체크 시

```python
# 보유 종목도 함정 감지 (긴급 매도 판단)
for item in holdings:
    traps = await korean_trap_detector.detect_traps(...)

    if traps:
        critical = [t for t in traps if t.severity == "CRITICAL"]
        if critical:
            # 긴급 매도 결정
            return {
                'reason': f'함정 감지: {critical[0].reason}',
                'reason_type': 'trap_detected',
                'sell_ratio': 1.0
            }
```

---

## 🔍 사용 예시

### 예시 1: 수급 이탈 감지

```python
# 입력 데이터
market_data = {
    'price_change_pct': 2.3,  # +2.3% 상승
    'open_price': 78500,
    'current_price': 78000,
    # ...
}

realtime_data = {
    'foreign_net_buy': -15000,  # 외국인 -15,000주 매도
    'inst_net_buy': -8000,      # 기관 -8,000주 매도
}

# 함정 감지
traps = await korean_trap_detector.detect_traps(
    stock_code="005930",
    stock_name="삼성전자",
    current_price=78000,
    market_data=market_data,
    realtime_data=realtime_data
)

# 결과
>>> traps[0].trap_type
"fake_rise"

>>> traps[0].severity
"CRITICAL"

>>> traps[0].recommendation
"AVOID"

>>> traps[0].reason
"주가 상승(+2.3%) BUT 수급 이탈! 외국인 -15,000주 매도, 기관 -8,000주 매도. 개미 유인 함정(Ant-Luring) 감지."
```

### 예시 2: 갭 과열 감지

```python
market_data = {
    'open_price': 78500,
    'prev_close': 75800,  # 전일 종가
}

gap_pct = (78500 - 75800) / 75800 * 100  # +3.56%

# 함정 감지
traps = await korean_trap_detector.detect_traps(...)

>>> traps[0].trap_type
"gap_overheat"

>>> traps[0].recommendation
"WAIT"  # 눌림목 대기
```

### 예시 3: 피드백 기록

```python
# 1시간 후 실제 결과 확인
price_at_decision = 78500
price_after_1h = 76800  # 하락

actual_result = "CORRECT" if price_after_1h < price_at_decision else "WRONG"
price_change_pct = ((price_after_1h - price_at_decision) / price_at_decision) * 100

# 피드백 기록
await korean_trap_detector.record_feedback(
    stock_code="005930",
    trap_detected=True,
    trap_type="fake_rise",
    avoided_buy=True,
    actual_result=actual_result,  # "CORRECT"
    price_change_pct=price_change_pct  # -2.17%
)

# 학습 결과
>>> korean_trap_detector.pattern_weights["fake_rise"]
0.96  # 0.95 → 0.96 (가중치 증가)
```

---

## 📈 개선 효과 시뮬레이션

### Before (함정 감지 없음)

```
2025-12-09 09:05 삼성전자
- 시초가: 78,500원 (+3.5% 갭상승)
- AI 판단: "미국장 호재 + 갭상승 = BUY!"
- 매수: 78,500원
- 종가: 76,800원
- 손실: -2.17% ❌
```

### After (함정 감지 있음)

```
2025-12-09 09:05 삼성전자
- 시초가: 78,500원 (+3.5% 갭상승)
- 🚨 함정 감지: "갭 과열 + 수급 이탈"
- AI 판단: "AVOID - 차익 실현 위험"
- 매수 회피 ✅
- 피드백: "CORRECT" → 가중치 강화
```

---

## 🧪 테스트 시나리오

### Test Case 1: 수급 이탈

**입력**:
- 주가: +2.5%
- 외국인: -20,000주
- 기관: -10,000주

**예상 출력**:
- trap_type: "fake_rise"
- severity: "CRITICAL"
- recommendation: "AVOID"

### Test Case 2: 갭 과열

**입력**:
- 전일 종가: 75,000원
- 시초가: 77,800원 (+3.73%)

**예상 출력**:
- trap_type: "gap_overheat"
- severity: "HIGH"
- recommendation: "WAIT"

### Test Case 3: 복합 함정

**입력**:
- 갭 과열 (+3.8%)
- 수급 이탈 (외국인 매도)
- 프로그램 매도 가속

**예상 출력**:
- 3개 함정 감지
- 최우선 CRITICAL 함정: "fake_rise"
- recommendation: "AVOID"

---

## 📚 관련 문서

- AI Models Spec: `19-AI-MODELS-SPECIFICATION.md`
- Safety Checker: `20-SAFETY-CHECKER.md`
- Partial Sell: `21-PARTIAL-SELL.md`
- Brain Analyzer: `brain/analyzer.py`
- Commander: `brain/commander.py`

---

## 🚀 배포 계획

### Phase 1: 기본 감지 (1주)
- [ ] 10가지 함정 패턴 구현
- [ ] Analyzer 통합
- [ ] 로깅 및 모니터링

### Phase 2: 학습 루프 (2주)
- [ ] 피드백 기록 시스템
- [ ] 가중치 자동 조정
- [ ] 정확도 추적 대시보드

### Phase 3: 실시간 감지 (3주)
- [ ] WebSocket 실시간 수급 데이터
- [ ] 프로그램 매매 추적
- [ ] 긴급 매도 자동화

---

## 👤 작성자

- **Author**: wonny
- **Date**: 2025-12-09 22:59:20
- **Project**: AEGIS v3.0
- **Phase**: 4.6 (AI Learning & Korean Market Adaptation)
