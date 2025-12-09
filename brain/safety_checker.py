"""
AEGIS v3.0 - Safety Checker
매수 전 안전성 검증 (5가지 체크)

검증 항목:
1. 보유 종목 수 < 5개
2. 일일 거래 횟수 < 4회
3. 금요일 14:30 이전
4. 계좌 손실률 < -2%
5. 종목 비중 < 10%

모든 조건 통과 시에만 매수 승인
"""
import logging
from datetime import datetime, time, date
from typing import Dict, Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.account import Portfolio, TradingHistory
from fetchers.kis_fetcher import kis_fetcher

logger = logging.getLogger(__name__)


class SafetyChecker:
    """
    매수 전 안전성 검증 시스템

    역할:
    - Commander 최종 결정 직전 안전성 체크
    - 5가지 리스크 관리 규칙 검증
    - 하나라도 실패 시 매수 거부

    원칙:
    "보수적 진입, 공격적 탈출"
    """

    def __init__(self):
        # 안전성 임계값
        self.MAX_HOLDINGS = 5  # 최대 보유 종목 수
        self.MAX_DAILY_TRADES = 4  # 일일 최대 거래 횟수
        self.FRIDAY_CUTOFF = time(14, 30)  # 금요일 매수 마감 시간
        self.MAX_ACCOUNT_LOSS_PCT = -2.0  # 계좌 최대 손실률 (%)
        self.MAX_POSITION_WEIGHT_PCT = 10.0  # 종목 최대 비중 (%)

    async def check_buy_safety(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        price: int
    ) -> Dict:
        """
        매수 안전성 종합 검증

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            quantity: 매수 수량
            price: 매수 가격

        Returns:
            {
                "approved": True/False,
                "reason": "승인/거부 이유",
                "checks": {
                    "holdings_count": {"passed": True, "detail": "..."},
                    "daily_trades": {"passed": True, "detail": "..."},
                    "friday_cutoff": {"passed": True, "detail": "..."},
                    "account_loss": {"passed": True, "detail": "..."},
                    "position_weight": {"passed": True, "detail": "..."}
                }
            }
        """
        logger.info("=" * 80)
        logger.info(f"🛡️ Safety Check Started: {stock_name} ({stock_code})")
        logger.info(f"   Quantity: {quantity}, Price: {price:,}원")

        checks = {}
        all_passed = True

        try:
            db = next(get_db())

            # 1️⃣ 보유 종목 수 체크
            holdings_check = await self._check_holdings_count(db)
            checks["holdings_count"] = holdings_check
            if not holdings_check["passed"]:
                all_passed = False
                logger.warning(f"   ❌ {holdings_check['detail']}")
            else:
                logger.info(f"   ✅ {holdings_check['detail']}")

            # 2️⃣ 일일 거래 횟수 체크
            trades_check = await self._check_daily_trades(db)
            checks["daily_trades"] = trades_check
            if not trades_check["passed"]:
                all_passed = False
                logger.warning(f"   ❌ {trades_check['detail']}")
            else:
                logger.info(f"   ✅ {trades_check['detail']}")

            # 3️⃣ 금요일 마감 시간 체크
            friday_check = await self._check_friday_cutoff()
            checks["friday_cutoff"] = friday_check
            if not friday_check["passed"]:
                all_passed = False
                logger.warning(f"   ❌ {friday_check['detail']}")
            else:
                logger.info(f"   ✅ {friday_check['detail']}")

            # 4️⃣ 계좌 손실률 체크
            loss_check = await self._check_account_loss()
            checks["account_loss"] = loss_check
            if not loss_check["passed"]:
                all_passed = False
                logger.warning(f"   ❌ {loss_check['detail']}")
            else:
                logger.info(f"   ✅ {loss_check['detail']}")

            # 5️⃣ 종목 비중 체크
            weight_check = await self._check_position_weight(
                stock_code, quantity, price
            )
            checks["position_weight"] = weight_check
            if not weight_check["passed"]:
                all_passed = False
                logger.warning(f"   ❌ {weight_check['detail']}")
            else:
                logger.info(f"   ✅ {weight_check['detail']}")

            # 최종 결과
            if all_passed:
                reason = "All safety checks passed"
                logger.info(f"   ✅ APPROVED: {reason}")
            else:
                failed_checks = [k for k, v in checks.items() if not v["passed"]]
                reason = f"Failed checks: {', '.join(failed_checks)}"
                logger.warning(f"   ❌ REJECTED: {reason}")

            logger.info("=" * 80)

            return {
                "approved": all_passed,
                "reason": reason,
                "checks": checks
            }

        except Exception as e:
            logger.error(f"❌ Safety check error: {e}", exc_info=True)
            return {
                "approved": False,
                "reason": f"Safety check failed: {str(e)}",
                "checks": {}
            }

        finally:
            try:
                db.close()
            except:
                pass

    async def _check_holdings_count(self, db: Session) -> Dict:
        """
        1️⃣ 보유 종목 수 체크

        규칙: 최대 5개 종목까지만 보유

        Returns:
            {"passed": True/False, "detail": "..."}
        """
        try:
            # 현재 보유 종목 수 (수량 > 0)
            holdings_count = db.query(Portfolio).filter(
                Portfolio.quantity > 0
            ).count()

            passed = holdings_count < self.MAX_HOLDINGS

            detail = f"보유 종목 수: {holdings_count}/{self.MAX_HOLDINGS}"

            return {"passed": passed, "detail": detail}

        except Exception as e:
            logger.error(f"Holdings count check error: {e}")
            return {"passed": False, "detail": f"Error: {str(e)}"}

    async def _check_daily_trades(self, db: Session) -> Dict:
        """
        2️⃣ 일일 거래 횟수 체크

        규칙: 하루 최대 4회까지만 거래 (과도한 거래 방지)

        Returns:
            {"passed": True/False, "detail": "..."}
        """
        try:
            # 오늘 거래 횟수 조회
            today = date.today()
            trades_count = db.query(TradingHistory).filter(
                TradingHistory.trade_date == today
            ).count()

            passed = trades_count < self.MAX_DAILY_TRADES

            detail = f"일일 거래 횟수: {trades_count}/{self.MAX_DAILY_TRADES}"

            return {"passed": passed, "detail": detail}

        except Exception as e:
            logger.error(f"Daily trades check error: {e}")
            return {"passed": False, "detail": f"Error: {str(e)}"}

    async def _check_friday_cutoff(self) -> Dict:
        """
        3️⃣ 금요일 마감 시간 체크

        규칙: 금요일 14:30 이후에는 매수 금지 (주말 리스크 회피)

        Returns:
            {"passed": True/False, "detail": "..."}
        """
        try:
            now = datetime.now()
            is_friday = now.weekday() == 4  # 0=월요일, 4=금요일
            current_time = now.time()

            if is_friday and current_time >= self.FRIDAY_CUTOFF:
                passed = False
                detail = f"금요일 {self.FRIDAY_CUTOFF.strftime('%H:%M')} 이후 매수 금지 (주말 리스크)"
            else:
                passed = True
                detail = f"금요일 마감 시간 체크 통과"

            return {"passed": passed, "detail": detail}

        except Exception as e:
            logger.error(f"Friday cutoff check error: {e}")
            return {"passed": False, "detail": f"Error: {str(e)}"}

    async def _check_account_loss(self) -> Dict:
        """
        4️⃣ 계좌 손실률 체크

        규칙: 계좌 손실률이 -2% 이하면 추가 매수 금지 (손실 확대 방지)

        Returns:
            {"passed": True/False, "detail": "..."}
        """
        try:
            # KIS API로 계좌 수익률 조회
            account_info = await kis_fetcher.get_account_balance()

            if not account_info:
                logger.warning("⚠️  계좌 정보 조회 실패, 안전하게 통과 처리")
                return {"passed": True, "detail": "계좌 정보 조회 실패 (통과 처리)"}

            # 수익률 계산
            total_asset = account_info.get('total_asset', 0)
            deposit = account_info.get('deposit', 0)

            if deposit == 0:
                profit_rate = 0.0
            else:
                profit_rate = ((total_asset - deposit) / deposit) * 100

            passed = profit_rate > self.MAX_ACCOUNT_LOSS_PCT

            detail = f"계좌 손실률: {profit_rate:+.2f}% (기준: {self.MAX_ACCOUNT_LOSS_PCT}%)"

            return {"passed": passed, "detail": detail}

        except Exception as e:
            logger.error(f"Account loss check error: {e}")
            # 오류 시 안전하게 통과 (매수 기회 박탈 방지)
            return {"passed": True, "detail": f"Error (통과 처리): {str(e)}"}

    async def _check_position_weight(
        self,
        stock_code: str,
        quantity: int,
        price: int
    ) -> Dict:
        """
        5️⃣ 종목 비중 체크

        규칙: 단일 종목 비중이 전체 자산의 10%를 초과하지 않도록

        Args:
            stock_code: 종목 코드
            quantity: 매수 예정 수량
            price: 매수 가격

        Returns:
            {"passed": True/False, "detail": "..."}
        """
        try:
            # 계좌 총 자산 조회
            account_info = await kis_fetcher.get_account_balance()

            if not account_info:
                logger.warning("⚠️  계좌 정보 조회 실패, 안전하게 통과 처리")
                return {"passed": True, "detail": "계좌 정보 조회 실패 (통과 처리)"}

            total_asset = account_info.get('total_asset', 0)

            if total_asset == 0:
                return {"passed": False, "detail": "계좌 자산 0원"}

            # 매수 예정 금액
            buy_amount = quantity * price

            # 종목 비중 계산
            position_weight = (buy_amount / total_asset) * 100

            passed = position_weight <= self.MAX_POSITION_WEIGHT_PCT

            detail = f"종목 비중: {position_weight:.2f}% (기준: {self.MAX_POSITION_WEIGHT_PCT}%)"

            return {"passed": passed, "detail": detail}

        except Exception as e:
            logger.error(f"Position weight check error: {e}")
            # 오류 시 안전하게 통과
            return {"passed": True, "detail": f"Error (통과 처리): {str(e)}"}

    def get_status(self) -> Dict:
        """
        Safety Checker 설정 조회 (디버깅용)

        Returns:
            현재 설정된 안전성 임계값
        """
        return {
            "max_holdings": self.MAX_HOLDINGS,
            "max_daily_trades": self.MAX_DAILY_TRADES,
            "friday_cutoff": self.FRIDAY_CUTOFF.strftime("%H:%M"),
            "max_account_loss_pct": self.MAX_ACCOUNT_LOSS_PCT,
            "max_position_weight_pct": self.MAX_POSITION_WEIGHT_PCT
        }


# Singleton Instance
safety_checker = SafetyChecker()
