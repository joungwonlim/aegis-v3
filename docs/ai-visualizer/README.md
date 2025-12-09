# AI Reasoning Visualizer - Documentation

> **프레젠테이션 퀄리티의 AI 추론 과정 시각화 시스템 - 완전 설계 문서**

## 🎯 프로젝트 개요

AEGIS v3.0의 AI 추론 과정(2,500종목 → 3종목)을 **인간이 인지 가능한 수준**으로 시각화하는 시스템입니다.

### 핵심 가치

- ✅ **투명성**: AI 의사결정 과정 완전 공개
- ✅ **신뢰성**: 글로벌 데이터 흐름 추적 가능
- ✅ **교육성**: 투자 논리 학습 지원
- ✅ **프레젠테이션**: 데모 및 홍보 활용

---

## 📚 문서 구조

이 문서는 **6개의 독립적이면서도 연결된** 설계 문서로 구성되어 있습니다.

### 1. [AI_VISUALIZER_SPEC.md](./AI_VISUALIZER_SPEC.md) ⭐ **시작점**

**전체 시스템 개요 및 아키텍처**

- 시스템 목적 및 범위
- 고수준 아키텍처
- 데이터 흐름
- 개발 단계 계획

**읽어야 할 사람**: 전체 팀 (PM, 개발자, 디자이너)

---

### 2. [TECH_STACK.md](./TECH_STACK.md) 🛠️ **기술 스택**

**반응형 + 고성능을 위한 기술 선택**

- 프론트엔드: React + TypeScript + Vite
- 시각화: Three.js + Konva + Framer Motion
- 백엔드: FastAPI + PostgreSQL
- 성능 최적화: Web Worker + Offscreen Canvas
- **실제 코드 예제 포함**

**읽어야 할 사람**: 프론트엔드 & 백엔드 개발자

**주요 내용**:
```typescript
// 반응형 설계
useBreakpoint() → mobile/tablet/desktop 분기

// Web Worker (파티클 계산)
particle.worker.ts → 물리 연산 오프로드

// React Query (데이터 페칭)
useVisualizerData() → 실시간 폴링 + 캐싱
```

---

### 3. [CONTROL_SYSTEM.md](./CONTROL_SYSTEM.md) 🎛️ **관제 시스템**

**백엔드 핸들링 가능한 관제 대시보드**

- 실시간 배치 모니터링
- 성능 지표 추적
- 수동 제어 (시작/중지/재시작)
- 히스토리 분석
- **FastAPI 엔드포인트 코드 포함**

**읽어야 할 사람**: 백엔드 개발자, DevOps

**주요 내용**:
```python
# REST API
POST /api/control/batch/start → 새 배치 시작
POST /api/control/batch/{id}/stop → 배치 중지
GET /api/control/metrics → 성능 메트릭

# WebSocket
WS /control/{batch_id} → 실시간 이벤트 스트리밍
```

---

### 4. [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) 🗄️ **데이터베이스**

**AI 시각화를 위한 DB 설계**

- 8개 테이블 구조
- 관계 다이어그램
- 인덱스 전략
- Alembic 마이그레이션 스크립트
- **SQLAlchemy 모델 코드 포함**

**읽어야 할 사람**: 백엔드 개발자, DBA

**핵심 테이블**:
```sql
analysis_batches       → 배치 실행 단위
signal_sources         → 글로벌 데이터 소스 (마스터)
signal_logs            → 수집된 신호
analysis_steps         → 단계별 진행 (FETCH, FLASH, PRO)
analysis_stocks        → 종목별 상세
signal_stock_impacts   → 신호 → 종목 영향 매핑
control_events         → 제어 이벤트 로그
performance_metrics    → 성능 메트릭
```

---

### 5. [ANIMATION_SPEC.md](./ANIMATION_SPEC.md) 🎬 **애니메이션**

**프레젠테이션 퀄리티 애니메이션 설계**

- 15초 타임라인 (Phase 0~5)
- 레이어 구조 (Z-Index)
- 파티클 시스템 (물리 엔진)
- 성능 최적화 전략
- **React + Konva + Framer Motion 코드 포함**

**읽어야 할 사람**: 프론트엔드 개발자, 디자이너

