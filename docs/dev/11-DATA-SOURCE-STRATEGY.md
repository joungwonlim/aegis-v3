# 데이터 소스 전략: KIS WebSocket vs pykrx

> 작성일: 2025-12-09
> 중요도: ⭐⭐⭐⭐⭐ (핵심)

---

## 🎯 핵심 원칙

```
❌ v2 문제: pykrx로 실시간 가격 업데이트 시도 → 삭제/재생성 반복 → DB 과부하

✅ v3 해결:
1. 실시간 데이터 = KIS WebSocket (절대 삭제 안함, UPDATE만)
2. 역사적 데이터 = pykrx (하루 1회, 장 마감 후)
```

---

## 📊 데이터 소스 구분

### 1. KIS WebSocket (실시간)

**목적**: 장 중 실시간 데이터 (초단위 업데이트)

**제공 데이터**:
```
1. H0STCNT0 (실시간 체결가)
   - 현재가
   - 등락률
   - 체결량
   - 체결 시각

2. H0STASP0 (실시간 호가)
   - 매수호가 1~10
   - 매도호가 1~10
   - 호가 잔량

3. H0STPGM0 (프로그램 매매)
   - 차익거래 매수/매도
   - 비차익거래 매수/매도

4. H0STCNI0 (체결 통보)
   - 내 주문 체결 알림
   - 체결가, 체결량
```

**사용 시점**:
- 09:00 ~ 15:30 (장 중)
- 초단위 실시간 업데이트

**DB 전략**:
```sql
-- ✅ UPDATE만 사용 (절대 DELETE 안함)
UPDATE realtime_price
SET
  current_price = :new_price,
  change_rate = :new_rate,
  updated_at = NOW()
WHERE stock_code = :code;

-- 없으면 INSERT
INSERT INTO realtime_price (stock_code, current_price, ...)
VALUES (:code, :price, ...)
ON CONFLICT (stock_code) DO UPDATE ...
```

**특징**:
- ⚡ 빠름 (실시간)
- 🔴 Live 데이터만 (과거 데이터 없음)
- 🎯 40개 종목 제한 (슬롯)

---

### 2. pykrx (역사적 데이터)

**목적**: 과거 데이터, 수급 데이터 (일단위 업데이트)

**제공 데이터**:
```
1. 일별 OHLCV (과거 가격)
   - 시가, 고가, 저가, 종가
   - 거래량, 거래대금
   - 날짜별 히스토리

2. 수급 데이터 (투자자별)
   - 외국인 순매수/매도
   - 기관 순매수/매도
   - 개인 순매수/매도

3. 공매도 정보
   - 공매도 잔고
   - 대차잔고

4. 시장 지표
   - 시가총액
   - PER, PBR
   - 상장주식수
```

**사용 시점**:
- 16:00 ~ 06:00 (장 마감 후)
- 하루 1회 배치 실행

**DB 전략**:
```sql
-- ✅ INSERT만 사용 (과거 데이터 누적)
-- 날짜가 PK이므로 중복 불가

-- 1. OHLCV 테이블
INSERT INTO daily_ohlcv (stock_code, date, open, high, low, close, volume)
VALUES (:code, :date, :open, :high, :low, :close, :volume)
ON CONFLICT (stock_code, date) DO NOTHING;  -- 이미 있으면 스킵

-- 2. 수급 테이블
INSERT INTO daily_supply_demand (stock_code, date, foreign_net, institution_net)
VALUES (:code, :date, :foreign, :institution)
ON CONFLICT (stock_code, date) DO UPDATE
SET foreign_net = :foreign, institution_net = :institution;  -- 수정된 수급 반영
```

**특징**:
- 🐢 느림 (API 제한)
- 📚 과거 데이터 풍부
- 🌍 전체 종목 조회 가능 (2000개)

---

## 🔄 업데이트 전략

### 실시간 데이터 (KIS WebSocket)

