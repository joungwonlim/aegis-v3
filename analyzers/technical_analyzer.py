"""
AEGIS v3.0 - Technical Analysis Engine
기술적 분석 엔진

Indicators:
- Trend: SMA, EMA, MACD
- Momentum: RSI, Stochastic
- Volatility: Bollinger Bands, ATR
- Volume: Volume MA, OBV

Data: 3년 일별 데이터 (1,893,659건)
"""
import os
import sys
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text

logger = logging.getLogger("TechnicalAnalyzer")


@dataclass
class TechnicalSignals:
    """기술적 분석 시그널"""
    code: str
    name: str

    # Trend
    sma_20: float
    sma_60: float
    ema_12: float
    ema_26: float
    macd: float
    macd_signal: float
    macd_hist: float

    # Momentum
    rsi_14: float
    stoch_k: float
    stoch_d: float

    # Volatility
    bb_upper: float
    bb_middle: float
    bb_lower: float
    bb_width: float
    atr_14: float

    # Volume
    volume_ma_20: float
    volume_ratio: float  # 현재 거래량 / 평균 거래량
    obv: float

    # Signals
    trend_signal: str  # UP, DOWN, SIDEWAYS
    momentum_signal: str  # STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL
    volatility_signal: str  # HIGH, MEDIUM, LOW
    volume_signal: str  # SURGE, NORMAL, DRY

    # Overall
    score: float  # -100 ~ 100
    signal: str  # BUY, SELL, HOLD


