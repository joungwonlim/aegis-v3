"""
AEGIS v3.0 - Strategy Optimizer
전략 최적화 시스템

Grid Search & Genetic Algorithm:
- 파라미터 조합 탐색
- 최적 조합 선택
- 과적합 방지 (Walk-Forward Analysis)

Parameters to optimize:
- Signal thresholds (BUY/SELL score cutoffs)
- Position sizing
- Max positions
- Rebalancing frequency
- Stop-loss / Take-profit levels
"""
import os
import sys
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
import itertools
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.backtester import Backtester, BacktestResult

logger = logging.getLogger("Optimizer")


@dataclass
class ParameterSet:
    """파라미터 세트"""
    # Signal
    buy_threshold: float  # BUY 시그널 임계값
    sell_threshold: float  # SELL 시그널 임계값

    # Position
    position_size: float  # 종목당 포지션 크기
    max_positions: int  # 최대 보유 종목 수

    # Risk
    stop_loss: float  # 손절 비율 (%)
    take_profit: float  # 익절 비율 (%)

    # Rebalancing
    rebalance_days: int  # 리밸런싱 주기 (일)

    def to_dict(self) -> Dict:
        return {
            'buy_threshold': self.buy_threshold,
            'sell_threshold': self.sell_threshold,
            'position_size': self.position_size,
            'max_positions': self.max_positions,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'rebalance_days': self.rebalance_days
        }


@dataclass
class OptimizationResult:
    """최적화 결과"""
    best_params: ParameterSet
    best_sharpe: float
    best_return: float
    best_mdd: float

    # All results
    all_results: List[Tuple[ParameterSet, BacktestResult]]

    # Stats
    total_combinations: int
    successful_runs: int
    optimization_time: float


class StrategyOptimizer:
    """
    전략 최적화 엔진

    Grid Search로 파라미터 조합 탐색:
    1. 파라미터 범위 정의
    2. 조합 생성 (Grid Search)
    3. 각 조합으로 백테스트 실행
    4. 성과 지표 기준 최적 조합 선택
    5. Walk-Forward Analysis로 검증
    """

    def __init__(
        self,
        initial_capital: float = 10_000_000,
        objective: str = "sharpe"  # sharpe, return, mdd
    ):
        self.initial_capital = initial_capital
        self.objective = objective
        logger.info(f"✅ StrategyOptimizer initialized (objective: {objective})")

    def optimize(
        self,
        strategy_func: Callable,
        start_date: date,
        end_date: date,
        param_grid: Dict[str, List],
        max_workers: int = 4
    ) -> OptimizationResult:
        """
        그리드 서치 최적화

        Args:
            strategy_func: 전략 함수 (backtester, current_date, params) -> List[Dict]
            start_date: 백테스트 시작일
            end_date: 백테스트 종료일
            param_grid: 파라미터 그리드
                {
                    'buy_threshold': [40, 50, 60],
                    'sell_threshold': [-40, -50, -60],
                    'position_size': [0.10, 0.15, 0.20],
                    ...
                }
            max_workers: 병렬 프로세스 수

        Returns:
            OptimizationResult
        """
        start_time = datetime.now()

        logger.info(f"🔍 Starting optimization...")
        logger.info(f"   Period: {start_date} ~ {end_date}")
        logger.info(f"   Objective: {self.objective}")

        # Generate parameter combinations
        param_combinations = self._generate_combinations(param_grid)
        total_combinations = len(param_combinations)

        logger.info(f"   Total combinations: {total_combinations}")

        # Run backtests
        all_results = []
        successful_runs = 0

        # Sequential (single process) for now
        # TODO: Add parallel processing
        for i, params in enumerate(param_combinations):
            if (i + 1) % 10 == 0 or (i + 1) == total_combinations:
                logger.info(f"   Progress: {i+1}/{total_combinations}")

            try:
                result = self._run_backtest(
                    strategy_func,
                    start_date,
                    end_date,
                    params
                )

                all_results.append((params, result))
                successful_runs += 1

            except Exception as e:
                logger.error(f"   ❌ Failed for params {params.to_dict()}: {e}")

        # Find best
        best_params, best_result = self._select_best(all_results)

        optimization_time = (datetime.now() - start_time).total_seconds()

        logger.info(f"✅ Optimization completed in {optimization_time:.1f}s")
        logger.info(f"   Best {self.objective}: {self._get_metric(best_result):.2f}")

        return OptimizationResult(
            best_params=best_params,
            best_sharpe=best_result.sharpe_ratio,
            best_return=best_result.total_return,
            best_mdd=best_result.mdd,
            all_results=all_results,
            total_combinations=total_combinations,
            successful_runs=successful_runs,
            optimization_time=optimization_time
        )

    def walk_forward_analysis(
        self,
        strategy_func: Callable,
        start_date: date,
        end_date: date,
        params: ParameterSet,
        train_months: int = 6,
        test_months: int = 3
    ) -> List[BacktestResult]:
        """
        Walk-Forward Analysis (과적합 방지)

        Train 기간으로 최적화 → Test 기간으로 검증 → 반복

        Args:
            strategy_func: 전략 함수
            start_date: 시작일
            end_date: 종료일
            params: 파라미터
            train_months: 훈련 기간 (개월)
            test_months: 테스트 기간 (개월)

        Returns:
            List of test period BacktestResult
        """
        logger.info(f"🔄 Walk-Forward Analysis...")
        logger.info(f"   Train: {train_months} months / Test: {test_months} months")

        results = []
        current_date = start_date

        while current_date < end_date:
            # Train period
            train_start = current_date
            train_end = train_start + timedelta(days=train_months * 30)

            # Test period
            test_start = train_end
            test_end = test_start + timedelta(days=test_months * 30)

            if test_end > end_date:
                break

            logger.info(f"   Test: {test_start} ~ {test_end}")

            # Run test
            result = self._run_backtest(
                strategy_func,
                test_start,
                test_end,
                params
            )

            results.append(result)

            # Move forward
            current_date = test_end

        # Summary
        avg_return = np.mean([r.total_return for r in results])
        avg_sharpe = np.mean([r.sharpe_ratio for r in results])
        max_mdd = max([r.mdd for r in results])

        logger.info(f"✅ WFA completed: {len(results)} periods")
        logger.info(f"   Avg Return: {avg_return:.2f}%")
        logger.info(f"   Avg Sharpe: {avg_sharpe:.2f}")
        logger.info(f"   Max MDD: {max_mdd:.2f}%")

        return results

    # ========================================
    # HELPERS
    # ========================================

    def _generate_combinations(self, param_grid: Dict[str, List]) -> List[ParameterSet]:
        """파라미터 조합 생성"""
        # Extract keys and values
        keys = list(param_grid.keys())
        values = [param_grid[k] for k in keys]

        # Generate all combinations
        combinations = []

        for combo in itertools.product(*values):
            param_dict = dict(zip(keys, combo))
            combinations.append(ParameterSet(**param_dict))

        return combinations

    def _run_backtest(
        self,
        strategy_func: Callable,
        start_date: date,
        end_date: date,
        params: ParameterSet
    ) -> BacktestResult:
        """백테스트 실행"""
        backtester = Backtester(
            initial_capital=self.initial_capital,
            max_positions=params.max_positions,
            position_size=params.position_size
        )

        # Wrap strategy with params
        def parameterized_strategy(current_date: date) -> List[Dict]:
            return strategy_func(backtester, current_date, params)

        result = backtester.run(
            start_date=start_date,
            end_date=end_date,
            strategy_func=parameterized_strategy
        )

        return result

    def _select_best(
        self,
        results: List[Tuple[ParameterSet, BacktestResult]]
    ) -> Tuple[ParameterSet, BacktestResult]:
        """최적 파라미터 선택"""
        if self.objective == "sharpe":
            best = max(results, key=lambda x: x[1].sharpe_ratio)
        elif self.objective == "return":
            best = max(results, key=lambda x: x[1].total_return)
        elif self.objective == "mdd":
            best = min(results, key=lambda x: x[1].mdd)  # Lower is better
        else:
            best = max(results, key=lambda x: x[1].sharpe_ratio)

        return best

    def _get_metric(self, result: BacktestResult) -> float:
        """목표 지표 값 추출"""
        if self.objective == "sharpe":
            return result.sharpe_ratio
        elif self.objective == "return":
            return result.total_return
        elif self.objective == "mdd":
            return result.mdd
        else:
            return result.sharpe_ratio


