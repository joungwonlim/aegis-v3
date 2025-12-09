"""
AEGIS v3.0 - Stock Fetcher
특정 종목에 대한 즉시 데이터 수집

역할:
- 종목별 실시간 데이터 수집
- KIS API, Naver, DART 통합
- DB 즉시 업데이트
"""
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime

from fetchers.kis_client import kis_client
from fetchers.kis_fetcher import kis_fetcher
from app.database import get_db

logger = logging.getLogger(__name__)


class StockFetcher:
    """
    종목별 즉시 데이터 수집기

    역할:
    - 특정 종목의 최신 데이터 수집
    - 여러 데이터 소스 통합
    - DB 즉시 업데이트
    """

    def __init__(self):
        self.kis = kis_fetcher

    async def fetch_single_stock(
        self,
        stock_code: str,
        reason: str,
        priority: str = "NORMAL"
    ) -> Dict:
        """
        특정 종목 즉시 데이터 수집

        Args:
            stock_code: 종목 코드
            reason: 트리거 이유 (execution_notice, breaking_news 등)
            priority: 우선순위 (HIGH/MEDIUM/NORMAL)

        Returns:
            {
                'stock_code': '005930',
                'current_price': 78000,
                'news_count': 3,
                'disclosure_count': 0,
                'fetch_time': datetime
            }
        """
        start_time = datetime.now()
        logger.info(f"🔍 Stock Fetcher: {stock_code} (reason: {reason})")

        result = {
            'stock_code': stock_code,
            'reason': reason,
            'priority': priority,
            'fetch_time': start_time,
            'success': False,
            'errors': []
        }

        try:
            # 1️⃣ KIS API: 현재가 & 호가
            await self._fetch_kis_data(stock_code, result)

            # 2️⃣ Naver: 최근 뉴스 (3시간 이내)
            # TODO: 구현 필요
            # await self._fetch_naver_news(stock_code, result)

            # 3️⃣ DART: 당일 공시
            # TODO: 구현 필요
            # await self._fetch_dart_disclosure(stock_code, result)

            # 4️⃣ pykrx: 수급 데이터
            # TODO: 구현 필요
            # await self._fetch_supply_demand(stock_code, result)

            result['success'] = True
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Stock Fetcher completed: {stock_code} ({elapsed:.2f}s)")

        except Exception as e:
            logger.error(f"❌ Stock Fetcher error: {stock_code} - {e}", exc_info=True)
            result['errors'].append(str(e))

        return result

    async def _fetch_kis_data(self, stock_code: str, result: Dict):
        """
        KIS API 데이터 수집

        수집 항목:
        - 현재가
        - 호가 (매수 1호가, 매도 1호가)
        - 거래량
        - 등락률
        """
        try:
            # 현재가 조회 (동기 API이므로 asyncio.to_thread 사용)
            current_price_data = await asyncio.to_thread(
                kis_client.get_current_price,
                stock_code
            )

            if current_price_data:
                result['current_price'] = int(current_price_data.get('stck_prpr', 0))
                result['change_rate'] = float(current_price_data.get('prdy_ctrt', 0))
                result['volume'] = int(current_price_data.get('acml_vol', 0))

                logger.info(f"  ✅ KIS 현재가: {result['current_price']:,}원 ({result['change_rate']:+.2f}%)")
            else:
                logger.warning(f"  ⚠️  KIS 현재가 조회 실패: {stock_code}")

            # 호가 조회
            orderbook_data = await asyncio.to_thread(
                kis_client.get_orderbook,
                stock_code
            )

            if orderbook_data:
                result['bid1'] = int(orderbook_data.get('bidp1', 0))
                result['ask1'] = int(orderbook_data.get('askp1', 0))

                logger.info(f"  ✅ KIS 호가: 매수 {result['bid1']:,}원 / 매도 {result['ask1']:,}원")
            else:
                logger.warning(f"  ⚠️  KIS 호가 조회 실패: {stock_code}")

        except Exception as e:
            logger.error(f"  ❌ KIS 데이터 수집 실패: {e}")
            result['errors'].append(f"KIS API error: {str(e)}")

    async def _fetch_naver_news(self, stock_code: str, result: Dict):
        """
        Naver 뉴스 수집

        수집 항목:
        - 최근 3시간 이내 뉴스
        - 제목, URL, 작성 시간
        """
        # TODO: Naver 뉴스 크롤링 구현
        result['news_count'] = 0
        logger.info(f"  ⏸️  Naver 뉴스: 구현 필요")

    async def _fetch_dart_disclosure(self, stock_code: str, result: Dict):
        """
        DART 공시 수집

        수집 항목:
        - 당일 공시
        - 공시명, 접수번호, 제출일
        """
        # TODO: DART API 구현
        result['disclosure_count'] = 0
        logger.info(f"  ⏸️  DART 공시: 구현 필요")

    async def _fetch_supply_demand(self, stock_code: str, result: Dict):
        """
        수급 데이터 수집 (pykrx)

        수집 항목:
        - 외국인 순매수
        - 기관 순매수
        - 개인 순매수
        """
        # TODO: pykrx 구현
        logger.info(f"  ⏸️  수급 데이터: 구현 필요")

    async def fetch_portfolio_holdings(self):
        """
        보유 종목 전체 데이터 수집

        역할:
        - Portfolio Manager가 1분마다 호출
        - 전체 보유 종목 최신 데이터 갱신
        """
        logger.info("📥 Fetching portfolio holdings...")

        try:
            # KIS 잔고 동기화 (기존 fetcher 사용)
            await self.kis.sync_portfolio()
            logger.info("  ✅ Portfolio synced")

        except Exception as e:
            logger.error(f"  ❌ Portfolio sync failed: {e}", exc_info=True)


# Singleton Instance
stock_fetcher = StockFetcher()
