# AEGIS v3.0 - 데이터 수집 가이드

## 📋 전체 스크립트 목록

### 1. 빠른 데이터 수집 (2~3분)
```bash
bash scripts/RUN_ALL_FUELING.sh
```
**수집 내용:**
- 글로벌 시장 데이터 (48개 지표)
- 테마 & 뉴스
- KIS 시장 데이터 (외국인 선물, 프로그램 매매, 베이시스)
- 시장 수급 데이터 (투자자별 순매수, 대차잔고)

---

### 2. 개별 스크립트 실행

#### 🌍 글로벌 시장 데이터 (1~2분)
```bash
bash scripts/RUN_GLOBAL_DATA.sh
```
**48개 지표:** 달러 인덱스, 위안화, 엔/원, Nasdaq, S&P 500, SOX, 엔비디아, 테슬라, 비트코인 등

#### 📰 테마 & 뉴스 (10초)
```bash
source venv/bin/activate && python scripts/init_theme_data.py
```
**내용:** 네이버 금융 인기 테마 20개, 주요 뉴스 헤드라인

#### 📊 KIS 시장 데이터 (10초)
```bash
source venv/bin/activate && python scripts/init_kis_market.py
```
**내용:** 외국인 선물 누적 순매수, 프로그램 비차익, KOSPI200 베이시스

#### 💰 시장 수급 데이터 (5~10분) ⚠️ 장 시간 필수
```bash
bash scripts/RUN_MARKET_FLOW.sh

# 또는 직접 실행
source venv/bin/activate && python scripts/init_market_flow.py

# 일수 지정 가능
python scripts/init_market_flow.py 60  # 최근 60일
```
**내용:** 투자자별 순매수 (외국인/기관/개인), 대차잔고
**⚠️ 주의:** 장 시간(09:00-15:30) 또는 장 마감 후 30분 내 실행 필수 (pykrx API 제약)

---

### 3. 장기 데이터 수집 (별도 실행)

#### 📈 3년치 일별 데이터 (2~3시간)
```bash
source venv/bin/activate && python scripts/init_daily_data.py
```
**내용:** 전체 종목 (2,773개) 3년치 OHLCV 데이터

**백그라운드 실행:**
```bash
nohup python scripts/init_daily_data.py > logs/daily_data.log 2>&1 &
```

#### 💼 DART 재무 데이터 (30분~1시간)
```bash
source venv/bin/activate && python scripts/init_dart_data.py
```
**내용:** 재무제표, 부채비율, ROE, 영업이익률, 공시 리스크

**백그라운드 실행:**
```bash
nohup python scripts/init_dart_data.py > logs/dart_data.log 2>&1 &
```

---

## 🔄 주기별 실행 권장사항

### 매일 장 시작 전 (08:00-08:30)
```bash
bash scripts/RUN_ALL_FUELING.sh
```
**주의:** 시장 수급 데이터는 제외됨 (pykrx API 제약)

### 매일 장 마감 후 (15:30-16:00)
```bash
bash scripts/RUN_MARKET_FLOW.sh
```
**필수:** 투자자별 순매수, 대차잔고 데이터 수집

### 주말 (데이터 보강)
```bash
# 빠른 데이터
bash scripts/RUN_ALL_FUELING.sh

# 신규 종목 확인 (필요시)
python scripts/init_daily_data.py

# 재무제표 업데이트 (분기별)
python scripts/init_dart_data.py
```

---

## 📊 수집 데이터 구조

### market_macro (글로벌 데이터)
- 환율/통화: dollar_index, cnh, jpy_krw
- 변동성: vix, move_index, hyg
- 미국 지수: nasdaq, sp500, dow
- 반도체: sox, nvda, amd, tsm
- 2차전지: tsla, lit_etf
- 원자재: wti, gold, copper
- M7 빅테크: aapl, msft, googl, meta, amzn
- 기타: btc

### market_flow (KIS 데이터)
- foreign_futures_net: 외국인 선물 누적 순매수
- program_net: 프로그램 비차익 순매수
- kospi200_spot: KOSPI200 현물
- kospi200_futures: KOSPI200 선물
- basis: 베이시스

### investor_net_buying (투자자별 순매수)
- foreign_net: 외국인 순매수
- institution_net: 기관 순매수
- individual_net: 개인 순매수

### short_balance (대차잔고)
- balance_qty: 대차잔고 수량
- balance_amount: 대차잔고 금액
- balance_ratio: 대차잔고율

### daily_prices (일별 시세)
- 3년치 OHLCV 데이터

### stocks (종목 기본 정보 + 재무)
- 기본: code, name, market, sector
- 재무: debt_ratio, roe, op_margin
- 리스크: is_deficit, last_risk_report

---

## 🚨 문제 해결

### 1. 토큰 오류
```bash
# .env 파일 확인
cat .env | grep KIS_APP_KEY
```

### 2. DB 연결 오류
```bash
# PostgreSQL 상태 확인
pg_isready -h localhost
```

### 3. 가상환경 오류
```bash
# 가상환경 재생성
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. 진행 중인 프로세스 확인
```bash
ps aux | grep python | grep init_
```

### 5. 로그 확인
```bash
tail -f logs/daily_data.log
tail -f logs/dart_data.log
tail -f logs/market_flow.log
```

---

## 📝 참고

- **EXTERNAL_DATA_SOURCES.md**: 전체 데이터 소스 목록
- **데이터 수집 주기**:
  - 글로벌/KIS 데이터: 매일 1회 (장 시작 전)
  - 시장 수급: 매일 1회 (장 마감 후)
  - 일별 데이터: 최초 1회 + 신규 종목 발생 시
  - DART 재무: 분기별 1회

- **예상 소요 시간**:
  - 빠른 수집: 2~3분
  - 전체 수집 (3년치): 3~4시간