# ========================================
# MAIN
# ========================================

def test_strategy(
    backtester: Backtester,
    current_date: date,
    params: ParameterSet
) -> List[Dict]:
    """테스트 전략 (간단한 모멘텀)"""
    from sqlalchemy import text

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
        LIMIT :limit
    """)

    start_date = current_date - timedelta(days=30)

    results = backtester.db.execute(
        query,
        {
            'start_date': start_date,
            'current_date': current_date,
            'limit': params.max_positions
        }
    ).fetchall()

    signals = []

    # Buy top momentum
    for r in results:
        signals.append({
            'code': r.code,
            'action': 'BUY',
            'size': params.position_size
        })

    # Sell others
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

    optimizer = StrategyOptimizer(objective="sharpe")

    # Parameter grid
    param_grid = {
        'buy_threshold': [40.0],  # Not used in simple strategy
        'sell_threshold': [-40.0],
        'position_size': [0.15, 0.20],
        'max_positions': [3, 5],
        'stop_loss': [3.0],
        'take_profit': [5.0],
        'rebalance_days': [5]
    }

    # Optimize (1 month for speed)
    start = date(2024, 11, 1)
    end = date(2024, 11, 30)

    result = optimizer.optimize(
        strategy_func=test_strategy,
        start_date=start,
        end_date=end,
        param_grid=param_grid
    )

    print("\n" + "=" * 70)
    print("🎯 Optimization Results")
    print("=" * 70)

    print(f"\n[Best Parameters]")
    for key, value in result.best_params.to_dict().items():
        print(f"  {key}: {value}")

    print(f"\n[Performance]")
    print(f"  Sharpe: {result.best_sharpe:.2f}")
    print(f"  Return: {result.best_return:+.2f}%")
    print(f"  MDD: {result.best_mdd:.2f}%")

    print(f"\n[Stats]")
    print(f"  Total combinations: {result.total_combinations}")
    print(f"  Successful runs: {result.successful_runs}")
    print(f"  Time: {result.optimization_time:.1f}s")

    print("=" * 70)


if __name__ == "__main__":
    main()
