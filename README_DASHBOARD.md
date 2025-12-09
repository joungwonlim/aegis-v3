# AEGIS v3.0 - Watch Dashboard 실행 가이드

## 🚀 실행 방법

### 1. 기본 실행 (1회 실행)

```bash
# venv 활성화 후 실행
source venv/bin/activate
python monitoring/watch_dashboard_rich.py
```

### 2. 자동 갱신 모드 (권장)

```bash
# 3초마다 자동 갱신
./watch.sh
```

또는

```bash
# 커스텀 갱신 주기 (예: 5초)
watch -n 5 python monitoring/watch_dashboard_rich.py
```

---

## 📊 대시보드 구성

### 1. 포트폴리오 요약
- 총 평가액, 현금, 주식평가
- 총 손익 (금액 & 수익률)
- 🎯 목표 수익률 달성도 프로그레스 바

### 2. 전체 수익률 추이 (30일)
```
│ +418.6%                           ││●●
│                               ││●●││
│    0.0%●│││───────────────────────────
└──────┬────────────────────▶ 시간
```
- 30일간 수익률 트렌드 차트
- 최고/최저 수익률 자동 표시

### 3. 오늘 수익률 (시간별)
```
│ +419.2% ●●●●
│        ││││●●
│ +418.7%││││││●
└──────┬──┬──┬──▶
   09:00 11:00 13:00 15:30
```
- 장중 09:00~15:30 실시간 추이
- 장 시작/고점/저점/현재 가격 표시
- 오늘 변화량 (상승/하락)

### 4. 보유 종목 상세
- 종목별 수량, 평단가, 현재가, 손익률
- 수익률 막대 그래프
- **합계/평균 행** 포함:
  - 종목 수
  - 총 평가금액
  - 가중 평균 수익률

### 5. 트레일링 스톱 차트
```
│ ★ 고점 131,685원
│
│ ← 손절가 (고점-2%)
│ ◆ 매수가 125,414원
│ ● 현재가 123,800원
└─────────────────▶ 시간
```
- 개별 종목 가격 추이
- 트레일링 스톱 활성화 상태
- 손절가 하회 시 자동 알림

### 6. 최근 시그널 (5개)
- AI 매매 시그널
- BUY/SELL/HOLD 액션
- 점수 및 신뢰도

### 7. 스케줄 & 프로세스
- 앞으로 실행될 작업
- 실행중인 프로세스 (PID, CPU, 메모리)

### 8. 최근 거래 내역
- 최근 5건 거래
- 시간, 종목, 액션, 수량, 가격

### 9. Sonnet Commander 결정
- 최근 3건 결정 로그
- 종목, 액션, 사유, 신뢰도

### 10. 시스템 상태
- MIN_SCORE (동적 조정)
- 연속 손절/익절 횟수
- Circuit Breaker 상태
- 오늘 거래 건수

---

## ⚙️ 환경 설정

### 필수 환경변수 (.env)

```bash
# Database
DATABASE_URL=postgresql://aegis:aegis2024@localhost:5432/aegis_v3

# KIS API
KIS_APP_KEY=your_app_key_here
KIS_APP_SECRET=your_app_secret_here
KIS_CANO=your_account_number_8digits
KIS_ACNT_PRDT_CD=01
```

### 데이터베이스 초기화

```bash
# 시스템 시작 시 한 번 실행
python scripts/initialize_account.py
```

이 스크립트는:
1. Access Token 발급
2. KIS API에서 보유종목 조회
3. DB에 동기화 (stock_assets, portfolio_summary)
4. 미체결 내역 확인

---

## 🔧 문제 해결

### 1. "Database connection failed"
```bash
# PostgreSQL 실행 확인
brew services start postgresql@16

# 데이터베이스 존재 확인
psql -d aegis_v3 -c "SELECT 1"
```

### 2. "KIS API token expired"
```bash
# 초기화 스크립트 재실행
python scripts/initialize_account.py
```

### 3. "No holdings found"
```bash
# DB 동기화
python scripts/initialize_account.py
```

---

## 📝 주의사항

1. **v2 절대 사용 금지**
   - v2는 KIS API 문제로 폐기됨
   - v3만 사용할 것

2. **실전 투자만 지원**
   - 모의투자 기능 없음
   - 실제 계좌 연동

3. **데이터 동기화**
   - 하이브리드 전략 (WebSocket + REST API)
   - 1분마다 자동 동기화
   - 재연결 시 비상 동기화

---

## 🚀 고급 기능

### 실시간 모니터링 (tmux 활용)

```bash
# tmux 세션 시작
tmux new -s aegis

# 대시보드 실행
./watch.sh

# Detach: Ctrl+B → D
# Attach: tmux attach -t aegis
```

### 백그라운드 실행

```bash
# nohup으로 백그라운드 실행
nohup ./watch.sh > dashboard.log 2>&1 &

# 프로세스 확인
ps aux | grep watch_dashboard

# 종료
pkill -f watch_dashboard
```

---

## 📚 관련 문서

- [하이브리드 동기화 전략](docs/HYBRID_SYNC_STRATEGY.md)
- [메인 README](README.md)

---

**마지막 업데이트**: 2025-12-10 03:24
