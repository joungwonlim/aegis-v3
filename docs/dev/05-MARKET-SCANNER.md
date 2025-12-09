# Market Scanner 설계

> 작성일: 2025-12-09
> 상태: 설계
> Phase: 2

---

## 🎯 목표

1분마다 등락률/거래량 상위 종목 스캔 → gemini-2.0-flash 빠른 평가 → WebSocket 구독

---

## 📊 Layer 2 역할

```
Layer 3 (07:20): DeepSeek R1 전체 분석 → daily_picks (2000종목)
     ↓
Layer 2 (1분마다): Market Scanner → gemini-2.0-flash 평가 (100종목)
     ↓
Layer 1 (실시간): WebSocket 40 슬롯 → 체결가/호가 수신
```

---

## 🔧 KIS API

### 등락률 상위 조회

**TR_ID**: `FHKST01010100` (국내주식 현재가 시세)

**파라미터**:
```python
{
    "FID_COND_MRKT_DIV_CODE": "J",  # 주식
    "FID_COND_SCR_DIV_CODE": "20171",  # 등락률 상위
    "FID_INPUT_ISCD": "0000",  # 전체
    "FID_DIV_CLS_CODE": "0",  # 전체
    "FID_BLNG_CLS_CODE": "0",  # 평균 거래량
    "FID_TRGT_CLS_CODE": "111111111",  # 전체 (증거금 제외)
    "FID_TRGT_EXLS_CLS_CODE": "000000",  # 제외 없음
    "FID_INPUT_PRICE_1": "",  # 가격 조건 없음
    "FID_INPUT_PRICE_2": "",
    "FID_VOL_CNT": "",  # 거래량 조건 없음
    "FID_INPUT_DATE_1": ""  # 날짜 조건 없음
}
```

**응답 예시**:
```json
{
    "output": [
        {
            "mksc_shrn_iscd": "005930",  // 종목코드
            "hts_kor_isnm": "삼성전자",   // 종목명
            "stck_prpr": "52000",        // 현재가
            "prdy_vrss": "1000",         // 전일대비
            "prdy_ctrt": "1.96",         // 등락률
            "acml_vol": "10234567"       // 거래량
        },
        ...
    ]
}
```

### 거래량 상위 조회

**TR_ID**: `FHKST01010400`

파라미터는 등락률과 동일

---

## 🏗️ 아키텍처

### MarketScanner 클래스

```python
class MarketScanner:
    """
    시장 스캔 (Layer 2)

    역할:
    - 1분마다 등락률/거래량 상위 조회
    - gemini-2.0-flash 빠른 평가
    - 70점 이상 → WebSocket 구독 (Priority 3)
    """

    # 메서드
    async def scan_top_gainers(limit: int = 50) -> List[dict]
    async def scan_top_volume(limit: int = 50) -> List[dict]
    async def evaluate_stock(stock: dict) -> int
    async def run_scanner()
```

---

## 💡 구현 계획

### 1. KIS API 조회 메서드

```python
# fetchers/kis_client.py에 추가

def get_top_gainers(self, limit: int = 50) -> List[dict]:
    """
    등락률 상위 조회

    Args:
        limit: 조회 개수

    Returns:
        등락률 상위 종목 리스트
    """
    if not self.access_token:
        self.get_access_token()

    url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/volume-rank"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {self.access_token}",
        "appkey": self.app_key,
        "appsecret": self.app_secret,
        "tr_id": "FHKST01010100"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "J",
        "FID_COND_SCR_DIV_CODE": "20171",  # 등락률 상위
        "FID_INPUT_ISCD": "0000",
        "FID_DIV_CLS_CODE": "0",
        "FID_BLNG_CLS_CODE": "0",
        "FID_TRGT_CLS_CODE": "111111111",
        "FID_TRGT_EXLS_CLS_CODE": "000000",
        "FID_INPUT_PRICE_1": "",
        "FID_INPUT_PRICE_2": "",
        "FID_VOL_CNT": "",
        "FID_INPUT_DATE_1": ""
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        stocks = data.get("output", [])[:limit]
        logger.info(f"✅ Top gainers: {len(stocks)} stocks")
        return stocks
    else:
        logger.error(f"❌ Failed to get top gainers: {response.text}")
        return []

def get_top_volume(self, limit: int = 50) -> List[dict]:
    """
    거래량 상위 조회

    Args:
        limit: 조회 개수

    Returns:
        거래량 상위 종목 리스트
    """
    # get_top_gainers와 동일한 구조
    # tr_id와 FID_COND_SCR_DIV_CODE만 변경
    # FID_COND_SCR_DIV_CODE: "20172" (거래량 상위)
    pass
```

