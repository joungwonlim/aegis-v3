"""
AEGIS v3.0 - KIS Market Data Initialization
한국투자증권 API로 시장 데이터 수집 및 DB 저장

실행: source venv/bin/activate && python scripts/init_kis_market.py
소요시간: 10초 이내
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
from fetchers.kis_market_fetcher import KISMarketFetcher
from sqlalchemy import text

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("KIS_MARKET")


class KISMarketInitializer:
    """KIS 시장 데이터 초기화 매니저"""

    def __init__(self):
        self.db = SessionLocal()
        self.fetcher = KISMarketFetcher()

    def __del__(self):
        """세션 종료"""
        if hasattr(self, 'db'):
            self.db.close()

    def run(self):
        """전체 초기화 프로세스"""
        logger.info("=" * 60)
        logger.info("📊 KIS 시장 데이터 수집 시작")
        logger.info("=" * 60)
        logger.info("")

        try:
            # 1. KIS API로 시장 데이터 수집
            logger.info("1️⃣ KIS API 데이터 수집 중...")
            market_data = self.fetcher.get_all_market_data()

            if not market_data:
                logger.error("❌ 데이터 수집 실패")
                return

            # 2. 수집된 데이터 출력
            logger.info("")
            logger.info("📥 수집된 데이터:")

            foreign_net = market_data.get('foreign_futures_net')
            program_net = market_data.get('program_net')
            spot = market_data.get('kospi200_spot')
            futures = market_data.get('kospi200_futures')
            basis = market_data.get('basis')

            logger.info(f"   - 외국인 선물 누적: {foreign_net:,}계약" if foreign_net else "   - 외국인 선물 누적: 데이터 없음")
            logger.info(f"   - 프로그램 비차익: {program_net:,}백만원" if program_net else "   - 프로그램 비차익: 데이터 없음")
            logger.info(f"   - KOSPI200 현물: {spot}" if spot else "   - KOSPI200 현물: 데이터 없음")
            logger.info(f"   - KOSPI200 선물: {futures}" if futures else "   - KOSPI200 선물: 데이터 없음")
            logger.info(f"   - 베이시스: {basis}" if basis else "   - 베이시스: 데이터 없음")
            logger.info("")

            # 3. DB에 저장
            logger.info("2️⃣ DB에 저장 중...")
            today = date.today()

            query = text("""
                INSERT INTO market_flow
                (date, foreign_futures_net, program_net, kospi200_spot, kospi200_futures, basis)
                VALUES (:date, :foreign_futures_net, :program_net, :kospi200_spot, :kospi200_futures, :basis)
                ON CONFLICT (date) DO UPDATE SET
                    foreign_futures_net = EXCLUDED.foreign_futures_net,
                    program_net = EXCLUDED.program_net,
                    kospi200_spot = EXCLUDED.kospi200_spot,
                    kospi200_futures = EXCLUDED.kospi200_futures,
                    basis = EXCLUDED.basis
            """)

            self.db.execute(query, {
                'date': today,
                'foreign_futures_net': market_data.get('foreign_futures_net'),
                'program_net': market_data.get('program_net'),
                'kospi200_spot': market_data.get('kospi200_spot'),
                'kospi200_futures': market_data.get('kospi200_futures'),
                'basis': market_data.get('basis')
            })

            self.db.commit()
            logger.info(f"   ✅ {today} 데이터 저장 완료")

            # 4. 완료
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ KIS 시장 데이터 수집 완료!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()


def main():
    """메인 함수"""
    try:
        initializer = KISMarketInitializer()
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
