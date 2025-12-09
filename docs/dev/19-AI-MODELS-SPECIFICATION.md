# AEGIS v3.0 AI 모델 명세

> 작성일: 2025-12-09
> 중요도: ⭐⭐⭐⭐⭐

---

## 🤖 사용 AI 모델

### 1. Claude Sonnet 4.5 (Anthropic)

**용도**: **최종 매매 결정 (Commander)**

**모델 ID**: `claude-sonnet-4-20250514`

**역할**:
- Brain Analyzer 분석 결과를 받아 CIO 최종 결정
- 매수/매도/보유 최종 승인
- VETO 권한 (시장 상황 고려)
- 리스크 평가

**호출 위치**: `brain/commander.py`

**호출 방식**: 동기식 (Synchronous)

**응답 시간**: 2~3초

**Temperature**: 0.1 (냉철한 판단, 창의성 낮음)

**Max Tokens**: 1000

**비용**: 약 $0.003 per call (3 USD / 1000 calls)

**예시**:
```python
response = self.client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    temperature=0.1,
    system="You are the Chief Investment Officer...",
    messages=[{"role": "user", "content": prompt}]
)
```

---

### 2. DeepSeek R1 (DeepSeek)

**용도**: **Layer 3 일별 심층 분석 (Daily Analyzer)**

**모델 ID**: `deepseek-reasoner`

**역할**:
- 매일 07:20 전체 2000개 종목 심층 분석
- 재무제표, 수급, 뉴스, 기술적 분석 종합
- AI Score (0~100) 산출
- 상위 20개 종목 선정 → daily_picks 테이블

**호출 위치**: `fetchers/daily_analyzer.py`

**호출 방식**: 배치 (Batch, 50개씩)

**응답 시간**: 10초/배치, 총 7분 (2000개)

**Temperature**: 0.3

**Max Tokens**: 1500

**비용**: 약 $0.001 per call (매우 저렴)

**예시**:
```python
response = await httpx.post(
    f"{self.deepseek_base_url}/chat/completions",
    json={
        "model": "deepseek-reasoner",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1500
    }
)
```

**특징**:
- 추론 과정(reasoning) 제공
- 수학적 계산 우수
- 장문 분석 능력

---

### 3. Gemini 2.0 Flash (Google)

**용도**: **Layer 2 실시간 빠른 평가 (Market Scanner)**

**모델 ID**: `gemini-2.0-flash-exp`

**역할**:
- 1분마다 등락률/거래량 상위 100개 스캔
- 급등주 빠른 평가 (0.5~1초)
- AI Score (0~100) 산출
- 70점 이상 → WebSocket Priority 3 구독

**호출 위치**: `fetchers/market_scanner.py`

**호출 방식**: 실시간 (1분마다)

**응답 시간**: 0.5~1초 (매우 빠름)

**Temperature**: 0.2

**Max Tokens**: 500

**비용**: 무료 (실험 모델)

**예시**:
```python
response = genai.GenerativeModel('gemini-2.0-flash-exp').generate_content(
    prompt,
    generation_config=genai.GenerationConfig(
        temperature=0.2,
        max_output_tokens=500
    )
)
```

**특징**:
- 극도로 빠른 응답 속도
- 간단한 평가에 최적화
- 무료 (실험 버전)

---

## 📊 AI 모델 역할 분담

### Layer 3: DeepSeek R1 (일별 심층)
```
시간: 07:20 (하루 1회)
대상: 2000개 종목 전체
목적: 심층 분석, 상위 20개 선정
소요: 7분
비용: $2 per day
```

### Layer 2: Gemini 2.0 Flash (실시간 빠름)
```
시간: 09:05~15:20 (1분마다)
대상: 등락률/거래량 상위 100개
목적: 급등주 빠른 평가
소요: 0.5~1초
비용: 무료
```

### Commander: Claude Sonnet 4.5 (최종 결정)
```
시간: 매 Pipeline 실행 시
대상: Brain Analyzer 추천 종목
목적: CIO 최종 승인/거부
소요: 2~3초
비용: $3 per 1000 calls
```

---

## 🔄 AI 모델 흐름

```
┌─────────────────────────────────────────┐
│  Layer 3: DeepSeek R1                   │
│  07:20 - 2000개 종목 심층 분석           │
│  AI Score → daily_picks 테이블           │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  Layer 2: Gemini 2.0 Flash              │
│  09:05~15:20 - 1분마다 빠른 평가         │
│  급등주 발견 → WebSocket Priority 3      │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│  Brain Analyzer (Python)                │
│  Quant Score + AI Score → Final Score   │
│  매수/매도 추천                           │
└──────────────┬──────────────────────────┘
               ↓ (즉시, 0.01초)
┌─────────────────────────────────────────┐
│  Commander: Claude Sonnet 4.5           │
│  CIO 최종 결정 (BUY/SELL/HOLD)          │
│  VETO 권한                               │
└──────────────┬──────────────────────────┘
               ↓
         [주문 실행]
```

---

## 💰 비용 분석

### 일일 예상 비용

