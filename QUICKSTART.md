# AEGIS v3.0 - Quick Start Guide

## 🚀 5분 안에 시작하기

### Step 1: 환경 설정 (1분)

```bash
# .env 파일 생성 및 편집
cp .env.example .env

# 필수 항목 입력
# - KIS_APP_KEY
# - KIS_APP_SECRET
# - KIS_ACCOUNT_NUMBER
# - ANTHROPIC_API_KEY
# - DEEPSEEK_API_KEY
```

### Step 2: 데이터베이스 시작 (1분)

```bash
# Docker로 PostgreSQL + TimescaleDB 실행
docker-compose up -d

# 데이터베이스 초기화
python scripts/setup.py
```

### Step 3: FastAPI 서버 실행 (1분)

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# 서버 실행
uvicorn app.main:app --reload
```

### Step 4: Swagger UI 접속 (1분)

```
http://localhost:8000/docs
```

**테스트 API:**
- `GET /health` - 시스템 상태 체크
- `GET /ping` - 간단한 핑
- `GET /api/portfolio` - 보유 종목 조회

### Step 5: 스케줄러 실행 (선택)

```bash
# 자동매매 시작
python -m scheduler.main_scheduler
```

---

## 🎯 빠른 테스트

### 1. Health Check

```bash
curl http://localhost:8000/health
```

### 2. Portfolio 조회

```bash
curl http://localhost:8000/api/portfolio
```

### 3. 오늘 거래 내역

```bash
curl http://localhost:8000/api/trades/today
```

---

## 📚 다음 단계

1. **v2에서 Fetcher 마이그레이션**
   - pykrx 데이터 수집
   - yfinance 매크로 지표
   - DART 공시 크롤링

2. **Brain 모듈 확장**
   - DeepSeek-V3 실시간 분석
   - DeepSeek-R1 심층 분석
   - Quant Score 계산 로직

3. **KIS WebSocket 실전 연동**
   - 실시간 시세 수신
   - 체결 통보 처리
   - 호가 데이터 분석

4. **Safety System 강화**
   - Circuit Breaker 구현
   - 손절/익절 자동화
   - Risk Management

---

## ⚠️ 문제 해결

### Docker 시작 실패

```bash
# Docker daemon 확인
docker ps

# 포트 충돌 확인
lsof -i :5432

# 재시작
docker-compose down
docker-compose up -d
```

### FastAPI 임포트 에러

```bash
# 가상환경 재생성
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### DB 연결 실패

```bash
# .env 확인
cat .env | grep DATABASE_URL

# DB 상태 확인
docker-compose logs db
```

---

**버전**: 3.0.0
**최종 업데이트**: 2025-12-09
