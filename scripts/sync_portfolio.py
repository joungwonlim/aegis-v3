"""
AEGIS v3.0 - Portfolio Sync Script
KIS API에서 보유종목 가져와서 DB에 동기화

작성일: 2025-12-09
목적: 보유종목 정보를 KIS → PostgreSQL 동기화
"""
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .env 파일 로드
load_dotenv()

from fetchers.kis_client import KISClient
from app.database import SessionLocal
from app.models.account import Portfolio
from sqlalchemy import select

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PORTFOLIO_SYNC")


class PortfolioSyncManager:
    """보유종목 동기화 매니저"""

    def __init__(self):
        self.kis_client = KISClient()
        self.db = SessionLocal()

    def __del__(self):
        """세션 종료"""
        if hasattr(self, 'db'):
            self.db.close()

    def sync_portfolio(self):
        """
        KIS API → PostgreSQL 보유종목 동기화

        Process:
        1. KIS API로 보유종목 조회
        2. 각 종목의 현재가 조회
        3. 수익률 계산
        4. DB에 저장/업데이트
        """
        logger.info("=" * 60)
        logger.info("📊 보유종목 동기화 시작")
        logger.info("=" * 60)

        try:
            # 1. KIS API로 보유종목 조회
            logger.info("1️⃣ KIS API 보유종목 조회 중...")
            holdings = self.kis_client.get_combined_balance()
            logger.info(f"   ✅ {len(holdings)}개 종목 조회 완료")

            if not holdings:
                logger.warning("   ⚠️  보유종목이 없습니다.")
                return

            # 2. 각 종목 처리
            logger.info("\n2️⃣ 종목별 데이터 처리 중...")

            updated_count = 0
            created_count = 0

            for holding in holdings:
                try:
                    result = self._process_holding(holding)
                    if result == "updated":
                        updated_count += 1
                    elif result == "created":
                        created_count += 1

                except Exception as e:
                    logger.error(f"   ❌ 종목 처리 실패 ({holding.get('pdno')}): {e}")

            # 3. 결과 출력
            logger.info("\n" + "=" * 60)
            logger.info("✅ 보유종목 동기화 완료")
            logger.info(f"   - 신규 추가: {created_count}개")
            logger.info(f"   - 업데이트: {updated_count}개")
            logger.info(f"   - 총 보유: {len(holdings)}개")
            logger.info("=" * 60)

            # 4. DB에서 없어진 종목 처리 (수량 0으로 매도됨)
            self._clean_sold_positions(holdings)

        except Exception as e:
            logger.error(f"❌ 동기화 실패: {e}")
            import traceback
            traceback.print_exc()

    def _process_holding(self, holding: dict) -> str:
        """
        개별 종목 처리

        Args:
            holding: KIS API 응답 데이터

        Returns:
            "created" | "updated"
        """
        # KIS API 응답 파싱
        stock_code = holding.get("pdno")  # 종목코드
        stock_name = holding.get("prdt_name")  # 종목명
        quantity = int(holding.get("hldg_qty", 0))  # 보유수량
        avg_price = float(holding.get("pchs_avg_pric", 0))  # 평균매입가
        current_price = float(holding.get("prpr", 0))  # 현재가

        # 수익률 계산
        if avg_price > 0:
            profit_rate = ((current_price - avg_price) / avg_price) * 100
        else:
            profit_rate = 0.0

        # DB에서 기존 데이터 확인
        stmt = select(Portfolio).where(Portfolio.stock_code == stock_code)
        existing = self.db.execute(stmt).scalar_one_or_none()

        if existing:
            # 업데이트
            existing.stock_name = stock_name
            existing.quantity = quantity
            existing.avg_price = avg_price
            existing.current_price = current_price
            existing.profit_rate = profit_rate
            existing.last_updated = datetime.now()

            # 최고가 업데이트
            if existing.max_price_reached is None or current_price > existing.max_price_reached:
                existing.max_price_reached = current_price

            self.db.commit()

            logger.info(f"   ✅ 업데이트: {stock_name} ({stock_code}) | "
                       f"{quantity}주 | 수익률: {profit_rate:+.2f}%")

            return "updated"

        else:
            # 신규 생성
            new_portfolio = Portfolio(
                stock_code=stock_code,
                stock_name=stock_name,
                quantity=quantity,
                avg_price=avg_price,
                current_price=current_price,
                profit_rate=profit_rate,
                bought_at=datetime.now(),
                max_price_reached=current_price,
                pyramid_stage=0,
                sell_stage=0
            )

            self.db.add(new_portfolio)
            self.db.commit()

            logger.info(f"   ✅ 신규 추가: {stock_name} ({stock_code}) | "
                       f"{quantity}주 | 수익률: {profit_rate:+.2f}%")

            return "created"

    def _clean_sold_positions(self, current_holdings: list):
        """
        매도되어 없어진 종목 정리

        Args:
            current_holdings: 현재 KIS에서 조회된 보유종목
        """
        current_codes = {h.get("pdno") for h in current_holdings}

        # DB에서 모든 보유종목 조회
        stmt = select(Portfolio)
        all_positions = self.db.execute(stmt).scalars().all()

        deleted_count = 0
        for position in all_positions:
            if position.stock_code not in current_codes:
                # KIS에 없는 종목 = 매도됨
                logger.info(f"   🗑️  매도 완료: {position.stock_name} ({position.stock_code}) 삭제")
                self.db.delete(position)
                deleted_count += 1

        if deleted_count > 0:
            self.db.commit()
            logger.info(f"\n   ✅ {deleted_count}개 매도 종목 정리 완료")


def main():
    """메인 함수"""
    try:
        manager = PortfolioSyncManager()
        manager.sync_portfolio()

        return 0

    except KeyboardInterrupt:
        logger.warning("\n\n⚠️  사용자 중단")
        return 1

    except Exception as e:
        logger.error(f"\n\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
