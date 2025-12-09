"""
AEGIS v3.0 - Backtesting Engine
백테스팅 엔진

Data: 3년 일별 데이터 (1,893,659건)
Period: 2022-01-01 ~ 2024-12-31

Metrics:
- Total Return
- CAGR (Compound Annual Growth Rate)
- MDD (Maximum Drawdown)
- Sharpe Ratio
- Win Rate
- Profit Factor
"""
import os
import sys
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from decimal import Decimal
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text

logger = logging.getLogger("Backtester")


@dataclass
class Trade:
    """거래 기록"""
    date: date
    code: str
    name: str
    action: str  # BUY, SELL
    quantity: int
    price: float
    amount: float
    commission: float


@dataclass
class Position:
    """보유 포지션"""
    code: str
    name: str
    quantity: int
    avg_price: float
    current_price: float

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def profit(self) -> float:
        return (self.current_price - self.avg_price) * self.quantity

    @property
    def profit_rate(self) -> float:
        return (self.current_price - self.avg_price) / self.avg_price * 100


@dataclass
class DailySnapshot:
    """일별 포트폴리오 스냅샷"""
    date: date
    cash: float
    stock_value: float
    total_value: float
    positions: List[Position]
    trades: List[Trade]


@dataclass
class BacktestResult:
    """백테스트 결과"""
    # Period
    start_date: date
    end_date: date
    trading_days: int

    # Portfolio
    initial_capital: float
    final_capital: float
    peak_capital: float

    # Returns
    total_return: float  # %
    cagr: float  # %
    mdd: float  # %

    # Risk
    sharpe_ratio: float
    volatility: float  # %
    beta: Optional[float]

    # Trading
    total_trades: int
    win_trades: int
    lose_trades: int
    win_rate: float  # %
    avg_profit: float
    avg_loss: float
    profit_factor: float

    # Daily snapshots
    snapshots: List[DailySnapshot] = field(default_factory=list)

    # Trades
    trades: List[Trade] = field(default_factory=list)


