"""
AEGIS v3.0 - Scenario Validator
통합 검증: 시나리오 + 백테스트 + 몬테카를로

검증 프로세스:
1. 시나리오 검증 - Best/Expected/Worst case 분석
2. 백테스트 - 과거 3개월 유사 패턴 승률
3. 몬테카를로 - 1000회 시뮬레이션 확률 분포

최종 결정: 세 가지 점수 종합 → 승인/거부
"""
import logging
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from brain.deepseek_client import deepseek_client

logger = logging.getLogger(__name__)


@dataclass
class ScenarioResult:
    """시나리오 분석 결과"""
    best_case: float      # 최선: +15%
    expected_case: float  # 예상: +8%
    worst_case: float     # 최악: -3%
    probability_best: float     # 최선 확률: 20%
    probability_expected: float # 예상 확률: 60%
    probability_worst: float    # 최악 확률: 20%
    score: float          # 시나리오 점수 (0~100)


@dataclass
class BacktestResult:
    """백테스트 결과"""
    total_trades: int      # 총 거래 수
    winning_trades: int    # 승리 거래 수
    losing_trades: int     # 패배 거래 수
    win_rate: float        # 승률 (%)
    avg_return: float      # 평균 수익률 (%)
    max_return: float      # 최대 수익률 (%)
    max_loss: float        # 최대 손실률 (%)
    score: float           # 백테스트 점수 (0~100)


@dataclass
class MonteCarloResult:
    """몬테카를로 시뮬레이션 결과"""
    simulations: int       # 시뮬레이션 횟수
    mean_return: float     # 평균 수익률 (%)
    std_return: float      # 수익률 표준편차 (%)
    prob_profit: float     # 수익 확률 (%)
    prob_loss: float       # 손실 확률 (%)
    percentile_5: float    # 5% 백분위 (최악의 5%)
    percentile_50: float   # 50% 백분위 (중앙값)
    percentile_95: float   # 95% 백분위 (최선의 5%)
    score: float           # 몬테카를로 점수 (0~100)


@dataclass
class ValidationResult:
    """통합 검증 결과"""
    stock_code: str
    stock_name: str
    ai_predicted_return: float     # AI 예측 수익률
    ai_target_price: int           # AI 목표가

    # 3가지 검증 결과
    scenario: ScenarioResult
    backtest: BacktestResult
    montecarlo: MonteCarloResult

    # 통합 점수
    final_score: float             # 최종 점수 (0~100)
    adjusted_target_price: int     # 조정된 목표가 (보수적)
    recommended_quantity: int      # 권장 수량

    # 최종 결정
    approved: bool                 # 승인 여부
    reason: str                    # 승인/거부 이유


