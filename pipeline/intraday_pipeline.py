"""
AEGIS v3.0 - Intraday Pipeline
Just-in-Time Data Feeding: Fetching → Pre-processing → Brain → Validation → Execution

핵심 원칙:
1. 데이터 수집 후 즉시 AI 분석 (0.1초 이내)
2. Brain이 최신 데이터만 분석하도록 보장
3. 순서 엄수: Fetching → Pre-processing → Brain → Validation → Execution
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional

from app.database import get_db
from app.models.brain import DailyPick
from fetchers.kis_fetcher import kis_fetcher
from fetchers.kis_client import kis_client
from services.portfolio_service import PortfolioService
from services.order_service import OrderService
from brain.analyzer import brain_analyzer
from brain.commander import brain_commander
from brain.scenario_validator import scenario_validator
from brain.safety_checker import safety_checker

logger = logging.getLogger(__name__)


class IntradayPipeline:
    """
    Intraday 파이프라인

    역할:
    - 5단계 파이프라인 오케스트레이션
    - Just-in-Time 데이터 수집
    - 순서 보장: Fetching → Brain → Order

    설계 원칙:
    - ❌ Brain → Fetcher (뒷북)
    - ✅ Fetcher → Brain (최신 데이터)
    """

    def __init__(self):
        self.portfolio_service = PortfolioService()
        self.order_service = OrderService()
        self.last_run: Optional[datetime] = None

    async def run(self) -> dict:
        """
        파이프라인 실행

        Returns:
            실행 결과 (buy_count, sell_count, candidates, orders)
        """
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info(f"🚀 Intraday Pipeline Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        result = {
            "start_time": start_time,
            "stage": None,
            "candidates": [],
            "validated_candidates": [],
            "buy_orders": [],
            "sell_orders": [],
            "errors": []
        }

        try:
            # ==========================================
            # 1️⃣ FETCHING (최신 데이터 수집)
            # ==========================================
            result["stage"] = "fetching"
            logger.info("📥 Stage 1/5: FETCHING")

            await self._fetch_latest_data()

            # ==========================================
            # 2️⃣ PRE-PROCESSING (DB 저장)
            # ==========================================
            result["stage"] = "preprocessing"
            logger.info("🔄 Stage 2/5: PRE-PROCESSING")

            # DB 커밋 (다음 단계에서 읽을 수 있도록)
            db = next(get_db())
            db.commit()
            logger.info("✅ Data committed to DB")

            # ==========================================
            # 3️⃣ BRAIN (AI 분석 + Quant)
            # ==========================================
            result["stage"] = "brain"
            logger.info("🧠 Stage 3/6: BRAIN (Analyzer)")

            candidates = await self._brain_analyze()
            result["candidates"] = candidates
            logger.info(f"🎯 Brain Analyzer: {len(candidates)} candidates")

            # ==========================================
            # 4️⃣ VALIDATION (시나리오 검증)
            # ==========================================
            result["stage"] = "validation"
            logger.info("✔️  Stage 4/6: VALIDATION (Risk Analysis)")

            # Brain 분석 후 즉시 Validation 실행 (0.01초)
            validated_candidates = await self._validate_candidates(candidates)
            result["validated_candidates"] = validated_candidates
            logger.info(f"✔️  Validated {len(validated_candidates)}/{len(candidates)} candidates")

            # ==========================================
            # 5️⃣ COMMANDER (Sonnet 4.5 최종 결정)
            # ==========================================
            result["stage"] = "commander"
            logger.info("👔 Stage 5/6: COMMANDER (CIO Final Decision)")

            # Brain + Validation 결과를 모두 받아서 최종 결정
            commander_decisions = await self._commander_decide(validated_candidates)
            result["commander_decisions"] = commander_decisions
            logger.info(f"✅ Commander decisions: {len(commander_decisions)} approved")

            # ==========================================
            # 6️⃣ EXECUTION (주문 실행)
            # ==========================================
            result["stage"] = "execution"
            logger.info("⚔️  Stage 6/6: EXECUTION")

            buy_orders, sell_orders = await self._execute_orders(validated_candidates)
            result["buy_orders"] = buy_orders
            result["sell_orders"] = sell_orders

            logger.info(f"📈 Buy Orders: {len(buy_orders)}")
            logger.info(f"📉 Sell Orders: {len(sell_orders)}")

        except Exception as e:
            logger.error(f"❌ Pipeline error at stage {result['stage']}: {e}", exc_info=True)
            result["errors"].append(str(e))

        finally:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            result["end_time"] = end_time
            result["duration"] = duration

            self.last_run = end_time

            logger.info(f"✅ Pipeline Complete: {duration:.2f}s")
            logger.info("=" * 80)

        return result

    async def _fetch_latest_data(self) -> None:
        """
        Stage 1: 최신 데이터 수집

        수집 항목:
        - KIS: 잔고, 체결, 프로그램 매매
        - Naver: 속보 뉴스
        - pykrx: 수급 데이터 (TODO)
        """
        logger.info("📥 Fetching latest data...")

        # KIS 잔고 동기화
        try:
            await kis_fetcher.sync_portfolio()
            logger.info("  ✅ Portfolio synced")
        except Exception as e:
            logger.error(f"  ❌ Portfolio sync failed: {e}")

        # KIS 미체결 동기화
        try:
            await kis_fetcher.sync_execution()
            logger.info("  ✅ Executions synced")
        except Exception as e:
            logger.error(f"  ❌ Execution sync failed: {e}")

        # TODO: Naver 뉴스 수집
        # try:
        #     latest_news = await naver_fetcher.fetch_breaking_news()
        #     logger.info(f"  ✅ News fetched: {len(latest_news)} items")
        # except Exception as e:
        #     logger.error(f"  ❌ News fetch failed: {e}")

        # TODO: pykrx 수급 데이터
        # try:
        #     supply_demand = await pykrx_fetcher.fetch_supply_demand()
        #     logger.info(f"  ✅ Supply/Demand data fetched")
        # except Exception as e:
        #     logger.error(f"  ❌ Supply/Demand fetch failed: {e}")

        logger.info("📥 Fetching complete")

    async def _brain_analyze(self) -> List[dict]:
        """
        Stage 3: Brain AI 분석

        분석 대상:
        - WebSocket Manager의 실시간 데이터
        - Market Scanner의 급등주
        - Daily Picks (DeepSeek R1)

        Returns:
            매수 후보 리스트
        """
        logger.info("🧠 Brain analyzing candidates...")

        # 1️⃣ 분석 대상 수집
        candidate_list = []

        # Daily Picks (Priority 2) - DeepSeek R1 종목
        try:
            from datetime import date
            db = next(get_db())
            daily_picks = db.query(DailyPick).filter(
                DailyPick.date == date.today(),
                DailyPick.is_executed == False  # 아직 매수하지 않은 종목만
            ).order_by(DailyPick.rank).limit(10).all()  # 상위 10개

            for pick in daily_picks:
                # 현재가 조회 필요 (WebSocket에서 가져오는 게 이상적)
                # 임시로 expected_entry_price 사용
                candidate_list.append({
                    "stock_code": pick.stock_code,
                    "stock_name": pick.stock_code,  # TODO: stock_name 테이블에서 조회
                    "current_price": int(pick.expected_entry_price),
                    "ai_score": pick.ai_score,
                    "ai_comment": pick.ai_comment,
                    "source": "daily_picks"
                })

            logger.info(f"  📋 Daily Picks: {len(daily_picks)} candidates")

        except Exception as e:
            logger.error(f"  ❌ Failed to get daily picks: {e}")

        # TODO: WebSocket Manager 실시간 데이터 연동
        # TODO: Market Scanner 급등주 연동

        # 2️⃣ Brain Analyzer 실행
        if not candidate_list:
            logger.info("🧠 No candidates to analyze")
            return []

        analyzed_results = await brain_analyzer.analyze_batch(candidate_list)

        # 3️⃣ 매수 추천 필터링 (recommendation == "BUY")
        buy_candidates = []
        for result in analyzed_results:
            if result['recommendation'] == 'BUY':
                buy_candidates.append({
                    'stock_code': result['stock_code'],
                    'stock_name': result['stock_name'],
                    'current_price': result['current_price'],
                    'target_price': result['target_price'],
                    'stop_loss': result['stop_loss'],
                    'predicted_return': (result['target_price'] - result['current_price']) / result['current_price'] * 100,
                    'final_score': result['final_score'],
                    'quant_score': result['quant_score'],
                    'ai_score': result['ai_score'],
                    'reasoning': result['reasoning']
                })

        logger.info(f"🧠 Brain analysis complete: {len(buy_candidates)}/{len(analyzed_results)} BUY candidates")
        return buy_candidates

    async def _commander_decide(self, candidates: List[dict]) -> List[dict]:
        """
        Stage 5: Commander 최종 결정 (Sonnet 4.5)

        역할:
        - Brain + Validation 결과를 받아 즉시 Sonnet 4.5 호출 (0.01초)
        - CIO 최종 승인/거부 결정
        - VETO 권한 (과열, 리스크 등)

        Args:
            candidates: Validated candidates (Brain + Validation 결과 포함)

        Returns:
            Commander 승인된 후보 리스트
        """
        logger.info(f"👔 Commander reviewing {len(candidates)} candidates...")

        approved = []

        # TODO: 시장 상태 조회 (MarketGuard)
        market_status = "NORMAL"  # "NORMAL" | "RISK_ON" | "IRON_SHIELD"

        for candidate in candidates:
            try:
                # Brain + Validation 결과를 모두 Commander에게 전달
                commander_decision = await brain_commander.decide(
                    analysis_result=candidate,
                    validation_result=candidate,  # candidate에 validation 정보 포함됨
                    market_status=market_status
                )

                # 승인된 후보만 추가 (decision == "BUY")
                if commander_decision['decision'] == 'BUY':
                    approved.append({
                        **candidate,
                        'commander_confidence': commander_decision['confidence'],
                        'commander_reasoning': commander_decision['reasoning'],
                        'commander_risk_level': commander_decision['risk_level']
                    })
                    logger.info(f"  ✅ {candidate['stock_name']}: APPROVED by Commander (Confidence: {commander_decision['confidence']})")
                else:
                    logger.info(f"  ❌ {candidate['stock_name']}: VETOED - {commander_decision.get('veto_reason', commander_decision['reasoning'])}")

            except Exception as e:
                logger.error(f"  ❌ Commander decision failed for {candidate.get('stock_name', 'Unknown')}: {e}")

        logger.info(f"👔 Commander decisions complete: {len(approved)}/{len(candidates)} approved")
        return approved

    async def _validate_candidates(self, candidates: List[dict]) -> List[dict]:
        """
        Stage 4: 시나리오 검증

        검증 항목:
        - 시나리오 분석 (Best/Expected/Worst)
        - 백테스트 (과거 3개월 승률)
        - 몬테카를로 시뮬레이션 (확률 분포)

        Args:
            candidates: Brain 분석 결과

        Returns:
            검증 통과한 후보 리스트
        """
        logger.info(f"✅ Validating {len(candidates)} candidates...")

        validated = []

        for candidate in candidates:
            try:
                # Scenario Validator 실행
                validation_result = await scenario_validator.validate(
                    stock_code=candidate['stock_code'],
                    stock_name=candidate['stock_name'],
                    current_price=candidate['current_price'],
                    ai_predicted_return=candidate['predicted_return'],
                    ai_target_price=candidate['target_price']
                )

                # 승인된 후보만 추가
                if validation_result.approved:
                    validated.append({
                        **candidate,
                        'adjusted_target_price': validation_result.adjusted_target_price,
                        'recommended_quantity': validation_result.recommended_quantity,
                        'final_score': validation_result.final_score,
                        'validation_reason': validation_result.reason
                    })
                    logger.info(f"  ✅ {candidate['stock_name']}: Approved (Score: {validation_result.final_score:.1f})")
                else:
                    logger.info(f"  ❌ {candidate['stock_name']}: Rejected - {validation_result.reason}")

            except Exception as e:
                logger.error(f"  ❌ Validation failed for {candidate.get('stock_name', 'Unknown')}: {e}")

        logger.info(f"✅ Validation complete: {len(validated)}/{len(candidates)} approved")
        return validated

    async def _execute_orders(self, validated_candidates: List[dict]) -> tuple:
        """
        Stage 5: 주문 실행

        실행 로직:
        1. 매도 우선 (보유종목 중 손절/익절)
        2. 매수 실행 (검증된 후보)

        Args:
            validated_candidates: 검증된 매수 후보

        Returns:
            (buy_orders, sell_orders) 튜플
        """
        logger.info("⚔️  Executing orders...")

        buy_orders = []
        sell_orders = []

        # 1. 매도 판단 (보유종목)
        portfolio = self.portfolio_service.get_portfolio()

        for stock in portfolio:
            # TODO: 매도 로직 구현
            # - 손절: -5% 이하
            # - 익절: 목표가 도달
            # - 시나리오 이탈

            pass

        # 2. 매수 실행 (검증된 후보)
        for candidate in validated_candidates:
            try:
                stock_code = candidate['stock_code']
                stock_name = candidate['stock_name']
                current_price = candidate.get('current_price', 0)

                # 주문 가능 금액 확인
                deposit = self.portfolio_service.get_deposit()
                available = deposit.get("available", 0)

                if available < 1_000_000:  # 최소 100만원
                    logger.warning(f"  ⚠️  Insufficient funds: {available:,}원")
                    continue

                # 🛡️ Safety Check (5가지 안전성 검증)
                # Calculate quantity and price for safety check
                budget_per_stock = available // 5  # 균등 분산 (최대 5종목)
                if budget_per_stock < 1_000_000:
                    budget_per_stock = available  # 자금 부족 시 전액

                estimated_quantity = int(budget_per_stock / current_price) if current_price > 0 else 0

                safety_result = await safety_checker.check_buy_safety(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    quantity=estimated_quantity,
                    price=current_price
                )

                # Safety check 실패 시 매수 스킵
                if not safety_result['approved']:
                    logger.warning(f"  ❌ {stock_name}: Safety check REJECTED - {safety_result['reason']}")
                    continue

                logger.info(f"  ✅ {stock_name}: Safety check PASSED - {safety_result['reason']}")

                # TODO: 실제 주문 실행
                # order_result = await self.order_service.place_buy_order(
                #     stock_code=stock_code,
                #     stock_name=stock_name,
                #     quantity=estimated_quantity,
                #     price=current_price,
                #     market=candidate.get('market', 'KRX')
                # )
                # buy_orders.append(order_result)

                pass

            except Exception as e:
                logger.error(f"  ❌ Buy order failed: {candidate.get('stock_code')} - {e}")

        logger.info(f"⚔️  Execution complete: {len(buy_orders)} buys, {len(sell_orders)} sells")
        return buy_orders, sell_orders

    async def check_market_hours(self) -> bool:
        """
        장 시간 확인

        Returns:
            장 중이면 True, 아니면 False
        """
        now = datetime.now()

        # 주말 체크
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False

        # 시간 체크 (09:00 ~ 15:30)
        current_time = now.time()
        market_open = datetime.strptime("09:00", "%H:%M").time()
        market_close = datetime.strptime("15:30", "%H:%M").time()

        return market_open <= current_time <= market_close


# Singleton Instance
intraday_pipeline = IntradayPipeline()
