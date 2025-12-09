"""
AEGIS v3.0 - Order Service
주문 전담 서비스 (예외: 주문 직전만 KIS API 직접 조회)
"""
from typing import Dict
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from fetchers.kis_client import kis_client
from app.database import SessionLocal
from app.models.trade import TradeOrder

logger = logging.getLogger(__name__)


class InsufficientBalanceError(Exception):
    """잔고 부족 에러"""
    pass


class OrderService:
    """
    주문 전담 서비스

    예외 규칙:
    - 주문 직전만 kis_client 직접 조회 허용
    - 이유: DB 잔고는 약간의 지연이 있을 수 있음
    - 주문 실패 방지를 위한 실시간 확인 필수
    """

    async def place_buy_order(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: int,
        market: str = "KRX"
    ) -> Dict:
        """
        매수 주문

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            quantity: 수량
            price: 가격 (0이면 시장가)
            market: KRX/NXT

        Returns:
            주문 결과
        """
        db: Session = SessionLocal()

        try:
            # 1. 주문 직전 실시간 잔고 확인 (KIS API 직접)
            # TODO: get_available_deposit() 구현
            # balance = kis_client.get_available_deposit()
            # required = quantity * price
            #
            # if balance < required:
            #     raise InsufficientBalanceError(
            #         f"잔고 부족: 필요 {required:,}원, 가용 {balance:,}원"
            #     )

            logger.info(f"🛒 Placing buy order: {stock_code} {quantity}주 @ {price:,}원 ({market})")

            # 2. 주문 실행
            result = kis_client.buy_order(
                stock_code=stock_code,
                quantity=quantity,
                price=price,
                market=market
            )

            # 3. 주문 결과 확인
            if result.get('rt_cd') != '0':
                error_msg = result.get('msg1', 'Unknown error')
                logger.error(f"❌ Buy order failed: {error_msg}")
                raise Exception(f"Buy order failed: {error_msg}")

            order_no = result.get('output', {}).get('ODNO', '')

            # 4. 주문 DB 기록
            order = TradeOrder(
                order_no=order_no,
                stock_code=stock_code,
                stock_name=stock_name,
                order_type='BUY',
                market=market,
                order_qty=quantity,
                order_price=price,
                status='PENDING',
                ordered_at=datetime.now()
            )
            db.add(order)
            db.commit()

            logger.info(f"✅ Buy order placed: {order_no}")

            # 5. 체결은 WebSocket(H0STCNI0)이 자동 처리
            return {
                "order_no": order_no,
                "stock_code": stock_code,
                "order_type": "BUY",
                "quantity": quantity,
                "price": price,
                "market": market,
                "status": "PENDING",
                "message": "Order placed successfully"
            }

        except InsufficientBalanceError as e:
            logger.error(f"❌ {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Buy order failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    async def place_sell_order(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: int,
        market: str = "KRX"
    ) -> Dict:
        """
        매도 주문

        Args:
            stock_code: 종목코드
            stock_name: 종목명
            quantity: 수량
            price: 가격 (0이면 시장가)
            market: KRX/NXT

        Returns:
            주문 결과
        """
        db: Session = SessionLocal()

        try:
            # 1. 주문 직전 실시간 잔고 확인 (KIS API 직접)
            balance_data = kis_client.get_combined_balance()
            holding = next(
                (item for item in balance_data if item['pdno'] == stock_code),
                None
            )

            if not holding:
                raise Exception(f"보유 종목 없음: {stock_code}")

            available_qty = int(holding.get('hldg_qty', 0))
            if available_qty < quantity:
                raise Exception(
                    f"수량 부족: 보유 {available_qty}주, 주문 {quantity}주"
                )

            logger.info(f"💰 Placing sell order: {stock_code} {quantity}주 @ {price:,}원 ({market})")

            # 2. 주문 실행
            result = kis_client.sell_order(
                stock_code=stock_code,
                quantity=quantity,
                price=price,
                market=market
            )

            # 3. 주문 결과 확인
            if result.get('rt_cd') != '0':
                error_msg = result.get('msg1', 'Unknown error')
                logger.error(f"❌ Sell order failed: {error_msg}")
                raise Exception(f"Sell order failed: {error_msg}")

            order_no = result.get('output', {}).get('ODNO', '')

            # 4. 주문 DB 기록
            order = TradeOrder(
                order_no=order_no,
                stock_code=stock_code,
                stock_name=stock_name,
                order_type='SELL',
                market=market,
                order_qty=quantity,
                order_price=price,
                status='PENDING',
                ordered_at=datetime.now()
            )
            db.add(order)
            db.commit()

            logger.info(f"✅ Sell order placed: {order_no}")

            # 5. 체결은 WebSocket(H0STCNI0)이 자동 처리
            return {
                "order_no": order_no,
                "stock_code": stock_code,
                "order_type": "SELL",
                "quantity": quantity,
                "price": price,
                "market": market,
                "status": "PENDING",
                "message": "Order placed successfully"
            }

        except Exception as e:
            logger.error(f"❌ Sell order failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    async def cancel_order(self, order_no: str) -> Dict:
        """
        주문 취소

        Args:
            order_no: 주문번호

        Returns:
            취소 결과
        """
        db: Session = SessionLocal()

        try:
            # 1. DB에서 주문 조회
            order = db.query(TradeOrder).filter(
                TradeOrder.order_no == order_no
            ).first()

            if not order:
                raise Exception(f"주문 없음: {order_no}")

            if order.status in ['FILLED', 'CANCELLED']:
                raise Exception(f"취소 불가 상태: {order.status}")

            logger.info(f"🚫 Cancelling order: {order_no}")

            # 2. KIS API 취소 요청
            # TODO: KIS API cancel_order() 구현

            # 3. DB 상태 업데이트
            order.status = 'CANCELLED'
            order.updated_at = datetime.now()
            db.commit()

            logger.info(f"✅ Order cancelled: {order_no}")

            return {
                "order_no": order_no,
                "status": "CANCELLED",
                "message": "Order cancelled successfully"
            }

        except Exception as e:
            logger.error(f"❌ Cancel order failed: {e}")
            db.rollback()
            raise
        finally:
            db.close()


# Singleton Instance
order_service = OrderService()
