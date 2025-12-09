"""
AEGIS v3.0 - Brain Commander
Opus/Sonnet 지원 - 금액에 따른 모델 선택
"""
import logging
from anthropic import Anthropic
from app.config import settings
from typing import Dict, Literal

logger = logging.getLogger(__name__)


class BrainCommander:
    """
    AI Commander (Claude Sonnet 4.5)

    역할:
    - Brain Analyzer 분석 결과 즉시 수신
    - 0.01초 만에 Sonnet 4.5 호출 (동기식)
    - 최종 매매 결정 (BUY/SELL/HOLD)
    - Python 내부에서 함수처럼 즉시 실행

    설계 원칙:
    - ❌ 1분 대기 (Polling)
    - ✅ 즉시 호출 (Synchronous Call)
    - Python 계산 끝 → 0.01초 → Claude 호출 → 2~3초 → 결정
    """

    def __init__(self):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"  # Sonnet 4.5 최신

    async def decide(
        self,
        analysis_result: Dict,
        validation_result: Dict,
        market_status: str = "NORMAL"
    ) -> Dict:
        """
        최종 매매 결정 (Brain + Validation 분석 후 즉시 호출)

        Args:
            analysis_result: Brain Analyzer 결과
            validation_result: Scenario Validator 결과
                {
                    "stock_code": "005930",
                    "stock_name": "삼성전자",
                    "current_price": 78000,
                    "quant_score": 75,
                    "ai_score": 85,
                    "final_score": 80,
                    "recommendation": "BUY",
                    "target_price": 82000,
                    "stop_loss": 74000,
                    "reasoning": "..."
                }
            market_status: 시장 상태 ("NORMAL", "RISK_ON", "IRON_SHIELD")

        Returns:
            {
                "decision": "BUY/SELL/HOLD",
                "confidence": 85,
                "reasoning": "...",
                "risk_level": "LOW/MEDIUM/HIGH",
                "veto_reason": None | "..."
            }
        """
        logger.info(f"🤖 Commander deciding on {analysis_result['stock_name']}")

        # 1️⃣ Prompt 구성 (Brain + Validation 결과 포함)
        prompt = self._build_prompt(analysis_result, validation_result, market_status)

        # 2️⃣ Claude Sonnet 4.5 즉시 호출 (동기식)
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,  # 냉철한 판단 (창의성 낮음)
                system="""You are the Chief Investment Officer (CIO) of AEGIS v3.0.

Your role:
1. Review the Brain Analyzer's quantitative analysis (Quant + AI Score)
2. Consider market regime and risk factors
3. Make the FINAL trading decision
4. You have VETO power - you can reject any recommendation

Decision criteria:
- Final Score > 80 but Market = IRON_SHIELD → VETO (too risky)
- News contains fatal risks (Embezzlement, Delisting) → REJECT
- Uncertainty too high (AI vs Quant diff > 30) → HOLD
- Otherwise, APPROVE based on logic

Return ONLY JSON:
{
  "decision": "BUY" | "HOLD" | "SELL",
  "confidence": 0-100,
  "reasoning": "brief explanation (2-3 sentences)",
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "veto_reason": null | "reason if vetoed"
}""",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # 3️⃣ 응답 파싱
            result_text = response.content[0].text
            decision_data = self._parse_response(result_text)

            logger.info(f"✅ Commander decision: {decision_data['decision']} (Confidence: {decision_data['confidence']})")
            if decision_data.get('veto_reason'):
                logger.warning(f"⚠️  VETO: {decision_data['veto_reason']}")

            return decision_data

        except Exception as e:
            logger.error(f"❌ Commander error: {e}", exc_info=True)
            return {
                "decision": "HOLD",
                "confidence": 0,
                "reasoning": f"API Error: {str(e)}",
                "risk_level": "HIGH",
                "veto_reason": "API failure"
            }

    def _build_prompt(self, analysis_result: Dict, validation_result: Dict, market_status: str) -> str:
        """
        Sonnet 4.5에게 전달할 프롬프트 구성

        Args:
            analysis_result: Brain 분석 결과
            validation_result: Scenario Validator 결과
            market_status: 시장 상태

        Returns:
            프롬프트 문자열
        """
        return f"""
# Trading Decision Request

## Stock Information
- **Name**: {analysis_result['stock_name']} ({analysis_result['stock_code']})
- **Current Price**: {analysis_result['current_price']:,}원

## Brain Analyzer Results (Quantitative Analysis)
- **Quant Score**: {analysis_result['quant_score']}/100 (Technical indicators: RSI, MACD, Bollinger Bands, Volume, MA)
- **AI Score**: {analysis_result['ai_score']}/100 (DeepSeek R1 / Gemini Flash)
- **Final Score**: {analysis_result['final_score']}/100 (Weighted average: AI 50% + Quant 50%)

## Brain Recommendation
- **Preliminary Decision**: {analysis_result['recommendation']}
- **Target Price**: {analysis_result['target_price']:,}원 (+{((analysis_result['target_price'] - analysis_result['current_price']) / analysis_result['current_price'] * 100):.1f}%)
- **Stop Loss**: {analysis_result['stop_loss']:,}원 ({((analysis_result['stop_loss'] - analysis_result['current_price']) / analysis_result['current_price'] * 100):.1f}%)
- **Reasoning**: {analysis_result['reasoning']}

## Validation Results (Risk Analysis)
- **Scenario Score**: {validation_result.get('scenario_score', 'N/A')}/100
  - Best Case: +{validation_result.get('best_case_return', 0):.1f}%
  - Expected Case: +{validation_result.get('expected_case_return', 0):.1f}%
  - Worst Case: {validation_result.get('worst_case_return', 0):.1f}%
- **Backtest Score**: {validation_result.get('backtest_score', 'N/A')}/100
  - Historical Win Rate: {validation_result.get('historical_win_rate', 0):.1f}%
- **Monte Carlo Score**: {validation_result.get('montecarlo_score', 'N/A')}/100
  - Profit Probability: {validation_result.get('profit_probability', 0):.1f}%
- **Final Validation Score**: {validation_result.get('final_score', 'N/A')}/100
- **Adjusted Target Price**: {validation_result.get('adjusted_target_price', analysis_result['target_price']):,}원
- **Recommended Quantity**: {validation_result.get('recommended_quantity', 0)} shares

## Market Context
- **Market Regime**: {market_status}
  - NORMAL: Regular market conditions
  - RISK_ON: High volatility, aggressive opportunities
  - IRON_SHIELD: Extreme risk, defensive mode

## Your Task (CIO Final Decision)
Review the above quantitative analysis and market context.

**Decision Logic**:
1. If Final Score > 80 but Market = IRON_SHIELD → Consider VETO (too risky in crisis)
2. If AI vs Quant score difference > 30 → HOLD (high uncertainty)
3. If Brain recommendation is SELL → APPROVE immediately (cut losses fast)
4. If Brain recommendation is BUY:
   - Check if market regime supports it
   - Assess risk/reward ratio
   - Decide: APPROVE (BUY) or VETO (HOLD)
5. If Brain recommendation is HOLD → APPROVE (HOLD)

**Return JSON only** (no explanation outside JSON):
{{
  "decision": "BUY" | "HOLD" | "SELL",
  "confidence": 0-100,
  "reasoning": "brief 2-3 sentences",
  "risk_level": "LOW" | "MEDIUM" | "HIGH",
  "veto_reason": null | "reason if vetoed"
}}
"""

    def _parse_response(self, response_text: str) -> Dict:
        """
        Claude 응답 파싱

        Args:
            response_text: Claude 응답

        Returns:
            파싱된 결과
        """
        import json
        import re

        # JSON 추출
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON parse error: {e}")
                pass

        # JSON 파싱 실패 시 기본값
        logger.warning("⚠️  Failed to parse Commander response, using default HOLD")
        return {
            "decision": "HOLD",
            "confidence": 0,
            "reasoning": "Failed to parse response",
            "risk_level": "HIGH",
            "veto_reason": "Parse failure"
        }


# Singleton Instance
brain_commander = BrainCommander()
