"""
AEGIS v3.0 - Real-time Feedback Engine
실시간 피드백 시스템

Features:
- 매도 후 즉시 검증 (Post-Trade Validation)
- 성과 분류 (SUCCESS/NEUTRAL/FAILURE)
- 원인 분석 (DeepSeek-V3)
- 점수 체계 동적 조정
- 연속 손절 자동 대응
"""
import os
import sys
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from sqlalchemy import text
import requests

logger = logging.getLogger("FeedbackEngine")


# ═══════════════════════════════════════════════════════════════
#                    설정값
# ═══════════════════════════════════════════════════════════════

# 결과 분류 기준
SUCCESS_THRESHOLD = 3.0          # +3% 이상 = 성공
FAILURE_THRESHOLD = -1.0         # -1% 이하 = 실패
PERFECT_THRESHOLD = 5.0          # +5% 이상 = 완벽
SEVERE_LOSS_THRESHOLD = -3.0     # -3% 이하 = 심각

# 자동 조정 트리거
CONSECUTIVE_LOSS_TRIGGER = 3     # 3연속 손절 시 조정
CIRCUIT_BREAKER_TRIGGER = 5      # 5연속 손절 시 중단
CONSECUTIVE_WIN_TRIGGER = 5      # 5연속 성공 시 완화

# 자동 조정 폭
AUTO_MIN_SCORE_INCREASE = 3      # 손절 시 MIN_SCORE 증가
AUTO_MIN_SCORE_DECREASE = 2      # 성공 시 MIN_SCORE 감소
MIN_SCORE_LOWER_BOUND = 65       # MIN_SCORE 하한선
MIN_SCORE_UPPER_BOUND = 80       # MIN_SCORE 상한선


@dataclass
class TradeFeedback:
    """매도 후 생성되는 피드백 데이터"""

    # 기본 정보
    stock_code: str
    stock_name: str
    trade_date: datetime

    # 거래 결과
    buy_price: float
    sell_price: float
    return_pct: float           # 수익률
    holding_days: int           # 보유일
    exit_reason: str            # 청산 사유

    # 매수 시점 점수
    buy_quant_score: int        # 매수 시 Quant 점수
    buy_deepseek_score: int     # 매수 시 DeepSeek-V3 점수
    buy_final_score: int        # 매수 시 Final 점수

    # 매수 시점 수급
    buy_foreigner_net: Optional[int] = None      # 매수일 외국인 순매수
    buy_institution_net: Optional[int] = None    # 매수일 기관 순매수
    buy_consecutive_days: Optional[int] = None   # 매수일 연속 매수일

    # 성과 분류
    result_category: str = ""        # SUCCESS/NEUTRAL/FAILURE
    result_detail: str = ""          # PERFECT/GOOD/MINOR_LOSS/...

    # 원인 분석 (DeepSeek-V3 생성)
    failure_reason: str = ""         # 실패 원인 (실패 시)
    lesson_learned: str = ""         # 교훈

    # 점수 조정 제안
    suggested_adjustment: Dict = field(default_factory=dict)  # 가중치/임계값 조정 제안


@dataclass
class ScoreAdjustment:
    """점수 조정 이력"""
    adjustment_date: datetime
    trigger_reason: str

    # 이전 값
    prev_min_score: int

    # 새로운 값
    new_min_score: int

    # 승인
    approved_by: str  # "AUTO" 또는 관리자 ID