class Backtester:
    """
    백테스팅 엔진

    전략을 3년 과거 데이터로 시뮬레이션:
    1. 일별로 시그널 생성 (전략 로직)
    2. 매수/매도 실행
    3. 포트폴리오 가치 추적
    4. 성과 지표 계산
    """

    def __init__(
        self,
        initial_capital: float = 10_000_000,  # 1천만원
        commission_rate: float = 0.00015,  # 0.015% (KIS 수수료)
        max_positions: int = 10,  # 최대 10종목 보유
        position_size: float = 0.10  # 종목당 10%
    ):
        self.db = SessionLocal()
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.max_positions = max_positions
        self.position_size = position_size

        # Portfolio state
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.snapshots: List[DailySnapshot] = []

        logger.info("✅ Backtester initialized")
        logger.info(f"   Initial Capital: {initial_capital:,.0f}원")
        logger.info(f"   Commission: {commission_rate*100:.3f}%")
        logger.info(f"   Max Positions: {max_positions}")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def run(
        self,
        start_date: date,
        end_date: date,
        strategy_func
    ) -> BacktestResult:
        """
        백테스트 실행

        Args:
            start_date: 시작일
            end_date: 종료일
            strategy_func: 시그널 생성 함수 (date) -> List[Dict]
                         [{'code': '005930', 'action': 'BUY', 'size': 0.1}, ...]

        Returns:
            BacktestResult
        """
        logger.info(f"🚀 Running backtest: {start_date} ~ {end_date}")

        # Reset portfolio
        self.cash = self.initial_capital
        self.positions = {}
        self.trades = []
        self.snapshots = []

        # Get trading days
        trading_days = self._get_trading_days(start_date, end_date)
        logger.info(f"   Trading days: {len(trading_days)}")

        # Simulate each day
        for i, current_date in enumerate(trading_days):
            if (i + 1) % 50 == 0:
                logger.info(f"   Processing: {i+1}/{len(trading_days)} ({current_date})")

            # Update prices
            self._update_positions(current_date)

            # Generate signals
            signals = strategy_func(current_date)

            # Execute trades
            daily_trades = []
            for signal in signals:
                trade = self._execute_signal(current_date, signal)
                if trade:
                    daily_trades.append(trade)

            # Take snapshot
            snapshot = DailySnapshot(
                date=current_date,
                cash=self.cash,
                stock_value=self._calculate_stock_value(),
                total_value=self.cash + self._calculate_stock_value(),
                positions=list(self.positions.values()),
                trades=daily_trades
            )
            self.snapshots.append(snapshot)

        # Calculate metrics
        result = self._calculate_metrics(start_date, end_date)

        logger.info(f"✅ Backtest completed")
        logger.info(f"   Total Return: {result.total_return:+.2f}%")
        logger.info(f"   CAGR: {result.cagr:.2f}%")
        logger.info(f"   MDD: {result.mdd:.2f}%")
        logger.info(f"   Sharpe: {result.sharpe_ratio:.2f}")
        logger.info(f"   Win Rate: {result.win_rate:.1f}%")

        return result

    # ========================================
    # TRADING
    # ========================================

    def _execute_signal(
        self,
        current_date: date,
        signal: Dict
    ) -> Optional[Trade]:
        """
        시그널 실행

        Args:
            current_date: 현재 날짜
            signal: {'code': '005930', 'action': 'BUY', 'size': 0.1}

        Returns:
            Trade or None
        """
        code = signal['code']
        action = signal['action']
        size = signal.get('size', self.position_size)

        # Get current price
        price = self._get_price(code, current_date)

        if price is None:
            return None

        if action == "BUY":
            return self._buy(current_date, code, size, price)
        elif action == "SELL":
            return self._sell(current_date, code, price)
        else:
            return None

    def _buy(
        self,
        current_date: date,
        code: str,
        size: float,
        price: float
    ) -> Optional[Trade]:
        """매수"""
        # Check max positions
        if len(self.positions) >= self.max_positions and code not in self.positions:
            return None

        # Calculate amount
        total_value = self.cash + self._calculate_stock_value()
        target_amount = total_value * size

        # Calculate quantity
        quantity = int(target_amount / price)

        if quantity == 0:
            return None

        amount = quantity * price
        commission = amount * self.commission_rate

        # Check cash
        if self.cash < amount + commission:
            return None

        # Execute
        self.cash -= (amount + commission)

        # Update position
        if code in self.positions:
            pos = self.positions[code]
            total_quantity = pos.quantity + quantity
            total_cost = pos.avg_price * pos.quantity + amount
            pos.quantity = total_quantity
            pos.avg_price = total_cost / total_quantity
        else:
            # Get name
            name = self._get_stock_name(code)
            self.positions[code] = Position(
                code=code,
                name=name,
                quantity=quantity,
                avg_price=price,
                current_price=price
            )

        # Record trade
        trade = Trade(
            date=current_date,
            code=code,
            name=self._get_stock_name(code),
            action="BUY",
            quantity=quantity,
            price=price,
            amount=amount,
            commission=commission
        )
        self.trades.append(trade)

        return trade

    def _sell(
        self,
        current_date: date,
        code: str,
        price: float
    ) -> Optional[Trade]:
        """매도"""
        if code not in self.positions:
            return None

        pos = self.positions[code]
        quantity = pos.quantity
        amount = quantity * price
        commission = amount * self.commission_rate

        # Execute
        self.cash += (amount - commission)

        # Remove position
        del self.positions[code]

        # Record trade
        trade = Trade(
            date=current_date,
            code=code,
            name=pos.name,
            action="SELL",
            quantity=quantity,
            price=price,
            amount=amount,
            commission=commission
        )
        self.trades.append(trade)

        return trade

    # ========================================
    # PORTFOLIO
    # ========================================

    def _update_positions(self, current_date: date):
        """포지션 가격 업데이트"""
        for code, pos in self.positions.items():
            price = self._get_price(code, current_date)
            if price:
                pos.current_price = price

    def _calculate_stock_value(self) -> float:
        """주식 평가액 계산"""
        return sum(pos.market_value for pos in self.positions.values())

    # ========================================
    # METRICS
    # ========================================

    def _calculate_metrics(
        self,
        start_date: date,
        end_date: date
    ) -> BacktestResult:
        """성과 지표 계산"""
        # Basic
        final_capital = self.cash + self._calculate_stock_value()
        peak_capital = max(s.total_value for s in self.snapshots)

        # Returns
        total_return = (final_capital - self.initial_capital) / self.initial_capital * 100

        # CAGR
        years = (end_date - start_date).days / 365.25
        cagr = ((final_capital / self.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

        # MDD
        mdd = self._calculate_mdd()

        # Volatility & Sharpe
        daily_returns = self._calculate_daily_returns()
        volatility = np.std(daily_returns) * np.sqrt(252) * 100 if len(daily_returns) > 0 else 0
        avg_return = np.mean(daily_returns) if len(daily_returns) > 0 else 0
        sharpe_ratio = (avg_return * 252) / (np.std(daily_returns) * np.sqrt(252)) if np.std(daily_returns) > 0 else 0

        # Trading
        total_trades = len(self.trades)
        closed_trades = self._get_closed_trades()
        win_trades = sum(1 for t in closed_trades if t['profit'] > 0)
        lose_trades = sum(1 for t in closed_trades if t['profit'] < 0)
        win_rate = win_trades / len(closed_trades) * 100 if closed_trades else 0

        profits = [t['profit'] for t in closed_trades if t['profit'] > 0]
        losses = [t['profit'] for t in closed_trades if t['profit'] < 0]
        avg_profit = np.mean(profits) if profits else 0
        avg_loss = np.mean(losses) if losses else 0
        profit_factor = sum(profits) / abs(sum(losses)) if losses else 0

        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            trading_days=len(self.snapshots),
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            peak_capital=peak_capital,
            total_return=total_return,
            cagr=cagr,
            mdd=mdd,
            sharpe_ratio=sharpe_ratio,
            volatility=volatility,
            beta=None,  # TODO: Calculate beta vs KOSPI
            total_trades=total_trades,
            win_trades=win_trades,
            lose_trades=lose_trades,
            win_rate=win_rate,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            snapshots=self.snapshots,
            trades=self.trades
        )

    def _calculate_mdd(self) -> float:
        """MDD 계산"""
        if not self.snapshots:
            return 0.0

        peak = self.snapshots[0].total_value
        max_dd = 0.0

        for snapshot in self.snapshots:
            if snapshot.total_value > peak:
                peak = snapshot.total_value

            dd = (peak - snapshot.total_value) / peak * 100
            if dd > max_dd:
                max_dd = dd

        return max_dd

    def _calculate_daily_returns(self) -> List[float]:
        """일별 수익률 계산"""
        if len(self.snapshots) < 2:
            return []

        returns = []
        for i in range(1, len(self.snapshots)):
            prev_value = self.snapshots[i-1].total_value
            curr_value = self.snapshots[i].total_value
            ret = (curr_value - prev_value) / prev_value
            returns.append(ret)

        return returns

    def _get_closed_trades(self) -> List[Dict]:
        """완결된 거래 (매수-매도 쌍) 추출"""
        closed = []
        buy_trades = {}

        for trade in self.trades:
            if trade.action == "BUY":
                if trade.code not in buy_trades:
                    buy_trades[trade.code] = []
                buy_trades[trade.code].append(trade)

            elif trade.action == "SELL":
                if trade.code in buy_trades and buy_trades[trade.code]:
                    buy_trade = buy_trades[trade.code].pop(0)
                    profit = (trade.price - buy_trade.price) * trade.quantity - trade.commission - buy_trade.commission
                    closed.append({
                        'code': trade.code,
                        'buy_date': buy_trade.date,
                        'sell_date': trade.date,
                        'buy_price': buy_trade.price,
                        'sell_price': trade.price,
                        'quantity': trade.quantity,
                        'profit': profit
                    })

        return closed

    # ========================================
    # DATA ACCESS
    # ========================================

    def _get_trading_days(self, start_date: date, end_date: date) -> List[date]:
        """거래일 조회"""
        query = text("""
            SELECT DISTINCT date
            FROM daily_prices
            WHERE date >= :start_date AND date <= :end_date
            ORDER BY date
        """)

        results = self.db.execute(
            query,
            {'start_date': start_date, 'end_date': end_date}
        ).fetchall()

        return [r.date for r in results]

    def _get_price(self, code: str, date: date) -> Optional[float]:
        """종목 가격 조회"""
        query = text("""
            SELECT close
            FROM daily_prices
            WHERE stock_code = :code AND date = :date
        """)

        result = self.db.execute(query, {'code': code, 'date': date}).fetchone()

        return float(result.close) if result else None

    def _get_stock_name(self, code: str) -> str:
        """종목명 조회"""
        query = text("SELECT name FROM stocks WHERE code = :code")
        result = self.db.execute(query, {'code': code}).fetchone()
        return result.name if result else code


# ========================================
# MAIN
# ========================================

def simple_momentum_strategy(backtester: Backtester, current_date: date) -> List[Dict]:
    """
    간단한 모멘텀 전략 (테스트용)

    20일 모멘텀 상위 5종목 매수
    """
    query = text("""
        SELECT
            s.code,
            AVG(dp.change_rate) as momentum
        FROM stocks s
        JOIN daily_prices dp ON s.code = dp.stock_code
        WHERE dp.date >= :start_date
          AND dp.date <= :current_date
          AND s.market IN ('KOSPI', 'KOSDAQ')
        GROUP BY s.code
        HAVING COUNT(*) >= 20
        ORDER BY AVG(dp.change_rate) DESC
        LIMIT 5
    """)

    start_date = current_date - timedelta(days=30)

    results = backtester.db.execute(
        query,
        {'start_date': start_date, 'current_date': current_date}
    ).fetchall()

    signals = []

    # Buy top momentum stocks
    for r in results:
        signals.append({
            'code': r.code,
            'action': 'BUY',
            'size': 0.15  # 15% each
        })

    # Sell stocks not in top 5
    current_codes = [r.code for r in results]
    for code in list(backtester.positions.keys()):
        if code not in current_codes:
            signals.append({
                'code': code,
                'action': 'SELL'
            })

    return signals


def main():
    """테스트"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    backtester = Backtester(
        initial_capital=10_000_000,
        max_positions=5
    )

    # Backtest 1 month (full 3 years takes too long for test)
    start = date(2024, 11, 1)
    end = date(2024, 11, 30)

    result = backtester.run(
        start_date=start,
        end_date=end,
        strategy_func=lambda d: simple_momentum_strategy(backtester, d)
    )

    print("\n" + "=" * 70)
    print("📊 Backtest Results")
    print("=" * 70)
    print(f"\n[Period]")
    print(f"  {result.start_date} ~ {result.end_date} ({result.trading_days} days)")

    print(f"\n[Returns]")
    print(f"  Initial: {result.initial_capital:,.0f}원")
    print(f"  Final: {result.final_capital:,.0f}원")
    print(f"  Total Return: {result.total_return:+.2f}%")
    print(f"  CAGR: {result.cagr:.2f}%")
    print(f"  MDD: {result.mdd:.2f}%")

    print(f"\n[Risk]")
    print(f"  Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"  Volatility: {result.volatility:.2f}%")

    print(f"\n[Trading]")
    print(f"  Total Trades: {result.total_trades}")
    print(f"  Win: {result.win_trades} / Lose: {result.lose_trades}")
    print(f"  Win Rate: {result.win_rate:.1f}%")
    print(f"  Avg Profit: {result.avg_profit:,.0f}원")
    print(f"  Avg Loss: {result.avg_loss:,.0f}원")
    print(f"  Profit Factor: {result.profit_factor:.2f}")

    print("=" * 70)


if __name__ == "__main__":
    main()
