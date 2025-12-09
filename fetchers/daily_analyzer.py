"""
AEGIS v3.0 - Daily Analyzer (Layer 3)
DeepSeek R1으로 2000종목 전체 심층 분석

실행 시각: 07:20 (장 시작 전)
목표: 상위 20개 종목 선정 → daily_picks 테이블 저장
"""
import asyncio
import logging
from datetime import date, datetime
from typing import List, Dict, Optional
import httpx

from app.config import settings
from app.database import get_db
from app.models.brain import DailyPick
from fetchers.websocket_manager import ws_manager

logger = logging.getLogger(__name__)


class DailyAnalyzer:
    """
    일일 심층 분석 (Layer 3)

    역할:
    - DeepSeek R1으로 전체 종목 분석
    - 재무제표, 뉴스, 수급 종합 분석
    - daily_picks 테이블 저장
    - WebSocket Manager에 picks 반영

    3-Layer 구조:
    - Layer 3: Daily Analyzer (07:20)  ← 이 클래스
    - Layer 2: Market Scanner (1분)
    - Layer 1: WebSocket 실시간 (40 슬롯)
    """

    def __init__(self):
        self.deepseek_api_key = settings.deepseek_api_key
        self.deepseek_base_url = settings.deepseek_base_url
        self.batch_size = 50  # 한 번에 분석할 종목 수

    async def analyze_all(self) -> List[dict]:
        """
        전체 종목 심층 분석

        플로우:
        1. 종목 리스트 조회 (2000종목)
        2. 배치 분석 (50개씩)
        3. 상위 20개 선정
        4. daily_picks 테이블 저장
        5. WebSocket Manager 업데이트

        Returns:
            상위 20개 종목 리스트
        """
        logger.info("=" * 80)
        logger.info(f"🧠 Daily Deep Analysis Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        try:
            # 1. 종목 리스트 조회
            stock_list = await self._get_stock_list()
            logger.info(f"📊 Total stocks to analyze: {len(stock_list)}")

            # 2. 배치 분석
            all_scores = []
            for i in range(0, len(stock_list), self.batch_size):
                batch = stock_list[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                total_batches = (len(stock_list) + self.batch_size - 1) // self.batch_size

                logger.info(f"🔍 Analyzing batch {batch_num}/{total_batches} ({len(batch)} stocks)...")

                batch_scores = await self._analyze_batch(batch)
                all_scores.extend(batch_scores)

                # API 호출 제한 대응 (약간의 딜레이)
                if i + self.batch_size < len(stock_list):
                    await asyncio.sleep(2)

            # 3. 상위 20개 선정 (AI 점수 기준)
            sorted_stocks = sorted(all_scores, key=lambda x: x['ai_score'], reverse=True)
            top_picks = sorted_stocks[:20]

            logger.info("")
            logger.info(f"🎯 Top 20 Picks Selected:")
            for i, pick in enumerate(top_picks, 1):
                logger.info(
                    f"   {i:2d}. {pick['stock_name']} ({pick['stock_code']}): "
                    f"AI {pick['ai_score']}/100, Quant {pick.get('quant_score', 0)}/100"
                )

            # 4. daily_picks 테이블 저장
            await self._save_picks(top_picks)
            logger.info(f"✅ Saved {len(top_picks)} picks to daily_picks table")

            # 5. WebSocket Manager 업데이트
            await self._update_websocket_manager(top_picks)
            logger.info(f"✅ Updated WebSocket Manager with {len(top_picks)} picks")

            logger.info("")
            logger.info("=" * 80)
            logger.info(f"✅ Daily Deep Analysis Complete: {len(top_picks)} picks")
            logger.info("=" * 80)

            return top_picks

        except Exception as e:
            logger.error(f"❌ Daily analysis failed: {e}", exc_info=True)
            return []

    async def _get_stock_list(self) -> List[dict]:
        """
        전체 종목 리스트 조회

        TODO: pykrx로 실제 코스피/코스닥 전체 조회
        현재: 임시 샘플 데이터

        Returns:
            종목 리스트 (stock_code, stock_name)
        """
        # TODO: pykrx 통합
        # from pykrx import stock
        # kospi_list = stock.get_market_ticker_list("KRX")
        # kosdaq_list = stock.get_market_ticker_list("KOSDAQ")

        # 임시: 샘플 종목 리스트 (실제로는 2000개)
        sample_stocks = [
            {"stock_code": "005930", "stock_name": "삼성전자"},
            {"stock_code": "000660", "stock_name": "SK하이닉스"},
            {"stock_code": "035420", "stock_name": "NAVER"},
            {"stock_code": "035720", "stock_name": "카카오"},
            {"stock_code": "051910", "stock_name": "LG화학"},
            {"stock_code": "006400", "stock_name": "삼성SDI"},
            {"stock_code": "028260", "stock_name": "삼성물산"},
            {"stock_code": "105560", "stock_name": "KB금융"},
            {"stock_code": "055550", "stock_name": "신한지주"},
            {"stock_code": "012330", "stock_name": "현대모비스"},
        ]

        logger.warning("⚠️  Using sample stock list (TODO: Integrate pykrx)")
        return sample_stocks

    async def _analyze_batch(self, batch: List[dict]) -> List[dict]:
        """
        배치 분석 (DeepSeek R1)

        Args:
            batch: 종목 리스트 (50개)

        Returns:
            분석 결과 (AI 점수 포함)
        """
        results = []

        for stock in batch:
            try:
                # DeepSeek R1 분석
                analysis = await self._analyze_single_stock(stock)
                results.append(analysis)

            except Exception as e:
                logger.error(f"❌ Analysis failed for {stock['stock_code']}: {e}")
                # 실패 시 0점 처리
                results.append({
                    "stock_code": stock['stock_code'],
                    "stock_name": stock['stock_name'],
                    "ai_score": 0,
                    "quant_score": 0,
                    "strategy_name": "ERROR",
                    "expected_entry_price": 0,
                    "ai_comment": f"Analysis failed: {str(e)}"
                })

        return results

    async def _analyze_single_stock(self, stock: dict) -> dict:
        """
        개별 종목 심층 분석 (DeepSeek R1)

        Args:
            stock: 종목 정보

        Returns:
            분석 결과
        """
        stock_code = stock['stock_code']
        stock_name = stock['stock_name']

        # DeepSeek R1 프롬프트 (심층 분석)
        prompt = f"""
주식 종목 심층 분석 (DeepSeek R1):

종목: {stock_name} ({stock_code})

다음 항목을 종합 분석하여 점수를 매겨주세요:

1. 재무제표 분석 (30점)
   - 매출 성장률
   - 영업이익률
   - 부채비율
   - ROE

2. 수급 분석 (30점)
   - 외국인/기관 수급
   - 프로그램 매매 동향
   - 거래량 추이

3. 뉴스/공시 분석 (20점)
   - 최근 중요 공시
   - 뉴스 감성 분석
   - 업종 동향

4. 기술적 분석 (20점)
   - 추세 방향
   - 지지/저항선
   - 모멘텀 지표

**응답 형식 (꼭 지켜주세요)**:
AI점수: [0~100 정수]
Quant점수: [0~100 정수]
전략: [모멘텀/가치투자/성장주/배당주]
예상진입가: [정수]
코멘트: [2-3줄 요약]

예시:
AI점수: 85
Quant점수: 78
전략: 모멘텀
예상진입가: 70000
코멘트: 실적 개선 기대, 외국인 순매수 지속, 단기 모멘텀 강함
"""

        try:
            # DeepSeek R1 API 호출
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.deepseek_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.deepseek_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-reasoner",  # DeepSeek R1
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 500
                    }
                )

                if response.status_code != 200:
                    logger.error(f"DeepSeek API error: {response.status_code} - {response.text}")
                    raise Exception(f"API error: {response.status_code}")

                result = response.json()
                content = result['choices'][0]['message']['content']

                # 응답 파싱
                parsed = self._parse_deepseek_response(content)

                return {
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "ai_score": parsed['ai_score'],
                    "quant_score": parsed['quant_score'],
                    "strategy_name": parsed['strategy'],
                    "expected_entry_price": parsed['entry_price'],
                    "ai_comment": parsed['comment']
                }

        except Exception as e:
            logger.error(f"❌ DeepSeek analysis failed for {stock_code}: {e}")
            raise

    def _parse_deepseek_response(self, content: str) -> dict:
        """
        DeepSeek R1 응답 파싱

        Args:
            content: DeepSeek 응답 텍스트

        Returns:
            파싱된 결과
        """
        import re

        # 기본값
        result = {
            'ai_score': 50,
            'quant_score': 50,
            'strategy': 'UNKNOWN',
            'entry_price': 0,
            'comment': content[:100]  # 첫 100자
        }

        try:
            # AI점수 추출
            ai_match = re.search(r'AI점수[:\s]*(\d+)', content)
            if ai_match:
                result['ai_score'] = int(ai_match.group(1))

            # Quant점수 추출
            quant_match = re.search(r'Quant점수[:\s]*(\d+)', content)
            if quant_match:
                result['quant_score'] = int(quant_match.group(1))

            # 전략 추출
            strategy_match = re.search(r'전략[:\s]*(\S+)', content)
            if strategy_match:
                result['strategy'] = strategy_match.group(1)

            # 예상진입가 추출
            price_match = re.search(r'예상진입가[:\s]*(\d+)', content)
            if price_match:
                result['entry_price'] = int(price_match.group(1))

            # 코멘트 추출
            comment_match = re.search(r'코멘트[:\s]*(.+?)(?:\n\n|\Z)', content, re.DOTALL)
            if comment_match:
                result['comment'] = comment_match.group(1).strip()

        except Exception as e:
            logger.error(f"Response parsing error: {e}")

        return result

    async def _save_picks(self, picks: List[dict]) -> None:
        """
        daily_picks 테이블에 저장

        Args:
            picks: 상위 종목 리스트
        """
        db = next(get_db())

        try:
            # 오늘 날짜의 기존 picks 삭제
            today = date.today()
            db.query(DailyPick).filter(DailyPick.date == today).delete()

            # 새 picks 저장
            for rank, pick in enumerate(picks, 1):
                daily_pick = DailyPick(
                    date=today,
                    stock_code=pick['stock_code'],
                    strategy_name=pick.get('strategy_name', 'DEEPSEEK_R1'),
                    rank=rank,
                    quant_score=pick.get('quant_score', 0),
                    ai_score=pick.get('ai_score', 0),
                    expected_entry_price=pick.get('expected_entry_price', 0.0),
                    ai_comment=pick.get('ai_comment', ''),
                    is_executed=False
                )
                db.add(daily_pick)

            db.commit()

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Failed to save picks: {e}", exc_info=True)
            raise

    async def _update_websocket_manager(self, picks: List[dict]) -> None:
        """
        WebSocket Manager에 daily picks 업데이트

        Args:
            picks: 상위 종목 리스트
        """
        try:
            # WebSocket Manager의 update_daily_picks 호출
            await ws_manager.update_daily_picks(picks)

        except Exception as e:
            logger.error(f"❌ Failed to update WebSocket Manager: {e}", exc_info=True)


# Singleton Instance
daily_analyzer = DailyAnalyzer()