class FeedbackEngine:
    """
    실시간 피드백 엔진

    매도 즉시 → 검증 → 피드백 → 다음 매수에 반영
    """

    def __init__(self):
        self.db = SessionLocal()
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

        # 현재 설정값 로드
        self.current_min_score = self._load_current_min_score()
        self.circuit_breaker_active = False

        logger.info("✅ FeedbackEngine initialized")
        logger.info(f"   Current MIN_SCORE: {self.current_min_score}")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def process_trade_exit(
        self,
        stock_code: str,
        buy_price: float,
        sell_price: float,
        buy_date: date,
        sell_date: date,
        exit_reason: str,
        buy_scores: Dict  # {'quant': 65, 'deepseek': 70, 'final': 68}
    ) -> TradeFeedback:
        """
        매도 후 즉시 피드백 생성

        Args:
            stock_code: 종목코드
            buy_price: 매수가
            sell_price: 매도가
            buy_date: 매수일
            sell_date: 매도일
            exit_reason: 청산 사유 (TP/SL/Time/DeepSeek-V3 Exit)
            buy_scores: 매수 시점 점수

        Returns:
            TradeFeedback
        """
        logger.info(f"📊 Processing trade exit: {stock_code}")

        # Get stock name
        name_query = text("SELECT name FROM stocks WHERE code = :code")
        name_result = self.db.execute(name_query, {'code': stock_code}).fetchone()
        stock_name = name_result.name if name_result else stock_code

        # Calculate metrics
        return_pct = (sell_price - buy_price) / buy_price * 100
        holding_days = (sell_date - buy_date).days

        # Create feedback
        feedback = TradeFeedback(
            stock_code=stock_code,
            stock_name=stock_name,
            trade_date=datetime.now(),
            buy_price=buy_price,
            sell_price=sell_price,
            return_pct=return_pct,
            holding_days=holding_days,
            exit_reason=exit_reason,
            buy_quant_score=buy_scores.get('quant', 0),
            buy_deepseek_score=buy_scores.get('deepseek', 0),
            buy_final_score=buy_scores.get('final', 0)
        )

        # Classify result
        feedback.result_category, feedback.result_detail = self._classify_result(return_pct)

        # Get buy date supply data
        feedback.buy_foreigner_net, feedback.buy_institution_net, feedback.buy_consecutive_days = \
            self._get_buy_date_supply(stock_code, buy_date)

        # Analyze with DeepSeek-V3 (if failure)
        if feedback.result_category == "FAILURE":
            feedback.failure_reason, feedback.lesson_learned, feedback.suggested_adjustment = \
                self._analyze_failure(feedback)

        # Save to DB
        self._save_feedback(feedback)

        # Check for consecutive losses
        self._check_consecutive_losses()

        # Send notification
        self._send_notification(feedback)

        logger.info(f"   Result: {feedback.result_category} ({feedback.result_detail})")
        logger.info(f"   Return: {return_pct:+.2f}%")

        return feedback

    def check_consecutive_losses(self) -> Optional[ScoreAdjustment]:
        """
        연속 손절 체크 및 자동 조정

        Returns:
            ScoreAdjustment if adjustment made, else None
        """
        # Get recent trades
        query = text("""
            SELECT result_category, result_detail
            FROM trade_feedback
            ORDER BY created_at DESC
            LIMIT 10
        """)

        results = self.db.execute(query).fetchall()

        if len(results) < CONSECUTIVE_LOSS_TRIGGER:
            return None

        # Count consecutive losses
        consecutive_losses = 0
        for r in results:
            if r.result_category == "FAILURE":
                consecutive_losses += 1
            else:
                break

        logger.info(f"   Consecutive losses: {consecutive_losses}")

        # Check triggers
        if consecutive_losses >= CIRCUIT_BREAKER_TRIGGER:
            return self._trigger_circuit_breaker()

        elif consecutive_losses >= CONSECUTIVE_LOSS_TRIGGER:
            return self._auto_increase_min_score()

        return None

    def check_consecutive_wins(self) -> Optional[ScoreAdjustment]:
        """
        연속 성공 체크 및 자동 완화

        Returns:
            ScoreAdjustment if adjustment made, else None
        """
        query = text("""
            SELECT result_category, result_detail
            FROM trade_feedback
            ORDER BY created_at DESC
            LIMIT 10
        """)

        results = self.db.execute(query).fetchall()

        if len(results) < CONSECUTIVE_WIN_TRIGGER:
            return None

        # Count consecutive wins
        consecutive_wins = 0
        for r in results:
            if r.result_category == "SUCCESS":
                consecutive_wins += 1
            else:
                break

        if consecutive_wins >= CONSECUTIVE_WIN_TRIGGER:
            return self._auto_decrease_min_score()

        return None

    def weekly_analysis(self) -> Dict:
        """
        주간 성과 분석 (DeepSeek-V3)

        Returns:
            Analysis result
        """
        logger.info("📈 Running weekly analysis...")

        # Get this week's trades
        week_ago = datetime.now() - timedelta(days=7)

        query = text("""
            SELECT *
            FROM trade_feedback
            WHERE created_at >= :week_ago
            ORDER BY created_at DESC
        """)

        trades = self.db.execute(query, {'week_ago': week_ago}).fetchall()

        if len(trades) < 5:
            logger.info("   Not enough trades for analysis (< 5)")
            return {'status': 'insufficient_data'}

        # Analyze with DeepSeek-V3
        analysis = self._deepseek_weekly_analysis(trades)

        logger.info(f"   Analyzed {len(trades)} trades")

        return analysis

    # ========================================
    # CLASSIFICATION
    # ========================================

    def _classify_result(self, return_pct: float) -> Tuple[str, str]:
        """
        성과 분류

        Returns:
            (category, detail)
        """
        if return_pct >= SUCCESS_THRESHOLD:
            # SUCCESS
            if return_pct >= PERFECT_THRESHOLD:
                return "SUCCESS", "PERFECT"
            else:
                return "SUCCESS", "GOOD"

        elif return_pct <= FAILURE_THRESHOLD:
            # FAILURE
            if return_pct <= SEVERE_LOSS_THRESHOLD:
                return "FAILURE", "SEVERE_LOSS"
            elif return_pct <= -2.0:
                return "FAILURE", "STOP_LOSS"
            else:
                return "FAILURE", "MINOR_LOSS"

        else:
            # NEUTRAL
            return "NEUTRAL", "BREAKEVEN"

    # ========================================
    # DATA RETRIEVAL
    # ========================================

    def _get_buy_date_supply(
        self,
        stock_code: str,
        buy_date: date
    ) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """매수일 수급 데이터 조회"""
        query = text("""
            SELECT foreign_net, institution_net
            FROM investor_net_buying
            WHERE stock_code = :code AND date = :date
        """)

        result = self.db.execute(query, {'code': stock_code, 'date': buy_date}).fetchone()

        if not result:
            return None, None, None

        foreigner_net = result.foreign_net
        institution_net = result.institution_net

        # Calculate consecutive days (simplified - would need actual calculation)
        consecutive_days = self._calculate_consecutive_days(stock_code, buy_date)

        return foreigner_net, institution_net, consecutive_days

    def _calculate_consecutive_days(self, stock_code: str, buy_date: date) -> Optional[int]:
        """연속 매수일 계산"""
        # TODO: Implement actual calculation
        # For now, return None
        return None

    # ========================================
    # DEEPSEEK-V3 ANALYSIS
    # ========================================

    def _analyze_failure(
        self,
        feedback: TradeFeedback
    ) -> Tuple[str, str, Dict]:
        """
        실패 거래 분석 (DeepSeek-V3)

        Returns:
            (failure_reason, lesson_learned, suggested_adjustment)
        """
        if not self.deepseek_api_key:
            return "No API key", "N/A", {}

        prompt = self._build_failure_analysis_prompt(feedback)

        try:
            response = self._call_deepseek_v3(prompt)
            analysis = self._parse_deepseek_response(response)

            return (
                analysis.get('analysis', ''),
                analysis.get('lesson', ''),
                analysis.get('adjustment', {})
            )

        except Exception as e:
            logger.error(f"   DeepSeek-V3 analysis failed: {e}")
            return f"Analysis failed: {e}", "", {}

    def _build_failure_analysis_prompt(self, feedback: TradeFeedback) -> str:
        """피드백 분석 프롬프트 생성"""
        return f"""
[매도 완료 - 피드백 요청]

종목: {feedback.stock_name} ({feedback.stock_code})
매수가: {feedback.buy_price:,}원 → 매도가: {feedback.sell_price:,}원
수익률: {feedback.return_pct:+.1f}%
보유기간: {feedback.holding_days}일
청산사유: {feedback.exit_reason}

[매수 시점 분석]
- Quant Score: {feedback.buy_quant_score}점
- DeepSeek-V3 Score: {feedback.buy_deepseek_score}점
- Final Score: {feedback.buy_final_score}점
- 외국인: {feedback.buy_foreigner_net or 0:+,}주
- 기관: {feedback.buy_institution_net or 0:+,}주

[분석 요청]
1. 이 거래의 실패 원인을 분석해주세요
2. 매수 시점의 점수가 적절했는지 평가해주세요
3. 앞으로의 매수 기준 조정이 필요하다면 제안해주세요

JSON 형식으로 응답:
{{
  "analysis": "원인 분석...",
  "score_evaluation": "점수 평가...",
  "adjustment": {{
    "min_score": +/-1~3
  }},
  "lesson": "교훈..."
}}
"""

    def _call_deepseek_v3(self, prompt: str) -> str:
        """DeepSeek-V3 API 호출"""
        url = "https://api.deepseek.com/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        return result['choices'][0]['message']['content']

    def _parse_deepseek_response(self, response: str) -> Dict:
        """DeepSeek 응답 파싱"""
        import json

        try:
            # Extract JSON from response
            start = response.find('{')
            end = response.rfind('}') + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                return {'analysis': response, 'lesson': '', 'adjustment': {}}

        except Exception as e:
            logger.error(f"Failed to parse DeepSeek response: {e}")
            return {'analysis': response, 'lesson': '', 'adjustment': {}}

    def _deepseek_weekly_analysis(self, trades: List) -> Dict:
        """주간 분석 (DeepSeek-V3)"""
        # TODO: Implement full weekly analysis
        return {
            'status': 'completed',
            'total_trades': len(trades),
            'suggestions': []
        }

    # ========================================
    # SCORE ADJUSTMENT
    # ========================================

    def _auto_increase_min_score(self) -> ScoreAdjustment:
        """자동 MIN_SCORE 증가 (3연속 손절)"""
        prev_score = self.current_min_score
        new_score = min(MIN_SCORE_UPPER_BOUND, prev_score + AUTO_MIN_SCORE_INCREASE)

        adjustment = ScoreAdjustment(
            adjustment_date=datetime.now(),
            trigger_reason=f"{CONSECUTIVE_LOSS_TRIGGER}연속 손절",
            prev_min_score=prev_score,
            new_min_score=new_score,
            approved_by="AUTO"
        )

        self._apply_adjustment(adjustment)

        logger.warning(f"⚠️ {CONSECUTIVE_LOSS_TRIGGER}연속 손절 - MIN_SCORE {prev_score} → {new_score}")

        return adjustment

    def _auto_decrease_min_score(self) -> ScoreAdjustment:
        """자동 MIN_SCORE 감소 (5연속 성공)"""
        prev_score = self.current_min_score
        new_score = max(MIN_SCORE_LOWER_BOUND, prev_score - AUTO_MIN_SCORE_DECREASE)

        adjustment = ScoreAdjustment(
            adjustment_date=datetime.now(),
            trigger_reason=f"{CONSECUTIVE_WIN_TRIGGER}연속 성공",
            prev_min_score=prev_score,
            new_min_score=new_score,
            approved_by="AUTO"
        )

        self._apply_adjustment(adjustment)

        logger.info(f"✅ {CONSECUTIVE_WIN_TRIGGER}연속 성공 - MIN_SCORE {prev_score} → {new_score}")

        return adjustment

    def _trigger_circuit_breaker(self) -> ScoreAdjustment:
        """서킷 브레이커 발동 (5연속 손절)"""
        self.circuit_breaker_active = True

        logger.critical(f"🚨 {CIRCUIT_BREAKER_TRIGGER}연속 손절 - 24시간 매수 중단!")

        # Also increase MIN_SCORE
        return self._auto_increase_min_score()

    def _apply_adjustment(self, adjustment: ScoreAdjustment):
        """조정 적용"""
        # Update current score
        self.current_min_score = adjustment.new_min_score

        # Save to DB
        query = text("""
            INSERT INTO score_adjustment_history
            (adjustment_date, trigger_reason, prev_min_score, new_min_score, approved_by)
            VALUES
            (:date, :reason, :prev, :new, :approved)
        """)

        self.db.execute(query, {
            'date': adjustment.adjustment_date,
            'reason': adjustment.trigger_reason,
            'prev': adjustment.prev_min_score,
            'new': adjustment.new_min_score,
            'approved': adjustment.approved_by
        })
        self.db.commit()

    def _check_consecutive_losses(self):
        """연속 손절 자동 체크"""
        adjustment = self.check_consecutive_losses()

        if adjustment:
            self._send_adjustment_notification(adjustment)

    # ========================================
    # DATABASE
    # ========================================

    def _save_feedback(self, feedback: TradeFeedback):
        """피드백 DB 저장"""
        query = text("""
            INSERT INTO trade_feedback
            (stock_code, buy_date, sell_date, return_pct, holding_days, exit_reason,
             result_category, result_detail, buy_quant_score, buy_deepseek_score,
             buy_final_score, buy_foreigner_net, buy_institution_net, buy_consecutive_days,
             deepseek_analysis, deepseek_lesson)
            VALUES
            (:code, :buy_date, :sell_date, :return_pct, :holding_days, :exit_reason,
             :category, :detail, :quant, :deepseek, :final, :foreigner, :institution,
             :consecutive, :analysis, :lesson)
        """)

        self.db.execute(query, {
            'code': feedback.stock_code,
            'buy_date': feedback.trade_date.date(),  # Simplified
            'sell_date': feedback.trade_date.date(),
            'return_pct': feedback.return_pct,
            'holding_days': feedback.holding_days,
            'exit_reason': feedback.exit_reason,
            'category': feedback.result_category,
            'detail': feedback.result_detail,
            'quant': feedback.buy_quant_score,
            'deepseek': feedback.buy_deepseek_score,
            'final': feedback.buy_final_score,
            'foreigner': feedback.buy_foreigner_net,
            'institution': feedback.buy_institution_net,
            'consecutive': feedback.buy_consecutive_days,
            'analysis': feedback.failure_reason,
            'lesson': feedback.lesson_learned
        })
        self.db.commit()

    def _load_current_min_score(self) -> int:
        """현재 MIN_SCORE 로드"""
        query = text("""
            SELECT new_min_score
            FROM score_adjustment_history
            ORDER BY adjustment_date DESC
            LIMIT 1
        """)

        result = self.db.execute(query).fetchone()

        return result.new_min_score if result else 70  # Default 70

    # ========================================
    # NOTIFICATIONS
    # ========================================

    def _send_notification(self, feedback: TradeFeedback):
        """텔레그램 알림"""
        # TODO: Implement Telegram notification
        pass

    def _send_adjustment_notification(self, adjustment: ScoreAdjustment):
        """설정 변경 알림"""
        # TODO: Implement Telegram notification
        pass


