"""
AEGIS v3.0 - Korean Market Trap Detector
한국 시장 특유의 함정 패턴 감지 및 학습 시스템

핵심 원칙:
- "전강후약(Gap Up & Die)" 패턴 감지
- 수급 이탈 (Fake Rise) 실시간 감지
- AI 학습 피드백 루프 (실패 → 학습 → 개선)

학습 메커니즘:
1. 패턴 감지 → 매수 회피
2. 실제 결과 수집 (맞았는지/틀렸는지)
3. 패턴 가중치 조정 (강화/약화)
4. AI 프롬프트 업데이트
"""
import logging
from datetime import datetime, date
from typing import Dict, Optional, List
from dataclasses import dataclass

from app.database import get_db
from app.models.learning import TrapPattern, TradeFeedback

logger = logging.getLogger(__name__)


@dataclass
class TrapDetection:
    """함정 감지 결과"""
    trapped: bool
    trap_type: str
    reason: str
    confidence: float
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    recommendation: str  # "AVOID", "WAIT", "REDUCE_SIZE"


class KoreanMarketTrapDetector:
    """
    한국 시장 함정 패턴 감지기

    역할:
    - 10가지 한국 시장 특유 함정 패턴 감지
    - 실시간 수급 이탈 감지
    - AI 학습 피드백 루프

    핵심 패턴:
    1. 수급 이탈 (Fake Rise)
    2. 매도벽 (Resistance Wall)
    3. 섹터 디커플링 (Alone in the Dark)
    4. 환율 쇼크 (FX Impact)
    5. 뉴스 후 음봉 (Sell on News)
    6. 거래량 없는 상승 (Hollow Rise)
    7. 장기 이평선 저항 (Technical Ceiling)
    8. ADR 경고 (Market Width)
    9. 오버행 상장 (Dilution Day)
    10. 프로그램 매도 가속 (Program Dump)
    """

    def __init__(self):
        # 임계값 설정
        self.GAP_OVERHEAT_PCT = 3.5  # 갭 과열 기준
        self.VOLUME_SUPPORT_RATIO = 0.5  # 거래량 지지 최소 비율
        self.SECTOR_DIVERGENCE_PCT = 2.0  # 섹터 괴리율
        self.FX_SHOCK_PCT = 0.5  # 환율 급등 기준

        # 학습된 패턴 가중치 (초기값)
        self.pattern_weights = {
            "fake_rise": 0.95,  # 수급 이탈: 가장 위험
            "gap_overheat": 0.90,  # 갭 과열
            "program_dump": 0.85,  # 프로그램 매도
            "sell_on_news": 0.80,
            "hollow_rise": 0.75,
            "sell_wall": 0.70,
            "sector_decouple": 0.65,
            "fx_shock": 0.60,
            "ma_resistance": 0.55,
            "dilution_day": 0.90
        }

    async def detect_traps(
        self,
        stock_code: str,
        stock_name: str,
        current_price: int,
        market_data: Dict,
        realtime_data: Optional[Dict] = None
    ) -> List[TrapDetection]:
        """
        종합 함정 감지

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            current_price: 현재가
            market_data: 시장 데이터 (호가, 거래량, 이평선 등)
            realtime_data: 실시간 데이터 (프로그램 매매, 외국인 수급)

        Returns:
            감지된 함정 리스트
        """
        traps = []

        # 1️⃣ 수급 이탈 (Fake Rise) - 최우선
        fake_rise = await self._detect_fake_rise(
            stock_code, current_price, market_data, realtime_data
        )
        if fake_rise:
            traps.append(fake_rise)

        # 2️⃣ 갭 과열 (Gap Overheat)
        gap_overheat = await self._detect_gap_overheat(
            stock_code, current_price, market_data
        )
        if gap_overheat:
            traps.append(gap_overheat)

        # 3️⃣ 프로그램 매도 가속 (Program Dump)
        if realtime_data:
            program_dump = await self._detect_program_dump(
                stock_code, realtime_data
            )
            if program_dump:
                traps.append(program_dump)

        # 4️⃣ 뉴스 후 음봉 (Sell on News)
        sell_on_news = await self._detect_sell_on_news(
            stock_code, market_data
        )
        if sell_on_news:
            traps.append(sell_on_news)

        # 5️⃣ 거래량 없는 상승 (Hollow Rise)
        hollow_rise = await self._detect_hollow_rise(
            stock_code, current_price, market_data
        )
        if hollow_rise:
            traps.append(hollow_rise)

        # 6️⃣ 매도벽 (Resistance Wall)
        sell_wall = await self._detect_sell_wall(
            stock_code, market_data
        )
        if sell_wall:
            traps.append(sell_wall)

        # 7️⃣ 섹터 디커플링 (Sector Decouple)
        sector_decouple = await self._detect_sector_decouple(
            stock_code, current_price, market_data
        )
        if sector_decouple:
            traps.append(sector_decouple)

        # 8️⃣ 환율 쇼크 (FX Impact)
        fx_shock = await self._detect_fx_shock(market_data)
        if fx_shock:
            traps.append(fx_shock)

        # 9️⃣ 장기 이평선 저항 (MA Resistance)
        ma_resistance = await self._detect_ma_resistance(
            stock_code, current_price, market_data
        )
        if ma_resistance:
            traps.append(ma_resistance)

        # 🔟 오버행 상장 (Dilution Day)
        dilution = await self._detect_dilution_day(stock_code)
        if dilution:
            traps.append(dilution)

        # 학습된 가중치 적용하여 정렬
        traps = self._apply_learned_weights(traps)

        return traps

    async def _detect_fake_rise(
        self,
        stock_code: str,
        current_price: int,
        market_data: Dict,
        realtime_data: Optional[Dict]
    ) -> Optional[TrapDetection]:
        """
        1️⃣ 수급 이탈 (Fake Rise) 감지

        조건:
        - 주가는 상승 중 (+1% 이상)
        - 외국인/기관 순매수는 음수(-)
        - 개미만 사고 있는 상황

        가장 위험한 패턴: 95% 신뢰도
        """
        try:
            price_change_pct = market_data.get('price_change_pct', 0)

            # 주가 상승 중이 아니면 패스
            if price_change_pct < 1.0:
                return None

            if not realtime_data:
                return None

            # 외국인/기관 순매수 (음수 = 순매도)
            foreign_net = realtime_data.get('foreign_net_buy', 0)
            inst_net = realtime_data.get('inst_net_buy', 0)

            # 둘 다 순매도 중이면 함정
            if foreign_net < 0 and inst_net < 0:
                severity = "CRITICAL"
                confidence = self.pattern_weights["fake_rise"]

                reason = (
                    f"주가 상승(+{price_change_pct:.2f}%) BUT 수급 이탈! "
                    f"외국인 {foreign_net:,}주 매도, 기관 {inst_net:,}주 매도. "
                    f"개미 유인 함정(Ant-Luring) 감지."
                )

                logger.warning(f"  🚨 [{stock_code}] FAKE RISE: {reason}")

                return TrapDetection(
                    trapped=True,
                    trap_type="fake_rise",
                    reason=reason,
                    confidence=confidence,
                    severity=severity,
                    recommendation="AVOID"
                )

        except Exception as e:
            logger.error(f"Fake rise detection error: {e}")

        return None

    async def _detect_gap_overheat(
        self,
        stock_code: str,
        current_price: int,
        market_data: Dict
    ) -> Optional[TrapDetection]:
        """
        2️⃣ 갭 과열 (Gap Overheat) 감지

        조건:
        - 시초가가 전일 대비 +3.5% 이상
        - "너무 높게 시작하면 먹을 게 없다"

        전강후약 패턴의 전조
        """
        try:
            open_price = market_data.get('open_price', 0)
            prev_close = market_data.get('prev_close', 0)

            if prev_close == 0:
                return None

            gap_pct = ((open_price - prev_close) / prev_close) * 100

            if gap_pct >= self.GAP_OVERHEAT_PCT:
                severity = "HIGH"
                confidence = self.pattern_weights["gap_overheat"]

                reason = (
                    f"갭 과열 (+{gap_pct:.2f}%). "
                    f"미국장 호재에 갭상승 → 차익 실현 위험. "
                    f"'전강후약' 패턴 전조."
                )

                logger.warning(f"  ⚠️  [{stock_code}] GAP OVERHEAT: {reason}")

                return TrapDetection(
                    trapped=True,
                    trap_type="gap_overheat",
                    reason=reason,
                    confidence=confidence,
                    severity=severity,
                    recommendation="WAIT"  # 눌림목 대기
                )

        except Exception as e:
            logger.error(f"Gap overheat detection error: {e}")

        return None

    async def _detect_program_dump(
        self,
        stock_code: str,
        realtime_data: Dict
    ) -> Optional[TrapDetection]:
        """
        3️⃣ 프로그램 매도 가속 (Program Dump) 감지

        조건:
        - 프로그램 순매수가 음수(-)
        - 매도 기울기가 가파름 (가속 중)

        오후장 폭락 전조
        """
        try:
            program_net = realtime_data.get('program_net_buy', 0)
            program_slope = realtime_data.get('program_slope', 0)

            # 순매도 + 가속 중
            if program_net < 0 and program_slope < -0.3:
                severity = "HIGH"
                confidence = self.pattern_weights["program_dump"]

                reason = (
                    f"프로그램 매도 가속 (순매수 {program_net:,}주, 기울기 {program_slope:.2f}). "
                    f"오후장 폭락 전조."
                )

                logger.warning(f"  🚨 [{stock_code}] PROGRAM DUMP: {reason}")

                return TrapDetection(
                    trapped=True,
                    trap_type="program_dump",
                    reason=reason,
                    confidence=confidence,
                    severity=severity,
                    recommendation="AVOID"
                )

        except Exception as e:
            logger.error(f"Program dump detection error: {e}")

        return None

    async def _detect_sell_on_news(
        self,
        stock_code: str,
        market_data: Dict
    ) -> Optional[TrapDetection]:
        """
        4️⃣ 뉴스 후 음봉 (Sell on News) 감지

        조건:
        - 호재 뉴스 발생
        - 거래량 급증
        - 현재가 < 시초가 (밀리고 있음)

        재료 소멸 패턴
        """
        try:
            has_news = market_data.get('has_positive_news', False)
            volume_ratio = market_data.get('volume_ratio', 1.0)
            open_price = market_data.get('open_price', 0)
            current_price = market_data.get('current_price', 0)

            # 호재 뉴스 + 거래량 터짐 + 시초가 대비 하락
            if has_news and volume_ratio > 2.0 and current_price < open_price:
                severity = "MEDIUM"
                confidence = self.pattern_weights["sell_on_news"]

                decline_pct = ((current_price - open_price) / open_price) * 100

                reason = (
                    f"뉴스 후 음봉. 호재 발표 → 거래량 {volume_ratio:.1f}배 → "
                    f"현재가 시초가 대비 {decline_pct:.2f}%. 재료 소멸."
                )

                logger.warning(f"  ⚠️  [{stock_code}] SELL ON NEWS: {reason}")

                return TrapDetection(
                    trapped=True,
                    trap_type="sell_on_news",
                    reason=reason,
                    confidence=confidence,
                    severity=severity,
                    recommendation="AVOID"
                )

        except Exception as e:
            logger.error(f"Sell on news detection error: {e}")

        return None

    async def _detect_hollow_rise(
        self,
        stock_code: str,
        current_price: int,
        market_data: Dict
    ) -> Optional[TrapDetection]:
        """
        5️⃣ 거래량 없는 상승 (Hollow Rise) 감지

        조건:
        - 주가 +3% 이상 상승
        - 거래량 < 전일 대비 50%

        적은 돈으로 가격만 올려놓은 상태
        """
        try:
            price_change_pct = market_data.get('price_change_pct', 0)
            volume_ratio = market_data.get('volume_ratio', 1.0)

            # 상승 중 + 거래량 부족
            if price_change_pct >= 3.0 and volume_ratio < self.VOLUME_SUPPORT_RATIO:
                severity = "MEDIUM"
                confidence = self.pattern_weights["hollow_rise"]

                reason = (
                    f"거래량 없는 상승 (+{price_change_pct:.2f}%, 거래량 {volume_ratio*100:.0f}%). "
                    f"취약한 상승. 툭 치면 무너짐."
                )

                logger.warning(f"  ⚠️  [{stock_code}] HOLLOW RISE: {reason}")

                return TrapDetection(
                    trapped=True,
                    trap_type="hollow_rise",
                    reason=reason,
                    confidence=confidence,
                    severity=severity,
                    recommendation="REDUCE_SIZE"
                )

        except Exception as e:
            logger.error(f"Hollow rise detection error: {e}")

        return None

    async def _detect_sell_wall(
        self,
        stock_code: str,
        market_data: Dict
    ) -> Optional[TrapDetection]:
        """
        6️⃣ 매도벽 (Resistance Wall) 감지

        조건:
        - 1~2호가에 평소 거래량의 5배 매도 물량

        돌파 불가능
        """
        try:
            orderbook = market_data.get('orderbook', {})
            avg_volume = market_data.get('avg_volume', 0)

            # 매도 1호가, 2호가 물량
            ask1_qty = orderbook.get('ask1_qty', 0)
            ask2_qty = orderbook.get('ask2_qty', 0)
            total_ask_qty = ask1_qty + ask2_qty

            # 평소 거래량의 5배 이상이면 매도벽
            if avg_volume > 0 and total_ask_qty > (avg_volume * 5):
                severity = "MEDIUM"
                confidence = self.pattern_weights["sell_wall"]

                ask1_price = orderbook.get('ask1_price', 0)

                reason = (
                    f"매도벽 감지. {ask1_price:,}원에 {total_ask_qty:,}주 ({total_ask_qty/avg_volume:.1f}배). "
                    f"모멘텀 차단."
                )

                logger.warning(f"  ⚠️  [{stock_code}] SELL WALL: {reason}")

                return TrapDetection(
                    trapped=True,
                    trap_type="sell_wall",
                    reason=reason,
                    confidence=confidence,
                    severity=severity,
                    recommendation="WAIT"
                )

        except Exception as e:
            logger.error(f"Sell wall detection error: {e}")

        return None

    async def _detect_sector_decouple(
        self,
        stock_code: str,
        current_price: int,
        market_data: Dict
    ) -> Optional[TrapDetection]:
        """
        7️⃣ 섹터 디커플링 (Sector Decouple) 감지

        조건:
        - 내 종목 +3% 상승
        - 섹터 지수 -1% 하락

        곧 따라 내려감
        """
        try:
            price_change_pct = market_data.get('price_change_pct', 0)
            sector_change_pct = market_data.get('sector_change_pct', 0)
            sector_name = market_data.get('sector_name', 'Unknown')

            # 종목 상승 + 섹터 하락 → 괴리
            divergence = price_change_pct - sector_change_pct

            if price_change_pct > 2.0 and divergence >= self.SECTOR_DIVERGENCE_PCT:
                severity = "MEDIUM"
                confidence = self.pattern_weights["sector_decouple"]

                reason = (
                    f"섹터 디커플링. 종목 +{price_change_pct:.2f}% BUT "
                    f"{sector_name} 섹터 {sector_change_pct:+.2f}%. "
                    f"괴리 {divergence:.2f}%p. 회귀 가능성 높음."
                )

                logger.warning(f"  ⚠️  [{stock_code}] SECTOR DECOUPLE: {reason}")

                return TrapDetection(
                    trapped=True,
                    trap_type="sector_decouple",
                    reason=reason,
                    confidence=confidence,
                    severity=severity,
                    recommendation="WAIT"
                )

        except Exception as e:
            logger.error(f"Sector decouple detection error: {e}")

        return None

    async def _detect_fx_shock(self, market_data: Dict) -> Optional[TrapDetection]:
        """
        8️⃣ 환율 쇼크 (FX Impact) 감지

        조건:
        - 원/달러 환율 +0.5% 이상 급등

        외국인 프로그램 매도 유발
        """
        try:
            fx_change_pct = market_data.get('fx_change_pct', 0)
            current_fx = market_data.get('current_fx', 0)

            if fx_change_pct >= self.FX_SHOCK_PCT:
                severity = "MEDIUM"
                confidence = self.pattern_weights["fx_shock"]

                reason = (
                    f"환율 쇼크. USD/KRW {current_fx:.2f}원 (+{fx_change_pct:.2f}%). "
                    f"외국인 Exit 리스크."
                )

                logger.warning(f"  ⚠️  FX SHOCK: {reason}")

                return TrapDetection(
                    trapped=True,
                    trap_type="fx_shock",
                    reason=reason,
                    confidence=confidence,
                    severity=severity,
                    recommendation="REDUCE_SIZE"
                )

        except Exception as e:
            logger.error(f"FX shock detection error: {e}")

        return None

    async def _detect_ma_resistance(
        self,
        stock_code: str,
        current_price: int,
        market_data: Dict
    ) -> Optional[TrapDetection]:
        """
        9️⃣ 장기 이평선 저항 (MA Resistance) 감지

        조건:
        - 현재가가 120일선 or 200일선에 근접 (±1%)

        한국 시장 80% 여기서 맞고 떨어짐
        """
        try:
            ma120 = market_data.get('ma120', 0)
            ma200 = market_data.get('ma200', 0)

            if ma120 == 0 and ma200 == 0:
                return None

            # 120일선 또는 200일선에 근접
            ma120_diff_pct = abs((current_price - ma120) / ma120 * 100) if ma120 > 0 else 999
            ma200_diff_pct = abs((current_price - ma200) / ma200 * 100) if ma200 > 0 else 999

            if ma120_diff_pct <= 1.0 or ma200_diff_pct <= 1.0:
                severity = "LOW"
                confidence = self.pattern_weights["ma_resistance"]

                ma_type = "120일선" if ma120_diff_pct <= 1.0 else "200일선"
                ma_price = ma120 if ma120_diff_pct <= 1.0 else ma200

                reason = (
                    f"{ma_type} 저항 근접 ({ma_price:,}원). "
                    f"한국 시장에서 여기서 떨어질 확률 80%."
                )

                logger.info(f"  ℹ️  [{stock_code}] MA RESISTANCE: {reason}")

                return TrapDetection(
                    trapped=True,
                    trap_type="ma_resistance",
                    reason=reason,
                    confidence=confidence,
                    severity=severity,
                    recommendation="WAIT"
                )

        except Exception as e:
            logger.error(f"MA resistance detection error: {e}")

        return None

    async def _detect_dilution_day(self, stock_code: str) -> Optional[TrapDetection]:
        """
        🔟 오버행 상장 (Dilution Day) 감지

        조건:
        - 오늘이 CB/BW/신주 상장일

        무조건 던져야 함
        """
        try:
            # TODO: DART API로 CB/BW 상장 예정일 조회
            # 임시로 DB에서 확인
            # is_dilution_day = check_dilution_schedule(stock_code, date.today())

            is_dilution_day = False  # Placeholder

            if is_dilution_day:
                severity = "CRITICAL"
                confidence = self.pattern_weights["dilution_day"]

                reason = (
                    f"오버행 상장일. CB/BW/신주 상장. "
                    f"물량 공급 쇼크 임박."
                )

                logger.warning(f"  🚨 [{stock_code}] DILUTION DAY: {reason}")

                return TrapDetection(
                    trapped=True,
                    trap_type="dilution_day",
                    reason=reason,
                    confidence=confidence,
                    severity=severity,
                    recommendation="AVOID"
                )

        except Exception as e:
            logger.error(f"Dilution day detection error: {e}")

        return None

    def _apply_learned_weights(self, traps: List[TrapDetection]) -> List[TrapDetection]:
        """
        학습된 가중치를 적용하여 함정 리스트 정렬

        가중치가 높을수록 (신뢰도 높을수록) 우선순위
        """
        return sorted(traps, key=lambda t: t.confidence, reverse=True)

    async def record_feedback(
        self,
        stock_code: str,
        trap_detected: bool,
        trap_type: Optional[str],
        avoided_buy: bool,
        actual_result: str,  # "CORRECT" | "WRONG"
        price_change_pct: float
    ):
        """
        AI 학습 피드백 루프

        Args:
            stock_code: 종목 코드
            trap_detected: 함정 감지 여부
            trap_type: 감지된 함정 타입
            avoided_buy: 매수 회피 여부
            actual_result: 실제 결과 (맞았는지/틀렸는지)
            price_change_pct: 실제 가격 변화

        학습 로직:
        - CORRECT: 가중치 증가 (강화)
        - WRONG: 가중치 감소 (약화)
        """
        try:
            db = next(get_db())

            # 피드백 저장
            feedback = TradeFeedback(
                trade_date=date.today(),
                stock_code=stock_code,
                trap_detected=trap_detected,
                trap_type=trap_type,
                avoided_buy=avoided_buy,
                actual_result=actual_result,
                price_change_pct=price_change_pct,
                created_at=datetime.now()
            )

            db.add(feedback)
            db.commit()

            # 가중치 업데이트
            if trap_type and trap_type in self.pattern_weights:
                if actual_result == "CORRECT":
                    # 맞췄으면 가중치 증가 (+0.01, 최대 0.99)
                    self.pattern_weights[trap_type] = min(
                        0.99,
                        self.pattern_weights[trap_type] + 0.01
                    )
                    logger.info(f"  ✅ [{trap_type}] weight increased: {self.pattern_weights[trap_type]:.2f}")

                elif actual_result == "WRONG":
                    # 틀렸으면 가중치 감소 (-0.02, 최소 0.30)
                    self.pattern_weights[trap_type] = max(
                        0.30,
                        self.pattern_weights[trap_type] - 0.02
                    )
                    logger.warning(f"  ⚠️  [{trap_type}] weight decreased: {self.pattern_weights[trap_type]:.2f}")

            # 학습된 가중치 DB 저장
            pattern = db.query(TrapPattern).filter(
                TrapPattern.trap_type == trap_type
            ).first()

            if pattern:
                pattern.weight = self.pattern_weights[trap_type]
                pattern.total_count += 1
                if actual_result == "CORRECT":
                    pattern.correct_count += 1
                pattern.accuracy = (pattern.correct_count / pattern.total_count) * 100
                pattern.updated_at = datetime.now()
            else:
                # 신규 패턴 생성
                pattern = TrapPattern(
                    trap_type=trap_type,
                    weight=self.pattern_weights[trap_type],
                    total_count=1,
                    correct_count=1 if actual_result == "CORRECT" else 0,
                    accuracy=100.0 if actual_result == "CORRECT" else 0.0,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(pattern)

            db.commit()
            logger.info(f"  📊 Feedback recorded: {trap_type} → {actual_result}")

        except Exception as e:
            logger.error(f"Feedback recording error: {e}")

        finally:
            try:
                db.close()
            except:
                pass


# Singleton Instance
korean_trap_detector = KoreanMarketTrapDetector()