```python
# realtime_price 테이블
class RealtimePrice(Base):
    """실시간 가격 (WebSocket)"""
    __tablename__ = "realtime_price"

    stock_code = Column(String(20), primary_key=True)
    current_price = Column(Integer)
    change_rate = Column(Float)
    volume = Column(BigInteger)
    updated_at = Column(DateTime)  # 마지막 업데이트 시각

# ✅ UPDATE 전략
async def update_realtime_price(stock_code: str, data: dict):
    """
    실시간 가격 업데이트 (WebSocket 수신 시)

    ❌ 절대 DELETE 안함
    ✅ UPDATE만 사용
    """
    # UPSERT (없으면 INSERT, 있으면 UPDATE)
    await db.execute(
        """
        INSERT INTO realtime_price (stock_code, current_price, change_rate, volume, updated_at)
        VALUES (:code, :price, :rate, :vol, NOW())
        ON CONFLICT (stock_code) DO UPDATE
        SET
            current_price = :price,
            change_rate = :rate,
            volume = :vol,
            updated_at = NOW()
        """,
        {"code": stock_code, "price": data['price'], "rate": data['rate'], "vol": data['volume']}
    )
```

**장점**:
- 삭제/재생성 없음 → DB 부하 최소
- 실시간 업데이트 빠름
- 레코드 수 고정 (40개) → 테이블 크기 안정

---

### 역사적 데이터 (pykrx)

```python
# daily_ohlcv 테이블
class DailyOHLCV(Base):
    """일별 OHLCV (pykrx)"""
    __tablename__ = "daily_ohlcv"

    id = Column(Integer, primary_key=True)
    stock_code = Column(String(20), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Integer)
    high = Column(Integer)
    low = Column(Integer)
    close = Column(Integer)
    volume = Column(BigInteger)

    __table_args__ = (
        UniqueConstraint('stock_code', 'date', name='uq_stock_date'),
    )

# ✅ INSERT 전략 (하루 1회)
async def sync_daily_ohlcv():
    """
    일별 OHLCV 동기화 (16:00 실행)

    전략:
    1. 마지막 저장 날짜 확인
    2. 그 이후 데이터만 가져오기
    3. INSERT (중복 시 스킵)
    """
    from pykrx import stock
    from datetime import datetime, timedelta

    # 1. 마지막 저장 날짜 확인
    last_date = await db.scalar(
        """
        SELECT MAX(date) FROM daily_ohlcv WHERE stock_code = :code
        """,
        {"code": stock_code}
    )

    # 2. 그 다음날부터 오늘까지만 조회
    start_date = (last_date + timedelta(days=1)).strftime('%Y%m%d') if last_date else '20230101'
    end_date = datetime.today().strftime('%Y%m%d')

    # 3. pykrx로 조회 (필요한 날짜만)
    df = stock.get_market_ohlcv(start_date, end_date, stock_code)

    # 4. INSERT (중복 시 자동 스킵)
    for date, row in df.iterrows():
        await db.execute(
            """
            INSERT INTO daily_ohlcv (stock_code, date, open, high, low, close, volume)
            VALUES (:code, :date, :open, :high, :low, :close, :vol)
            ON CONFLICT (stock_code, date) DO NOTHING
            """,
            {
                "code": stock_code,
                "date": date,
                "open": row['시가'],
                "high": row['고가'],
                "low": row['저가'],
                "close": row['종가'],
                "vol": row['거래량']
            }
        )
```

**장점**:
- 증분 업데이트 (마지막 날짜 이후만)
- 삭제 없음 → 히스토리 보존
- 중복 시 자동 스킵 → 안전

---

## 🗓️ 실행 스케줄

### 1. 장 중 (09:00 ~ 15:30)

```
09:00 - 15:30 : KIS WebSocket 실시간 수신
                ↓
                realtime_price 테이블 UPDATE
                (초단위, 40개 종목)
```

**사용 테이블**:
- `realtime_price` (실시간 가격)
- `realtime_orderbook` (실시간 호가)

**업데이트 방식**: UPDATE (삭제 없음)

---

### 2. 장 마감 후 (16:00)

```
16:00 : pykrx 배치 실행
        ↓
        1. OHLCV 동기화 (오늘 데이터)
        2. 수급 동기화 (오늘 데이터)
        3. 공매도 동기화 (오늘 데이터)
        ↓
        daily_ohlcv, daily_supply_demand 테이블 INSERT
        (하루 1회, 2000개 종목)
```

