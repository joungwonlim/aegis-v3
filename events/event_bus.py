"""
AEGIS v3.0 - Event Bus
Pub/Sub pattern for event-driven architecture

역할:
- 이벤트 발행/구독
- 즉시 실행 (0.01초 이내)
- Fetcher 즉시 트리거
"""
import asyncio
import logging
from datetime import datetime
from typing import Callable, Dict, List, Any
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """이벤트 타입"""
    # Schedule-based
    SCHEDULE_TRIGGER = "schedule_trigger"  # 스케줄 실행

    # WebSocket-based
    EXECUTION_NOTICE = "execution_notice"  # 체결 통보 (매수/매도 체결)

    # News-based
    BREAKING_NEWS = "breaking_news"  # 속보 뉴스

    # Disclosure-based
    DART_DISCLOSURE = "dart_disclosure"  # DART 공시

    # Market-based
    HOT_STOCK_FOUND = "hot_stock_found"  # 급등주 발견 (Market Scanner)
    MARKET_REGIME_CHANGE = "market_regime_change"  # 시장 지표 급변 (VIX, NASDAQ 등)

    # Pipeline-based
    BRAIN_ANALYSIS_COMPLETE = "brain_analysis_complete"  # Brain 분석 완료
    ORDER_EXECUTED = "order_executed"  # 주문 실행 완료


class Event:
    """이벤트 객체"""

    def __init__(self, event_type: EventType, data: Dict[str, Any]):
        """
        이벤트 생성

        Args:
            event_type: 이벤트 타입
            data: 이벤트 데이터
                - stock_code: 종목 코드 (필수)
                - 기타 이벤트별 데이터
        """
        self.type = event_type
        self.data = data
        self.timestamp = datetime.now()

    def __repr__(self):
        return f"Event(type={self.type.value}, stock_code={self.data.get('stock_code', 'N/A')}, time={self.timestamp.strftime('%H:%M:%S')})"


class EventBus:
    """
    이벤트 버스 (Singleton)

    역할:
    - 이벤트 구독 (subscribe)
    - 이벤트 발행 (publish)
    - 구독자에게 즉시 전달 (0.01초)

    설계 원칙:
    - Pub/Sub 패턴
    - 비동기 처리 (asyncio)
    - 오류 격리 (한 구독자 오류가 다른 구독자에 영향 없음)
    """

    def __init__(self):
        self.subscribers: Dict[EventType, List[Callable]] = {}
        self.event_history: List[Event] = []  # 디버깅용
        self.max_history = 100  # 최근 100개 이벤트만 보관

    def subscribe(self, event_type: EventType, callback: Callable):
        """
        이벤트 구독

        Args:
            event_type: 구독할 이벤트 타입
            callback: 이벤트 발생 시 호출할 비동기 함수
                - async def callback(event: Event) -> None

        Example:
            event_bus.subscribe(
                EventType.EXECUTION_NOTICE,
                self.on_execution_notice
            )
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(callback)
        logger.info(f"📡 Subscribed to {event_type.value}: {callback.__name__}")

    async def publish(self, event: Event):
        """
        이벤트 발행 (즉시 실행)

        Args:
            event: 발행할 이벤트

        동작:
        1. 이벤트 히스토리에 기록
        2. 해당 타입의 모든 구독자에게 즉시 전달
        3. 구독자 비동기 병렬 실행
        4. 오류 발생 시 격리 (다른 구독자는 계속 실행)

        Example:
            await event_bus.publish(Event(
                EventType.EXECUTION_NOTICE,
                {"stock_code": "005930", "quantity": 10, "price": 78000}
            ))
        """
        # 이벤트 히스토리 저장
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        logger.info(f"📢 Event published: {event}")

        # 구독자 확인
        if event.type not in self.subscribers:
            logger.debug(f"⚠️  No subscribers for {event.type.value}")
            return

        # 모든 구독자에게 병렬 전달
        tasks = []
        for callback in self.subscribers[event.type]:
            tasks.append(self._safe_callback(callback, event))

        # 병렬 실행 (0.01초 이내)
        await asyncio.gather(*tasks)

    async def _safe_callback(self, callback: Callable, event: Event):
        """
        안전한 콜백 실행 (오류 격리)

        Args:
            callback: 실행할 콜백
            event: 이벤트 객체
        """
        try:
            await callback(event)
        except Exception as e:
            logger.error(
                f"❌ Event handler error: {callback.__name__} for {event.type.value}",
                exc_info=True
            )

    def get_recent_events(self, limit: int = 10) -> List[Event]:
        """
        최근 이벤트 조회 (디버깅용)

        Args:
            limit: 조회할 이벤트 수

        Returns:
            최근 이벤트 리스트
        """
        return self.event_history[-limit:]

    def get_subscriber_count(self, event_type: EventType) -> int:
        """
        특정 이벤트 타입의 구독자 수

        Args:
            event_type: 이벤트 타입

        Returns:
            구독자 수
        """
        return len(self.subscribers.get(event_type, []))


# Singleton Instance
event_bus = EventBus()
