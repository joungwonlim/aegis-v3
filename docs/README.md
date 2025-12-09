# AEGIS v3.0 Documentation Index

> **개발 설계 문서 통합 인덱스**

---

## 📚 문서 목록

### 🎯 핵심 문서 (필독)

| 문서 | 설명 | 대상 |
|-----|------|------|
| [IMPROVEMENT_PLAN.md](./IMPROVEMENT_PLAN.md) | 🆕 **시스템 개선 계획 (DeepSeek R1 분석)** | 전체 팀 |
| [CORE_PHILOSOPHY.md](./CORE_PHILOSOPHY.md) | 핵심 철학 및 AI 모델 전략 | 전체 팀 |
| [BRAIN_SIMPLE.md](./BRAIN_SIMPLE.md) | Brain 의사결정 시스템 | 개발자 |
| [PYRAMIDING_STRATEGY.md](./PYRAMIDING_STRATEGY.md) | 피라미딩 + 분할매도 전략 | 개발자 |
| [TRADING_TECHNIQUES.md](./TRADING_TECHNIQUES.md) | 고급 매매 기법 (DCA, Grid, Kelly) | 개발자 |
| [MICRO_OPTIMIZATION.md](./MICRO_OPTIMIZATION.md) | 미세 최적화 (0.001%를 만드는 디테일) | 개발자 |
| [BACKEND_MICRO_OPT.md](./BACKEND_MICRO_OPT.md) | 백엔드 최적화 (학습 + SAFE MODE) | 개발자 |

### 🏗️ 아키텍처

| 문서 | 설명 |
|-----|------|
| [DEVELOPMENT_PLAN.md](./DEVELOPMENT_PLAN.md) | v3.0 전환 계획 (FastAPI + Next.js) |
| [PHASED_DEVELOPMENT.md](./PHASED_DEVELOPMENT.md) | **단계별 개발 (Backend 먼저!)** |
| [COMBAT_ARCHITECTURE.md](./COMBAT_ARCHITECTURE.md) | 실전 아키텍처 |
| [DATA_FLOW.md](./DATA_FLOW.md) | 데이터 흐름 상세 |

### 💾 데이터베이스

| 문서 | 설명 |
|-----|------|
| [DATABASE_DESIGN.md](./DATABASE_DESIGN.md) | DB 스키마 설계 |
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

## 🚀 읽기 순서 (역할별)

### 새 개발자
```
1. CORE_PHILOSOPHY.md       ← 시스템 이해
2. BRAIN_SIMPLE.md           ← 의사결정 로직
3. PYRAMIDING_STRATEGY.md    ← 핵심 전략
4. DATABASE_DESIGN.md        ← DB 구조
5. DEVELOPMENT_PLAN.md       ← v3.0 로드맵
```

### PM / 전략가
```
1. CORE_PHILOSOPHY.md        ← 철학
2. PYRAMIDING_STRATEGY.md     ← 매매 전략
3. BACKTESTER_SIMPLE.md      ← 성과 검증
4. SAFETY_SYSTEM.md          ← 리스크 관리
```

### DevOps
```
1. DEVELOPMENT_PLAN.md       ← 기술 스택
2. SCHEDULER_DESIGN.md       ← 스케줄러
3. KIS_API_SPECIFICATION.md  ← API 연동
```

---

## 🆕 최근 업데이트 (2025-12-08)

### 추가된 문서
- ✅ **PYRAMIDING_STRATEGY.md**: 피라미딩 + 분할매도 완전 가이드
- ✅ **AI Visualizer** (ai-visualizer/ 폴더): 10개 문서

### 업데이트된 문서
- ✅ **BRAIN_SIMPLE.md**: Section 5 피라미딩 + 분할매도 추가
- ✅ **내일 전략**: `data/tomorrow_strategy.json` (목표 2%)

---

## 📊 내일(2025-12-09) 전략 요약

### 목표
- **수익률: 2.0%** (오늘 미달성 1% + 내일 1%)

### 핵심 변경
- 매수 점수: **60 → 65점** (더 엄격)
- 집중 섹터: **반도체, 자동차**
- 회피 섹터: **해운, 가전**

### 전략
- **매수**: 피라미딩 3단계 (30% → 50% → 20%)
- **매도**: 분할매도 3단계 (+3% → +5% → +8%)
- **손절**: -2.0% 엄격 적용

---

## 🤖 AI 모델 활용

### 3-Layer 분석
1. **Flash** (gemini-2.0-flash): 빠른 데이터 분석
2. **Pro** (gemini-2.5-pro): 패턴 분석 및 전략 조정
3. **Opus** (claude-opus-4): 최종 전략 검증 (조건부)

---

**작성일**: 2025-12-08
**버전**: 3.0
**프로젝트**: AEGIS