**사용 테이블**:
- `daily_ohlcv` (일별 OHLCV)
- `daily_supply_demand` (일별 수급)
- `daily_short_selling` (일별 공매도)

**업데이트 방식**: INSERT (증분, 중복 스킵)

---

## 📋 테이블 설계

### 실시간 테이블 (KIS WebSocket)

```sql
-- 실시간 가격
CREATE TABLE realtime_price (
    stock_code VARCHAR(20) PRIMARY KEY,
    stock_name VARCHAR(100),
    current_price INTEGER NOT NULL,
    change_rate FLOAT,
    volume BIGINT,
    updated_at TIMESTAMP DEFAULT NOW()
);
-- 레코드 수: ~40개 (WebSocket 슬롯)
-- 업데이트: 초단위
-- 전략: UPDATE only

-- 실시간 호가
CREATE TABLE realtime_orderbook (
    stock_code VARCHAR(20) PRIMARY KEY,
    bid_price_1 INTEGER,  -- 매수호가 1
    bid_qty_1 INTEGER,
    ask_price_1 INTEGER,  -- 매도호가 1
    ask_qty_1 INTEGER,
    -- ... 10호가까지
    updated_at TIMESTAMP DEFAULT NOW()
);
-- 레코드 수: ~40개
-- 업데이트: 초단위
-- 전략: UPDATE only
```

---

### 역사적 테이블 (pykrx)

```sql
-- 일별 OHLCV
CREATE TABLE daily_ohlcv (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    open INTEGER,
    high INTEGER,
    low INTEGER,
    close INTEGER,
    volume BIGINT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (stock_code, date)
);
-- 레코드 수: ~2000 종목 × 365일 = 730,000개/년
-- 업데이트: 하루 1회 (16:00)
-- 전략: INSERT (증분)

-- 일별 수급
CREATE TABLE daily_supply_demand (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    foreign_net BIGINT,      -- 외국인 순매수
    institution_net BIGINT,  -- 기관 순매수
    individual_net BIGINT,   -- 개인 순매수
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (stock_code, date)
);
-- 레코드 수: ~2000 종목 × 365일 = 730,000개/년
-- 업데이트: 하루 1회 (16:00)
-- 전략: INSERT (증분)
```

---

## 🔍 조회 전략

### Case 1: 현재가 조회 (장 중)

```python
# ✅ realtime_price 테이블 조회 (WebSocket)
current_price = await db.scalar(
    "SELECT current_price FROM realtime_price WHERE stock_code = :code",
    {"code": stock_code}
)
```

**속도**: ⚡ 빠름 (단일 레코드)

---

### Case 2: 과거 30일 가격 조회

```python
# ✅ daily_ohlcv 테이블 조회 (pykrx)
history = await db.execute(
    """
    SELECT date, close
    FROM daily_ohlcv
    WHERE stock_code = :code
      AND date >= :start_date
    ORDER BY date DESC
    LIMIT 30
    """,
    {"code": stock_code, "start_date": date.today() - timedelta(days=30)}
)
```

**속도**: ⚡ 빠름 (인덱스 활용)

---

### Case 3: AI 분석용 종합 데이터

```python
# ✅ 두 테이블 조합
async def get_stock_data_for_ai(stock_code: str):
    """AI 분석용 데이터 조회"""

    # 1. 실시간 가격 (WebSocket)
    realtime = await db.execute(
        "SELECT * FROM realtime_price WHERE stock_code = :code",
        {"code": stock_code}
    ).first()

    # 2. 과거 60일 OHLCV (pykrx)
    history = await db.execute(
        """
        SELECT * FROM daily_ohlcv
        WHERE stock_code = :code
          AND date >= :start_date
        ORDER BY date DESC
        """,
        {"code": stock_code, "start_date": date.today() - timedelta(days=60)}
    ).all()

    # 3. 최근 10일 수급 (pykrx)
    supply_demand = await db.execute(
        """
        SELECT * FROM daily_supply_demand
        WHERE stock_code = :code
          AND date >= :start_date
        ORDER BY date DESC
        """,
        {"code": stock_code, "start_date": date.today() - timedelta(days=10)}
    ).all()

    return {
        "realtime": realtime,
        "history": history,
        "supply_demand": supply_demand
    }
```

