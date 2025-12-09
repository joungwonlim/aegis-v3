# Data Integrity Rules (데이터 무결성 규칙)

> **"어렵게 모은 데이터, 절대 삭제 금지!"**

---

## 🚨 절대 규칙 (CRITICAL)

### Rule #1: 절대 삭제 금지

```
┌─────────────────────────────────────────────────────────────┐
│           🚫 데이터 삭제 절대 금지 🚫                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ❌ DELETE FROM stocks                                      │
│  ❌ DELETE FROM daily_prices                                │
│  ❌ TRUNCATE TABLE                                          │
│  ❌ DROP TABLE                                              │
│                                                             │
│  이유:                                                      │
│  • 어렵게 모은 데이터 (2,772종목 × 365일)                   │
│  • 복구 불가능 (과거 데이터)                                │
│  • 시스템 신뢰성 하락                                       │
│                                                             │
│  ✅ 올바른 방법: UPSERT (UPDATE or INSERT)                  │
│  ✅ 갱신: UPDATE                                            │
│  ✅ 추가: INSERT                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ 올바른 데이터 갱신 방법

### UPSERT 패턴

```python
# ❌ 잘못된 방법 (절대 금지!)
db.query(DailyPrice).delete()  # 전체 삭제
db.commit()
# 새 데이터 INSERT

# ✅ 올바른 방법 (UPSERT)
from sqlalchemy.dialects.postgresql import insert

stmt = insert(DailyPrice).values(
    stock_code='005930',
    date='2025-12-08',
    open=109000,
    high=110000,
    low=108000,
    close=109500,
    volume=15000000
).on_conflict_do_update(
    index_elements=['stock_code', 'date'],  # Unique Key
    set_=dict(
        open=109000,
        high=110000,
        low=108000,
        close=109500,
        volume=15000000
    )
)

db.execute(stmt)
db.commit()
```

**작동 방식:**
- 데이터 있으면 → **UPDATE** (갱신)
- 데이터 없으면 → **INSERT** (추가)
- 삭제는 **절대 안 함**!

---

## 📋 데이터 갱신 체크리스트

### 스크립트 작성 시

```
[ ] UPSERT 사용 확인
[ ] DELETE 문 없는지 확인
[ ] TRUNCATE 없는지 확인
[ ] 롤백 처리 포함
[ ] 진행률 표시
[ ] 에러 처리 (계속 진행)
```

### 코드 리뷰 시

```python
# 금지 키워드 검색
grep -r "DELETE FROM" scripts/
grep -r "TRUNCATE" scripts/
grep -r "DROP TABLE" scripts/

# 결과가 나오면 → 즉시 수정!
```

---

## 🔧 안전한 데이터 갱신 예제

### 1. 종목 마스터 갱신

```python
# scripts/update_stock_master.py

def update_stock_master():
    """
    종목 마스터 안전 갱신
    - 기존 종목: 이름 업데이트
    - 신규 종목: 추가
    - 삭제: 없음!
    """
    from pykrx import stock

    db = SessionLocal()

    for market in ['KOSPI', 'KOSDAQ']:
        codes = stock.get_market_ticker_list(market=market)

        for code in codes:
            name = stock.get_market_ticker_name(code)

            existing = db.query(Stock).filter(Stock.code == code).first()

            if existing:
                # 기존 종목: 업데이트만
                existing.name = name
                existing.market = market
                existing.is_active = True
            else:
                # 신규 종목: 추가
                db.add(Stock(
                    code=code,
                    name=name,
                    market=market,
                    is_active=True
                ))

    db.commit()
    db.close()
```

### 2. 가격 데이터 갱신

```python
# scripts/update_daily_prices.py

