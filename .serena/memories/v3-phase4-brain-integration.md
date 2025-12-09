# v3 Phase 4: Brain 통합 완료

## 완료 일자: 2025-12-09

## 구현 완료 항목

### 1. Brain Analyzer (`brain/analyzer.py`)
**통합 분석 엔진**:
- Quant Score 계산
- AI Score 활용 (DeepSeek/Gemini)
- Final Score = AI (50%) + Quant (50%)
- 매수/매도 추천 (BUY/SELL/HOLD)
- 목표가/손절가 계산

**핵심 메서드**:
```python
analyze_candidate() - 개별 종목 분석
analyze_batch() - 배치 분석
_calculate_final_score() - Final Score 계산
_make_recommendation() - 매수/매도 추천
_calculate_target_price() - 목표가 계산
_calculate_stop_loss() - 손절가 계산
```

### 2. Quant Calculator (`brain/quant_calculator.py`)
**기술적 지표 계산기** (총 100점):
1. RSI (30점) - 과매수/과매도 판단
2. MACD (25점) - 추세 방향 및 골든크로스
3. 볼린저밴드 (20점) - 가격 위치 분석
4. 거래량 (15점) - 관심도 측정
5. 이동평균선 (10점) - 추세 강도

**데이터 소스**: `daily_ohlcv` 테이블 (pykrx, 최근 60일)

### 3. Final Score 계산식
```
Final Score = (AI Score × 0.5) + (Quant Score × 0.5)

예시:
AI: 85, Quant: 75 → Final: 80
```

### 4. 추천 규칙
```
Final Score >= 75: BUY
Final Score <= 40: SELL
그 외: HOLD

추가 조건:
AI와 Quant 점수 차이 >= 30: HOLD (불확실성)
```

### 5. 목표가/손절가
**목표가**:
- Score >= 80: +8%
- Score >= 70: +6%
- Score >= 60: +4%
- 그 외: +2%

**손절가**:
- Score >= 80: -3%
- Score >= 70: -4%
- Score >= 60: -5%
- 그 외: -6%

### 6. Pipeline 통합
**파일**: `pipeline/intraday_pipeline.py`

**_brain_analyze() 구현**:
1. Daily Picks 조회 (DeepSeek R1 종목)
2. Brain Analyzer 실행
3. BUY 추천 필터링
4. Validation 단계로 전달

## 데이터 흐름

```
Layer 3 (DeepSeek R1) → AI Score → daily_picks 테이블
Layer 2 (Gemini) → AI Score → WebSocket Priority 3
Quant Calculator → Quant Score (RSI, MACD, BB, Volume, MA)
────────────────────────────────────────────────────
Brain Analyzer → Final Score → 매수/매도 추천
```

## 핵심 성과

1. ✅ AI + Quant 통합 분석 시스템
2. ✅ 객관적 매수/매도 기준 수립
3. ✅ 리스크 관리 (목표가/손절가)
4. ✅ Pipeline 완전 통합

## TODO (Phase 5)

1. WebSocket Manager 연동
2. Market Scanner 연동
3. pykrx Fetcher 구현 (daily_ohlcv 실제 데이터)
4. 종목명 조회 최적화

## 핵심 원칙

- Final Score는 AI와 Quant를 동등하게 반영
- 불확실성 높으면 무조건 HOLD
- 리스크는 Final Score 기반 동적 조정
