# AEGIS v3.1 Documentation (DeepSeek Enhanced)

> **DeepSeek R1 분석 기반 개선사항 반영 버전**
> **기존 구조 유지 + 핵심 개선사항 통합**

---

## 📚 문서 목록

### 🎯 핵심 문서 (필독)

| 문서 | 설명 | 대상 |
|-----|------|------|
| [IMPROVEMENT_PLAN.md](./IMPROVEMENT_PLAN.md) | 🆕 **DeepSeek R1 시스템 개선 계획** (캐싱, 모니터링, 변동성 손절) | 전체 팀 |
| [CORE_PHILOSOPHY.md](./CORE_PHILOSOPHY.md) | 핵심 철학 및 AI 모델 전략 (개선사항 반영) | 전체 팀 |
| [BRAIN_SIMPLE.md](./BRAIN_SIMPLE.md) | Brain 의사결정 시스템 (AI 캐싱 레이어 추가) | 개발자 |
| [PYRAMIDING_STRATEGY.md](./PYRAMIDING_STRATEGY.md) | 피라미딩 + 분할매도 전략 (변동성 손절 통합) | 개발자 |
| [TRADING_TECHNIQUES.md](./TRADING_TECHNIQUES.md) | 고급 매매 기법 (DCA, Grid, Kelly) | 개발자 |
| [MICRO_OPTIMIZATION.md](./MICRO_OPTIMIZATION.md) | 미세 최적화 (0.001%를 만드는 디테일) | 개발자 |
| [BACKEND_MICRO_OPT.md](./BACKEND_MICRO_OPT.md) | 백엔드 최적화 (학습 + SAFE MODE) | 개발자 |

### 🏗️ 아키텍처

| 문서 | 설명 |
|-----|------|
| [PHASED_DEVELOPMENT.md](./PHASED_DEVELOPMENT.md) | **단계별 개발 (Backend 먼저!)** |
| [COMBAT_ARCHITECTURE.md](./COMBAT_ARCHITECTURE.md) | 실전 아키텍처 |
| [DATA_FLOW.md](./DATA_FLOW.md) | 데이터 흐름 상세 |

### 💾 데이터베이스

| 문서 | 설명 |
|-----|------|
| [DATABASE_DESIGN.md](./DATABASE_DESIGN.md) | DB 스키마 설계 (v3.2) |
| [DATA_INTEGRITY_RULES.md](./DATA_INTEGRITY_RULES.md) | **데이터 무결성 규칙 (삭제 금지!)** |
| [EXTERNAL_DATA_SOURCES.md](./EXTERNAL_DATA_SOURCES.md) | 외부 데이터 소스 |

### 🛡️ 시스템

| 문서 | 설명 |
|-----|------|
| [SAFETY_SYSTEM.md](./SAFETY_SYSTEM.md) | 안전장치 시스템 |
| [SCHEDULER_DESIGN.md](./SCHEDULER_DESIGN.md) | 스케줄러 설계 |

### 📡 API & 통신

| 문서 | 설명 |
|-----|------|
| [KIS_API_SPECIFICATION.md](./KIS_API_SPECIFICATION.md) | 한국투자증권 API 사양 |
| [TELEGRAM_BOT_SPEC.md](./TELEGRAM_BOT_SPEC.md) | 텔레그램 봇 사양 |

### 🧪 백테스팅

| 문서 | 설명 |
|-----|------|
| [BACKTESTER_SIMPLE.md](./BACKTESTER_SIMPLE.md) | 백테스팅 시스템 |

---

## 🔥 v3.1 주요 변경사항

### 1. AI 비용 최적화 (캐싱 레이어)
```python
# brain/ai_cache.py - TTL 기반 캐싱 시스템
cache = AIResponseCache(ttl_minutes=60)
response = cache.get(stock_code, analysis_type, params)
# 기대 효과: API 호출 비용 30-50% 절감
```

### 2. Grafana 실시간 모니터링
```yaml
# docker-compose.yml에 Grafana 추가
grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
# 대시보드: AI 성능, 매매 성과, 시스템 건강
```

### 3. 변동성 기반 손절선
```python
# brain/risk_manager.py - ATR 기반 동적 손절
stop_loss = VolatilityStopLoss()
loss_pct = stop_loss.calculate_atr_stop("005930", atr_multiplier=2.0)
# 삼성전자: -2.5%, 테슬라: -6.8%, 중소형주: -9.2%
```

### 4. Walk-Forward 백테스트
```python
# backtester/walk_forward.py - 과최적화 방지
optimizer = WalkForwardOptimizer(train_period=60, test_period=20)
results = optimizer.optimize(start_date, end_date, strategy_params)
# 실전 성과와 백테스트 괴리 감소
```

---

## 🚀 읽기 순서 (역할별)

### 새 개발자
```
1. CORE_PHILOSOPHY.md       ← 시스템 이해
2. BRAIN_SIMPLE.md          ← 의사결정 로직
3. PYRAMIDING_STRATEGY.md   ← 핵심 전략
4. DATABASE_DESIGN.md       ← DB 구조
5. BACKEND_MICRO_OPT.md     ← 백엔드 최적화
```

### PM / 전략가
```
1. CORE_PHILOSOPHY.md       ← 철학
2. PYRAMIDING_STRATEGY.md   ← 매매 전략
3. TRADING_TECHNIQUES.md    ← 고급 매매 기법
4. SAFETY_SYSTEM.md         ← 리스크 관리
```

