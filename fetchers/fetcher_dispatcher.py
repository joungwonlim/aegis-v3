"""
AEGIS v3.0 - Fetcher Dispatcher
Event-driven Fetcher 즉시 실행 관리

역할:
- 이벤트 수신 → 즉시 Fetcher 트리거
- 중복 실행 방지 (debounce)
- 종목별 데이터 수집 조율
"""
import asyncio
import logging
from typing import Set, Dict, Optional
from datetime import datetime

from events.event_bus import event_bus, EventType, Event

logger = logging.getLogger(__name__)


class FetcherDispatcher:
    """
    Fetcher 즉시 실행 관리자

    역할:
    - 이벤트 발생 → 즉시 Stock Fetcher 실행
    - 중복 방지 (같은 종목 동시 실행 방지)
    - 실행 이력 관리
    """

    def __init__(self):
        self.running_fetchers: Set[str] = set()  # 현재 실행 중인 종목 코드
        self.last_fetch_time: Dict[str, datetime] = {}  # 종목별 마지막 실행 시간

        # 이벤트 구독
        self._subscribe_events()

    def _subscribe_events(self):
        """이벤트 구독 설정"""
        # 체결 통보
        event_bus.subscribe(EventType.EXECUTION_NOTICE, self.on_execution_notice)

        # 속보 뉴스
        event_bus.subscribe(EventType.BREAKING_NEWS, self.on_breaking_news)

        # 급등주 발견
        event_bus.subscribe(EventType.HOT_STOCK_FOUND, self.on_hot_stock_found)

        # DART 공시
        event_bus.subscribe(EventType.DART_DISCLOSURE, self.on_dart_disclosure)

        # 시장 지표 급변
        event_bus.subscribe(EventType.MARKET_REGIME_CHANGE, self.on_market_regime_change)

        logger.info("📡 Fetcher Dispatcher: Event subscriptions completed")

    async def on_execution_notice(self, event: Event):
        """
        체결 통보 이벤트 처리

        Args:
            event.data: {
                'stock_code': '005930',
                'order_type': 'BUY' | 'SELL',
                'quantity': 10,
                'price': 78000
            }
        """
        stock_code = event.data.get('stock_code')
        order_type = event.data.get('order_type', 'UNKNOWN')

        if not stock_code:
            logger.warning("⚠️  Execution notice without stock_code")
            return

        logger.info(f"🔔 체결 통보: {stock_code} {order_type}")

        # 즉시 Fetcher 실행
        await self.trigger_fetcher(
            stock_code=stock_code,
            reason=f"execution_notice_{order_type}",
            priority="HIGH"
        )

    async def on_breaking_news(self, event: Event):
        """
        속보 뉴스 이벤트 처리

        Args:
            event.data: {
                'stock_code': '005930',
                'title': '삼성전자 3분기 실적 서프라이즈',
                'url': 'https://...'
            }
        """
        stock_code = event.data.get('stock_code')
        title = event.data.get('title', '(제목 없음)')

        if not stock_code:
            logger.warning("⚠️  Breaking news without stock_code")
            return

        logger.info(f"📰 속보 뉴스: {title[:30]}...")

        # 즉시 Fetcher 실행
        await self.trigger_fetcher(
            stock_code=stock_code,
            reason="breaking_news",
            priority="HIGH"
        )

    async def on_hot_stock_found(self, event: Event):
        """
        급등주 발견 이벤트 처리

        Args:
            event.data: {
                'stock_code': '035720',
                'change_rate': 8.5,
                'ai_score': 75
            }
        """
        stock_code = event.data.get('stock_code')
        change_rate = event.data.get('change_rate', 0)

        if not stock_code:
            logger.warning("⚠️  Hot stock found without stock_code")
            return

        logger.info(f"🔥 급등주 발견: {stock_code} (+{change_rate:.1f}%)")

        # 즉시 Fetcher 실행
        await self.trigger_fetcher(
            stock_code=stock_code,
            reason="hot_stock",
            priority="MEDIUM"
        )

    async def on_dart_disclosure(self, event: Event):
        """
        DART 공시 이벤트 처리

        Args:
            event.data: {
                'stock_code': '005930',
                'report_nm': '분기보고서',
                'rcept_no': '20251209000001'
            }
        """
        stock_code = event.data.get('stock_code')
        report_nm = event.data.get('report_nm', '(공시명 없음)')

        if not stock_code:
            logger.warning("⚠️  DART disclosure without stock_code")
            return

        logger.info(f"📄 DART 공시: {stock_code} - {report_nm}")

        # 즉시 Fetcher 실행
        await self.trigger_fetcher(
            stock_code=stock_code,
            reason="dart_disclosure",
            priority="MEDIUM"
        )

    async def on_market_regime_change(self, event: Event):
        """
        시장 지표 급변 이벤트 처리

        Args:
            event.data: {
                'regime': 'IRON_SHIELD',
                'reason': 'VIX 급등 (30)',
                'action': 'RECHECK_ALL'
            }
        """
        regime = event.data.get('regime', 'UNKNOWN')
        reason = event.data.get('reason', '(이유 없음)')

        logger.warning(f"🚨 시장 지표 급변: {regime} - {reason}")

        # 전체 보유 종목 재점검 (TODO)
        # 현재는 로그만 남김
        pass

    async def trigger_fetcher(
        self,
        stock_code: str,
        reason: str,
        priority: str = "NORMAL"
    ):
        """
        Fetcher 즉시 실행

        Args:
            stock_code: 종목 코드
            reason: 트리거 이유
            priority: 우선순위 (HIGH/MEDIUM/NORMAL)

        중복 방지:
        - 이미 실행 중이면 스킵 (debounce)
        - 같은 종목은 최소 10초 간격
        """
        # 중복 실행 방지 (이미 실행 중)
        if stock_code in self.running_fetchers:
            logger.debug(f"⏸️  Fetcher already running for {stock_code}, skipping")
            return

        # 최소 실행 간격 체크 (10초)
        last_time = self.last_fetch_time.get(stock_code)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < 10:
                logger.debug(f"⏸️  Fetcher throttled for {stock_code} (last run {elapsed:.1f}s ago)")
                return

        try:
            # 실행 중 표시
            self.running_fetchers.add(stock_code)
            self.last_fetch_time[stock_code] = datetime.now()

            logger.info(f"🔍 Fetcher triggered: {stock_code} (reason: {reason}, priority: {priority})")

            # Stock-specific Fetcher 실행
            from fetchers.stock_fetcher import stock_fetcher
            await stock_fetcher.fetch_single_stock(
                stock_code=stock_code,
                reason=reason,
                priority=priority
            )

            logger.info(f"✅ Fetcher completed: {stock_code}")

        except Exception as e:
            logger.error(f"❌ Fetcher error for {stock_code}: {e}", exc_info=True)

        finally:
            # 실행 중 표시 해제
            self.running_fetchers.discard(stock_code)

    def get_status(self) -> Dict:
        """
        Dispatcher 상태 조회 (디버깅용)

        Returns:
            {
                'running_count': 3,
                'running_stocks': ['005930', '035720', '068270'],
                'total_triggered': 157
            }
        """
        return {
            'running_count': len(self.running_fetchers),
            'running_stocks': list(self.running_fetchers),
            'total_triggered': len(self.last_fetch_time)
        }


# Singleton Instance
fetcher_dispatcher = FetcherDispatcher()