**타임라인 요약**:
```
0:00~0:02  Phase 0: 초기화 (지구본 페이드인)
0:02~0:05  Phase 1: 데이터 수집 (파티클 발사)
0:05~0:08  Phase 2: 신호 융합 (Brain으로 수렴)
0:08~0:10  Phase 3: Flash Filter (2500 → 50)
0:10~0:13  Phase 4: Pro Reasoning (50 → 3)
0:13~0:15  Phase 5: 결과 발표 (카드 팝업)
```

---

## 🚀 빠른 시작

### 🎯 Sonnet을 위한 개발 플로우

```
START → QUICK_START.md (5분)
         ↓
         프로젝트 생성 완료
         ↓
      SONNET_DEV_GUIDE.md 읽기
         ↓
    ┌────┴────────────────────┐
    │                         │
Phase 2: Database        Phase 3: Backend API
    │                         │
    ├── DATABASE_SCHEMA.md    ├── CONTROL_SYSTEM.md
    ├── Alembic 실행          ├── API 구현
    └── 테이블 생성           └── WebSocket 구현
         │                         │
         └────┬────────────────────┘
              ↓
        Phase 4: Frontend
              │
              ├── TECH_STACK.md
              ├── React 기본
              └── API 연동
              ↓
        Phase 5: 시각화
              │
              ├── ANIMATION_SPEC.md
              ├── 파티클 시스템
              └── Three.js 배경
              ↓
            DONE!
```

### 📖 첫 개발 세션 시작

**Sonnet에게 이렇게 요청하세요:**

```
"QUICK_START.md를 읽고 프로젝트를 시작해줘"
```

### 1. 문서 읽기 순서 (역할별)

#### 프로젝트 매니저
```
1. AI_VISUALIZER_SPEC.md (전체 이해)
2. ANIMATION_SPEC.md (데모 시나리오)
3. CONTROL_SYSTEM.md (관리 기능)
```

#### 프론트엔드 개발자
```
1. AI_VISUALIZER_SPEC.md (전체 이해)
2. TECH_STACK.md (기술 스택)
3. ANIMATION_SPEC.md (애니메이션 구현)
→ 코드 예제 복사 → 수정 → 테스트
```

#### 백엔드 개발자
```
1. AI_VISUALIZER_SPEC.md (전체 이해)
2. DATABASE_SCHEMA.md (DB 설계)
3. CONTROL_SYSTEM.md (API 구현)
→ Alembic 마이그레이션 실행 → API 개발
```

#### DevOps
```
1. AI_VISUALIZER_SPEC.md (전체 이해)
2. TECH_STACK.md (인프라 요구사항)
3. CONTROL_SYSTEM.md (모니터링)
```

---

### 2. 개발 환경 설정

#### 프론트엔드
```bash
# 프로젝트 루트에서
cd frontend  # (또는 해당 디렉토리)

# 패키지 설치
pnpm install

# 필요한 패키지 추가
pnpm add @react-three/fiber @react-three/drei three
pnpm add react-konva konva
pnpm add framer-motion
pnpm add @tanstack/react-query axios socket.io-client

# 개발 서버 실행
pnpm dev
```

#### 백엔드
```bash
# 가상환경 활성화
source venv/bin/activate

# 마이그레이션 실행
alembic upgrade head

# 초기 데이터 입력 (signal_sources)
python scripts/seed_signal_sources.py

# 개발 서버 실행
uvicorn src.main:app --reload
```

---

### 3. 개발 단계

#### Phase 1: 데이터베이스 및 백엔드 (1주)
- [ ] DB 스키마 생성 (Alembic)
- [ ] Fetcher 수정 (signal_logs 저장)
- [ ] Brain 수정 (단계별 로그)
- [ ] REST API 구현
- [ ] WebSocket 스트리밍

**참고 문서**: [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md), [CONTROL_SYSTEM.md](./CONTROL_SYSTEM.md)

#### Phase 2: 시각화 기본 (1주)
- [ ] Canvas 파티클 시스템
- [ ] 기본 애니메이션 구현
- [ ] 실시간 데이터 연동
- [ ] 반응형 레이아웃

**참고 문서**: [TECH_STACK.md](./TECH_STACK.md), [ANIMATION_SPEC.md](./ANIMATION_SPEC.md)

#### Phase 3: 고급 기능 (1주)
- [ ] Three.js 3D 배경
- [ ] 히스토리 재생
- [ ] 관제 시스템
- [ ] 성능 최적화

**참고 문서**: 모든 문서

#### Phase 4: 테스트 및 개선 (1주)
- [ ] 모바일 테스트
- [ ] 성능 프로파일링
- [ ] UX 개선
- [ ] 문서화 완료