class TechnicalAnalyzer:
    """
    기술적 분석 엔진

    3년 일별 데이터로:
    - 추세 분석 (이동평균선, MACD)
    - 모멘텀 분석 (RSI, 스토캐스틱)
    - 변동성 분석 (볼린저 밴드, ATR)
    - 거래량 분석 (거래량 이동평균, OBV)
    """

    def __init__(self):
        self.db = SessionLocal()
        logger.info("✅ TechnicalAnalyzer initialized")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def get_price_data(
        self,
        code: str,
        days: int = 200
    ) -> Optional[pd.DataFrame]:
        """
        종목 가격 데이터 조회

        Args:
            code: 종목코드
            days: 조회 일수 (기본 200일)

        Returns:
            DataFrame with columns: date, open, high, low, close, volume, change_rate
        """
        query = text("""
            SELECT date, open, high, low, close, volume, change_rate
            FROM daily_prices
            WHERE stock_code = :code
            ORDER BY date DESC
            LIMIT :days
        """)

        results = self.db.execute(query, {'code': code, 'days': days}).fetchall()

        if not results:
            return None

        df = pd.DataFrame(results, columns=['date', 'open', 'high', 'low', 'close', 'volume', 'change_rate'])
        df = df.sort_values('date')  # 오래된 순으로 정렬 (계산 위해)
        df = df.reset_index(drop=True)

        return df

    def analyze(self, code: str, name: str) -> Optional[TechnicalSignals]:
        """
        종목 기술적 분석

        Args:
            code: 종목코드
            name: 종목명

        Returns:
            TechnicalSignals or None
        """
        df = self.get_price_data(code, days=200)

        if df is None or len(df) < 60:
            logger.warning(f"   ⚠️  {name} ({code}): 데이터 부족")
            return None

        # Calculate indicators
        try:
            # Trend
            sma_20 = self._sma(df['close'], 20)
            sma_60 = self._sma(df['close'], 60)
            ema_12 = self._ema(df['close'], 12)
            ema_26 = self._ema(df['close'], 26)
            macd, macd_signal, macd_hist = self._macd(df['close'])

            # Momentum
            rsi_14 = self._rsi(df['close'], 14)
            stoch_k, stoch_d = self._stochastic(df, 14, 3)

            # Volatility
            bb_upper, bb_middle, bb_lower = self._bollinger_bands(df['close'], 20, 2)
            bb_width = (bb_upper - bb_lower) / bb_middle * 100
            atr_14 = self._atr(df, 14)

            # Volume
            volume_ma_20 = self._sma(df['volume'], 20)
            current_volume = float(df['volume'].iloc[-1])
            volume_ratio = current_volume / volume_ma_20 if volume_ma_20 > 0 else 1.0
            obv = self._obv(df)

            # Generate signals
            trend_signal = self._trend_signal(
                close=float(df['close'].iloc[-1]),
                sma_20=sma_20,
                sma_60=sma_60,
                macd_hist=macd_hist
            )

            momentum_signal = self._momentum_signal(rsi_14, stoch_k)
            volatility_signal = self._volatility_signal(bb_width, atr_14)
            volume_signal = self._volume_signal(volume_ratio, obv)

            # Calculate overall score
            score = self._calculate_score(
                trend_signal, momentum_signal,
                volatility_signal, volume_signal
            )

            signal = self._overall_signal(score)

            return TechnicalSignals(
                code=code,
                name=name,
                sma_20=sma_20,
                sma_60=sma_60,
                ema_12=ema_12,
                ema_26=ema_26,
                macd=macd,
                macd_signal=macd_signal,
                macd_hist=macd_hist,
                rsi_14=rsi_14,
                stoch_k=stoch_k,
                stoch_d=stoch_d,
                bb_upper=bb_upper,
                bb_middle=bb_middle,
                bb_lower=bb_lower,
                bb_width=bb_width,
                atr_14=atr_14,
                volume_ma_20=volume_ma_20,
                volume_ratio=volume_ratio,
                obv=obv,
                trend_signal=trend_signal,
                momentum_signal=momentum_signal,
                volatility_signal=volatility_signal,
                volume_signal=volume_signal,
                score=score,
                signal=signal
            )

        except Exception as e:
            logger.error(f"   ❌  {name} ({code}): Analysis failed - {e}")
            return None

    # ========================================
    # TREND INDICATORS
    # ========================================

    def _sma(self, series: pd.Series, period: int) -> float:
        """Simple Moving Average"""
        return float(series.iloc[-period:].mean())

    def _ema(self, series: pd.Series, period: int) -> float:
        """Exponential Moving Average"""
        return float(series.ewm(span=period, adjust=False).mean().iloc[-1])

    def _macd(
        self,
        series: pd.Series,
        fast=12,
        slow=26,
        signal=9
    ) -> Tuple[float, float, float]:
        """
        MACD (Moving Average Convergence Divergence)

        Returns:
            (macd, signal, histogram)
        """
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_hist = macd - macd_signal

        return (
            float(macd.iloc[-1]),
            float(macd_signal.iloc[-1]),
            float(macd_hist.iloc[-1])
        )

    # ========================================
    # MOMENTUM INDICATORS
    # ========================================

    def _rsi(self, series: pd.Series, period: int = 14) -> float:
        """
        RSI (Relative Strength Index)

        Returns:
            RSI value (0-100)
        """
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return float(rsi.iloc[-1])

    def _stochastic(
        self,
        df: pd.DataFrame,
        period: int = 14,
        smooth: int = 3
    ) -> Tuple[float, float]:
        """
        Stochastic Oscillator

        Returns:
            (%K, %D)
        """
        low_min = df['low'].rolling(window=period).min()
        high_max = df['high'].rolling(window=period).max()

        k = 100 * (df['close'] - low_min) / (high_max - low_min)
        d = k.rolling(window=smooth).mean()

        return (float(k.iloc[-1]), float(d.iloc[-1]))

    # ========================================
    # VOLATILITY INDICATORS
    # ========================================

    def _bollinger_bands(
        self,
        series: pd.Series,
        period: int = 20,
        std_dev: float = 2.0
    ) -> Tuple[float, float, float]:
        """
        Bollinger Bands

        Returns:
            (upper, middle, lower)
        """
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return (
            float(upper.iloc[-1]),
            float(middle.iloc[-1]),
            float(lower.iloc[-1])
        )

    def _atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        ATR (Average True Range)

        Returns:
            ATR value
        """
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return float(atr.iloc[-1])

    # ========================================
    # VOLUME INDICATORS
    # ========================================

    def _obv(self, df: pd.DataFrame) -> float:
        """
        OBV (On-Balance Volume)

        Returns:
            Current OBV value
        """
        obv = (df['volume'] * (~df['close'].diff().le(0) * 2 - 1)).cumsum()
        return float(obv.iloc[-1])

    # ========================================
    # SIGNAL GENERATION
    # ========================================

    def _trend_signal(
        self,
        close: float,
        sma_20: float,
        sma_60: float,
        macd_hist: float
    ) -> str:
        """추세 시그널"""
        if close > sma_20 > sma_60 and macd_hist > 0:
            return "UP"
        elif close < sma_20 < sma_60 and macd_hist < 0:
            return "DOWN"
        else:
            return "SIDEWAYS"

    def _momentum_signal(self, rsi: float, stoch_k: float) -> str:
        """모멘텀 시그널"""
        if rsi > 70 and stoch_k > 80:
            return "STRONG_SELL"  # 과매수
        elif rsi > 60 and stoch_k > 70:
            return "SELL"
        elif rsi < 30 and stoch_k < 20:
            return "STRONG_BUY"  # 과매도
        elif rsi < 40 and stoch_k < 30:
            return "BUY"
        else:
            return "NEUTRAL"

    def _volatility_signal(self, bb_width: float, atr: float) -> str:
        """변동성 시그널"""
        if bb_width > 10:
            return "HIGH"
        elif bb_width < 5:
            return "LOW"
        else:
            return "MEDIUM"

    def _volume_signal(self, volume_ratio: float, obv: float) -> str:
        """거래량 시그널"""
        if volume_ratio > 2.0:
            return "SURGE"  # 거래량 급증
        elif volume_ratio < 0.5:
            return "DRY"  # 거래량 감소
        else:
            return "NORMAL"

    def _calculate_score(
        self,
        trend: str,
        momentum: str,
        volatility: str,
        volume: str
    ) -> float:
        """
        종합 점수 계산

        Returns:
            -100 ~ 100
        """
        score = 0.0

        # Trend (40점)
        if trend == "UP":
            score += 40
        elif trend == "DOWN":
            score -= 40

        # Momentum (40점)
        momentum_scores = {
            "STRONG_BUY": 40,
            "BUY": 20,
            "NEUTRAL": 0,
            "SELL": -20,
            "STRONG_SELL": -40
        }
        score += momentum_scores.get(momentum, 0)

        # Volume (20점)
        if volume == "SURGE":
            score += 20
        elif volume == "DRY":
            score -= 10

        # Volatility adjustment
        if volatility == "HIGH":
            score *= 0.8  # 변동성 높으면 점수 감점

        return max(-100, min(100, score))

    def _overall_signal(self, score: float) -> str:
        """종합 시그널"""
        if score > 50:
            return "BUY"
        elif score < -50:
            return "SELL"
        else:
            return "HOLD"


# ========================================
# MAIN
# ========================================

def main():
    """테스트"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    analyzer = TechnicalAnalyzer()

    # Test with 삼성전자
    signals = analyzer.analyze("005930", "삼성전자")

    if signals:
        print("\n" + "=" * 60)
        print(f"📊 {signals.name} ({signals.code}) Technical Analysis")
        print("=" * 60)
        print(f"\n[Trend]")
        print(f"  SMA(20): {signals.sma_20:,.0f}")
        print(f"  SMA(60): {signals.sma_60:,.0f}")
        print(f"  MACD: {signals.macd:.2f}")
        print(f"  Signal: {signals.trend_signal}")

        print(f"\n[Momentum]")
        print(f"  RSI(14): {signals.rsi_14:.2f}")
        print(f"  Stoch %K: {signals.stoch_k:.2f}")
        print(f"  Signal: {signals.momentum_signal}")

        print(f"\n[Volatility]")
        print(f"  BB Width: {signals.bb_width:.2f}%")
        print(f"  ATR(14): {signals.atr_14:,.0f}")
        print(f"  Signal: {signals.volatility_signal}")

        print(f"\n[Volume]")
        print(f"  Volume Ratio: {signals.volume_ratio:.2f}x")
        print(f"  Signal: {signals.volume_signal}")

        print(f"\n[Overall]")
        print(f"  Score: {signals.score:.1f}/100")
        print(f"  Signal: {signals.signal}")
        print("=" * 60)


if __name__ == "__main__":
    main()
