"""
AEGIS v3.0 - Initialize Daily Data
종목 기초 데이터 & 3년 치 과거 데이터 채우기

실행: source venv/bin/activate && python scripts/init_daily_data.py
소요시간: 2~3시간 예상
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .env 파일 로드
load_dotenv()

from app.database import SessionLocal
from app.models.market import Stock, DailyPrice
from sqlalchemy import select

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("INIT_DAILY_DATA")


class DailyDataInitializer:
    """일별 데이터 초기화 매니저"""

    def __init__(self):
        self.db = SessionLocal()

    def __del__(self):
        """세션 종료"""
        if hasattr(self, 'db'):
            self.db.close()

    def run(self):
        """전체 초기화 프로세스"""
        logger.info("=" * 60)
        logger.info("📊 종목 기초 데이터 & 3년 치 과거 데이터 초기화")
        logger.info("=" * 60)
        logger.info("")

        try:
            # 1. 종목 마스터 데이터 생성
            logger.info("1️⃣ 종목 마스터 데이터 생성 중...")
            self._init_stocks()

            # 2. 3년 치 일별 시세 데이터 수집
            logger.info("")
            logger.info("2️⃣ 3년 치 일별 시세 데이터 수집 중...")
            logger.info("   (시간이 걸립니다. 2~3시간 예상)")
            self._fetch_daily_prices()

            # 3. 완료
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ 초기화 완료!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 초기화 실패: {e}")
            import traceback
            traceback.print_exc()

    def _init_stocks(self):
        """
        종목 마스터 데이터 생성
        FinanceDataReader를 사용하여 전체 KOSPI + KOSDAQ 종목 리스트 가져오기
        """
        import FinanceDataReader as fdr

        logger.info("   전체 종목 리스트 가져오는 중...")

        # KOSPI 전체 종목
        logger.info("   📥 KOSPI 종목 조회 중...")
        kospi_stocks = fdr.StockListing('KOSPI')
        logger.info(f"      KOSPI {len(kospi_stocks)}개 종목 조회됨")

        # KOSDAQ 전체 종목
        logger.info("   📥 KOSDAQ 종목 조회 중...")
        kosdaq_stocks = fdr.StockListing('KOSDAQ')
        logger.info(f"      KOSDAQ {len(kosdaq_stocks)}개 종목 조회됨")

        # 합치기
        all_stocks = []

        # KOSPI 처리
        for _, row in kospi_stocks.iterrows():
            all_stocks.append({
                'code': row['Code'],
                'name': row['Name'],
                'market': 'KOSPI',
                'sector': row.get('Sector', ''),
                'market_cap': int(row['Marcap']) if 'Marcap' in row and row['Marcap'] > 0 else None
            })

        # KOSDAQ 처리
        for _, row in kosdaq_stocks.iterrows():
            all_stocks.append({
                'code': row['Code'],
                'name': row['Name'],
                'market': 'KOSDAQ',
                'sector': row.get('Sector', ''),
                'market_cap': int(row['Marcap']) if 'Marcap' in row and row['Marcap'] > 0 else None
            })

        logger.info(f"   총 {len(all_stocks)}개 종목 DB에 등록 중...")
        logger.info("")

        # DB에 저장
        saved_count = 0
        for idx, stock_data in enumerate(all_stocks, 1):
            # 진행률 표시
            if idx % 100 == 0:
                progress = int((idx / len(all_stocks)) * 50)
                bar = "█" * progress + "░" * (50 - progress)
                percent = (idx / len(all_stocks)) * 100
                print(f"\r   [{bar}] {percent:.1f}% ({idx}/{len(all_stocks)})", end="", flush=True)

            # 이미 존재하는지 확인
            stmt = select(Stock).where(Stock.code == stock_data['code'])
            existing = self.db.execute(stmt).scalar_one_or_none()

            if not existing:
                stock = Stock(
                    code=stock_data['code'],
                    name=stock_data['name'],
                    market=stock_data['market'],
                    sector=stock_data['sector'],
                    market_cap=stock_data['market_cap'],
                    is_active=True
                )
                self.db.add(stock)
                saved_count += 1

        print()  # 진행률 막대 후 줄바꿈
        self.db.commit()
        logger.info(f"   ✅ {saved_count}개 신규 종목 등록 완료 (전체: {len(all_stocks)}개)")

    def _fetch_daily_prices(self):
        """
        3년 치 일별 시세 데이터 수집

        FinanceDataReader를 사용하여 과거 3년간의 OHLCV 데이터 수집
        """
        import FinanceDataReader as fdr

        # 날짜 범위 설정 (3년 전 ~ 오늘)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 3)

        logger.info(f"   기간: {start_date.date()} ~ {end_date.date()}")
        logger.info("")

        # 데이터가 없는 종목만 가져오기 (Resume 기능)
        from sqlalchemy import text

        # daily_prices에 데이터가 없는 종목 코드 조회
        query = text("""
            SELECT s.code FROM stocks s
            LEFT JOIN daily_prices dp ON s.code = dp.stock_code
            WHERE dp.stock_code IS NULL
            GROUP BY s.code
        """)

        result = self.db.execute(query)
        stock_codes = [row.code for row in result]

        # Stock 객체로 변환
        stocks = []
        for code in stock_codes:
            stock = self.db.query(Stock).filter(Stock.code == code).first()
            if stock:
                stocks.append(stock)

        total = len(stocks)
        logger.info(f"   총 {total}개 종목 처리 예정 (이미 완료된 종목 제외)")
        logger.info("")

        for idx, stock_item in enumerate(stocks, 1):
            try:
                # 진행률 막대 그래프
                progress = int((idx / total) * 50)  # 50칸 막대
                bar = "█" * progress + "░" * (50 - progress)
                percent = (idx / total) * 100

                print(f"\r   [{bar}] {percent:.1f}% ({idx}/{total}) {stock_item.name[:10]:10s}", end="", flush=True)

                # FinanceDataReader로 데이터 가져오기
                df = fdr.DataReader(stock_item.code, start_date, end_date)

                if df.empty:
                    continue

                # DB에 저장
                saved_count = 0
                for date, row in df.iterrows():
                    # 이미 존재하는지 확인
                    stmt = select(DailyPrice).where(
                        DailyPrice.stock_code == stock_item.code,
                        DailyPrice.date == date.date()
                    )
                    existing = self.db.execute(stmt).scalar_one_or_none()

                    if existing:
                        continue  # 이미 있으면 스킵

                    # 등락률 계산
                    change_rate = 0.0
                    if row['Open'] > 0:
                        change_rate = ((row['Close'] - row['Open']) / row['Open']) * 100

                    # DailyPrice 생성 (FinanceDataReader 컬럼: Open, High, Low, Close, Volume, Change)
                    daily_price = DailyPrice(
                        stock_code=stock_item.code,
                        date=date.date(),
                        open=int(row['Open']),
                        high=int(row['High']),
                        low=int(row['Low']),
                        close=int(row['Close']),
                        volume=int(row['Volume']),
                        change_rate=float(row.get('Change', change_rate))
                    )

                    self.db.add(daily_price)
                    saved_count += 1

                # 주기적으로 커밋 (메모리 절약)
                if saved_count > 0:
                    self.db.commit()

            except Exception as e:
                self.db.rollback()
                continue

        print()  # 진행률 막대 후 줄바꿈
        logger.info("")
        logger.info("   ✅ 1년 치 일별 시세 데이터 수집 완료")


def main():
    """메인 함수"""
    try:
        initializer = DailyDataInitializer()
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
