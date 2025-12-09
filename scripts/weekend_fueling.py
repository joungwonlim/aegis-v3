"""
AEGIS v3.0 - Macro Data Fueling
글로벌 매크로 데이터 수집 및 DB 저장

목적: 미국장(Nasdaq, SOX), 환율, 원자재 데이터 수집 → market_macro 테이블 저장
"""
import os
import sys
import logging
from datetime import datetime, date
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .env 파일 로드
load_dotenv()

from app.database import SessionLocal
from app.models.market import MarketMacro
from fetchers.yfinance.client import YFinanceFetcher
from sqlalchemy import select

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MACRO_FUELING")


class MacroDataFueler:
    """글로벌 매크로 데이터 수집 및 DB 저장"""

    def __init__(self):
        self.db = SessionLocal()
        self.fetcher = YFinanceFetcher()

    def __del__(self):
        """세션 종료"""
        if hasattr(self, 'db'):
            self.db.close()

    def run(self):
        """전체 수집 프로세스"""
        logger.info("=" * 60)
        logger.info("📊 글로벌 매크로 데이터 수집")
        logger.info("=" * 60)
        logger.info("")

        try:
            # 1. YFinance로 데이터 수집
            logger.info("1️⃣ YFinance 데이터 수집 중...")
            macro_data = self.fetcher.get_macro_data()

            if not macro_data:
                logger.error("❌ 데이터 수집 실패")
                return

            # 2. 데이터 출력
            logger.info("")
            logger.info("📥 수집된 데이터:")
            logger.info(f"   - Nasdaq: {macro_data.get('nasdaq_index')} ({macro_data.get('nasdaq_change_pct'):+.2f}%)")
            logger.info(f"   - SOX: {macro_data.get('sox_index')} ({macro_data.get('sox_change_pct'):+.2f}%)")
            logger.info(f"   - USD/KRW: {macro_data.get('us_krw_index')} ({macro_data.get('us_krw_change_pct'):+.2f}%)")
            logger.info(f"   - VIX: {macro_data.get('vix_index')}")
            logger.info("")

            # 3. DB에 저장
            logger.info("2️⃣ DB에 저장 중...")
            today = date.today()

            # 기존 데이터 확인
            stmt = select(MarketMacro).where(MarketMacro.date == today)
            existing = self.db.execute(stmt).scalar_one_or_none()

            if existing:
                # 업데이트
                existing.us_krw = macro_data.get('us_krw_index')
                existing.nasdaq = macro_data.get('nasdaq_index')
                existing.sox = macro_data.get('sox_index')
                existing.vix = macro_data.get('vix_index')
                logger.info(f"   ✅ {today} 데이터 업데이트됨")
            else:
                # 신규 생성
                macro_record = MarketMacro(
                    date=today,
                    us_krw=macro_data.get('us_krw_index'),
                    nasdaq=macro_data.get('nasdaq_index'),
                    sox=macro_data.get('sox_index'),
                    vix=macro_data.get('vix_index')
                )
                self.db.add(macro_record)
                logger.info(f"   ✅ {today} 신규 데이터 저장됨")

            self.db.commit()

            # 4. 완료
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ 매크로 데이터 수집 완료!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()


def main():
    """메인 함수"""
    try:
        fueler = MacroDataFueler()
        fueler.run()
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
