"""
AEGIS v3.0 - Database Models
6 Schemas: MARKET, ACCOUNT, BRAIN, TRADE, SYSTEM, ANALYTICS
"""
from app.models.market import Stock, DailyPrice, MarketCandle, MarketMacro
from app.models.account import Portfolio, AccountSnapshot
from app.models.brain import DailyPick, DailyAnalysisLog, IntelFeed, MarketRegime
from app.models.trade import TradeLog, TradeFeedback
from app.models.system import SystemConfig, FetcherHealthLog, StrategyState
from app.models.analytics import BacktestResult

__all__ = [
    # Market
    'Stock', 'DailyPrice', 'MarketCandle', 'MarketMacro',
    # Account
    'Portfolio', 'AccountSnapshot',
    # Brain
    'DailyPick', 'DailyAnalysisLog', 'IntelFeed', 'MarketRegime',
    # Trade
    'TradeLog', 'TradeFeedback',
    # System
    'SystemConfig', 'FetcherHealthLog', 'StrategyState',
    # Analytics
    'BacktestResult',
]
