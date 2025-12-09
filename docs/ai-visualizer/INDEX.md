# 📚 AI Visualizer 문서 인덱스

> **모든 문서를 한눈에 - Sonnet을 위한 내비게이션**

---

## 🗺️ 문서 맵

```
ai-visualizer/
├── 📖 시작 문서
│   ├── README.md              ← 전체 개요
│   ├── QUICK_START.md         ← 5분 시작 가이드 ⭐
│   └── SONNET_DEV_GUIDE.md    ← Sonnet 개발 가이드 ⭐⭐⭐
│
├── 🏗️ 설계 문서
│   ├── AI_VISUALIZER_SPEC.md  ← 시스템 아키텍처
│   ├── TECH_STACK.md          ← 기술 스택 + 코드
│   └── PROJECT_SETUP.md       ← 프로젝트 생성 가이드
│
├── 💻 개발 문서
│   ├── DATABASE_SCHEMA.md     ← DB 설계 (Phase 2)
│   ├── CONTROL_SYSTEM.md      ← Backend API (Phase 3)
│   └── ANIMATION_SPEC.md      ← 시각화 (Phase 5)
│
└── 🛠️ 도구
    └── create_project.sh      ← 자동 생성 스크립트
```

---

## 🚀 시작하기

### Sonnet 첫 세션

```bash
# Step 1: 시작 가이드 읽기
"QUICK_START.md를 읽고 프로젝트를 시작해줘"

# Step 2: 개발 가이드 읽기
"SONNET_DEV_GUIDE.md를 읽고 Phase 2부터 진행해줘"
```

---

## 📋 문서별 상세 정보

### 1. README.md (9KB)
- **용도**: 전체 프로젝트 소개
- **대상**: 전체 팀
- **읽는 시점**: 프로젝트 시작 전
- **핵심 내용**:
  - 프로젝트 개요
  - 문서 구조
  - 성능 목표
  - 디자인 시스템

### 2. QUICK_START.md (3KB) ⚡
- **용도**: 5분 빠른 시작
- **대상**: Sonnet
- **읽는 시점**: 개발 시작 전
- **핵심 내용**:
  - 프로젝트 생성 (1분)
  - Docker 실행 (2분)
  - 접속 테스트 (2분)

### 3. SONNET_DEV_GUIDE.md (36KB) ⭐⭐⭐
- **용도**: Sonnet 전용 개발 가이드
- **대상**: Sonnet
- **읽는 시점**: 개발 시작 시
- **핵심 내용**:
  - Phase 1~5 단계별 가이드
  - 실행 가능한 코드 예제
  - 체크리스트
  - 트러블슈팅

**Phase 구성:**
```
Phase 1: 프로젝트 생성
Phase 2: Database 개발      → DATABASE_SCHEMA.md 참조
Phase 3: Backend API 개발    → CONTROL_SYSTEM.md 참조
Phase 4: Frontend 기본 개발  → TECH_STACK.md 참조
Phase 5: 시각화 구현         → ANIMATION_SPEC.md 참조
```

### 4. AI_VISUALIZER_SPEC.md (16KB)
- **용도**: 시스템 전체 아키텍처
- **대상**: 전체 팀
- **읽는 시점**: 설계 이해 필요 시
- **핵심 내용**:
  - 시스템 목적 및 범위
  - 5-Layer 아키텍처
  - 데이터 흐름
  - 개발 단계 계획

### 5. DATABASE_SCHEMA.md (28KB)
- **용도**: DB 설계 및 구현
- **대상**: Sonnet (Phase 2)
- **읽는 시점**: Database 개발 시
- **핵심 내용**:
  - 8개 테이블 정의
  - 관계 다이어그램
  - Alembic 마이그레이션 스크립트
  - SQLAlchemy 모델 코드

**포함된 코드:**
- ✅ CREATE TABLE 스크립트 (8개)
- ✅ 인덱스 생성 스크립트
- ✅ Alembic 마이그레이션 파일
- ✅ SQLAlchemy 모델 클래스

### 6. CONTROL_SYSTEM.md (28KB)
- **용도**: Backend API 설계 및 구현
- **대상**: Sonnet (Phase 3)
- **읽는 시점**: Backend 개발 시
- **핵심 내용**:
  - FastAPI 엔드포인트
  - WebSocket 구현
  - 관제 대시보드
  - 성능 모니터링

**포함된 코드:**
- ✅ FastAPI 라우터 (control.py)
- ✅ WebSocket 핸들러
- ✅ BatchExecutor 클래스
- ✅ React 관제 컴포넌트

### 7. TECH_STACK.md (20KB)
- **용도**: 기술 스택 및 Frontend 기본
- **대상**: Sonnet (Phase 4)
- **읽는 시점**: Frontend 개발 시
- **핵심 내용**:
  - React + TypeScript 설정
  - 반응형 설계
  - 성능 최적화
  - Web Worker

**포함된 코드:**
- ✅ useBreakpoint() 훅
- ✅ React Query 설정
- ✅ WebSocket 연동
- ✅ API 클라이언트

### 8. ANIMATION_SPEC.md (31KB)
- **용도**: 시각화 및 애니메이션 구현
- **대상**: Sonnet (Phase 5)
- **읽는 시점**: 시각화 개발 시
- **핵심 내용**:
  - 15초 애니메이션 타임라인
  - 파티클 시스템
  - Three.js 3D 배경
  - Framer Motion

