# Korean Market Data Integration Summary

**작성일**: 2025-12-09 23:10:00
**작성자**: wonny
**단계**: Phase 4.7 - Korean Market Data Sources

---

## 📌 배경

한국 주식시장의 고유한 특성:
1. **외국인이 파생상품(선물)으로 현물을 흔듦** (Wag the dog)
2. **개인 비중이 높아 신용 물량에 민감**
3. **삼성전자 한 종목이 지수를 결정**
4. **프로그램 매매가 시장을 지배**

→ 이런 한국 시장의 독특한 메커니즘을 AI가 학습해야 함

---

## 🎯 목표

### 핵심 5대 지표 추가

| 순위 | 지표명 | 중요도 | 데이터 소스 | Fetcher |
|------|--------|--------|------------|---------|
| 1️⃣ | 외국인 선물 누적 순매수 | ⭐⭐⭐⭐⭐ | KIS API (`FHKIF03020100`) | KIS Fetcher |
| 2️⃣ | 프로그램 비차익 순매수 | ⭐⭐⭐⭐⭐ | KIS API (`FHKST01010600`) | KIS Fetcher |
| 3️⃣ | 시장 베이시스 (Basis) | ⭐⭐⭐⭐ | KIS API (선물-현물) | KIS Fetcher |
| 4️⃣ | 신용융자 잔고율 추이 | ⭐⭐⭐⭐ | 금투협/네이버 | Market Fetcher (신규) |
| 5️⃣ | 대차잔고 증감 | ⭐⭐⭐ | pykrx / KIS API | Stock Fetcher |

---

## 🧠 AI 학습 공식

### 1. 선물 주도 패턴
```python
if (foreign_futures_net > 5000 and basis > 5):
    signal = "BUY"
    reason = "외국인 선물 매수 + 베이시스 호전 → 기관 프로그램 매수 유입 예상"
    target_sector = "KOSPI 200 대형주"
```

### 2. 가짜 상승 필터링 (★ 핵심)
```python
if (kospi_change > 0 and program_non_arbitrage < 0):
    signal = "AVOID"
    reason = "지수 상승 중이나 프로그램 비차익 순매도 → 개인만 사고 있는 껍데기 상승"
    trap_type = "fake_rise"
    confidence = 0.95
```

**실전 사례**: 2025-12-09 삼성전자/SK하이닉스
- 미국장 호재 → 시초가 갭상승 (+3.5%)
- 프로그램 비차익 순매도 (외국인/기관 차익 실현)
- AI가 감지했다면 매수 회피 가능

### 3. 폭락 전조 감지
```python
if (price < ma20 and margin_debt_ratio >= historical_max):
    signal = "EMERGENCY_EXIT"
    reason = "주가 20일선 이탈 + 신용잔고율 역대 최고 → 반대매매 투매 임박"
    action = "전량 매도 및 현금화"
```

### 4. 공매도 압력 감지
```python
if (short_balance_change_pct > 50):
    signal = "CAUTION"
    reason = "대차잔고 급증 → 외국인/기관 하락 베팅 → 상승 천장 형성"
    recommendation = "상승 시 익절 or 보유 축소"
```

---

## 🔄 Fetcher 역할 분담

### ✅ 기존 Fetcher 활용

#### KIS Fetcher (`fetchers/kis_fetcher.py`)
**신규 메서드 추가**:
```python
async def fetch_futures_net_buy() -> Dict:
    """외국인 선물 누적 순매수 (FHKIF03020100)"""

async def fetch_program_trading() -> Dict:
    """프로그램 비차익 순매수 (FHKST01010600)"""

async def calculate_basis() -> float:
    """시장 베이시스 계산"""
```

**부담 수준**: ⭐⭐⭐ (중간)
- WebSocket으로 실시간 수집
- 기존 KIS API 인프라 활용

#### Stock Fetcher (`fetchers/stock_fetcher.py`)
**기존 기능 확장**:
```python
async def fetch_shorting_status(stock_code: str) -> Dict:
    """대차잔고 증감 (pykrx)"""
```

**부담 수준**: ⭐⭐ (낮음)
- 일 1회 실행
- pykrx 기존 메서드 활용

---

### 🆕 신규 Fetcher 필요

#### Market Data Fetcher (`fetchers/market_fetcher.py`)
**담당 데이터**:
- 신용융자 잔고율 (웹 스크래핑)
- 시장 지수 (KOSPI, KOSDAQ, KOSPI200)
- 섹터 지수 (반도체, 자동차, 2차전지)