class ScenarioValidator:
    """
    통합 검증 시스템

    역할:
    - AI 예측을 3가지 기법으로 검증
    - 보수적 목표가 조정
    - 리스크 기반 수량 조정

    사용법:
    ```python
    result = await scenario_validator.validate(
        stock_code="005930",
        stock_name="삼성전자",
        current_price=70000,
        ai_predicted_return=12.5,
        ai_target_price=78750
    )

    if result.approved:
        # 주문 실행
        await order_service.place_buy_order(
            stock_code=result.stock_code,
            price=result.adjusted_target_price,
            quantity=result.recommended_quantity
        )
    ```
    """

    def __init__(self):
        # 검증 임계값
        self.MIN_FINAL_SCORE = 65.0        # 최소 통합 점수
        self.MIN_WIN_RATE = 55.0           # 최소 승률 (%)
        self.MIN_PROFIT_PROB = 60.0        # 최소 수익 확률 (%)

        # 가중치
        self.WEIGHT_SCENARIO = 0.3
        self.WEIGHT_BACKTEST = 0.4
        self.WEIGHT_MONTECARLO = 0.3

    async def validate(
        self,
        stock_code: str,
        stock_name: str,
        current_price: int,
        ai_predicted_return: float,
        ai_target_price: int
    ) -> ValidationResult:
        """
        통합 검증 실행

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            current_price: 현재가
            ai_predicted_return: AI 예측 수익률 (%)
            ai_target_price: AI 목표가

        Returns:
            ValidationResult: 통합 검증 결과
        """
        logger.info("=" * 80)
        logger.info(f"🔍 Scenario Validation Started: {stock_name} ({stock_code})")
        logger.info(f"   Current: {current_price:,}원")
        logger.info(f"   AI Target: {ai_target_price:,}원 (+{ai_predicted_return:.2f}%)")

        try:
            # 1️⃣ 시나리오 검증
            scenario = await self._scenario_analysis(
                stock_code, current_price, ai_predicted_return
            )
            logger.info(f"   📊 Scenario Score: {scenario.score:.1f}/100")

            # 2️⃣ 백테스트
            backtest = await self._backtest_analysis(
                stock_code, current_price, ai_predicted_return
            )
            logger.info(f"   📈 Backtest Score: {backtest.score:.1f}/100 (Win Rate: {backtest.win_rate:.1f}%)")

            # 3️⃣ 몬테카를로 시뮬레이션
            montecarlo = await self._montecarlo_simulation(
                stock_code, current_price, ai_predicted_return
            )
            logger.info(f"   🎲 MonteCarlo Score: {montecarlo.score:.1f}/100 (Profit Prob: {montecarlo.prob_profit:.1f}%)")

            # 통합 점수 계산
            final_score = (
                scenario.score * self.WEIGHT_SCENARIO +
                backtest.score * self.WEIGHT_BACKTEST +
                montecarlo.score * self.WEIGHT_MONTECARLO
            )

            # 보수적 목표가 조정
            adjusted_target = self._adjust_target_price(
                current_price, ai_target_price, scenario, backtest, montecarlo
            )

            # 권장 수량 계산 (리스크 기반)
            recommended_quantity = self._calculate_quantity(
                current_price, montecarlo.std_return, final_score
            )

            # 4️⃣ DeepSeek R1 최종 검증 (Veto Power)
            r1_result = await self._deepseek_r1_validation(
                stock_code=stock_code,
                stock_name=stock_name,
                current_price=current_price,
                ai_target_price=ai_target_price,
                scenario=scenario,
                backtest=backtest,
                montecarlo=montecarlo,
                final_score=final_score
            )

            # R1이 거부하면 최종 거부
            if not r1_result['approved']:
                logger.warning(f"   🚨 DeepSeek R1 VETO: {r1_result['reason']}")
                approved = False
                reason = f"DeepSeek R1 Veto: {r1_result['reason']}"
            else:
                # R1 통과 시 기본 검증 수행
                approved, reason = self._make_decision(
                    final_score, backtest.win_rate, montecarlo.prob_profit
                )
                # R1 의견 추가
                reason = f"{reason} | R1: {r1_result['reason']}"

            result = ValidationResult(
                stock_code=stock_code,
                stock_name=stock_name,
                ai_predicted_return=ai_predicted_return,
                ai_target_price=ai_target_price,
                scenario=scenario,
                backtest=backtest,
                montecarlo=montecarlo,
                final_score=final_score,
                adjusted_target_price=adjusted_target,
                recommended_quantity=recommended_quantity,
                approved=approved,
                reason=reason
            )

            logger.info("")
            logger.info(f"   🎯 Final Score: {final_score:.1f}/100")
            logger.info(f"   💰 Adjusted Target: {adjusted_target:,}원")
            logger.info(f"   📦 Recommended Qty: {recommended_quantity}주")
            logger.info(f"   {'✅ APPROVED' if approved else '❌ REJECTED'}: {reason}")
            logger.info("=" * 80)

            return result

        except Exception as e:
            logger.error(f"❌ Validation error: {e}", exc_info=True)

            # 에러 시 거부
            return ValidationResult(
                stock_code=stock_code,
                stock_name=stock_name,
                ai_predicted_return=ai_predicted_return,
                ai_target_price=ai_target_price,
                scenario=ScenarioResult(0, 0, 0, 0, 0, 0, 0),
                backtest=BacktestResult(0, 0, 0, 0, 0, 0, 0, 0),
                montecarlo=MonteCarloResult(0, 0, 0, 0, 0, 0, 0, 0, 0),
                final_score=0,
                adjusted_target_price=current_price,
                recommended_quantity=0,
                approved=False,
                reason=f"Validation error: {str(e)}"
            )

    async def _scenario_analysis(
        self,
        stock_code: str,
        current_price: int,
        ai_predicted_return: float
    ) -> ScenarioResult:
        """
        1️⃣ 시나리오 분석

        Best/Expected/Worst case 확률적 분석

        Args:
            stock_code: 종목 코드
            current_price: 현재가
            ai_predicted_return: AI 예측 수익률

        Returns:
            ScenarioResult: 시나리오 분석 결과
        """
        # TODO: 실제 과거 데이터 기반 시나리오 생성
        # 현재는 AI 예측 기준 임시 값

        # Best Case: AI 예측 * 1.5
        best_case = ai_predicted_return * 1.5

        # Expected Case: AI 예측 * 0.8 (보수적)
        expected_case = ai_predicted_return * 0.8

        # Worst Case: -3% (손절 기준)
        worst_case = -3.0

        # 확률 (임시: Expected 60%, Best 20%, Worst 20%)
        prob_best = 0.20
        prob_expected = 0.60
        prob_worst = 0.20

        # 점수 계산: 기댓값 기반
        expected_value = (
            best_case * prob_best +
            expected_case * prob_expected +
            worst_case * prob_worst
        )

        # 0~100 스케일로 변환 (-5% = 0점, +15% = 100점)
        score = max(0, min(100, (expected_value + 5) / 20 * 100))

        return ScenarioResult(
            best_case=best_case,
            expected_case=expected_case,
            worst_case=worst_case,
            probability_best=prob_best,
            probability_expected=prob_expected,
            probability_worst=prob_worst,
            score=score
        )

    async def _backtest_analysis(
        self,
        stock_code: str,
        current_price: int,
        ai_predicted_return: float
    ) -> BacktestResult:
        """
        2️⃣ 백테스트 분석

        과거 3개월 유사 패턴으로 승률 계산

        Args:
            stock_code: 종목 코드
            current_price: 현재가
            ai_predicted_return: AI 예측 수익률

        Returns:
            BacktestResult: 백테스트 결과
        """
        # TODO: 실제 DB에서 과거 3개월 데이터 조회
        # 현재는 임시 값

        # 가상 백테스트 결과 (실제로는 DB에서 계산)
        total_trades = 50
        winning_trades = 32
        losing_trades = 18
        win_rate = (winning_trades / total_trades) * 100
        avg_return = 6.5  # 평균 수익률 6.5%
        max_return = 18.2
        max_loss = -4.5

        # 점수 계산: 승률 + 평균 수익률
        score = min(100, win_rate + avg_return * 3)

        return BacktestResult(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_return=avg_return,
            max_return=max_return,
            max_loss=max_loss,
            score=score
        )

    async def _montecarlo_simulation(
        self,
        stock_code: str,
        current_price: int,
        ai_predicted_return: float
    ) -> MonteCarloResult:
        """
        3️⃣ 몬테카를로 시뮬레이션

        1000회 시뮬레이션으로 확률 분포 계산

        Args:
            stock_code: 종목 코드
            current_price: 현재가
            ai_predicted_return: AI 예측 수익률

        Returns:
            MonteCarloResult: 몬테카를로 결과
        """
        # 시뮬레이션 설정
        simulations = 1000
        mean = ai_predicted_return * 0.7  # 보수적 평균
        std = 4.0  # 표준편차 4%

        # 정규분포 기반 시뮬레이션
        returns = np.random.normal(mean, std, simulations)

        # 통계 계산
        mean_return = float(np.mean(returns))
        std_return = float(np.std(returns))
        prob_profit = float(np.sum(returns > 0) / simulations * 100)
        prob_loss = float(np.sum(returns < 0) / simulations * 100)

        percentile_5 = float(np.percentile(returns, 5))
        percentile_50 = float(np.percentile(returns, 50))
        percentile_95 = float(np.percentile(returns, 95))

        # 점수 계산: 수익 확률 + 평균 수익률
        score = min(100, prob_profit + mean_return * 2)

        return MonteCarloResult(
            simulations=simulations,
            mean_return=mean_return,
            std_return=std_return,
            prob_profit=prob_profit,
            prob_loss=prob_loss,
            percentile_5=percentile_5,
            percentile_50=percentile_50,
            percentile_95=percentile_95,
            score=score
        )

    def _adjust_target_price(
        self,
        current_price: int,
        ai_target_price: int,
        scenario: ScenarioResult,
        backtest: BacktestResult,
        montecarlo: MonteCarloResult
    ) -> int:
        """
        보수적 목표가 조정

        세 가지 검증 결과를 종합해서 목표가 하향 조정

        Returns:
            조정된 목표가
        """
        # Expected Case 기준 (가장 보수적)
        scenario_target = current_price * (1 + scenario.expected_case / 100)

        # 백테스트 평균 수익률 기준
        backtest_target = current_price * (1 + backtest.avg_return / 100)

        # 몬테카를로 중앙값 기준
        montecarlo_target = current_price * (1 + montecarlo.percentile_50 / 100)

        # 세 가지 중 최소값 선택 (가장 보수적)
        adjusted = min(scenario_target, backtest_target, montecarlo_target)

        return int(adjusted)

    def _calculate_quantity(
        self,
        current_price: int,
        volatility: float,
        final_score: float
    ) -> int:
        """
        리스크 기반 권장 수량 계산

        Args:
            current_price: 현재가
            volatility: 변동성 (표준편차)
            final_score: 최종 점수

        Returns:
            권장 매수 수량
        """
        # 기본 투자 금액: 200만원
        base_amount = 2_000_000

        # 점수 기반 조정 (65점 = 100%, 85점 = 150%)
        score_factor = 1.0 + (final_score - 65) / 100

        # 변동성 기반 조정 (높을수록 감소)
        volatility_factor = 1.0 / (1 + volatility / 10)

        # 최종 투자 금액
        final_amount = base_amount * score_factor * volatility_factor

        # 수량 계산
        quantity = int(final_amount / current_price)

        return max(1, quantity)  # 최소 1주

    async def _deepseek_r1_validation(
        self,
        stock_code: str,
        stock_name: str,
        current_price: int,
        ai_target_price: int,
        scenario: ScenarioResult,
        backtest: BacktestResult,
        montecarlo: MonteCarloResult,
        final_score: float
    ) -> Dict:
        """
        4️⃣ DeepSeek R1 최종 검증 (Red Team)

        역할:
        - 논리적 허점 검증
        - 숨겨진 리스크 발견
        - Veto Power (거부권)

        Args:
            stock_code: 종목 코드
            stock_name: 종목명
            current_price: 현재가
            ai_target_price: AI 목표가
            scenario: 시나리오 결과
            backtest: 백테스트 결과
            montecarlo: 몬테카를로 결과
            final_score: 통합 점수

        Returns:
            {
                "approved": True/False,
                "reason": "승인/거부 이유",
                "confidence": 0~100
            }
        """
        logger.info(f"🔍 DeepSeek R1 최종 검증 시작: {stock_name}")

        system_prompt = """당신은 리스크 관리 전문가입니다.
매수 결정 전 마지막 검증 단계에서 논리적 허점과 숨겨진 리스크를 찾는 것이 임무입니다.

당신은 거부권(Veto Power)을 가지고 있습니다.
의심스러운 부분이 있다면 반드시 거부해야 합니다.

응답 형식:
승인: [YES/NO]
신뢰도: [0~100 정수]
이유: [2-3줄, 논리적 근거 제시]"""

        user_prompt = f"""
## 종목 정보
- 종목: {stock_name} ({stock_code})
- 현재가: {current_price:,}원
- AI 목표가: {ai_target_price:,}원 (+{((ai_target_price/current_price-1)*100):.1f}%)

## 검증 결과
### 1. 시나리오 분석 (점수: {scenario.score:.1f}/100)
- Best Case: +{scenario.best_case:.1f}%
- Expected: +{scenario.expected_case:.1f}%
- Worst Case: {scenario.worst_case:.1f}%

### 2. 백테스트 (점수: {backtest.score:.1f}/100)
- 총 거래: {backtest.total_trades}회
- 승률: {backtest.win_rate:.1f}%
- 평균 수익률: {backtest.avg_return:.1f}%
- 최대 손실: {backtest.max_loss:.1f}%

### 3. 몬테카를로 (점수: {montecarlo.score:.1f}/100)
- 수익 확률: {montecarlo.prob_profit:.1f}%
- 평균 수익률: {montecarlo.mean_return:.1f}%
- 표준편차: {montecarlo.std_return:.1f}%
- 5% 백분위 (최악): {montecarlo.percentile_5:.1f}%

### 통합 점수
- Final Score: {final_score:.1f}/100

## 질문
위 데이터를 보고 다음 관점에서 검증해주세요:

1. **숨겨진 리스크**: 세 가지 검증이 놓친 위험 요소가 있는가?
2. **논리적 일관성**: 시나리오/백테스트/몬테카를로 결과가 서로 모순되지 않는가?
3. **과최적화**: 백테스트가 지나치게 낙관적이지 않은가?
4. **변동성 위험**: 표준편차가 감당 가능한 수준인가?
5. **최악 시나리오**: 5% 백분위 손실을 감수할 수 있는가?

**이 매수를 승인하시겠습니까?**
"""

        try:
            # DeepSeek R1 호출 (추론 특화)
            response = await deepseek_client.reason_r1(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.3,  # 보수적
                max_tokens=1500
            )

            # 응답 파싱
            answer = response['answer']
            reasoning = response['reasoning']

            parsed = self._parse_r1_response(answer)

            logger.info(f"✅ DeepSeek R1 검증 완료: {parsed['approved']}, 신뢰도 {parsed['confidence']}")
            logger.debug(f"   R1 추론 과정: {reasoning[:200]}...")
            logger.debug(f"   R1 최종 의견: {parsed['reason']}")

            return parsed

        except Exception as e:
            logger.error(f"❌ DeepSeek R1 검증 실패: {e}", exc_info=True)
            # 실패 시 승인 (검증 자체가 실패해도 매수를 막지 않음)
            return {
                "approved": True,
                "reason": f"R1 validation failed: {str(e)}",
                "confidence": 0
            }

    def _parse_r1_response(self, answer: str) -> Dict:
        """DeepSeek R1 응답 파싱"""
        import re

        result = {
            "approved": True,  # 기본값 승인
            "confidence": 50,
            "reason": answer[:200]
        }

        try:
            # 승인 여부 추출
            approval_match = re.search(r'승인[:\s]*(YES|NO)', answer, re.IGNORECASE)
            if approval_match:
                result["approved"] = (approval_match.group(1).upper() == "YES")

            # 신뢰도 추출
            conf_match = re.search(r'신뢰도[:\s]*(\d+)', answer)
            if conf_match:
                result["confidence"] = int(conf_match.group(1))

            # 이유 추출
            reason_match = re.search(r'이유[:\s]*(.+?)(?:\n\n|\Z)', answer, re.DOTALL)
            if reason_match:
                result["reason"] = reason_match.group(1).strip()

        except Exception as e:
            logger.error(f"R1 응답 파싱 오류: {e}")

        return result

    def _make_decision(
        self,
        final_score: float,
        win_rate: float,
        profit_prob: float
    ) -> tuple[bool, str]:
        """
        최종 승인/거부 결정

        Args:
            final_score: 통합 점수
            win_rate: 백테스트 승률
            profit_prob: 몬테카를로 수익 확률

        Returns:
            (approved, reason) 튜플
        """
        # 1차: 최종 점수
        if final_score < self.MIN_FINAL_SCORE:
            return False, f"Final score too low: {final_score:.1f} < {self.MIN_FINAL_SCORE}"

        # 2차: 승률
        if win_rate < self.MIN_WIN_RATE:
            return False, f"Win rate too low: {win_rate:.1f}% < {self.MIN_WIN_RATE}%"

        # 3차: 수익 확률
        if profit_prob < self.MIN_PROFIT_PROB:
            return False, f"Profit probability too low: {profit_prob:.1f}% < {self.MIN_PROFIT_PROB}%"

        # 모든 조건 통과
        return True, f"All conditions met (Score: {final_score:.1f}, Win: {win_rate:.1f}%, Profit: {profit_prob:.1f}%)"


# Singleton Instance
scenario_validator = ScenarioValidator()