# ========================================
# MAIN
# ========================================

def main():
    """테스트"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    engine = FeedbackEngine()

    # Simulate trade exit
    feedback = engine.process_trade_exit(
        stock_code="005930",
        buy_price=95000,
        sell_price=92000,
        buy_date=date(2024, 12, 1),
        sell_date=date(2024, 12, 5),
        exit_reason="STOP_LOSS",
        buy_scores={'quant': 68, 'deepseek': 72, 'final': 70}
    )

    print("\n" + "=" * 70)
    print("📊 Trade Feedback")
    print("=" * 70)
    print(f"\nStock: {feedback.stock_name} ({feedback.stock_code})")
    print(f"Return: {feedback.return_pct:+.2f}%")
    print(f"Result: {feedback.result_category} ({feedback.result_detail})")
    print(f"\nBuy Scores:")
    print(f"  Quant: {feedback.buy_quant_score}")
    print(f"  DeepSeek: {feedback.buy_deepseek_score}")
    print(f"  Final: {feedback.buy_final_score}")

    if feedback.failure_reason:
        print(f"\nFailure Reason:")
        print(f"  {feedback.failure_reason}")

    if feedback.lesson_learned:
        print(f"\nLesson Learned:")
        print(f"  {feedback.lesson_learned}")

    print("=" * 70)


if __name__ == "__main__":
    main()