**포함된 코드:**
- ✅ ParticleSystem 컴포넌트
- ✅ Web Worker (물리 계산)
- ✅ Globe3D 컴포넌트
- ✅ BrainCore 애니메이션

### 9. PROJECT_SETUP.md (15KB)
- **용도**: 수동 프로젝트 생성 가이드
- **대상**: 개발자
- **읽는 시점**: 자동 스크립트 사용 불가 시
- **핵심 내용**:
  - Backend 디렉토리 구조
  - Frontend 디렉토리 구조
  - Docker Compose 설정
  - 환경 변수 설정

---

## 🎯 개발 순서 (추천)

### 1차: 프로젝트 생성 (5분)
```
QUICK_START.md 읽기
→ create_project.sh 실행
→ Docker 실행
→ 접속 확인
```

### 2차: Database (30분)
```
SONNET_DEV_GUIDE.md (Phase 2)
→ DATABASE_SCHEMA.md 참조
→ Alembic 마이그레이션
→ 테이블 생성
```

### 3차: Backend API (1시간)
```
SONNET_DEV_GUIDE.md (Phase 3)
→ CONTROL_SYSTEM.md 참조
→ FastAPI 엔드포인트 구현
→ 테스트
```

### 4차: Frontend 기본 (1시간)
```
SONNET_DEV_GUIDE.md (Phase 4)
→ TECH_STACK.md 참조
→ React 컴포넌트 구현
→ API 연동
```

### 5차: 시각화 (2시간)
```
SONNET_DEV_GUIDE.md (Phase 5)
→ ANIMATION_SPEC.md 참조
→ 파티클 시스템 구현
→ 애니메이션 최적화
```

**총 예상 시간**: 약 4.5시간

---

## 🔍 문서 검색 가이드

### Database 관련
- 테이블 구조: **DATABASE_SCHEMA.md** (Section 2)
- 마이그레이션: **DATABASE_SCHEMA.md** (Section 5)
- 모델 클래스: **DATABASE_SCHEMA.md** (마지막 섹션)

### API 관련
- REST API: **CONTROL_SYSTEM.md** (Section 3.1)
- WebSocket: **CONTROL_SYSTEM.md** (Section 3.2)
- 엔드포인트 목록: **CONTROL_SYSTEM.md** (맨 위)

### Frontend 관련
- React 설정: **TECH_STACK.md** (Section 2)
- 반응형: **TECH_STACK.md** (Section 4)
- API 클라이언트: **TECH_STACK.md** (코드 예제 3)

### 시각화 관련
- 타임라인: **ANIMATION_SPEC.md** (Section 2)
- 파티클 시스템: **ANIMATION_SPEC.md** (Section 4)
- Three.js: **ANIMATION_SPEC.md** (코드 예제 2)

---

## 💡 Sonnet 사용 팁

### 효율적인 질문 방법

#### ❌ 나쁜 예
```
"AI Visualizer를 만들어줘"
```
→ 너무 광범위함

#### ✅ 좋은 예
```
"QUICK_START.md를 읽고 프로젝트를 시작해줘"
```
→ 명확한 문서 지정

#### ✅ 더 좋은 예
```
"SONNET_DEV_GUIDE.md의 Phase 2를 읽고,
DATABASE_SCHEMA.md를 참조해서 database를 만들어줘"
```
→ Phase + 참조 문서 명시

### 단계별 요청

```
# 1단계
"QUICK_START.md를 읽고 프로젝트를 생성해줘"

# 2단계 (1단계 완료 후)
"SONNET_DEV_GUIDE.md의 Phase 2만 읽고 실행해줘"

# 3단계 (2단계 완료 후)
"SONNET_DEV_GUIDE.md의 Phase 3만 읽고 실행해줘"

# ... 반복
```

---

## 📊 문서 의존성

```
QUICK_START.md
    ↓
SONNET_DEV_GUIDE.md
    ├─→ DATABASE_SCHEMA.md (Phase 2)
    ├─→ CONTROL_SYSTEM.md (Phase 3)
    ├─→ TECH_STACK.md (Phase 4)
    └─→ ANIMATION_SPEC.md (Phase 5)

AI_VISUALIZER_SPEC.md (독립적, 설계 이해용)
PROJECT_SETUP.md (독립적, 수동 생성용)
```

---

## ✅ 완료 확인 체크리스트

각 Phase 완료 후 확인:

### Phase 1 완료
- [ ] `docker-compose ps` 모두 Up
- [ ] http://localhost:8001/health 응답
- [ ] http://localhost:5174 화면 보임

### Phase 2 완료
- [ ] `\dt` 명령으로 8개 테이블 확인
- [ ] signal_sources에 8개 데이터 확인

### Phase 3 완료
- [ ] `/api/control/batches` 동작
- [ ] POST `/batch/start` 동작
- [ ] Swagger UI에서 테스트 가능

### Phase 4 완료
- [ ] Frontend에 배치 목록 표시
- [ ] "새 배치 시작" 버튼 동작
- [ ] API 연동 확인

### Phase 5 완료
- [ ] 파티클 애니메이션 동작
- [ ] 60 FPS 유지
- [ ] 반응형 동작 확인

---

**작성일**: 2025-12-08
**작성자**: wonny
**버전**: 1.0.0

**이 문서는 모든 문서의 내비게이션 허브입니다.** 📚
