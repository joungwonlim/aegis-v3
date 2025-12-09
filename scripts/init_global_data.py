"""
AEGIS v3.0 - Global Market Data Initialization
전체 글로벌 시장 데이터 수집 및 DB 저장

실행: source venv/bin/activate && python scripts/init_global_data.py
소요시간: 1~2분
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
from fetchers.yfinance.global_fetcher import GlobalMarketFetcher
from sqlalchemy import select

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GLOBAL_INIT")


class GlobalDataInitializer:
    """글로벌 시장 데이터 초기화 매니저"""

    def __init__(self):
        self.db = SessionLocal()
        self.fetcher = GlobalMarketFetcher()

    def __del__(self):
        """세션 종료"""
        if hasattr(self, 'db'):
            self.db.close()

    def run(self):
        """전체 초기화 프로세스"""
        logger.info("=" * 60)
        logger.info("🌍 글로벌 시장 데이터 수집 시작")
        logger.info("=" * 60)
        logger.info("")

        try:
            # 1. 전체 글로벌 데이터 수집
            logger.info("1️⃣ YFinance 데이터 수집 중...")
            global_data = self.fetcher.get_all_global_data()

            if not global_data:
                logger.error("❌ 데이터 수집 실패")
                return

            # 2. 주요 데이터 출력
            logger.info("")
            logger.info("📥 주요 수집 데이터:")
            key_indicators = [
                ("dollar_index", "달러 인덱스"),
                ("cnh", "위안화"),
                ("jpy_krw", "엔/원"),
                ("nasdaq", "Nasdaq"),
                ("sp500", "S&P 500"),
                ("sox", "반도체 지수"),
                ("vix", "VIX"),
                ("nvda", "엔비디아"),
                ("tsla", "테슬라"),
                ("btc", "비트코인"),
            ]

            for col_name, display_name in key_indicators:
                value = global_data.get(col_name)
                if value is not None:
                    logger.info(f"   - {display_name}: {value}")

            # 3. DB에 저장
            logger.info("")
            logger.info("2️⃣ DB에 저장 중...")
            today = date.today()

            # 기존 데이터 확인
            stmt = select(MarketMacro).where(MarketMacro.date == today)
            existing = self.db.execute(stmt).scalar_one_or_none()

            if existing:
                # 업데이트
                for col_name, value in global_data.items():
                    if hasattr(existing, col_name):
                        setattr(existing, col_name, value)
                logger.info(f"   ✅ {today} 데이터 업데이트됨")
            else:
                # 신규 생성
                macro_record = MarketMacro(date=today, **global_data)
                self.db.add(macro_record)
                logger.info(f"   ✅ {today} 신규 데이터 저장됨")

            self.db.commit()

            # 4. 통계
            logger.info("")
            logger.info("📊 저장 통계:")
            total_fields = len(global_data)
            saved_fields = sum(1 for v in global_data.values() if v is not None)
            null_fields = total_fields - saved_fields

            logger.info(f"   - 전체 필드: {total_fields}개")
            logger.info(f"   - 저장 완료: {saved_fields}개")
            logger.info(f"   - 데이터 없음: {null_fields}개")

            # 5. 완료
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ 글로벌 데이터 수집 완료!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()


def main():
    """메인 함수"""
    try:
        initializer = GlobalDataInitializer()
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