**구현 예시**:
```python
class MarketFetcher:
    async def fetch_margin_debt_ratio(self, stock_code: str) -> float:
        """
        신용융자 잔고율 조회 (네이버 금융)

        URL: https://finance.naver.com/item/main.naver?code={stock_code}
        Returns: 신용잔고율 (%)
        """
        pass

    async def fetch_kospi_status(self) -> Dict:
        """
        KOSPI 지수 현황

        Returns:
            {
                'index': 2500.0,
                'change_pct': 1.2,
                'volume': 500000000,
                'foreign_net': 150000000000,  # 원화
                'inst_net': -80000000000
            }
        """
        pass

    async def fetch_sector_indices(self) -> Dict:
        """
        섹터 지수 현황

        Returns:
            {
                'semiconductor': {'index': 180.5, 'change_pct': 2.3},
                'automotive': {'index': 150.2, 'change_pct': -0.5},
                'battery': {'index': 200.1, 'change_pct': 1.8}
            }
        """
        pass
```

**부담 수준**: ⭐⭐ (낮음)
- 웹 스크래핑 캐싱 (5분~1시간)
- 비동기 처리

---

## 📊 Fetcher 부담 평가

| Fetcher | 기존 데이터 | 신규 데이터 | 총 부담 | 비고 |
|---------|------------|------------|---------|------|
| KIS Fetcher | 계좌, 시세 | +3개 핵심 지표 | ⭐⭐⭐ | WebSocket 활용 |
| Stock Fetcher | pykrx 종목 | +대차잔고 | ⭐⭐ | 일 1회 |
| **Market Fetcher** | - | **신용잔고, 지수** | ⭐⭐ | **신규 생성** |
| Global Fetcher | yfinance 40+ | (변경 없음) | ⭐⭐ | 캐싱 활용 |
| DART Fetcher | 공시 | (변경 없음) | ⭐ | API 제한 여유 |

**결론**: ✅ **Fetcher가 충분히 감당 가능**

---

## 🛠️ 구현 계획

### Phase 1: KIS Fetcher 확장 (1주)
- [ ] `fetch_futures_net_buy()` 구현
- [ ] `fetch_program_trading()` 구현
- [ ] `calculate_basis()` 구현
- [ ] WebSocket 실시간 스트림 추가
- [ ] 테스트 및 로깅

### Phase 2: Market Data Fetcher 생성 (1주)
- [ ] `MarketFetcher` 클래스 생성
- [ ] 신용융자 잔고율 웹 스크래핑
- [ ] KOSPI/KOSDAQ 지수 수집
- [ ] 섹터 지수 수집
- [ ] 캐싱 및 에러 처리

### Phase 3: Stock Fetcher 확장 (3일)
- [ ] 대차잔고 증감 계산 로직
- [ ] 전일 대비 증감률 추적
- [ ] DB 저장 및 히스토리 관리

### Phase 4: Brain 통합 (1주)
- [ ] Analyzer에 5대 지표 입력
- [ ] Trap Detector 연동
- [ ] AI 학습 공식 적용
- [ ] 백테스트 검증

---

## 📈 예상 개선 효과

### Before (함정 감지 없음)
```
2025-12-09 삼성전자
- 시초가: 78,500원 (+3.5% 갭상승)
- 프로그램 비차익: -850억원 (순매도)
- AI: "미국장 호재 + 갭상승 = BUY!"
- 결과: 최고점 매수 → -2.17% 손실 ❌
```

### After (5대 지표 감지)
```
2025-12-09 삼성전자
- 시초가: 78,500원 (+3.5% 갭상승)
- 프로그램 비차익: -850억원 (순매도)
- 🚨 함정 감지: "가짜 상승 (fake_rise)"
- AI: "AVOID - 개인만 사고 있는 껍데기 상승"
- 결과: 매수 회피 ✅
- 피드백: "CORRECT" → 가중치 강화
```

---

## 🔗 관련 문서

- 한국 시장 함정 감지: `22-KOREAN-MARKET-TRAPS.md`
- 외부 데이터 소스: `../EXTERNAL_DATA_SOURCES.md` (Section 3.3)
- Safety Checker: `20-SAFETY-CHECKER.md`
- Partial Sell: `21-PARTIAL-SELL.md`

---

## 👤 작성자

- **Author**: wonny
- **Date**: 2025-12-09 23:10:00
- **Project**: AEGIS v3.0
- **Phase**: 4.7 (Korean Market Data Integration)