### 2. MarketScanner 클래스

```python
# fetchers/market_scanner.py

import google.generativeai as genai
from typing import List, Dict
import logging

from fetchers.kis_client import kis_client
from fetchers.websocket_manager import ws_manager
from app.config import settings

logger = logging.getLogger(__name__)

# Gemini API 설정
genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-2.0-flash-exp")


class MarketScanner:
    """
    시장 스캔 (Layer 2)

    특징:
    - 1분마다 등락률/거래량 상위 스캔
    - gemini-2.0-flash 빠른 평가
    - WebSocket Priority 3 구독
    """

    def __init__(self):
        self.kis_client = kis_client
        self.is_running = False

    async def scan_top_gainers(self, limit: int = 50) -> List[dict]:
        """
        등락률 상위 조회

        Args:
            limit: 조회 개수

        Returns:
            등락률 상위 종목
        """
        try:
            stocks = self.kis_client.get_top_gainers(limit)
            logger.info(f"📈 Top gainers scanned: {len(stocks)} stocks")
            return stocks
        except Exception as e:
            logger.error(f"❌ Top gainers scan failed: {e}")
            return []

    async def scan_top_volume(self, limit: int = 50) -> List[dict]:
        """
        거래량 상위 조회

        Args:
            limit: 조회 개수

        Returns:
            거래량 상위 종목
        """
        try:
            stocks = self.kis_client.get_top_volume(limit)
            logger.info(f"📊 Top volume scanned: {len(stocks)} stocks")
            return stocks
        except Exception as e:
            logger.error(f"❌ Top volume scan failed: {e}")
            return []

    async def evaluate_stock(self, stock: dict) -> int:
        """
        종목 빠른 평가 (gemini-2.0-flash)

        Args:
            stock: 종목 정보

        Returns:
            AI 점수 (0~100)
        """
        try:
            stock_code = stock.get("mksc_shrn_iscd", "")
            stock_name = stock.get("hts_kor_isnm", "")
            current_price = int(stock.get("stck_prpr", 0))
            change_rate = float(stock.get("prdy_ctrt", 0))
            volume = int(stock.get("acml_vol", 0))

            # Gemini 프롬프트
            prompt = f"""
종목 빠른 평가 (1분 이내 응답):

종목: {stock_name} ({stock_code})
현재가: {current_price:,}원
등락률: {change_rate:+.2f}%
거래량: {volume:,}주

평가 기준:
1. 급등 지속 가능성 (30점)
2. 거래량 적정성 (20점)
3. 단기 모멘텀 (30점)
4. 리스크 (20점)

응답 형식:
점수: 0~100 (정수만)
이유: 1줄 요약
"""

            response = model.generate_content(prompt)
            text = response.text.strip()

            # 점수 추출 (첫 번째 숫자)
            import re
            match = re.search(r'\d+', text)
            score = int(match.group()) if match else 0

            logger.debug(f"🤖 {stock_code}: {score}점 - {text[:50]}...")

            return score

        except Exception as e:
            logger.error(f"❌ Stock evaluation failed: {e}")
            return 0

    async def run_scanner(self):
        """
        스캐너 실행 (1분 간격)
        """
        logger.info("🔍 Market Scanner started")
        self.is_running = True

        while self.is_running:
            try:
                # 1. 등락률 상위 스캔 (상위 20개)
                top_gainers = await self.scan_top_gainers(limit=20)

                # 2. 거래량 상위 스캔 (상위 20개)
                top_volume = await self.scan_top_volume(limit=20)

                # 3. 중복 제거
                all_stocks = {s["mksc_shrn_iscd"]: s for s in top_gainers + top_volume}

                logger.info(f"📊 Total unique stocks: {len(all_stocks)}")

                # 4. gemini-2.0-flash 평가
                candidates = []
                for stock in list(all_stocks.values())[:30]:  # 최대 30개 평가
                    score = await self.evaluate_stock(stock)

                    if score >= 70:
                        candidates.append({
                            "stock_code": stock["mksc_shrn_iscd"],
                            "stock_name": stock["hts_kor_isnm"],
                            "score": score,
                            "change_rate": float(stock["prdy_ctrt"])
                        })

                        logger.info(
                            f"⭐ Candidate: {stock['hts_kor_isnm']} "
                            f"({score}점, {stock['prdy_ctrt']}%)"
                        )

                # 5. WebSocket 구독 (Priority 3)
                for candidate in candidates[:5]:  # 상위 5개만
                    await ws_manager.subscribe(
                        stock_code=candidate["stock_code"],
                        stock_name=candidate["stock_name"],
                        priority=3
                    )

                # 6. 1분 대기
                logger.info(f"✅ Scanner cycle complete: {len(candidates)} candidates")
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"❌ Scanner error: {e}")
                await asyncio.sleep(60)

        logger.info("🛑 Market Scanner stopped")

    async def stop(self):
        """스캐너 정지"""
        self.is_running = False
        logger.info("🛑 Stopping Market Scanner...")


# Singleton Instance
market_scanner = MarketScanner()
```

