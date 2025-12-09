"""
AEGIS v3.0 - Market Scanner (Layer 2)
1분마다 등락률/거래량 상위 스캔 → gemini-2.0-flash 평가 → WebSocket 구독
"""
import asyncio
import re
from typing import List, Dict
import logging

# Gemini API
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logging.warning("⚠️  google-generativeai not installed, Market Scanner will be disabled")

from fetchers.kis_client import kis_client
from fetchers.websocket_manager import ws_manager
from app.config import settings

logger = logging.getLogger(__name__)

# Gemini API 설정
if GEMINI_AVAILABLE:
    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        logger.info("✅ Gemini API configured")
    except Exception as e:
        logger.error(f"❌ Gemini API configuration failed: {e}")
        model = None
else:
    model = None


class MarketScanner:
    """
    시장 스캔 (Layer 2)

    역할:
    - 1분마다 등락률/거래량 상위 스캔
    - gemini-2.0-flash 빠른 평가
    - WebSocket Priority 3 구독

    3-Layer 구조:
    - Layer 3: DeepSeek R1 전체 분석 (07:20)
    - Layer 2: Market Scanner (1분)  ← 이 클래스
    - Layer 1: WebSocket 실시간 (40 슬롯)
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
        if not model:
            logger.warning("⚠️  Gemini API not available, returning 0 score")
            return 0

        try:
            stock_code = stock.get("mksc_shrn_iscd", "")
            stock_name = stock.get("hts_kor_isnm", "")
            current_price = int(stock.get("stck_prpr", 0))
            change_rate = float(stock.get("prdy_ctrt", 0))
            volume = int(stock.get("acml_vol", 0))

            # Gemini 프롬프트 (빠른 평가)
            prompt = f"""
종목 빠른 평가 (30초 이내 응답):

종목: {stock_name} ({stock_code})
현재가: {current_price:,}원
등락률: {change_rate:+.2f}%
거래량: {volume:,}주

평가 기준:
1. 급등 지속 가능성 (30점)
   - 재료성 급등인가 vs 단순 작전
   - 과열 여부
2. 거래량 적정성 (20점)
   - 평소 대비 몇 배?
   - 매집 vs 분산
3. 단기 모멘텀 (30점)
   - 추가 상승 여력
   - 저항선 돌파 여부
4. 리스크 (20점)
   - 변동성
   - 단기 급락 가능성

**응답 형식 (꼭 지켜주세요)**:
점수: [0~100 정수]
이유: [1줄 요약]

예시:
점수: 75
이유: 거래량 급증하며 저항선 돌파, 단기 모멘텀 강함
"""

            response = model.generate_content(prompt)
            text = response.text.strip()

            # 점수 추출 (첫 번째 숫자)
            match = re.search(r'점수[:\s]*(\d+)', text)
            if not match:
                match = re.search(r'\d+', text)

            score = int(match.group(1) if match and match.lastindex >= 1 else match.group()) if match else 0

            # 점수 범위 제한
            score = max(0, min(100, score))

            logger.debug(f"🤖 {stock_code} ({stock_name}): {score}점")

            return score

        except Exception as e:
            logger.error(f"❌ Stock evaluation failed: {stock_code} - {e}")
            return 0

    async def run_scanner(self):
        """
        스캐너 실행 (1분 간격)

        플로우:
        1. 등락률 상위 20개 조회
        2. 거래량 상위 20개 조회
        3. 중복 제거 (약 30개)
        4. gemini-2.0-flash 평가
        5. 70점 이상 → WebSocket 구독 (Priority 3)
        6. 1분 대기
        """
        logger.info("🔍 Market Scanner started")
        self.is_running = True

        while self.is_running:
            try:
                logger.info("=" * 60)
                logger.info("🔍 Scanner cycle started")

                # 1. 등락률 상위 스캔 (상위 20개)
                top_gainers = await self.scan_top_gainers(limit=20)

                # 2. 거래량 상위 스캔 (상위 20개)
                top_volume = await self.scan_top_volume(limit=20)

                # 3. 중복 제거
                all_stocks = {}
                for s in top_gainers + top_volume:
                    code = s.get("mksc_shrn_iscd", "")
                    if code and code not in all_stocks:
                        all_stocks[code] = s

                logger.info(f"📊 Total unique stocks: {len(all_stocks)}")

                # 4. gemini-2.0-flash 평가 (최대 30개)
                candidates = []
                evaluated_count = 0

                for stock in list(all_stocks.values())[:30]:
                    # 평가 제한 (API 호출 제한 고려)
                    if evaluated_count >= 30:
                        break

                    score = await self.evaluate_stock(stock)
                    evaluated_count += 1

                    if score >= 70:
                        candidates.append({
                            "stock_code": stock["mksc_shrn_iscd"],
                            "stock_name": stock["hts_kor_isnm"],
                            "score": score,
                            "change_rate": float(stock.get("prdy_ctrt", 0)),
                            "current_price": int(stock.get("stck_prpr", 0))
                        })

                        logger.info(
                            f"⭐ Candidate: {stock['hts_kor_isnm']} "
                            f"({score}점, {stock.get('prdy_ctrt', 0)}%, "
                            f"{stock.get('stck_prpr', 0):,}원)"
                        )

                    # API 호출 제한 대응 (약간의 딜레이)
                    await asyncio.sleep(0.5)

                # 5. WebSocket 구독 (Priority 3, 최대 5개)
                subscribed = 0
                for candidate in sorted(candidates, key=lambda x: x["score"], reverse=True)[:5]:
                    result = await ws_manager.subscribe(
                        stock_code=candidate["stock_code"],
                        stock_name=candidate["stock_name"],
                        priority=3
                    )
                    if result:
                        subscribed += 1

                logger.info(f"✅ Scanner cycle complete: {len(candidates)} candidates, {subscribed} subscribed")
                logger.info("=" * 60)

                # 6. 1분 대기
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