**DeepSeek R1 (Daily Analyzer)**:
```
2000개 종목 / 50개 배치 = 40개 배치
40 배치 × $0.001 = $0.04 per day
월간: $1.2
```

**Gemini 2.0 Flash (Market Scanner)**:
```
무료 (실험 모델)
```

**Claude Sonnet 4.5 (Commander)**:
```
파이프라인 1회당 평균 5개 종목 결정
1일 10회 실행 × 5개 = 50 calls
50 × $0.003 = $0.15 per day
월간: $4.5
```

**총 예상 비용**:
```
일간: $0.19 (약 250원)
월간: $5.7 (약 7,500원)

매우 저렴! (기존 Opus 대비 1/10)
```

---

## 🎯 모델 선택 근거

### 1. DeepSeek R1 선택 이유

**장점**:
- ✅ 추론 과정 제공 (reasoning)
- ✅ 장문 분석 능력 우수
- ✅ 비용 매우 저렴 ($0.001/call)
- ✅ 재무제표 계산 정확

**단점**:
- ⚠️ 응답 속도 중간 (10초/배치)
- ⚠️ 한국어 지원 제한적

**결론**: Layer 3 (일별 심층) 최적

### 2. Gemini 2.0 Flash 선택 이유

**장점**:
- ✅ 극도로 빠름 (0.5~1초)
- ✅ 무료 (실험 모델)
- ✅ 간단한 평가에 충분
- ✅ Google 안정성

**단점**:
- ⚠️ 실험 모델 (변경 가능)
- ⚠️ 심층 분석 능력 제한

**결론**: Layer 2 (실시간 빠름) 최적

### 3. Claude Sonnet 4.5 선택 이유

**장점**:
- ✅ 최고 수준 판단 능력
- ✅ 리스크 평가 우수
- ✅ Context 이해 탁월
- ✅ 안정성 (Anthropic)

**단점**:
- ⚠️ 비용 (Opus 대비 1/3, 하지만 합리적)
- ⚠️ 응답 속도 (2~3초)

**결론**: Commander (최종 결정) 최적

---

## 🔄 모델 전환 (Fallback)

### DeepSeek R1 장애 시

**Fallback**: Claude Sonnet 4.5

```python
try:
    score = await deepseek_api.analyze(stock)
except Exception:
    # DeepSeek 장애 시 Sonnet으로 전환
    score = await claude_api.analyze(stock)
```

### Gemini 2.0 Flash 장애 시

**Fallback**: Gemini 1.5 Flash

```python
try:
    score = await gemini_20_flash.evaluate(stock)
except Exception:
    # Gemini 2.0 장애 시 1.5로 전환
    score = await gemini_15_flash.evaluate(stock)
```

### Claude Sonnet 4.5 장애 시

**Fallback**: 자동 HOLD

```python
try:
    decision = await sonnet_45.decide(analysis)
except Exception:
    # Commander 장애 시 안전하게 HOLD
    decision = {"decision": "HOLD", "reason": "API failure"}
```

---

## 📊 성능 비교

### 응답 속도

```
Gemini 2.0 Flash:  0.5~1초   (가장 빠름)
DeepSeek R1:       5~10초    (중간)
Claude Sonnet 4.5: 2~3초     (빠름)
```

### 분석 품질

```
Claude Sonnet 4.5:  ⭐⭐⭐⭐⭐ (최고)
DeepSeek R1:        ⭐⭐⭐⭐   (우수)
Gemini 2.0 Flash:   ⭐⭐⭐     (보통)
```

### 비용 효율

```
Gemini 2.0 Flash:  무료       (최고)
DeepSeek R1:       $0.001     (매우 저렴)
Claude Sonnet 4.5: $0.003     (합리적)
```

---

## 🎯 최적화 전략

### 1. 캐싱 (TODO)

```python
# DeepSeek R1 결과 캐싱 (3일)
if stock_code in cache and cache_age < 3_days:
    return cache[stock_code]
else:
    score = await deepseek_r1.analyze(stock_code)
    cache[stock_code] = score
```

### 2. 배치 처리

```python
# 현재: 50개씩 배치
# 최적: 100개씩 배치 (API 허용 시)
# 효과: 7분 → 3.5분 (2배 빠름)
```

### 3. 병렬 호출

```python
# 현재: 순차 호출
# 최적: 병렬 호출 (종목별)
tasks = [commander.decide(c) for c in candidates]
decisions = await asyncio.gather(*tasks)
# 효과: N초 → N/5초 (5배 빠름)
```

---

## 📝 환경 변수 설정

### `.env` 파일

```bash
# Anthropic API (Claude)
ANTHROPIC_API_KEY=sk-ant-api03-xxx

# DeepSeek API
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Google Gemini API
GOOGLE_API_KEY=AIzaSyxxx
```

---

**작성**: Claude Code
**상태**: AI 모델 명세 완료 ✅
**핵심 모델**:
- **Commander**: Claude Sonnet 4.5 (`claude-sonnet-4-20250514`)
- **Layer 3**: DeepSeek R1 (`deepseek-reasoner`)
- **Layer 2**: Gemini 2.0 Flash (`gemini-2.0-flash-exp`)
