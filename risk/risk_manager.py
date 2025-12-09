"""
AEGIS v3.0 - Risk Management System
리스크 관리 시스템

Features:
- 포지션 사이징 (Position Sizing)
- 자동 손절 (Stop-Loss)
- 자동 익절 (Take-Profit)
- 포트폴리오 리밸런싱
- 리스크 한도 모니터링
"""
import os
import sys
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text

logger = logging.getLogger("RiskManager")


@dataclass
class RiskLimits:
    """리스크 한도"""
    # Portfolio level
    max_portfolio_risk: float = 0.20  # 최대 포트폴리오 리스크 20%
    max_position_size: float = 0.15  # 종목당 최대 15%
    max_positions: int = 10  # 최대 10종목

    # Trade level
    max_loss_per_trade: float = 0.02  # 거래당 최대 손실 2%
    stop_loss_pct: float = 0.03  # 손절 -3%
    take_profit_pct: float = 0.05  # 익절 +5%

    # Sector
    max_sector_exposure: float = 0.30  # 섹터당 최대 30%

    # Daily
    max_daily_loss: float = 0.05  # 일일 최대 손실 5%
    max_daily_trades: int = 20  # 일일 최대 거래 20건


@dataclass
class PositionRisk:
    """포지션 리스크"""
    code: str
    name: str
    quantity: int
    avg_price: float
    current_price: float

    # Risk
    position_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float

    # Limits
    stop_loss_price: float
    take_profit_price: float

    # Action
    action: Optional[str] = None  # STOP_LOSS, TAKE_PROFIT, REBALANCE, None


class RiskManager:
    """
    리스크 관리 시스템

    실시간 리스크 모니터링:
    1. 포지션별 손익 추적
    2. 손절/익절 조건 감지
    3. 포트폴리오 리스크 한도 체크
    4. 리밸런싱 필요성 판단
    """

    def __init__(self, limits: Optional[RiskLimits] = None):
        self.db = SessionLocal()
        self.limits = limits or RiskLimits()

        logger.info("✅ RiskManager initialized")
        logger.info(f"   Max Portfolio Risk: {self.limits.max_portfolio_risk*100:.0f}%")
        logger.info(f"   Stop Loss: {self.limits.stop_loss_pct*100:.0f}%")
        logger.info(f"   Take Profit: {self.limits.take_profit_pct*100:.0f}%")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def check_positions(self) -> Tuple[List[PositionRisk], List[str]]:
        """
        모든 포지션 리스크 체크

        Returns:
            (position_risks, warnings)
        """
        # Get current positions
        query = text("""
            SELECT
                s.code,
                s.name,
                sa.quantity,
                sa.avg_price,
                dp.close as current_price
            FROM stock_assets sa
            JOIN stocks s ON sa.stock_code = s.code
            LEFT JOIN LATERAL (
                SELECT close FROM daily_prices
                WHERE stock_code = sa.stock_code
                ORDER BY date DESC LIMIT 1
            ) dp ON true
            WHERE sa.quantity > 0
        """)

        results = self.db.execute(query).fetchall()

        position_risks = []
        warnings = []

        for r in results:
            risk = self._calculate_position_risk(
                code=r.code,
                name=r.name,
                quantity=r.quantity,
                avg_price=float(r.avg_price),
                current_price=float(r.current_price) if r.current_price else float(r.avg_price)
            )

            position_risks.append(risk)

            # Check for actions
            if risk.action == "STOP_LOSS":
                warnings.append(f"⚠️ {risk.name}: 손절 조건 도달 ({risk.unrealized_pnl_pct:.2f}%)")
            elif risk.action == "TAKE_PROFIT":
                warnings.append(f"✅ {risk.name}: 익절 조건 도달 ({risk.unrealized_pnl_pct:.2f}%)")

        # Portfolio-level checks
        portfolio_warnings = self._check_portfolio_limits(position_risks)
        warnings.extend(portfolio_warnings)

        return position_risks, warnings

    def calculate_position_size(
        self,
        code: str,
        signal_strength: float,
        total_capital: float
    ) -> Tuple[int, float]:
        """
        포지션 크기 계산 (Kelly Criterion 변형)

        Args:
            code: 종목코드
            signal_strength: 시그널 강도 (0-100)
            total_capital: 총 자본

        Returns:
            (quantity, position_value)
        """
        # Get current price
        price = self._get_current_price(code)

        if price is None:
            return 0, 0.0

        # Base position size from signal strength
        strength_factor = signal_strength / 100.0

        # Max position size
        max_value = total_capital * self.limits.max_position_size

        # Calculated position value
        position_value = max_value * strength_factor

        # Calculate quantity
        quantity = int(position_value / price)

        return quantity, quantity * price

    def should_rebalance(
        self,
        positions: List[PositionRisk],
        total_value: float
    ) -> bool:
        """
        리밸런싱 필요성 판단

        Args:
            positions: 포지션 리스트
            total_value: 총 자산

        Returns:
            True if rebalancing needed
        """
        if not positions:
            return False

        # Check if any position exceeds max size
        for pos in positions:
            weight = pos.position_value / total_value

            if weight > self.limits.max_position_size * 1.5:
                logger.info(f"   Rebalance needed: {pos.name} weight {weight*100:.1f}%")
                return True

        # Check sector concentration
        # TODO: Implement sector tracking

        return False

    def get_daily_risk_status(self) -> Dict:
        """
        일일 리스크 현황

        Returns:
            {
                'daily_pnl': float,
                'daily_pnl_pct': float,
                'trades_today': int,
                'limit_exceeded': bool,
                'warnings': List[str]
            }
        """
        today = date.today()

        # Get today's trades
        trades_query = text("""
            SELECT COUNT(*) as count
            FROM trade_orders
            WHERE DATE(created_at) = :today
        """)

        trades_result = self.db.execute(trades_query, {'today': today}).fetchone()
        trades_today = trades_result.count if trades_result else 0

        # Get today's PnL (simplified - from portfolio value change)
        # TODO: Implement accurate daily PnL tracking

        warnings = []

        if trades_today >= self.limits.max_daily_trades:
            warnings.append(f"⚠️ 일일 거래 한도 도달 ({trades_today}/{self.limits.max_daily_trades})")

        return {
            'daily_pnl': 0.0,  # TODO
            'daily_pnl_pct': 0.0,
            'trades_today': trades_today,
            'limit_exceeded': len(warnings) > 0,
            'warnings': warnings
        }

    # ========================================
    # HELPERS
    # ========================================

    def _calculate_position_risk(
        self,
        code: str,
        name: str,
        quantity: int,
        avg_price: float,
        current_price: float
    ) -> PositionRisk:
        """포지션 리스크 계산"""
        position_value = quantity * current_price
        unrealized_pnl = (current_price - avg_price) * quantity
        unrealized_pnl_pct = (current_price - avg_price) / avg_price * 100

        # Stop-loss and take-profit prices
        stop_loss_price = avg_price * (1 - self.limits.stop_loss_pct)
        take_profit_price = avg_price * (1 + self.limits.take_profit_pct)

        # Determine action
        action = None

        if current_price <= stop_loss_price:
            action = "STOP_LOSS"
        elif current_price >= take_profit_price:
            action = "TAKE_PROFIT"

        return PositionRisk(
            code=code,
            name=name,
            quantity=quantity,
            avg_price=avg_price,
            current_price=current_price,
            position_value=position_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            action=action
        )

    def _check_portfolio_limits(self, positions: List[PositionRisk]) -> List[str]:
        """포트폴리오 한도 체크"""
        warnings = []

        # Check number of positions
        if len(positions) > self.limits.max_positions:
            warnings.append(f"⚠️ 보유 종목 수 초과 ({len(positions)}/{self.limits.max_positions})")

        # Check total portfolio value
        # Get total capital
        cash_query = text("SELECT cash FROM portfolio_summary LIMIT 1")
        cash_result = self.db.execute(cash_query).fetchone()
        cash = float(cash_result.cash) if cash_result else 0.0

        stock_value = sum(p.position_value for p in positions)
        total_value = cash + stock_value

        # Check individual position sizes
        for pos in positions:
            weight = pos.position_value / total_value if total_value > 0 else 0

            if weight > self.limits.max_position_size:
                warnings.append(
                    f"⚠️ {pos.name}: 포지션 크기 초과 ({weight*100:.1f}% > {self.limits.max_position_size*100:.0f}%)"
                )

        return warnings

    def _get_current_price(self, code: str) -> Optional[float]:
        """현재가 조회"""
        query = text("""
            SELECT close
            FROM daily_prices
            WHERE stock_code = :code
            ORDER BY date DESC
            LIMIT 1
        """)

        result = self.db.execute(query, {'code': code}).fetchone()

        return float(result.close) if result else None


