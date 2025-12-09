# AEGIS v3.0 - 아키텍처 핵심 원칙

## 1. Write/Read Only Pattern (엄격 준수)

```
✅ Write: KISFetcher만 DB에 쓰기
✅ Read: 모든 모듈은 DB에서만 읽기
⚠️ 예외: OrderService만 주문 직전 KIS API 직접 조회
```

**절대 금지**:
- Dashboard/Brain/Telegram에서 kis_client 직접 호출
- DB Write를 KISFetcher 외 다른 곳에서 수행

## 2. Just-in-Time Data Feeding (핵심!)

```
❌ Wrong Order (뒷북):
   await brain.analyze()   # 1시간 전 데이터 사용
   await fetcher.sync()    # 너무 늦음!

✅ Correct Order (최신):
   await fetcher.sync()    # 최신 데이터 수집
   await db.commit()       # DB 저장 (0.1초)
   await brain.analyze()   # 최신 데이터 분석!
```

**핵심**: AI가 최신 데이터만 분석하도록 데이터 수집을 분석 직전에 수행

## 3. Dynamic Schedule (10-60-30 전략)

시장 활동 패턴에 맞춘 차등 실행:

```
🔥 오전장 (09:00~10:00): 10분 간격 (70% 변동성)
💤 점심장 (10:00~13:00): 60분 간격 (저거래량)
🌤️ 오후장 (13:00~15:00): 20분 간격 (추세 확인)
🏁 막판 (15:00~15:20): 10분 간격 (마지막 기회)
```

**절대 금지**: 30분 고정 간격

## 4. 3-Layer Monitoring

```
Layer 3: DeepSeek R1 전체 분석 (07:20, 2000종목)
   ↓
Layer 2: Market Scanner (1분, gemini-2.0-flash, ~100종목)
   ↓
Layer 1: WebSocket 실시간 (40 슬롯, Priority 1/2/3)
```

## 5. Single Source of Truth

```
KIS API → KISFetcher → DB → All Modules
```

DB가 유일한 진실의 원천. 모든 모듈은 DB만 읽음.

## 6. NXT Market Support

- NXT와 KRX 별도 TR_ID 사용
- NXT 시장가 주문 차단 (지정가만 허용)
- get_combined_balance()로 통합 잔고 조회