### DevOps
```
1. PHASED_DEVELOPMENT.md    ← 개발 로드맵
2. SCHEDULER_DESIGN.md      ← 스케줄러
3. KIS_API_SPECIFICATION.md ← API 연동
4. DATA_FLOW.md             ← 데이터 흐름
```

### 데이터 과학자
```
1. BACKTESTER_SIMPLE.md     ← 백테스팅 시스템
2. MICRO_OPTIMIZATION.md    ← 미세 최적화
3. DATA_INTEGRITY_RULES.md  ← 데이터 무결성
```

---

## 🆕 최근 업데이트 (2025-12-09)

### v3.1 추가 문서 (DeepSeek R1 분석 기반)
- ✅ **BACKEND_MICRO_OPT.md**: 백엔드 최적화 (N+1, Redis, Celery)
- ✅ **DATA_INTEGRITY_RULES.md**: 데이터 무결성 규칙 (UPSERT, 삭제금지)
- ✅ **EXTERNAL_DATA_SOURCES.md**: 외부 데이터 소스 (KIS, pykrx, DART)
- ✅ **MICRO_OPTIMIZATION.md**: 미세 최적화 기법

### 업데이트된 문서
- ✅ **IMPROVEMENT_PLAN.md**: DeepSeek R1 분석 결과 반영
- ✅ **CORE_PHILOSOPHY.md**: AI 캐싱, 모니터링, 변동성 손절 반영
- ✅ **DATABASE_DESIGN.md**: v3.2로 버전 업데이트

---

## 📊 개선 효과 예상

| 개선사항 | 예상 효과 | 측정 지표 | 적용 시기 |
|---------|----------|----------|----------|
| AI 캐싱 레이어 | API 비용 -40% | 월 API 호출 횟수 | 즉시 (1주) |
| 변동성 손절 | 수익률 +3~5%p | 백테스트 연간 수익률 | 즉시 (1주) |
| Grafana 모니터링 | 문제 조기 발견 | MTTR (평균 복구 시간) | 단기 (1달) |
| Walk-Forward 백테스트 | 실전 괴리 -50% | 백테스트 vs 실전 차이 | 단기 (1달) |

---

## 📈 내일(2025-12-10) 전략 요약 (v3.1 적용)

### 목표
- **수익률: 2.5%** (변동성 손절 적용으로 목표 상향)

### 핵심 변경 (v3.1 기능 적용)
- 손절 전략: **고정 -2% → 변동성 기반 동적 손절**
- 모니터링: **Telegram 알림 → Grafana 대시보드 + Telegram**
- AI 비용: **캐싱 레이어 적용으로 API 호출 최소화**

### 전략
- **매수**: 피라미딩 3단계 (30% → 50% → 20%)
- **매도**: 분할매도 3단계 (+3% → +5% → +8%)
- **손절**: 변동성 기반 (삼성전자: -2.5%, 테슬라: -6.8%, 중소형주: -9.2%)

---

## 🤖 AI 모델 활용 (v3.1 개선)

### 3-Layer 분석 (캐싱 적용)
1. **캐시 우선 확인** → 히트 시 즉시 반환
2. **Flash** (gemini-2.0-flash): 빠른 데이터 분석 (캐시 미스 시)
3. **Pro** (gemini-2.5-pro): 패턴 분석 및 전략 조정
4. **Opus** (claude-opus-4): 최종 전략 검증 (조건부)

### AI 캐싱 규칙
- TTL: 60분
- 캐시 키: 종목코드 + 분석유형 + 파라미터 해시
- 히트율 목표: 60% 이상

---

## 🎯 실행 우선순위

### Phase 1: 즉시 적용 (1-2주)
1. ✅ **AI 캐싱 레이어** - `brain/ai_cache.py` 구현
2. ✅ **변동성 기반 손절** - `brain/risk_manager.py` 구현

### Phase 2: 단기 적용 (1개월)
3. ✅ **Grafana 모니터링** - Docker Compose 구성
4. ✅ **Walk-Forward 백테스트** - `backtester/walk_forward.py` 구현

### Phase 3: 중기 계획 (3개월)
5. ⏳ **실시간 웹소켓 시세** (KIS API WebSocket)
6. ⏳ **멀티 계좌 지원** (가족 계좌 등)

---

## 📝 참고 문서

- [IMPROVEMENT_PLAN.md](./IMPROVEMENT_PLAN.md) - DeepSeek R1 전체 분석 결과
- [CORE_PHILOSOPHY.md](./CORE_PHILOSOPHY.md) - 시스템 설계 철학 (v3.1 업데이트)
- [DATABASE_DESIGN.md](./DATABASE_DESIGN.md) - DB 스키마 v3.2
- [PYRAMIDING_STRATEGY.md](./PYRAMIDING_STRATEGY.md) - 피라미딩 전략 (변동성 손절 통합)

---

**작성일**: 2025-12-09
**버전**: 3.1 (DeepSeek Enhanced)
**분석 모델**: DeepSeek R1 (Reasoner)
**프로젝트**: AEGIS
**핵심 개선**: AI 캐싱 + Grafana + 변동성 손절 + Walk-Forward 백테스트
