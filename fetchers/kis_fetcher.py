"""
AEGIS v3.0 - KIS Fetcher
KIS API → DB 동기화 전담 (유일한 DB Writer)
"""
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import logging

from fetchers.kis_client import kis_client
from app.database import SessionLocal
from app.models.account import Portfolio, AccountSnapshot
from app.models.trade import TradeOrder, TradeExecution

logger = logging.getLogger(__name__)


class KISFetcher:
    """
    KIS API → DB 동기화 전담

    Write Only 역할:
    - KIS API에서 데이터 조회
    - DB에 동기화 (유일한 Writer)
    """

    def __init__(self):
        self.kis_client = kis_client

    async def sync_portfolio(self) -> None:
        """
        KIS API → DB 잔고 동기화

        실행 주기:
        - 장중: 1분마다
        - 장외: 10분마다

        동작:
        1. KIS API에서 잔고 조회 (KRX + NXT)
        2. DB Portfolio 테이블 Upsert
        3. 수량 0인 종목 삭제
        """
        db: Session = SessionLocal()

        try:
            # 1. KIS API에서 잔고 조회 (KRX + NXT 통합)
            balance_data = self.kis_client.get_combined_balance()

            logger.info(f"📊 Syncing portfolio: {len(balance_data)} stocks")

            # 2. DB 업데이트 (Upsert)
            for item in balance_data:
                stock_code = item.get('pdno', '')
                if not stock_code:
                    continue

                quantity = int(item.get('hldg_qty', 0))
                if quantity == 0:
                    continue

                portfolio = db.query(Portfolio).filter(
                    Portfolio.stock_code == stock_code
                ).first()

                if portfolio:
                    # 기존 종목 업데이트
                    portfolio.quantity = quantity
                    portfolio.avg_price = float(item.get('pchs_avg_pric', 0))
                    portfolio.current_price = float(item.get('prpr', 0))
                    portfolio.profit_rate = float(item.get('evlu_pfls_rt', 0))
                    portfolio.last_updated = datetime.now()

                    logger.debug(f"  📝 Updated: {stock_code} {quantity}주")
                else:
                    # 신규 종목 추가
                    new_portfolio = Portfolio(
                        stock_code=stock_code,
                        stock_name=item.get('prdt_name', ''),
                        quantity=quantity,
                        avg_price=float(item.get('pchs_avg_pric', 0)),
                        current_price=float(item.get('prpr', 0)),
                        profit_rate=float(item.get('evlu_pfls_rt', 0)),
                        bought_at=datetime.now()
                    )
                    db.add(new_portfolio)

                    logger.info(f"  ✅ Added: {stock_code} {quantity}주")

            # 3. 수량 0인 종목 삭제
            deleted = db.query(Portfolio).filter(
                Portfolio.quantity == 0
            ).delete()

            if deleted > 0:
                logger.info(f"  🗑️  Removed {deleted} zero-quantity stocks")

            db.commit()

            logger.info(f"✅ Portfolio synced: {len(balance_data)} stocks")

        except Exception as e:
            logger.error(f"❌ Portfolio sync failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    async def on_execution_notice(self, data: Dict) -> None:
        """
        체결 통보 수신 시 즉시 처리

        WebSocket H0STCNI0에서 호출됨 (10~50ms 지연)

        Args:
            data: WebSocket 체결 통보 데이터

        데이터 예시:
        {
            'ODNO': '0000117057',        # 주문번호
            'PDNO': '005930',            # 종목코드
            'CNTG_QTY': '10',            # 체결 수량
            'CNTG_UNPR': '52000',        # 체결 단가
            'STCK_CNTG_HOUR': '153000',  # 체결 시각 (HHMMSS)
            'SELN_BYOV_CLS': '02',       # 매수(02)/매도(01)
        }
        """
        db: Session = SessionLocal()

        try:
            order_no = data.get('ODNO')
            stock_code = data.get('PDNO')
            exec_qty = int(data.get('CNTG_QTY', 0))
            exec_price = int(data.get('CNTG_UNPR', 0))
            order_type = 'BUY' if data.get('SELN_BYOV_CLS') == '02' else 'SELL'

            logger.info(f"📡 Execution notice: {stock_code} {order_type} {exec_qty}주 @ {exec_price:,}원")

            # 1. trade_orders 상태 업데이트
            order = db.query(TradeOrder).filter(
                TradeOrder.order_no == order_no
            ).first()

            if not order:
                logger.warning(f"⚠️  Order not found: {order_no}")
                return

            order.filled_qty = (order.filled_qty or 0) + exec_qty

            # 평균 체결가 계산
            total_filled = order.filled_qty
            if total_filled > 0:
                prev_amount = (order.filled_qty - exec_qty) * (order.avg_filled_price or 0)
                new_amount = exec_qty * exec_price
                order.avg_filled_price = (prev_amount + new_amount) / total_filled

            # 상태 업데이트
            if order.filled_qty >= order.order_qty:
                order.status = 'FILLED'
                order.executed_at = datetime.now()
            else:
                order.status = 'PARTIALLY_FILLED'

            # 2. trade_executions 기록
            execution = TradeExecution(
                order_no=order_no,
                stock_code=stock_code,
                exec_qty=exec_qty,
                exec_price=exec_price,
                exec_amount=exec_qty * exec_price,
                executed_at=self._parse_time(data.get('STCK_CNTG_HOUR', ''))
            )
            db.add(execution)

            # 3. portfolio 업데이트
            if order_type == 'BUY':
                await self._update_portfolio_on_buy(db, stock_code, exec_qty, exec_price)
            else:
                await self._update_portfolio_on_sell(db, stock_code, exec_qty, exec_price)

            db.commit()

            logger.info(f"✅ Execution processed: {order_no} ({order.status})")

        except Exception as e:
            logger.error(f"❌ Execution processing failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    async def sync_execution(self) -> None:
        """
        미체결 주문 조회 및 동기화

        실행 주기:
        - 장중: 5분마다
        - 주문 직후: 30초 후 1회

        동작:
        1. KIS API에서 미체결 조회
        2. DB 주문 상태 업데이트
        3. 체결된 주문은 FILLED로 변경
        """
        db: Session = SessionLocal()

        try:
            # DB에서 미체결 주문 조회
            pending_orders = db.query(TradeOrder).filter(
                TradeOrder.status.in_(['PENDING', 'PARTIALLY_FILLED'])
            ).all()

            if not pending_orders:
                logger.debug("📋 No pending orders")
                return

            logger.info(f"🔍 Checking {len(pending_orders)} pending orders")

            # TODO: KIS API에서 미체결 조회 (TR_ID: TTTC8036R/TTTN8036R)
            # 현재는 간단히 잔고 조회로 확인
            balance_data = self.kis_client.get_combined_balance()
            balance_stocks = {item['pdno']: int(item.get('hldg_qty', 0)) for item in balance_data}

            for order in pending_orders:
                # 매수 주문: 잔고에 나타나면 체결된 것
                if order.order_type == 'BUY':
                    current_qty = balance_stocks.get(order.stock_code, 0)
                    if current_qty > 0:
                        order.status = 'FILLED'
                        order.executed_at = datetime.now()
                        logger.info(f"  ✅ Buy order filled: {order.stock_code}")

            db.commit()
            logger.info(f"✅ Execution sync completed")

        except Exception as e:
            logger.error(f"❌ Execution sync failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    async def _update_portfolio_on_buy(
        self,
        db: Session,
        stock_code: str,
        quantity: int,
        price: int
    ) -> None:
        """
        매수 체결 시 포트폴리오 업데이트

        Args:
            db: DB 세션
            stock_code: 종목코드
            quantity: 체결 수량
            price: 체결 가격
        """
        portfolio = db.query(Portfolio).filter(
            Portfolio.stock_code == stock_code
        ).first()

        if portfolio:
            # 기존 종목 - 평균단가 재계산
            total_qty = portfolio.quantity + quantity
            total_cost = (portfolio.quantity * portfolio.avg_price) + (quantity * price)
            portfolio.avg_price = total_cost / total_qty
            portfolio.quantity = total_qty
            portfolio.last_updated = datetime.now()

            logger.debug(f"  📝 Portfolio updated (buy): {stock_code} {total_qty}주")
        else:
            # 신규 종목
            new_portfolio = Portfolio(
                stock_code=stock_code,
                stock_name="",  # 나중에 sync_portfolio에서 채워짐
                quantity=quantity,
                avg_price=float(price),
                current_price=float(price),
                profit_rate=0.0,
                bought_at=datetime.now()
            )
            db.add(new_portfolio)

            logger.debug(f"  ✅ Portfolio created (buy): {stock_code} {quantity}주")

    async def _update_portfolio_on_sell(
        self,
        db: Session,
        stock_code: str,
        quantity: int,
        price: int
    ) -> None:
        """
        매도 체결 시 포트폴리오 업데이트

        Args:
            db: DB 세션
            stock_code: 종목코드
            quantity: 체결 수량
            price: 체결 가격
        """
        portfolio = db.query(Portfolio).filter(
            Portfolio.stock_code == stock_code
        ).first()

        if portfolio:
            portfolio.quantity -= quantity

            if portfolio.quantity <= 0:
                db.delete(portfolio)
                logger.debug(f"  🗑️  Portfolio removed (sell): {stock_code}")
            else:
                portfolio.last_updated = datetime.now()
                logger.debug(f"  📝 Portfolio updated (sell): {stock_code} {portfolio.quantity}주")
        else:
            logger.warning(f"⚠️  Portfolio not found for sell: {stock_code}")

    def _parse_time(self, time_str: str) -> datetime:
        """
        체결 시각 파싱 (HHMMSS → datetime)

        Args:
            time_str: 시각 문자열 (예: "153000")

        Returns:
            datetime 객체
        """
        try:
            if len(time_str) == 6:
                hour = int(time_str[0:2])
                minute = int(time_str[2:4])
                second = int(time_str[4:6])
                now = datetime.now()
                return now.replace(hour=hour, minute=minute, second=second, microsecond=0)
        except Exception as e:
            logger.warning(f"⚠️  Failed to parse time: {time_str} ({e})")

        return datetime.now()


# Singleton Instance
kis_fetcher = KISFetcher()
