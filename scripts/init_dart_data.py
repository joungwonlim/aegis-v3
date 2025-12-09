"""
AEGIS v3.0 - DART 재무 데이터 초기화
전체 종목의 재무제표 & 공시 데이터 수집

실행: source venv/bin/activate && python scripts/init_dart_data.py
소요시간: 30분~1시간 예상 (API 제한으로 천천히 수집)
"""
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
import time

# 프로젝트 루트 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .env 파일 로드
load_dotenv()

from app.database import SessionLocal
from app.models.market import Stock
from fetchers.dart_fetcher import DartFetcher
from sqlalchemy import select

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DART_INIT")


class DartDataInitializer:
    """DART 재무 데이터 초기화 매니저"""

    def __init__(self):
        self.db = SessionLocal()
        self.fetcher = DartFetcher()

    def __del__(self):
        """세션 종료"""
        if hasattr(self, 'db'):
            self.db.close()

    def run(self):
        """전체 초기화 프로세스"""
        logger.info("=" * 60)
        logger.info("📊 DART 재무 데이터 수집 시작")
        logger.info("=" * 60)
        logger.info("")

        try:
            # 1. 종목 목록 조회
            logger.info("1️⃣ DB에서 종목 목록 조회 중...")
            stmt = select(Stock).where(Stock.is_active == True)
            stocks = self.db.execute(stmt).scalars().all()

            total = len(stocks)
            logger.info(f"   총 {total}개 종목 처리 예정")
            logger.info("")

            # 2. 재무 데이터 수집
            logger.info("2️⃣ 종목별 재무 데이터 수집 중...")
            logger.info("   (API 제한으로 천천히 수집됩니다. 30분~1시간 예상)")
            logger.info("")

            success_count = 0
            fail_count = 0
            risk_count = 0

            for idx, stock in enumerate(stocks, 1):
                try:
                    # 진행률 막대
                    progress = int((idx / total) * 50)
                    bar = "█" * progress + "░" * (50 - progress)
                    percent = (idx / total) * 100

                    print(f"\r   [{bar}] {percent:.1f}% ({idx}/{total}) {stock.name[:10]:10s}", end="", flush=True)

                    # 재무제표 수집
                    financial = self.fetcher.get_financial_summary(stock.code)

                    if financial:
                        # Stock 테이블에 업데이트
                        stock.debt_ratio = financial['debt_ratio']
                        stock.roe = financial['roe']
                        stock.op_margin = financial['op_margin']
                        stock.is_deficit = financial['is_deficit']

                        success_count += 1

                    # 최근 공시 체크 (리스크 감지)
                    disclosures = self.fetcher.check_recent_disclosures(stock.code, days=30)

                    if disclosures:
                        # 악재 공시가 있으면 기록
                        critical_risks = [d for d in disclosures if d['type'] in ['CRITICAL_RISK', 'OVERHANG_RISK']]
                        if critical_risks:
                            stock.last_risk_report = critical_risks[0]['title']
                            risk_count += 1

                    # 주기적으로 커밋
                    if idx % 100 == 0:
                        self.db.commit()

                    # API 호출 제한 방지 (초당 10건)
                    time.sleep(0.1)

                except Exception as e:
                    fail_count += 1
                    logger.debug(f"   ⚠️  {stock.name} 처리 실패: {e}")
                    continue

            print()  # 진행률 막대 후 줄바꿈
            self.db.commit()

            logger.info("")
            logger.info(f"   ✅ 재무 데이터 수집: {success_count}개")
            logger.info(f"   ⚠️  리스크 종목 발견: {risk_count}개")
            logger.info(f"   ❌ 실패: {fail_count}개")

            # 3. 완료
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ DART 데이터 수집 완료!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()


def main():
    """메인 함수"""
    try:
        initializer = DartDataInitializer()
        initializer.run()
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
