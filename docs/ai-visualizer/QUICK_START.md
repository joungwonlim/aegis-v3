# ⚡ Quick Start - 5분 안에 시작하기

> **Claude Sonnet이 5분 안에 프로젝트를 시작할 수 있는 초간단 가이드**

---

## 🎯 목표

5분 안에:
- ✅ 프로젝트 생성
- ✅ Docker 실행
- ✅ 접속 확인

---

## 1️⃣ 프로젝트 생성 (1분)

```bash
# 스크립트 실행
bash ~/Dev/aegis/v2/docs/dev3/ai-visualizer/create_project.sh

# 완료 메시지 대기
# ✅ 프로젝트 생성 완료!
```

## 2️⃣ Docker 실행 (2분)

```bash
# 프로젝트로 이동
cd ~/Dev/aegis-visualizer

# Docker Compose 실행
docker-compose up -d

# 컨테이너 확인
docker-compose ps

# 모두 "Up" 상태 확인
```

## 3️⃣ 접속 테스트 (2분)

### Backend 테스트
```bash
curl http://localhost:8001/health
# 응답: {"status":"healthy"}
```

### Frontend 테스트
```bash
# 브라우저 열기
open http://localhost:5174
# "🚀 AEGIS Visualizer" 보이면 성공!
```

### API 문서 확인
```bash
# 브라우저에서
open http://localhost:8001/docs
# Swagger UI 보이면 성공!
```

---

## ✅ 완료!

모든 접속이 성공했다면, 이제 개발을 시작할 수 있습니다!

---

## 📚 다음 단계

### Sonnet에게 요청하세요:

```
"SONNET_DEV_GUIDE.md를 읽고 Phase 2부터 시작해줘"
```

또는

```
"DATABASE_SCHEMA.md를 읽고 database를 만들어줘"
```

---

## 🐛 문제 발생 시

### 컨테이너가 시작 안 됨
```bash
docker-compose down -v
docker-compose up -d --build
```

### Port 충돌
```bash
# 다른 프로그램이 포트 사용 중인지 확인
lsof -i :8001  # Backend
lsof -i :5174  # Frontend
lsof -i :5433  # Database
```

### 로그 확인
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

---

**소요 시간**: 약 5분
**난이도**: ⭐☆☆☆☆ (매우 쉬움)
