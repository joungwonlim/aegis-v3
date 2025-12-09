"""
AEGIS v3.0 - Brain Analyzer
Quant Score + AI Score → Final Score 계산

통합 분석:
- Layer 3: DeepSeek R1 (일별 심층 분석)
- Layer 2: gemini-2.0-flash (실시간 빠른 분석)
- Quant: 기술적 지표 (RSI, MACD, 볼린저밴드 등)
"""
import logging
from typing import Dict, Optional, List
from datetime import date
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.brain import DailyPick
from brain.quant_calculator import quant_calculator
from brain.deepseek_client import deepseek_client
from brain.korean_market_traps import korean_trap_detector

logger = logging.getLogger(__name__)


class BrainAnalyzer:
    """
    통합 분석 엔진

    역할:
    - Quant Score 계산 (기술적 지표)
    - AI Score 활용 (DeepSeek/Gemini)
    - Final Score 산출
    - 매수/매도 추천

    설계 원칙:
    - AI Score는 외부에서 제공 (DeepSeek R1 or Gemini)
    - Quant Score는 내부에서 계산 (기술적 지표)
    - Final Score = AI Score (50%) + Quant Score (50%)
    """

    def __init__(self):
        self.db: Session = next(get_db())

    async def analyze_candidate(
        self,
        stock_code: str,
        stock_name: str,
        current_price: int,
        ai_score: Optional[int] = None,
        ai_comment: Optional[str] = None
    ) -> Dict:
        """
        종목 통합 분석

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            current_price: 현재가
            ai_score: AI 점수 (0~100, 선택)
            ai_comment: AI 코멘트 (선택)

        Returns:
            {
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "current_price": 78000,
                "quant_score": 75,
                "ai_score": 85,
                "final_score": 80,
                "recommendation": "BUY/SELL/HOLD",
                "target_price": 82000,
                "stop_loss": 74000,
                "reasoning": "..."
            }
        """
        logger.info(f"🧠 Analyzing: {stock_name} ({stock_code})")

        # 1️⃣ Quant Score 계산
        quant_score = await self._calculate_quant_score(stock_code, current_price)

        # 🚨 한국 시장 함정 감지 (Quant 이후, AI 이전)
        market_data = {}  # TODO: 실제 시장 데이터 수집
        realtime_data = {}  # TODO: 실시간 수급 데이터 수집

        traps = await korean_trap_detector.detect_traps(
            stock_code=stock_code,
            stock_name=stock_name,
            current_price=current_price,
            market_data=market_data,
            realtime_data=realtime_data
        )

        # 함정 감지 시 AI 점수 조정
        trap_penalty = 0
        trap_info = None

        if traps:
            critical_traps = [t for t in traps if t.severity == "CRITICAL"]

            if critical_traps:
                # CRITICAL 함정 → AI 점수 강제 0점
                logger.warning(f"  🚨 CRITICAL 함정 감지: {critical_traps[0].reason}")
                trap_penalty = 100  # AI 점수 완전 제거
                trap_info = {
                    "trapped": True,
                    "trap_type": critical_traps[0].trap_type,
                    "severity": "CRITICAL",
                    "reason": critical_traps[0].reason,
                    "recommendation": critical_traps[0].recommendation
                }
            else:
                # HIGH/MEDIUM 함정 → AI 점수 감점
                trap_penalty = sum(t.confidence * 20 for t in traps)
                logger.warning(f"  ⚠️  함정 {len(traps)}개 감지, AI 점수 -{trap_penalty:.0f}점")
                trap_info = {
                    "trapped": True,
                    "trap_count": len(traps),
                    "reasons": [t.reason for t in traps]
                }

        # 2️⃣ AI Score 확인
        if ai_score is None:
            # daily_picks에서 조회
            ai_score = await self._get_ai_score_from_daily_picks(stock_code)

        # 함정 페널티 적용
        if trap_penalty > 0:
            original_ai_score = ai_score
            ai_score = max(0, ai_score - trap_penalty)
            logger.info(f"  📉 AI 점수 조정: {original_ai_score} → {ai_score} (함정 페널티 -{trap_penalty}점)")

        # 3️⃣ Final Score 계산
        final_score = self._calculate_final_score(quant_score, ai_score)

        # 4️⃣ 추천 결정
        recommendation = self._make_recommendation(final_score, quant_score, ai_score)

        # 5️⃣ 목표가/손절가 계산
        target_price = self._calculate_target_price(current_price, final_score)
        stop_loss = self._calculate_stop_loss(current_price, final_score)

        # 6️⃣ 추론 생성
        reasoning = self._generate_reasoning(
            quant_score, ai_score, final_score, recommendation
        )

        result = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "current_price": current_price,
            "quant_score": quant_score,
            "ai_score": ai_score,
            "final_score": final_score,
            "recommendation": recommendation,
            "target_price": target_price,
            "stop_loss": stop_loss,
            "reasoning": reasoning,
            "ai_comment": ai_comment,
            "trap_info": trap_info  # 한국 시장 함정 정보
        }

        logger.info(f"✅ Analysis complete: {stock_name} - {recommendation} ({final_score}점)")
        return result

    async def _calculate_quant_score(self, stock_code: str, current_price: int) -> int:
        """
        Quant Score 계산 (기술적 지표)

        지표:
        1. RSI (Relative Strength Index) - 30점
        2. MACD (Moving Average Convergence Divergence) - 25점
        3. 볼린저밴드 (Bollinger Bands) - 20점
        4. 거래량 (Volume) - 15점
        5. 이동평균선 (Moving Average) - 10점

        Returns:
            Quant Score (0~100)
        """
        # QuantCalculator 사용
        quant_score = await quant_calculator.calculate_quant_score(stock_code, current_price)
        logger.debug(f"📊 Quant Score calculated: {quant_score}")
        return quant_score

    async def _get_ai_score_from_daily_picks(self, stock_code: str) -> int:
        """
        daily_picks 테이블에서 AI Score 조회

        Args:
            stock_code: 종목 코드

        Returns:
            AI Score (0~100), 없으면 50
        """
        try:
            daily_pick = self.db.query(DailyPick).filter(
                DailyPick.stock_code == stock_code,
                DailyPick.date == date.today()
            ).first()

            if daily_pick and daily_pick.ai_score:
                logger.debug(f"🤖 AI Score from daily_picks: {daily_pick.ai_score}")
                return daily_pick.ai_score
            else:
                logger.debug("🤖 No AI Score found in daily_picks, using default: 50")
                return 50

        except Exception as e:
            logger.error(f"❌ Error fetching AI Score: {e}")
            return 50

    async def get_deepseek_v3_analysis(
        self,
        stock_code: str,
        stock_name: str,
        current_price: int,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        DeepSeek V3 실시간 분석 (Layer 2)

        역할:
        - 수급 데이터 맥락 분석
        - 섹터 트렌드 분석
        - 뉴스/공시 감성 분석

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            current_price: 현재가
            context: 추가 정보 (수급, 뉴스 등)

        Returns:
            {
                "ai_score": 85,
                "ai_comment": "외국인 순매수 지속, 섹터 강세",
                "confidence": 80,
                "recommendation": "BUY"
            }
        """
        logger.info(f"🧠 DeepSeek V3 분석 시작: {stock_name} ({stock_code})")

        # Context 정보 정리
        supply_demand = context.get("supply_demand", {}) if context else {}
        recent_news = context.get("recent_news", []) if context else []
        sector_info = context.get("sector", {}) if context else {}

        # DeepSeek V3 프롬프트
        system_prompt = """당신은 주식 실시간 분석 전문가입니다.
주어진 수급, 뉴스, 섹터 정보를 종합하여 종목을 평가하세요.

응답 형식 (꼭 지켜주세요):
점수: [0~100 정수]
신뢰도: [0~100 정수]
추천: [BUY/SELL/HOLD]
코멘트: [2-3줄 요약]"""

        user_prompt = f"""
종목: {stock_name} ({stock_code})
현재가: {current_price:,}원

## 수급 데이터
- 외국인 순매수: {supply_demand.get('foreign_net', 'N/A')}
- 기관 순매수: {supply_demand.get('institution_net', 'N/A')}
- 거래량 비율: {supply_demand.get('volume_ratio', 'N/A')}

## 최근 뉴스
{self._format_news(recent_news)}

## 섹터 정보
- 섹터: {sector_info.get('name', 'N/A')}
- 섹터 등락률: {sector_info.get('change_rate', 'N/A')}%

위 정보를 종합하여 이 종목의 단기 전망을 평가해주세요.
"""

        try:
            # DeepSeek V3 호출
            response = await deepseek_client.chat_v3(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.7,
                max_tokens=500
            )

            # 응답 파싱
            parsed = self._parse_v3_response(response)

            logger.info(f"✅ DeepSeek V3 분석 완료: {parsed['ai_score']}점, {parsed['recommendation']}")

            return {
                "ai_score": parsed["ai_score"],
                "ai_comment": parsed["comment"],
                "confidence": parsed["confidence"],
                "recommendation": parsed["recommendation"]
            }

        except Exception as e:
            logger.error(f"❌ DeepSeek V3 분석 실패: {e}", exc_info=True)
            # 실패 시 기본값 반환
            return {
                "ai_score": 50,
                "ai_comment": f"DeepSeek V3 분석 실패: {str(e)}",
                "confidence": 0,
                "recommendation": "HOLD"
            }

    def _format_news(self, news_list: List[Dict]) -> str:
        """뉴스 리스트 포맷팅"""
        if not news_list:
            return "N/A"

        formatted = []
        for i, news in enumerate(news_list[:3], 1):  # 최근 3개
            title = news.get('title', 'N/A')
            formatted.append(f"{i}. {title}")

        return "\n".join(formatted)

    def _parse_v3_response(self, response: str) -> Dict:
        """DeepSeek V3 응답 파싱"""
        import re

        result = {
            "ai_score": 50,
            "confidence": 50,
            "recommendation": "HOLD",
            "comment": response[:100]
        }

        try:
            # 점수 추출
            score_match = re.search(r'점수[:\s]*(\d+)', response)
            if score_match:
                result["ai_score"] = int(score_match.group(1))

            # 신뢰도 추출
            conf_match = re.search(r'신뢰도[:\s]*(\d+)', response)
            if conf_match:
                result["confidence"] = int(conf_match.group(1))

            # 추천 추출
            rec_match = re.search(r'추천[:\s]*(BUY|SELL|HOLD)', response, re.IGNORECASE)
            if rec_match:
                result["recommendation"] = rec_match.group(1).upper()

            # 코멘트 추출
            comment_match = re.search(r'코멘트[:\s]*(.+?)(?:\n\n|\Z)', response, re.DOTALL)
            if comment_match:
                result["comment"] = comment_match.group(1).strip()

        except Exception as e:
            logger.error(f"V3 응답 파싱 오류: {e}")

        return result

    def _calculate_final_score(self, quant_score: int, ai_score: int) -> int:
        """
        Final Score 계산

        Formula:
        Final Score = (Quant Score × 0.57) + (AI Score × 0.43)

        가중치 설명:
        - Quant Score (57%): 객관적 지표 중심
          * 기본 60점, 외국인/기관 수급, 양매수, 거래량, MA 위치 등
          * 범위: 0~90점 (최대 오버행 -10점)
        - DeepSeek V3 Score (43%): 맥락 해석
          * 뉴스/공시 해석, 섹터 모멘텀, 매크로 환경, 기술적 패턴
          * 범위: 0~100점

        Args:
            quant_score: Quant 점수 (0~90)
            ai_score: AI 점수 (0~100)

        Returns:
            Final Score (0~100)
        """
        final_score = int((quant_score * 0.57) + (ai_score * 0.43))
        logger.debug(f"🎯 Final Score: {final_score} (Quant {quant_score}×57% + AI {ai_score}×43%)")
        return final_score

    def _make_recommendation(
        self,
        final_score: int,
        quant_score: int,
        ai_score: int
    ) -> str:
        """
        매수/매도/보유 추천

        규칙:
        - Final Score >= 75: BUY
        - Final Score <= 40: SELL
        - 그 외: HOLD

        추가 조건:
        - AI Score와 Quant Score 차이가 30점 이상이면 HOLD (불확실성)

        Args:
            final_score: 최종 점수
            quant_score: Quant 점수
            ai_score: AI 점수

        Returns:
            "BUY" | "SELL" | "HOLD"
        """
        # 1차: 점수 차이 확인 (불확실성)
        score_diff = abs(ai_score - quant_score)
        if score_diff >= 30:
            logger.debug(f"⚠️  High uncertainty (diff: {score_diff}), recommending HOLD")
            return "HOLD"

        # 2차: Final Score 기준
        if final_score >= 75:
            return "BUY"
        elif final_score <= 40:
            return "SELL"
        else:
            return "HOLD"

    def _calculate_target_price(self, current_price: int, final_score: int) -> int:
        """
        목표가 계산

        Formula:
        - Final Score >= 80: +8%
        - Final Score >= 70: +6%
        - Final Score >= 60: +4%
        - 그 외: +2%

        Args:
            current_price: 현재가
            final_score: 최종 점수

        Returns:
            목표가 (원)
        """
        if final_score >= 80:
            multiplier = 1.08
        elif final_score >= 70:
            multiplier = 1.06
        elif final_score >= 60:
            multiplier = 1.04
        else:
            multiplier = 1.02

        target = int(current_price * multiplier)
        logger.debug(f"🎯 Target Price: {target:,}원 (+{(multiplier-1)*100:.1f}%)")
        return target

    def _calculate_stop_loss(self, current_price: int, final_score: int) -> int:
        """
        손절가 계산

        Formula:
        - Final Score >= 80: -3% (높은 확신)
        - Final Score >= 70: -4%
        - Final Score >= 60: -5%
        - 그 외: -6% (낮은 확신)

        Args:
            current_price: 현재가
            final_score: 최종 점수

        Returns:
            손절가 (원)
        """
        if final_score >= 80:
            multiplier = 0.97
        elif final_score >= 70:
            multiplier = 0.96
        elif final_score >= 60:
            multiplier = 0.95
        else:
            multiplier = 0.94

        stop_loss = int(current_price * multiplier)
        logger.debug(f"🛑 Stop Loss: {stop_loss:,}원 ({(multiplier-1)*100:.1f}%)")
        return stop_loss

    def _generate_reasoning(
        self,
        quant_score: int,
        ai_score: int,
        final_score: int,
        recommendation: str
    ) -> str:
        """
        추론 생성

        Args:
            quant_score: Quant 점수
            ai_score: AI 점수
            final_score: 최종 점수
            recommendation: 추천

        Returns:
            추론 문자열
        """
        # 점수 평가
        if final_score >= 75:
            score_eval = "매우 긍정적"
        elif final_score >= 60:
            score_eval = "긍정적"
        elif final_score >= 45:
            score_eval = "중립적"
        else:
            score_eval = "부정적"

        # AI vs Quant 평가
        if abs(ai_score - quant_score) <= 10:
            consistency = "AI와 기술적 지표가 일치"
        elif ai_score > quant_score:
            consistency = "AI가 기술적 지표보다 긍정적"
        else:
            consistency = "기술적 지표가 AI보다 긍정적"

        # 추천 근거
        if recommendation == "BUY":
            action_reason = "매수 적기로 판단"
        elif recommendation == "SELL":
            action_reason = "매도 권장"
        else:
            action_reason = "관망 권장"

        reasoning = f"{score_eval}인 분석 결과 (Final: {final_score}, AI: {ai_score}, Quant: {quant_score}). {consistency}하며, {action_reason}됩니다."

        return reasoning

    async def analyze_batch(
        self,
        candidates: List[Dict]
    ) -> List[Dict]:
        """
        배치 분석

        Args:
            candidates: 후보 종목 리스트
                [
                    {
                        "stock_code": "005930",
                        "stock_name": "삼성전자",
                        "current_price": 78000,
                        "ai_score": 85,
                        "ai_comment": "..."
                    },
                    ...
                ]

        Returns:
            분석 결과 리스트
        """
        results = []

        for candidate in candidates:
            try:
                result = await self.analyze_candidate(
                    stock_code=candidate["stock_code"],
                    stock_name=candidate["stock_name"],
                    current_price=candidate["current_price"],
                    ai_score=candidate.get("ai_score"),
                    ai_comment=candidate.get("ai_comment")
                )
                results.append(result)

            except Exception as e:
                logger.error(f"❌ Error analyzing {candidate['stock_name']}: {e}")
                continue

        logger.info(f"✅ Batch analysis complete: {len(results)}/{len(candidates)}")
        return results


# Singleton Instance
brain_analyzer = BrainAnalyzer()