def update_daily_prices(stock_code, start_date, end_date):
    """
    가격 데이터 안전 갱신 (UPSERT)
    """
    from sqlalchemy.dialects.postgresql import insert
    from pykrx import stock

    db = SessionLocal()

    # pykrx로 데이터 조회
    df = stock.get_market_ohlcv_by_date(start_date, end_date, stock_code)

    for date_idx, row in df.iterrows():
        stmt = insert(DailyPrice).values(
            stock_code=stock_code,
            date=date_idx.date(),
            open=int(row['시가']),
            high=int(row['고가']),
            low=int(row['저가']),
            close=int(row['종가']),
            volume=int(row['거래량']),
        ).on_conflict_do_update(
            index_elements=['stock_code', 'date'],
            set_=dict(
                open=int(row['시가']),
                high=int(row['고가']),
                low=int(row['저가']),
                close=int(row['종가']),
                volume=int(row['거래량']),
            )
        )

        db.execute(stmt)

    db.commit()
    db.close()
```

### 3. 상장 폐지 종목 처리

```python
# 삭제 금지! is_active 플래그 사용

def mark_delisted_stock(stock_code):
    """
    상장 폐지 종목은 삭제가 아닌 비활성화
    """
    db = SessionLocal()

    stock = db.query(Stock).filter(Stock.code == stock_code).first()

    if stock:
        stock.is_active = False  # 비활성화만
        # ❌ db.delete(stock)  # 삭제 금지!

    db.commit()
    db.close()
```

---

## 📊 데이터 갱신 전략

### 일일 갱신 (매일 자동)

```python
# scheduler: 매일 08:00
- 최근 5일 가격 데이터 UPSERT
- KIS 포트폴리오 동기화
- 삭제 없음!
```

### 주간 갱신 (매주 토요일)

```python
# scheduler: 매주 토 09:00
- 전체 종목 마스터 점검
- 최근 30일 가격 데이터 UPSERT
- 비활성 종목 is_active = False
- 삭제 없음!
```

### 월간 갱신 (매월 1일)

```python
# scheduler: 매월 1일 06:00
- 전체 데이터 검증
- 누락 데이터 보충
- 데이터 무결성 체크
- 삭제 없음!
```

---

## 🛡️ 안전장치

### 1. 삭제 감지 시스템

```python
# database/safe_session.py

from sqlalchemy.orm import Session
from sqlalchemy import event

class SafeSession(Session):
    """
    삭제를 감지하고 경고하는 안전한 Session
    """
    pass

@event.listens_for(SafeSession, 'before_flush')
def prevent_delete(session, flush_context, instances):
    """DELETE 작업 감지 및 경고"""
    if session.deleted:
        deleted_items = list(session.deleted)

        # 중요 테이블 삭제 시 에러
        for item in deleted_items:
            table_name = item.__tablename__

            if table_name in ['stocks', 'daily_prices', 'portfolio']:
                raise ValueError(
                    f"🚫 삭제 금지! {table_name} 테이블에서 삭제 시도 감지됨. "
                    f"is_active=False 또는 UPDATE를 사용하세요."
                )
```

### 2. 코드 리뷰 자동화

```bash
# .git/hooks/pre-commit

#!/bin/bash

# 삭제 키워드 검색
if git diff --cached | grep -i "DELETE FROM\|TRUNCATE\|DROP TABLE" > /dev/null; then
    echo "🚫 경고: 데이터 삭제 코드 감지됨!"
    echo "삭제 대신 UPSERT를 사용하세요."
    exit 1
fi
```

---

## 📚 관련 문서

- `DATA_FLOW.md`: 데이터 흐름
- `DATABASE_DESIGN.md`: DB 스키마
- `.serena/memories/data-integrity-policy.md`: 무결성 정책

---

## 💡 핵심 교훈

```
"삭제는 쉽지만, 복구는 불가능하다"

- 상장 폐지 → is_active = False
- 잘못된 데이터 → UPDATE로 수정
- 오래된 데이터 → 보관 (분석용)

절대 DELETE 사용 금지!
```

---

**작성일**: 2025-12-08
**작성자**: wonny
**버전**: 1.0.0
**원칙**: UPSERT ONLY, NO DELETE
