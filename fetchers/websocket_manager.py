"""
AEGIS v3.0 - WebSocket Manager
40개 슬롯 제한 하에서 우선순위 기반 동적 구독 관리
"""
import asyncio
import json
import websockets
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from fetchers.kis_client import kis_client
from fetchers.kis_fetcher import kis_fetcher
from services.portfolio_service import portfolio_service

logger = logging.getLogger(__name__)


@dataclass
class WebSocketSlot:
    """WebSocket 구독 슬롯"""
    stock_code: str
    stock_name: str
    tr_id: str  # H0STCNT0, H0STASP0, H0STPGM0
    priority: int  # 1=보유, 2=AI picks, 3=급등주
    subscribed_at: datetime
    last_data_at: Optional[datetime] = None

    def is_stale(self, threshold_minutes: int = 30) -> bool:
        """
        데이터 수신이 오래되었는지 확인

        Args:
            threshold_minutes: 임계값 (분)

        Returns:
            오래된 데이터 여부
        """
        if not self.last_data_at:
            return False
        elapsed = (datetime.now() - self.last_data_at).total_seconds() / 60
        return elapsed > threshold_minutes


class KISWebSocketManager:
    """
    KIS WebSocket 슬롯 관리자

    특징:
    - 40개 슬롯 제한
    - 우선순위 기반 자동 관리
    - 재연결 처리

    우선순위:
    - Priority 1: 보유종목 (항상 유지)
    - Priority 2: AI Daily Picks (DeepSeek R1)
    - Priority 3: 급등주/거래량 상위 (동적)
    """

    MAX_SLOTS = 40

    def __init__(self):
        self.kis_client = kis_client
        self.slots: Dict[str, WebSocketSlot] = {}
        self.ws_connection = None
        self.is_running = False

    async def start(self):
        """WebSocket 연결 및 리스너 시작"""
        logger.info("🚀 Starting WebSocket Manager...")

        # WebSocket 연결
        await self.kis_client.connect_websocket()
        self.ws_connection = self.kis_client.ws_connection

        if not self.ws_connection:
            logger.error("❌ WebSocket connection failed")
            return

        self.is_running = True

        # 체결 통보 구독 (슬롯 소비 안함)
        await self.kis_client.subscribe_execution_notice()

        # 데이터 수신 루프 시작
        asyncio.create_task(self.listen())

        logger.info(f"✅ WebSocket Manager started (max_slots={self.MAX_SLOTS})")

    async def subscribe(
        self,
        stock_code: str,
        stock_name: str,
        priority: int,
        tr_id: str = "H0STCNT0"
    ) -> bool:
        """
        종목 구독

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            priority: 우선순위 (1, 2, 3)
            tr_id: TR_ID (기본: H0STCNT0 실시간 체결가)

        Returns:
            구독 성공 여부
        """
        # 이미 구독중
        if stock_code in self.slots:
            logger.debug(f"Already subscribed: {stock_code}")
            return True

        # 슬롯 부족 - 낮은 우선순위 제거
        if len(self.slots) >= self.MAX_SLOTS:
            evicted = await self.evict_lowest_priority(priority)
            if not evicted:
                logger.warning(f"⚠️  Cannot subscribe {stock_code}: slots full, priority too low")
                return False

        # WebSocket 구독 메시지 전송
        try:
            subscribe_msg = {
                "header": {
                    "approval_key": self.kis_client.ws_approval_key,
                    "custtype": "P",
                    "tr_type": "1",  # 1=구독
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": tr_id,
                        "tr_key": stock_code
                    }
                }
            }

            await self.ws_connection.send(json.dumps(subscribe_msg))

            # 슬롯 기록
            self.slots[stock_code] = WebSocketSlot(
                stock_code=stock_code,
                stock_name=stock_name,
                tr_id=tr_id,
                priority=priority,
                subscribed_at=datetime.now()
            )

            logger.info(
                f"📡 Subscribed: {stock_code} ({stock_name}) "
                f"priority={priority}, slots={len(self.slots)}/{self.MAX_SLOTS}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Subscribe failed: {stock_code} - {e}")
            return False

    async def unsubscribe(self, stock_code: str) -> bool:
        """
        종목 구독 해제

        Args:
            stock_code: 종목코드

        Returns:
            해제 성공 여부
        """
        if stock_code not in self.slots:
            logger.debug(f"Not subscribed: {stock_code}")
            return True

        slot = self.slots[stock_code]

        # WebSocket 구독 해제 메시지 전송
        try:
            unsubscribe_msg = {
                "header": {
                    "approval_key": self.kis_client.ws_approval_key,
                    "custtype": "P",
                    "tr_type": "2",  # 2=해제
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": slot.tr_id,
                        "tr_key": stock_code
                    }
                }
            }

            await self.ws_connection.send(json.dumps(unsubscribe_msg))

            # 슬롯 제거
            del self.slots[stock_code]

            logger.info(
                f"🔕 Unsubscribed: {stock_code} ({slot.stock_name}) "
                f"slots={len(self.slots)}/{self.MAX_SLOTS}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Unsubscribe failed: {stock_code} - {e}")
            return False

    async def evict_lowest_priority(self, required_priority: int) -> bool:
        """
        가장 낮은 우선순위 종목 제거

        Args:
            required_priority: 필요한 우선순위

        Returns:
            제거 성공 여부
        """
        # Priority 3 (급등주) 중 가장 오래된 것 찾기
        priority_3_slots = [
            (code, slot) for code, slot in self.slots.items()
            if slot.priority == 3
        ]

        if not priority_3_slots:
            # Priority 3이 없으면 Priority 2 확인
            if required_priority <= 2:
                priority_2_slots = [
                    (code, slot) for code, slot in self.slots.items()
                    if slot.priority == 2
                ]
                if priority_2_slots:
                    # Priority 2 중 가장 오래된 것 제거
                    oldest = min(priority_2_slots, key=lambda x: x[1].subscribed_at)
                    await self.unsubscribe(oldest[0])
                    logger.info(f"🔄 Evicted: {oldest[0]} (priority=2)")
                    return True

            logger.warning("⚠️  No slots to evict")
            return False

        # Priority 3 중 가장 오래된 슬롯 제거
        oldest = min(priority_3_slots, key=lambda x: x[1].subscribed_at)
        await self.unsubscribe(oldest[0])
        logger.info(f"🔄 Evicted: {oldest[0]} (priority=3)")
        return True

    async def sync_with_portfolio(self):
        """
        보유종목과 동기화 (Priority 1)

        동작:
        1. 현재 보유종목 조회
        2. 구독 추가/해제
        """
        try:
            # 현재 보유종목 조회
            portfolio = await portfolio_service.get_portfolio()
            portfolio_codes = {p.stock_code for p in portfolio}

            # 현재 Priority 1 슬롯
            current_priority1 = {
                code for code, slot in self.slots.items()
                if slot.priority == 1
            }

            # 추가할 종목 (보유하는데 구독 안됨)
            to_add = portfolio_codes - current_priority1
            for code in to_add:
                stock = next(p for p in portfolio if p.stock_code == code)
                await self.subscribe(code, stock.stock_name, priority=1)

            # 제거할 종목 (구독중인데 보유 안함)
            to_remove = current_priority1 - portfolio_codes
            for code in to_remove:
                await self.unsubscribe(code)

            logger.info(f"✅ Portfolio synced: +{len(to_add)}, -{len(to_remove)}")

        except Exception as e:
            logger.error(f"❌ Portfolio sync failed: {e}")

    async def update_daily_picks(self, picks: list):
        """
        Daily Picks 업데이트 (Priority 2)

        Args:
            picks: [{"stock_code": "005930", "stock_name": "삼성전자"}, ...]

        동작:
        1. 기존 Priority 2 전체 해제
        2. 새로운 Picks 구독 (최대 20개)
        """
        try:
            # 기존 Priority 2 해제
            priority_2_slots = [
                code for code, slot in self.slots.items()
                if slot.priority == 2
            ]

            for code in priority_2_slots:
                await self.unsubscribe(code)

            logger.info(f"🔄 Removed {len(priority_2_slots)} old daily picks")

            # 새로운 Picks 구독 (최대 20개)
            added = 0
            for pick in picks[:20]:
                result = await self.subscribe(
                    stock_code=pick["stock_code"],
                    stock_name=pick["stock_name"],
                    priority=2
                )
                if result:
                    added += 1

            logger.info(f"✅ Daily picks updated: {added} stocks")

        except Exception as e:
            logger.error(f"❌ Daily picks update failed: {e}")

    async def listen(self):
        """WebSocket 데이터 수신 루프"""
        logger.info("👂 WebSocket listener started")

        while self.is_running:
            try:
                if not self.ws_connection:
                    logger.warning("⚠️  WebSocket not connected")
                    await asyncio.sleep(5)
                    continue

                async for message in self.ws_connection:
                    data = json.loads(message)
                    await self.handle_message(data)

            except websockets.exceptions.ConnectionClosed:
                logger.warning("⚠️  WebSocket connection closed, reconnecting...")
                await self.reconnect()

            except Exception as e:
                logger.error(f"❌ Listener error: {e}")
                await asyncio.sleep(1)

        logger.info("🛑 WebSocket listener stopped")

    async def handle_message(self, data: Dict):
        """
        WebSocket 메시지 처리

        Args:
            data: WebSocket 메시지
        """
        try:
            tr_id = data.get('header', {}).get('tr_id', '')

            # 체결 통보 (H0STCNI0)
            if tr_id == 'H0STCNI0':
                await kis_fetcher.on_execution_notice(data)
                return

            # 실시간 체결가 (H0STCNT0)
            body = data.get('body', {})
            output = body.get('output', {})
            stock_code = output.get('MKSC_SHRN_ISCD', '')

            if tr_id == 'H0STCNT0' and stock_code in self.slots:
                # last_data_at 갱신
                self.slots[stock_code].last_data_at = datetime.now()

                # 현재가 정보
                current_price = int(output.get('STCK_PRPR', 0))
                change_rate = float(output.get('PRDY_CTRT', 0))

                logger.debug(
                    f"📊 {stock_code}: {current_price:,}원 ({change_rate:+.2f}%)"
                )

                # TODO: 시세 데이터 DB 저장 또는 Brain 전달

            # 실시간 호가 (H0STASP0)
            elif tr_id == 'H0STASP0' and stock_code in self.slots:
                self.slots[stock_code].last_data_at = datetime.now()

                # 호가 정보
                ask_price_1 = int(output.get('ASKP1', 0))
                bid_price_1 = int(output.get('BIDP1', 0))

                logger.debug(
                    f"📈 {stock_code}: 매도 {ask_price_1:,}원 / 매수 {bid_price_1:,}원"
                )

                # TODO: 호가 데이터 DB 저장

        except Exception as e:
            logger.error(f"❌ Message handling failed: {e}")

    async def reconnect(self):
        """WebSocket 재연결"""
        logger.info("🔄 Reconnecting WebSocket...")

        try:
            await self.kis_client.connect_websocket()
            self.ws_connection = self.kis_client.ws_connection

            if not self.ws_connection:
                logger.error("❌ Reconnection failed")
                await asyncio.sleep(10)
                return

            # 기존 구독 전체 재구독
            await self.resubscribe_all()

            logger.info("✅ WebSocket reconnected")

        except Exception as e:
            logger.error(f"❌ Reconnection error: {e}")
            await asyncio.sleep(10)

    async def resubscribe_all(self):
        """모든 슬롯 재구독"""
        logger.info("🔄 Resubscribing all slots...")

        slots_copy = list(self.slots.items())
        self.slots.clear()

        resubscribed = 0
        for code, slot in slots_copy:
            result = await self.subscribe(
                stock_code=code,
                stock_name=slot.stock_name,
                priority=slot.priority,
                tr_id=slot.tr_id
            )
            if result:
                resubscribed += 1

        logger.info(f"✅ Resubscribed: {resubscribed}/{len(slots_copy)} slots")

    async def get_status(self) -> dict:
        """
        WebSocket Manager 상태 조회

        Returns:
            상태 정보
        """
        priority_counts = {1: 0, 2: 0, 3: 0}
        for slot in self.slots.values():
            priority_counts[slot.priority] += 1

        return {
            "is_running": self.is_running,
            "total_slots": len(self.slots),
            "max_slots": self.MAX_SLOTS,
            "available_slots": self.MAX_SLOTS - len(self.slots),
            "priority_1": priority_counts[1],  # 보유종목
            "priority_2": priority_counts[2],  # AI picks
            "priority_3": priority_counts[3],  # 급등주
        }

    async def stop(self):
        """WebSocket Manager 정지"""
        logger.info("🛑 Stopping WebSocket Manager...")

        self.is_running = False

        # 모든 구독 해제
        for code in list(self.slots.keys()):
            await self.unsubscribe(code)

        # WebSocket 연결 종료
        await self.kis_client.close()

        logger.info("✅ WebSocket Manager stopped")


# Singleton Instance
ws_manager = KISWebSocketManager()