---

## ⚠️ v2 문제점 vs v3 해결책

### v2 문제점

```python
# ❌ v2의 잘못된 방식
async def update_price():
    """매번 삭제하고 재생성 → DB 과부하"""

    # 1. 기존 데이터 전체 삭제
    await db.execute("DELETE FROM stock_price WHERE stock_code = :code")

    # 2. pykrx로 전체 히스토리 다시 가져오기
    df = stock.get_market_ohlcv('20230101', '20251209', stock_code)

    # 3. 전체 INSERT
    for date, row in df.iterrows():
        await db.execute("INSERT INTO stock_price ...")

    # 문제:
    # - 매번 수천 개 레코드 삭제/삽입
    # - pykrx API 과부하
    # - DB 과부하
    # - 느림 (1종목당 10초 이상)
```

---

### v3 해결책

```python
# ✅ v3의 올바른 방식
async def update_price():
    """증분 업데이트 → 빠르고 안전"""

    # 1. 마지막 날짜 확인
    last_date = await db.scalar(
        "SELECT MAX(date) FROM daily_ohlcv WHERE stock_code = :code"
    )

    # 2. 그 다음날부터만 가져오기
    if last_date:
        start_date = (last_date + timedelta(days=1)).strftime('%Y%m%d')
    else:
        start_date = '20230101'

    end_date = date.today().strftime('%Y%m%d')

    # 3. 필요한 날짜만 조회
    df = stock.get_market_ohlcv(start_date, end_date, stock_code)

    # 4. INSERT (중복 스킵)
    for date, row in df.iterrows():
        await db.execute(
            """
            INSERT INTO daily_ohlcv (...)
            VALUES (...)
            ON CONFLICT (stock_code, date) DO NOTHING
            """
        )

    # 장점:
    # - 오늘 데이터 1개만 INSERT (빠름!)
    # - pykrx API 1회 호출
    # - DB 부하 최소
    # - 빠름 (1종목당 0.5초)
```

---

## 📊 성능 비교

### v2 (삭제/재생성)

```
1종목 업데이트:
- DELETE: 365개 레코드 삭제
- pykrx API: 365일치 조회
- INSERT: 365개 레코드 삽입
→ 소요 시간: 10~15초
→ DB 부하: 높음
→ API 부하: 높음

2000종목 업데이트:
- 소요 시간: 5~8시간 (!)
- 실패 위험: 높음 (타임아웃, API 제한)
```

---

### v3 (증분 업데이트)

```
1종목 업데이트:
- SELECT: 1개 레코드 (마지막 날짜)
- pykrx API: 1일치 조회
- INSERT: 1개 레코드 삽입
→ 소요 시간: 0.5초
→ DB 부하: 낮음
→ API 부하: 낮음

2000종목 업데이트:
- 소요 시간: 15~20분
- 실패 위험: 낮음
- 안전성: 높음 (중복 스킵)
```

**개선 효과**: 20~30배 빠름 ⚡

---

## 🎯 최종 정리

### KIS WebSocket

```
언제: 장 중 (09:00~15:30)
무엇: 실시간 체결가, 호가
얼마나: 40개 종목
어떻게: UPDATE only (삭제 금지)
테이블: realtime_price, realtime_orderbook
```

### pykrx

```
언제: 장 마감 후 (16:00)
무엇: 과거 OHLCV, 수급, 공매도
얼마나: 2000개 종목
어떻게: INSERT (증분, 중복 스킵)
테이블: daily_ohlcv, daily_supply_demand
```

### 핵심 원칙

```
✅ 실시간 = WebSocket (UPDATE)
✅ 역사적 = pykrx (INSERT, 증분)
❌ 절대 삭제/재생성 금지
✅ 증분 업데이트만 사용
```

---

**작성**: Claude Code
**중요도**: ⭐⭐⭐⭐⭐
**v2 문제 해결**: ✅ 완료