# ========================================
# MAIN
# ========================================

def main():
    """테스트"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    risk_manager = RiskManager()

    # Check all positions
    position_risks, warnings = risk_manager.check_positions()

    print("\n" + "=" * 70)
    print("⚠️ Risk Management Report")
    print("=" * 70)

    print(f"\n[Positions] {len(position_risks)} holdings")

    for pos in position_risks:
        status = "🔴" if pos.action == "STOP_LOSS" else "🟢" if pos.action == "TAKE_PROFIT" else "⚪"

        print(f"\n{status} {pos.name} ({pos.code})")
        print(f"   Quantity: {pos.quantity:,}주")
        print(f"   Avg Price: {pos.avg_price:,.0f}원 → Current: {pos.current_price:,.0f}원")
        print(f"   P&L: {pos.unrealized_pnl:+,.0f}원 ({pos.unrealized_pnl_pct:+.2f}%)")
        print(f"   Stop Loss: {pos.stop_loss_price:,.0f}원 | Take Profit: {pos.take_profit_price:,.0f}원")

        if pos.action:
            print(f"   ⚡ Action: {pos.action}")

    if warnings:
        print(f"\n[Warnings]")
        for warning in warnings:
            print(f"  {warning}")
    else:
        print(f"\n✅ No warnings")

    # Daily risk
    daily_status = risk_manager.get_daily_risk_status()

    print(f"\n[Daily Status]")
    print(f"  Trades Today: {daily_status['trades_today']}")

    if daily_status['warnings']:
        for warning in daily_status['warnings']:
            print(f"  {warning}")

    print("=" * 70)


if __name__ == "__main__":
    main()
