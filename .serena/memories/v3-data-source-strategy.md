# AEGIS v3.0 - 데이터 소스 전략

## 핵심 구분

### KIS WebSocket (실시간)

```
언제: 장 중 (09:00~15:30)
무엇: 실시간 체결가, 호가, 프로그램 매매
개수: 40개 종목 (슬롯 제한)
방식: UPDATE only (절대 DELETE 금지)
속도: 초단위 업데이트
```

**제공 데이터**:
- H0STCNT0: 실시간 체결가 (현재가, 등락률, 체결량)
- H0STASP0: 실시간 호가 (매수/매도 10호가)
- H0STPGM0: 프로그램 매매 (차익/비차익)
- H0STCNI0: 체결 통보 (내 주문)

**DB 테이블**:
- realtime_price (실시간 가격)
- realtime_orderbook (실시간 호가)

**업데이트 방식**:
```sql
-- UPSERT (UPDATE or INSERT)
INSERT INTO realtime_price (stock_code, current_price, ...)
VALUES (...)
ON CONFLICT (stock_code) DO UPDATE ...
```

### pykrx (역사적 데이터)

```
언제: 장 마감 후 (16:00), 하루 1회
무엇: 과거 OHLCV, 수급, 공매도
개수: 2000개 종목 (전체)
방식: INSERT only (증분 업데이트)
속도: 하루 1회 배치
```

**제공 데이터**:
- 일별 OHLCV (시가, 고가, 저가, 종가, 거래량)
- 수급 데이터 (외국인, 기관, 개인 순매수)
- 공매도 정보 (공매도 잔고, 대차잔고)
- 시장 지표 (시가총액, PER, PBR)

**DB 테이블**:
- daily_ohlcv (일별 OHLCV)
- daily_supply_demand (일별 수급)
- daily_short_selling (일별 공매도)

**업데이트 방식**:
```sql
-- 증분 INSERT (마지막 날짜 이후만)
-- 1. 마지막 날짜 확인
SELECT MAX(date) FROM daily_ohlcv WHERE stock_code = :code;

-- 2. 그 다음날부터만 조회
pykrx.get_market_ohlcv(last_date+1, today, stock_code)

-- 3. INSERT (중복 스킵)
INSERT INTO daily_ohlcv (...)
VALUES (...)
ON CONFLICT (stock_code, date) DO NOTHING;
```

## v2 문제점 → v3 해결책

### ❌ v2 문제

```python
# 매번 삭제/재생성
DELETE FROM stock_price WHERE stock_code = :code;
pykrx.get_market_ohlcv('20230101', 'today', code);  # 전체 조회
INSERT ... (수천 개 레코드)

# 결과:
- 1종목당 10~15초 소요
- 2000종목: 5~8시간
- DB 과부하
- API 과부하
- 타임아웃 빈번
```

### ✅ v3 해결

```python
# 증분 업데이트
last_date = SELECT MAX(date) FROM daily_ohlcv WHERE stock_code = :code;
pykrx.get_market_ohlcv(last_date+1, today, code);  # 오늘 1개만
INSERT ... (1개 레코드, 중복 스킵)

# 결과:
- 1종목당 0.5초
- 2000종목: 15~20분
- DB 부하 최소
- API 부하 최소
- 안정적
```

**개선 효과**: 20~30배 빠름 ⚡

## 조회 전략

### 현재가 (장 중)
```python
# WebSocket 테이블
SELECT current_price FROM realtime_price WHERE stock_code = :code;
```

### 과거 30일 가격
```python
# pykrx 테이블
SELECT date, close FROM daily_ohlcv
WHERE stock_code = :code AND date >= :start_date
ORDER BY date DESC LIMIT 30;
```

### AI 분석용 종합 데이터
```python
# 1. 실시간 (WebSocket)
realtime = SELECT * FROM realtime_price WHERE stock_code = :code;

# 2. 과거 60일 (pykrx)
history = SELECT * FROM daily_ohlcv
WHERE stock_code = :code AND date >= :start_date;

# 3. 수급 10일 (pykrx)
supply = SELECT * FROM daily_supply_demand
WHERE stock_code = :code AND date >= :start_date;
```

## 실행 스케줄

### 09:00~15:30 (장 중)
- KIS WebSocket 실시간 수신
- realtime_price UPDATE (초단위)

### 16:00 (장 마감 후)
- pykrx 배치 실행
- daily_ohlcv INSERT (오늘 1개)
- daily_supply_demand INSERT (오늘 1개)

## 핵심 원칙

```
✅ 실시간 = WebSocket → UPDATE only
✅ 역사적 = pykrx → INSERT (증분)
❌ 절대 삭제/재생성 금지
✅ 마지막 날짜 이후만 조회
✅ 중복 시 자동 스킵
```
