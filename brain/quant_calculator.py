"""
AEGIS v3.0 - Quant Calculator
기술적 지표 계산 및 Quant Score 산출

지표:
1. RSI (Relative Strength Index) - 30점
2. MACD (Moving Average Convergence Divergence) - 25점
3. 볼린저밴드 (Bollinger Bands) - 20점
4. 거래량 (Volume) - 15점
5. 이동평균선 (Moving Average) - 10점
"""
import logging
from typing import Dict, List, Optional
from datetime import date, timedelta
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.market import DailyOHLCV

logger = logging.getLogger(__name__)


class QuantCalculator:
    """
    기술적 지표 계산기

    역할:
    - RSI, MACD, 볼린저밴드 등 계산
    - 각 지표별 점수 산출
    - 통합 Quant Score 계산

    데이터 소스:
    - daily_ohlcv 테이블 (pykrx 데이터)
    """

    def __init__(self):
        self.db: Session = next(get_db())

    async def calculate_quant_score(
        self,
        stock_code: str,
        current_price: int
    ) -> int:
        """
        Quant Score 계산

        Args:
            stock_code: 종목 코드
            current_price: 현재가

        Returns:
            Quant Score (0~100)
        """
        logger.debug(f"📊 Calculating Quant Score for {stock_code}")

        # 1️⃣ 과거 데이터 조회 (최근 60일)
        historical_data = await self._get_historical_data(stock_code, days=60)

        if not historical_data or len(historical_data) < 20:
            logger.warning(f"⚠️  Insufficient data for {stock_code}, using default score")
            return 50  # 데이터 부족 시 중립 점수

        # 2️⃣ 각 지표 계산
        rsi_score = await self._calculate_rsi_score(historical_data, current_price)
        macd_score = await self._calculate_macd_score(historical_data, current_price)
        bb_score = await self._calculate_bollinger_score(historical_data, current_price)
        volume_score = await self._calculate_volume_score(historical_data)
        ma_score = await self._calculate_ma_score(historical_data, current_price)

        # 3️⃣ 통합 점수 계산
        quant_score = int(
            rsi_score * 0.30 +
            macd_score * 0.25 +
            bb_score * 0.20 +
            volume_score * 0.15 +
            ma_score * 0.10
        )

        logger.info(f"✅ Quant Score: {quant_score} (RSI: {rsi_score}, MACD: {macd_score}, BB: {bb_score}, Vol: {volume_score}, MA: {ma_score})")
        return quant_score

    async def _get_historical_data(
        self,
        stock_code: str,
        days: int = 60
    ) -> List[DailyOHLCV]:
        """
        과거 OHLCV 데이터 조회

        Args:
            stock_code: 종목 코드
            days: 조회 일수

        Returns:
            OHLCV 데이터 리스트 (오래된 것부터)
        """
        try:
            start_date = date.today() - timedelta(days=days)

            data = self.db.query(DailyOHLCV).filter(
                DailyOHLCV.stock_code == stock_code,
                DailyOHLCV.date >= start_date
            ).order_by(DailyOHLCV.date.asc()).all()

            logger.debug(f"📊 Retrieved {len(data)} days of historical data")
            return data

        except Exception as e:
            logger.error(f"❌ Error fetching historical data: {e}")
            return []

    async def _calculate_rsi_score(
        self,
        historical_data: List[DailyOHLCV],
        current_price: int
    ) -> int:
        """
        RSI (Relative Strength Index) 점수 계산

        RSI 해석:
        - RSI > 70: 과매수 (매도 신호) → 낮은 점수
        - RSI 50~70: 상승 추세 → 높은 점수
        - RSI 30~50: 중립 → 중간 점수
        - RSI < 30: 과매도 (매수 신호) → 높은 점수

        Args:
            historical_data: 과거 데이터
            current_price: 현재가

        Returns:
            RSI 점수 (0~100)
        """
        if len(historical_data) < 14:
            return 50  # 최소 14일 필요

        # RSI 계산 (14일 기준)
        closes = [d.close for d in historical_data[-14:]] + [current_price]

        gains = []
        losses = []

        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains) / len(gains)
        avg_loss = sum(losses) / len(losses)

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # RSI → 점수 변환
        if rsi >= 70:
            # 과매수 → 낮은 점수
            score = max(30, 100 - int((rsi - 70) * 2))
        elif rsi >= 50:
            # 상승 추세 → 높은 점수
            score = 70 + int((rsi - 50) * 1.5)
        elif rsi >= 30:
            # 중립 → 중간 점수
            score = 50 + int((rsi - 30))
        else:
            # 과매도 → 높은 점수 (매수 기회)
            score = 70 + int((30 - rsi))

        logger.debug(f"📊 RSI: {rsi:.2f} → Score: {score}")
        return min(100, max(0, score))

    async def _calculate_macd_score(
        self,
        historical_data: List[DailyOHLCV],
        current_price: int
    ) -> int:
        """
        MACD (Moving Average Convergence Divergence) 점수 계산

        MACD 해석:
        - MACD > Signal: 상승 신호 → 높은 점수
        - MACD < Signal: 하락 신호 → 낮은 점수
        - 골든크로스: MACD가 Signal을 상향 돌파 → 매우 높은 점수

        Args:
            historical_data: 과거 데이터
            current_price: 현재가

        Returns:
            MACD 점수 (0~100)
        """
        if len(historical_data) < 26:
            return 50  # 최소 26일 필요

        closes = [d.close for d in historical_data] + [current_price]

        # EMA 계산 헬퍼
        def calculate_ema(data: List[float], period: int) -> float:
            multiplier = 2 / (period + 1)
            ema = sum(data[:period]) / period

            for price in data[period:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))

            return ema

        # MACD Line = EMA(12) - EMA(26)
        ema_12 = calculate_ema(closes, 12)
        ema_26 = calculate_ema(closes, 26)
        macd_line = ema_12 - ema_26

        # Signal Line = EMA(MACD, 9)
        # 간단히 최근 9일 MACD 평균으로 근사
        recent_macd_values = []
        for i in range(len(closes) - 9, len(closes)):
            temp_ema_12 = calculate_ema(closes[:i+1], 12)
            temp_ema_26 = calculate_ema(closes[:i+1], 26)
            recent_macd_values.append(temp_ema_12 - temp_ema_26)

        signal_line = sum(recent_macd_values) / len(recent_macd_values)

        # Histogram = MACD - Signal
        histogram = macd_line - signal_line

        # 골든크로스 확인 (최근 2일)
        if len(recent_macd_values) >= 2:
            prev_histogram = recent_macd_values[-2] - signal_line
            if prev_histogram < 0 and histogram > 0:
                # 골든크로스!
                logger.debug("🌟 MACD Golden Cross detected!")
                return 95

        # MACD → 점수 변환
        if histogram > 0:
            # 상승 신호
            score = 60 + int(min(40, histogram / current_price * 10000))
        else:
            # 하락 신호
            score = 40 + int(max(-40, histogram / current_price * 10000))

        logger.debug(f"📊 MACD: {macd_line:.2f}, Signal: {signal_line:.2f}, Hist: {histogram:.2f} → Score: {score}")
        return min(100, max(0, score))

    async def _calculate_bollinger_score(
        self,
        historical_data: List[DailyOHLCV],
        current_price: int
    ) -> int:
        """
        볼린저밴드 점수 계산

        볼린저밴드 해석:
        - 가격이 하단 밴드 근처: 과매도 → 높은 점수
        - 가격이 중간: 정상 → 중간 점수
        - 가격이 상단 밴드 근처: 과매수 → 낮은 점수

        Args:
            historical_data: 과거 데이터
            current_price: 현재가

        Returns:
            볼린저밴드 점수 (0~100)
        """
        if len(historical_data) < 20:
            return 50  # 최소 20일 필요

        closes = [d.close for d in historical_data[-20:]] + [current_price]

        # 중심선 (20일 이동평균)
        middle_band = sum(closes) / len(closes)

        # 표준편차
        variance = sum((x - middle_band) ** 2 for x in closes) / len(closes)
        std_dev = variance ** 0.5

        # 상단/하단 밴드
        upper_band = middle_band + (std_dev * 2)
        lower_band = middle_band - (std_dev * 2)

        # 현재가 위치 계산 (0~1, 0=하단, 0.5=중간, 1=상단)
        if upper_band == lower_band:
            position = 0.5
        else:
            position = (current_price - lower_band) / (upper_band - lower_band)

        # 위치 → 점수 변환
        if position < 0.2:
            # 하단 밴드 근처 (과매도) → 높은 점수
            score = 80 + int((0.2 - position) * 100)
        elif position < 0.4:
            # 중하위 → 중상위 점수
            score = 60 + int((0.4 - position) * 100)
        elif position < 0.6:
            # 중간 → 중간 점수
            score = 50 + int(abs(0.5 - position) * 100)
        elif position < 0.8:
            # 중상위 → 중하위 점수
            score = 40 + int((0.8 - position) * 100)
        else:
            # 상단 밴드 근처 (과매수) → 낮은 점수
            score = 20 + int((1.0 - position) * 100)

        logger.debug(f"📊 Bollinger: Lower={lower_band:.0f}, Middle={middle_band:.0f}, Upper={upper_band:.0f}, Position={position:.2f} → Score: {score}")
        return min(100, max(0, score))

    async def _calculate_volume_score(
        self,
        historical_data: List[DailyOHLCV]
    ) -> int:
        """
        거래량 점수 계산

        거래량 해석:
        - 최근 거래량이 평균 대비 2배 이상: 강한 관심 → 높은 점수
        - 최근 거래량이 평균 수준: 정상 → 중간 점수
        - 최근 거래량이 평균 미만: 관심 저조 → 낮은 점수

        Args:
            historical_data: 과거 데이터

        Returns:
            거래량 점수 (0~100)
        """
        if len(historical_data) < 20:
            return 50

        volumes = [d.volume for d in historical_data]
        recent_volume = volumes[-1]  # 최근 1일
        avg_volume = sum(volumes) / len(volumes)

        # 거래량 비율
        if avg_volume == 0:
            ratio = 1.0
        else:
            ratio = recent_volume / avg_volume

        # 비율 → 점수 변환
        if ratio >= 2.0:
            # 2배 이상: 매우 강한 관심
            score = 85 + int(min(15, (ratio - 2.0) * 10))
        elif ratio >= 1.5:
            # 1.5배: 강한 관심
            score = 70 + int((ratio - 1.5) * 30)
        elif ratio >= 1.0:
            # 평균 이상
            score = 50 + int((ratio - 1.0) * 40)
        elif ratio >= 0.5:
            # 평균 미만
            score = 30 + int((ratio - 0.5) * 40)
        else:
            # 0.5배 미만: 관심 매우 저조
            score = int(ratio * 60)

        logger.debug(f"📊 Volume: Recent={recent_volume:,}, Avg={avg_volume:,.0f}, Ratio={ratio:.2f} → Score: {score}")
        return min(100, max(0, score))

    async def _calculate_ma_score(
        self,
        historical_data: List[DailyOHLCV],
        current_price: int
    ) -> int:
        """
        이동평균선 점수 계산

        이동평균선 해석:
        - 가격 > MA5 > MA20 > MA60: 강한 상승 추세 → 높은 점수
        - 가격 > MA5 > MA20: 상승 추세 → 중상위 점수
        - 가격 > MA5: 단기 상승 → 중간 점수
        - 가격 < MA5: 하락 → 낮은 점수

        Args:
            historical_data: 과거 데이터
            current_price: 현재가

        Returns:
            이동평균선 점수 (0~100)
        """
        if len(historical_data) < 60:
            return 50

        closes = [d.close for d in historical_data]

        # 이동평균 계산
        ma_5 = sum(closes[-5:]) / 5
        ma_20 = sum(closes[-20:]) / 20
        ma_60 = sum(closes[-60:]) / 60

        # 정렬 확인
        score = 50  # 기본 점수

        if current_price > ma_5:
            score += 10
            if ma_5 > ma_20:
                score += 15
                if ma_20 > ma_60:
                    score += 25  # 완벽한 정배열
                else:
                    score += 10
            else:
                score += 5
        else:
            score -= 20

        logger.debug(f"📊 MA: MA5={ma_5:.0f}, MA20={ma_20:.0f}, MA60={ma_60:.0f}, Price={current_price} → Score: {score}")
        return min(100, max(0, score))


# Singleton Instance
quant_calculator = QuantCalculator()