---

## 📊 성능 목표

| 항목 | 목표 | 측정 방법 |
|-----|------|---------|
| 애니메이션 FPS | 60 FPS (데스크톱) | Chrome DevTools Performance |
| 모바일 FPS | 30+ FPS | 실제 기기 테스트 |
| WebSocket 지연 | < 50ms | Network 탭 |
| DB 쿼리 | < 100ms | PostgreSQL EXPLAIN ANALYZE |
| 페이지 로드 | < 2초 | Lighthouse |

---

## 🎨 디자인 시스템

### 색상 팔레트

```css
/* 신호 감성 */
--color-positive: #00ff88;   /* 밝은 초록 */
--color-negative: #ff4444;   /* 밝은 빨강 */
--color-neutral: #cccccc;    /* 회색 */

/* Brain */
--color-brain-core: #00ffff; /* Cyan */
--color-brain-glow: rgba(0, 255, 255, 0.8);

/* UI */
--color-background: #000000; /* 검정 */
--color-card: #1a1a1a;       /* 다크 그레이 */
--color-border: #00ffff;     /* Cyan */
```

### 아이콘 (Emoji)

```
🇺🇸 미국    🇪🇺 유럽    🇯🇵 일본    🇨🇳 중국
🥇 금      🛢️ 원유     🔶 구리     📈 주식
```

---

## 🐛 트러블슈팅

### 자주 발생하는 문제

#### 1. 파티클 애니메이션이 느려요
```typescript
// 해결: 파티클 수 줄이기
const particleCount = useAdaptiveParticleCount(2500);
// FPS < 30 → 자동으로 파티클 수 감소
```

#### 2. WebSocket 연결이 끊겨요
```typescript
// 해결: 재연결 로직 확인
socket.on('disconnect', (reason) => {
  if (reason === 'io server disconnect') {
    socket.connect(); // 수동 재연결
  }
});
```

#### 3. DB 쿼리가 느려요
```sql
-- 해결: 인덱스 확인
EXPLAIN ANALYZE SELECT * FROM signal_logs WHERE batch_id = '...';
-- INDEX SCAN이 아니면 인덱스 추가 필요
```

---

## 📝 체크리스트

### 개발 전
- [ ] 모든 문서를 읽었나요?
- [ ] 팀과 아키텍처를 논의했나요?
- [ ] 개발 환경이 설정되었나요?

### 개발 중
- [ ] 코드 예제를 참고하고 있나요?
- [ ] 성능을 측정하고 있나요?
- [ ] Git commit을 자주 하고 있나요?

### 개발 후
- [ ] 모든 디바이스에서 테스트했나요?
- [ ] 성능 목표를 달성했나요?
- [ ] 문서를 업데이트했나요?

---

## 🤝 기여 가이드

### 문서 수정
```bash
# 오타 수정, 내용 추가, 코드 예제 개선 등
1. 해당 .md 파일 수정
2. Git commit
3. Pull Request
```

### 코드 예제 추가
```bash
# 새로운 코드 예제를 추가할 때
1. 해당 문서에 코드 블록 추가
2. 주석으로 설명 추가
3. 실제 동작 확인 후 commit
```

---

## 📞 연락처

- **작성자**: wonny
- **작성일**: 2025-12-08
- **버전**: 1.0.0
- **프로젝트**: AEGIS v3.0

---

## 🎉 마무리

이 문서들은 **AI 추론 시각화 시스템의 완전한 설계**를 담고 있습니다.

각 문서는 **독립적으로 읽을 수 있지만**, 전체를 함께 읽으면 시스템의 **전체 그림**을 이해할 수 있습니다.

**Happy Coding! 🚀**

---

## 📚 문서 인덱스 (빠른 참조)

| 문서 | 핵심 내용 | 대상 |
|-----|---------|------|
| [AI_VISUALIZER_SPEC.md](./AI_VISUALIZER_SPEC.md) | 전체 개요 | 전체 팀 |
| [TECH_STACK.md](./TECH_STACK.md) | 기술 스택 + 코드 | Frontend |
| [CONTROL_SYSTEM.md](./CONTROL_SYSTEM.md) | 관제 시스템 + API | Backend |
| [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) | DB 설계 + 마이그레이션 | Backend |
| [ANIMATION_SPEC.md](./ANIMATION_SPEC.md) | 애니메이션 + 타임라인 | Frontend |
