"""
AEGIS v3.0 - Portfolio Manager
보유 종목 관리 및 매도 판단

역할:
- 1분마다 보유 종목 체크
- 손절/익절/트레일링 스탑 조건 감시
- 즉시 매도 실행

핵심 원칙:
"손실은 짧게(-3%), 수익은 길게(끝까지 추적)"
"""
import logging
from datetime import datetime, date
from typing import List, Dict, Optional

from app.database import get_db
from app.models.portfolio import Portfolio
from fetchers.kis_fetcher import kis_fetcher
from fetchers.stock_fetcher import stock_fetcher

logger = logging.getLogger(__name__)


class PortfolioManager:
    """
    포트폴리오 관리자 (매도 판사)

    역할:
    - 1분마다 실행
    - 매도 조건 체크 (손절/익절/트레일링)
    - 즉시 주문 실행
    """

    def __init__(self):
        # 매도 조건 설정
        self.STOP_LOSS_PCT = -3.0  # -3% 손절 (전량)
        self.PARTIAL_SELL_1_PCT = 3.5  # +3.5% 분할 매도 (50%)
        self.TRAILING_START_PCT = 5.0  # +5%부터 트레일링 시작
        self.PARTIAL_SELL_2_PCT = 5.5  # +5.5% 익절 (전량)
        self.TRAILING_GAP_PCT = 2.0  # 고점 대비 -2% 빠지면 매도
        self.TAKE_PROFIT_PCT = 8.0  # +8% 강화 트레일링 (고점-1.5%)
        self.STRONG_TRAILING_GAP_PCT = 1.5  # +8% 이상 시 고점 대비 -1.5%

        # AI 손절 기준
        self.AI_PANIC_SCORE = 30  # AI 점수 30점 이하 시 긴급 매도

    async def run_cycle(self) -> Dict:
        """
        1분마다 실행되는 매도 감시 루틴

        Returns:
            {
                'checked': 5,
                'stop_loss': 1,
                'take_profit': 0,
                'trailing_stop': 1,
                'ai_panic': 0
            }
        """
        logger.info("🔍 Portfolio Manager: Checking holdings...")

        result = {
            'checked': 0,
            'stop_loss': 0,
            'partial_sell_1': 0,
            'partial_sell_2': 0,
            'take_profit': 0,
            'trailing_stop': 0,
            'strong_trailing': 0,
            'ai_panic': 0,
            'errors': []
        }

        try:
            # 1️⃣ KIS 잔고 싱크 (최신 현재가 및 수익률 업데이트)
            await stock_fetcher.fetch_portfolio_holdings()

            # 2️⃣ DB에서 보유 종목 조회
            db = next(get_db())
            holdings = db.query(Portfolio).filter(
                Portfolio.quantity > 0
            ).all()

            result['checked'] = len(holdings)
            logger.info(f"  📋 보유 종목: {len(holdings)}개")

            # 3️⃣ 종목별 매도 조건 체크
            for item in holdings:
                sell_decision = await self._judge_stock(item, db)

                if sell_decision:
                    # 매도 실행
                    success = await self._execute_sell(item, sell_decision)

                    if success:
                        # 결과 카운트
                        reason_type = sell_decision['reason_type']
                        result[reason_type] = result.get(reason_type, 0) + 1

            db.commit()
            logger.info(f"✅ Portfolio Manager cycle complete")

        except Exception as e:
            logger.error(f"❌ Portfolio Manager error: {e}", exc_info=True)
            result['errors'].append(str(e))

        finally:
            try:
                db.close()
            except:
                pass

        return result

    async def _judge_stock(self, item: Portfolio, db) -> Optional[Dict]:
        """
        종목별 매도 조건 판단

        Args:
            item: Portfolio 객체
            db: DB 세션

        Returns:
            매도 결정 시:
            {
                'reason': '칼손절 (Stop Loss)',
                'reason_type': 'stop_loss',
                'price': 0,  # 시장가
                'confidence': 100
            }

            매도 안 함 시: None
        """
        stock_code = item.stock_code
        stock_name = item.stock_name or stock_code
        current_price = item.current_price
        profit_rate = item.profit_rate  # (%)

        logger.debug(f"  🔍 {stock_name}: 현재 {current_price:,}원 ({profit_rate:+.2f}%)")

        # 0️⃣ 최고가 갱신 (트레일링 스탑용)
        highest_price = item.max_price_reached or item.avg_price

        if current_price > highest_price:
            # 새 고점 갱신
            item.max_price_reached = current_price
            logger.debug(f"  📈 {stock_name}: 신고가 갱신 {current_price:,}원")

        # --- 매도 조건 체크 (우선순위 순) ---

        # 1️⃣ 손절 (Stop Loss) - 전량 매도
        if profit_rate <= self.STOP_LOSS_PCT:
            logger.warning(f"  🔴 {stock_name}: 손절 조건 ({profit_rate:.2f}% <= {self.STOP_LOSS_PCT}%)")
            return {
                'reason': f'칼손절 (Stop Loss) - {profit_rate:.2f}%',
                'reason_type': 'stop_loss',
                'sell_ratio': 1.0,  # 전량
                'price': 0,  # 시장가
                'confidence': 100
            }

        # 2️⃣ 분할 매도 1단계 (+3.5%) - 50% 매도
        if profit_rate >= self.PARTIAL_SELL_1_PCT and profit_rate < self.PARTIAL_SELL_2_PCT:
            # 이미 분할 매도했는지 확인 (수량이 원래의 50% 이하면 이미 매도함)
            if not hasattr(item, 'partial_sold_1') or not item.partial_sold_1:
                logger.info(f"  🟡 {stock_name}: 1차 분할 매도 (+{profit_rate:.2f}%, 50% 매도)")
                return {
                    'reason': f'1차 분할 매도 (+{profit_rate:.2f}%)',
                    'reason_type': 'partial_sell_1',
                    'sell_ratio': 0.5,  # 50%
                    'price': 0,  # 시장가
                    'confidence': 85,
                    'mark_partial_sold': True  # 분할 매도 플래그
                }

        # 3️⃣ 트레일링 스탑 (+5% 달성 후 활성화)
        # 수익이 5% 이상 났던 종목이, 고점 대비 2% 빠지면 매도
        max_profit_rate = (highest_price - item.avg_price) / item.avg_price * 100

        if max_profit_rate >= self.TRAILING_START_PCT:
            drop_from_high = (highest_price - current_price) / highest_price * 100

            # 3-1. 강화 트레일링 (+8% 이상)
            if max_profit_rate >= self.TAKE_PROFIT_PCT:
                if drop_from_high >= self.STRONG_TRAILING_GAP_PCT:
                    logger.warning(f"  🟠 {stock_name}: 강화 트레일링 스탑 (고점 {highest_price:,}원 대비 -{drop_from_high:.1f}%)")
                    return {
                        'reason': f'강화 트레일링 스탑 (고점 대비 -{drop_from_high:.1f}%)',
                        'reason_type': 'strong_trailing',
                        'sell_ratio': 1.0,  # 전량
                        'price': 0,  # 시장가
                        'confidence': 95
                    }

            # 3-2. 일반 트레일링 (+5% ~ +8%)
            else:
                if drop_from_high >= self.TRAILING_GAP_PCT:
                    logger.warning(f"  🟡 {stock_name}: 트레일링 스탑 (고점 {highest_price:,}원 대비 -{drop_from_high:.1f}%)")
                    return {
                        'reason': f'트레일링 스탑 (고점 대비 -{drop_from_high:.1f}%)',
                        'reason_type': 'trailing_stop',
                        'sell_ratio': 1.0,  # 전량
                        'price': 0,  # 시장가
                        'confidence': 90
                    }

        # 4️⃣ 2차 익절 (+5.5%) - 전량 매도
        if profit_rate >= self.PARTIAL_SELL_2_PCT:
            logger.info(f"  🟢 {stock_name}: 2차 익절 (+{profit_rate:.2f}%, 전량 매도)")
            return {
                'reason': f'2차 익절 (전량) (+{profit_rate:.2f}%)',
                'reason_type': 'partial_sell_2',
                'sell_ratio': 1.0,  # 전량
                'price': 0,  # 시장가
                'confidence': 85
            }

        # 4️⃣ AI 손절 (AI Panic Sell)
        # TODO: AI Score 조회 후 판단
        # ai_score = await self._get_ai_score(stock_code)
        # if ai_score and ai_score < self.AI_PANIC_SCORE:
        #     logger.warning(f"  🚨 {stock_name}: AI 경고 (점수 {ai_score}점)")
        #     return {
        #         'reason': f'AI 경고 (점수 {ai_score}점 급락)',
        #         'reason_type': 'ai_panic',
        #         'price': 0,
        #         'confidence': 80
        #     }

        # 매도 조건 없음
        return None

    async def _execute_sell(self, item: Portfolio, decision: Dict) -> bool:
        """
        매도 주문 실행 (분할 매도 지원)

        Args:
            item: Portfolio 객체
            decision: 매도 결정 정보
                - reason: 매도 사유
                - sell_ratio: 매도 비율 (0.5 = 50%, 1.0 = 전량)
                - mark_partial_sold: 분할 매도 플래그 설정 여부

        Returns:
            True: 주문 성공
            False: 주문 실패
        """
        stock_code = item.stock_code
        stock_name = item.stock_name or stock_code
        total_quantity = item.quantity
        reason = decision['reason']
        sell_ratio = decision.get('sell_ratio', 1.0)  # 기본값: 전량
        mark_partial_sold = decision.get('mark_partial_sold', False)

        # 매도 수량 계산
        sell_quantity = int(total_quantity * sell_ratio)

        if sell_quantity <= 0:
            logger.warning(f"  ⚠️  매도 수량 0주, 주문 스킵")
            return False

        logger.info(f"📉 매도 신호 발생!")
        logger.info(f"  종목: {stock_name} ({stock_code})")

        if sell_ratio < 1.0:
            logger.info(f"  수량: {sell_quantity}주 / {total_quantity}주 ({sell_ratio*100:.0f}% 분할 매도)")
        else:
            logger.info(f"  수량: {sell_quantity}주 (전량)")

        logger.info(f"  사유: {reason}")

        try:
            # TODO: 실제 주문 전송 (시장가)
            # result = await kis_fetcher.send_order(
            #     stock_code=stock_code,
            #     order_type='SELL',
            #     quantity=sell_quantity,
            #     price=0,  # 시장가
            #     reason=reason
            # )

            # 임시: 로그만 출력
            logger.info(f"  ⚠️  매도 주문 실행 (TODO: KIS API 연동 필요)")

            # 분할 매도 플래그 설정
            if mark_partial_sold:
                item.partial_sold_1 = True
                logger.debug(f"  ✅ 분할 매도 플래그 설정 완료")

            # TODO: 텔레그램 알림
            # await send_telegram_alert(f"📉 매도: {stock_name}\n수량: {sell_quantity}주\n사유: {reason}")

            return True

        except Exception as e:
            logger.error(f"  ❌ 매도 주문 실패: {e}", exc_info=True)
            return False

    async def _get_ai_score(self, stock_code: str) -> Optional[int]:
        """
        AI Score 조회

        TODO: Brain Analyzer 또는 daily_picks 테이블에서 조회

        Returns:
            AI Score (0~100) 또는 None
        """
        # TODO: 구현 필요
        return None

    async def check_sell_opportunity_for_stock(self, stock_code: str):
        """
        특정 종목의 매도 기회 체크 (이벤트 트리거용)

        Args:
            stock_code: 종목 코드

        사용처:
        - 속보 뉴스 발생 시
        - DART 악재 공시 발생 시
        - AI Score 급락 시
        """
        logger.info(f"🔍 특정 종목 매도 체크: {stock_code}")

        try:
            db = next(get_db())
            item = db.query(Portfolio).filter(
                Portfolio.stock_code == stock_code,
                Portfolio.quantity > 0
            ).first()

            if not item:
                logger.debug(f"  ⏸️  {stock_code}: 보유하지 않음")
                return

            # 매도 조건 체크
            sell_decision = await self._judge_stock(item, db)

            if sell_decision:
                # 매도 실행
                await self._execute_sell(item, sell_decision)

            db.commit()

        except Exception as e:
            logger.error(f"❌ 매도 체크 오류: {e}", exc_info=True)

        finally:
            try:
                db.close()
            except:
                pass


# Singleton Instance
portfolio_manager = PortfolioManager()
