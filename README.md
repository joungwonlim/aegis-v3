# AEGIS v3.0 - Backend

AI-Powered Automated Trading System for Korean Stock Market

## 프로젝트 구조

```
v3/
├── app/                    # FastAPI 애플리케이션
│   ├── main.py            # 앱 엔트리포인트
│   ├── config.py          # 설정
│   ├── database.py        # DB 연결
│   ├── models/            # SQLAlchemy 모델 (6 schemas)
│   ├── routers/           # API 라우터
│   └── schemas/           # Pydantic 스키마
├── brain/                 # AI 의사결정 모듈
│   └── commander.py       # Opus/Sonnet 지휘관
├── fetchers/              # 데이터 수집
│   └── kis_client.py      # KIS WebSocket/REST
├── scheduler/             # 자동매매 스케줄러
│   └── main_scheduler.py
├── docs/                  # 설계 문서
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## 시작하기

### 1. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (API 키 입력)
```

### 2. 데이터베이스 시작

```bash
# Docker로 PostgreSQL + TimescaleDB 실행
docker-compose up -d

# 데이터베이스 생성 확인
docker-compose ps
```

### 3. Python 환경 설정

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 패키지 설치
pip install -r requirements.txt
```

### 4. 데이터베이스 초기화

```bash
# 테이블 생성
alembic upgrade head

# 또는 Python에서
python -c "from app.database import init_db; init_db()"
```

### 5. FastAPI 서버 실행

```bash
# 개발 모드 (Hot Reload)
uvicorn app.main:app --reload --port 8000

# 프로덕션 모드
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. Swagger UI 접속

```
http://localhost:8000/docs
```

## API 엔드포인트

### Health Check
- `GET /health` - 시스템 상태 체크
- `GET /ping` - 간단한 핑 체크

### Portfolio
- `GET /api/portfolio` - 보유 종목 조회
- `GET /api/portfolio/{stock_code}` - 개별 포지션 조회

### Trades
- `GET /api/trades/today` - 오늘 거래 내역
- `GET /api/trades` - 거래 내역 (페이지네이션)
- `GET /api/trades/{trade_id}` - 거래 상세 조회

### Analysis
- `GET /api/analysis/picks` - AI 추천 종목
- `GET /api/analysis/stock/{stock_code}` - 종목 분석
- `POST /api/analysis/execute` - 분석 수동 실행

## 📊 Watch Dashboard (Real-time Monitoring)

### Rich UI Dashboard (권장)

```bash
# 일회성 실행
python monitoring/watch_dashboard_rich.py

# Auto-refresh (3초마다 갱신)
./watch.sh
```

**Features:**
- 📊 포트폴리오 현황 + 목표 수익률 달성도 그래프
- 📈 보유 종목 + 수익률 막대 그래프
- 🎯 Recent Signals (최근 5개)
- ⏰ Upcoming Schedule
- 🔄 Running Processes
- 💰 Recent Trades
- 🧠 Sonnet Commander Decisions
- ⚙️ System Status

상세: [monitoring/README.md](monitoring/README.md)

## 스케줄러 실행

```bash
python -m scheduler.main_scheduler
```

### 스케줄러 작업 목록

| 시간 | 작업 | 설명 |
|------|------|------|
| 06:00 | US 시장 데이터 | NASDAQ, SOX, VIX 수집 |
| 07:00 | KRX 데이터 | 수급 데이터 수집 |
| 07:20 | Brain 분석 | DeepSeek-R1 심층 분석 |
| 08:00 | Opus 브리핑 | Claude Opus 오늘 전략 |
| 09:00-15:30 | 자동매매 | 30초마다 실행 |
| 16:00 | 일일 정산 | 거래 피드백 반영 |

## Brain Commander

### ⚠️ Commander Model: Sonnet 4.5

**중요**: Commander는 **Opus가 아닌 Sonnet 4.5** 사용!

```python
from commander.sonnet_commander import SonnetCommander

# Sonnet 4.5 Commander 초기화
commander = SonnetCommander()

# Model ID: "claude-sonnet-4-20250514"
# 이유: Cost-effective + Fast response (<3s)

decisions = commander.monitor_and_decide()
```

## KIS API

### WebSocket (실시간)

```python
from fetchers.kis_client import kis_client

# 실시간 시세 구독
await kis_client.connect_websocket()
await kis_client.subscribe_realtime_price("005930")

# 데이터 수신
async def handle_data(data):
    print(data)

await kis_client.listen_realtime_data(handle_data)
```

### REST API

```python
# 현재가 조회
price = kis_client.get_current_price("005930")

# 매수 주문
result = kis_client.buy_order("005930", quantity=10, price=52000)

# 매도 주문
result = kis_client.sell_order("005930", quantity=10, price=53000)
```

## 데이터베이스 스키마

6개 스키마:
1. **MARKET** - 시장 데이터 (stocks, daily_prices, market_candles, market_macro)
2. **ACCOUNT** - 자산 관리 (portfolio, account_snapshots)
3. **BRAIN** - AI 분석 (daily_picks, daily_analysis_logs, intel_feed, market_regime)
4. **TRADE** - 매매 기록 (trade_logs, trade_feedbacks)
5. **SYSTEM** - 시스템 (system_config, fetcher_health_logs, strategy_states)
6. **ANALYTICS** - 백테스트 (backtest_results)

상세 스키마: [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md)

## 개발 문서

- [CORE_PHILOSOPHY.md](docs/CORE_PHILOSOPHY.md) - 핵심 철학
- [BRAIN_SIMPLE.md](docs/BRAIN_SIMPLE.md) - Brain 의사결정
- [COMBAT_ARCHITECTURE.md](docs/COMBAT_ARCHITECTURE.md) - 실전 아키텍처
- [PHASED_DEVELOPMENT.md](docs/PHASED_DEVELOPMENT.md) - 단계별 개발
- [KIS_API_SPECIFICATION.md](docs/KIS_API_SPECIFICATION.md) - KIS API 명세

## 라이선스

Private - AEGIS Development Team