---

## 📋 사용 시나리오

### 1. 시스템 시작 시

```python
# main.py
async def startup():
    # WebSocket Manager 시작
    await ws_manager.start()

    # Market Scanner 시작
    asyncio.create_task(market_scanner.run_scanner())
```

### 2. 급등주 발견 → WebSocket 구독

```
09:05:00 - Market Scanner 실행
         ↓
         KIS API 조회 (등락률 상위 20개, 거래량 상위 20개)
         ↓
         중복 제거 (약 30개 유일 종목)
         ↓
         gemini-2.0-flash 평가 (각 1초, 총 30초)
         ↓
         70점 이상 필터링 (예: 5개)
         ↓
         WebSocket 구독 (Priority 3)
         ↓
09:06:00 - 다음 사이클
```

---

## 🧪 테스트 계획

### 단위 테스트

```python
async def test_scan_top_gainers():
    """등락률 상위 조회 테스트"""
    stocks = await market_scanner.scan_top_gainers(limit=10)
    assert len(stocks) <= 10
    assert all("mksc_shrn_iscd" in s for s in stocks)

async def test_evaluate_stock():
    """종목 평가 테스트"""
    stock = {
        "mksc_shrn_iscd": "005930",
        "hts_kor_isnm": "삼성전자",
        "stck_prpr": "52000",
        "prdy_ctrt": "1.96",
        "acml_vol": "10234567"
    }
    score = await market_scanner.evaluate_stock(stock)
    assert 0 <= score <= 100
```

---

## 🚨 주의사항

### 1. API 호출 제한

- KIS API: 초당 20회 제한
- Gemini API: 분당 60회 제한 (free tier)
- 1분 사이클에서 총 40개 정도 평가 가능

### 2. WebSocket 슬롯 부족

- Priority 3이 가득 차면 가장 오래된 것 제거
- 급등주는 실시간 모니터링 필요성이 높으므로 자주 교체

### 3. 비용 관리

- gemini-2.0-flash: 매우 저렴 (100만 토큰당 $0.10)
- 1분 40개 평가 = 하루 약 40 × 60 × 7시간 = 16,800회
- 예상 비용: 하루 약 $1~2

---

## 📝 다음 단계

1. ✅ kis_client에 get_top_gainers() 추가
2. ✅ kis_client에 get_top_volume() 추가
3. ✅ MarketScanner 클래스 구현
4. ✅ gemini-2.0-flash 통합
5. ⏳ 통합 테스트

---

**작성**: Claude Code
**상태**: 설계 완료
**다음**: Market Scanner 구현
