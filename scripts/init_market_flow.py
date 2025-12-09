"""
AEGIS v3.0 - Market Flow Data Initialization
투자자별 순매수 & 대차잔고 데이터 수집 (pykrx)

실행: source venv/bin/activate && python scripts/init_market_flow.py
소요시간: 5~10분
"""
import os
import sys
import logging
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
import time

# 프로젝트 루트 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .env 파일 로드
load_dotenv()

from app.database import SessionLocal
from app.models.market import Stock
from sqlalchemy import select, text

# pykrx import
try:
    from pykrx import stock
except ImportError:
    print("❌ pykrx가 설치되지 않았습니다. pip install pykrx 실행 필요")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MARKET_FLOW")


class MarketFlowInitializer:
    """시장 수급 데이터 초기화 매니저"""

    def __init__(self):
        self.db = SessionLocal()

    def __del__(self):
        """세션 종료"""
        if hasattr(self, 'db'):
            self.db.close()

    def run(self, days=30):
        """
        전체 초기화 프로세스

        Args:
            days: 과거 N일치 데이터 수집 (기본 30일)
        """
        logger.info("=" * 60)
        logger.info("📊 시장 수급 데이터 수집 시작")
        logger.info("=" * 60)
        logger.info("")

        try:
            # 날짜 범위 설정
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            logger.info(f"📅 수집 기간: {start_date} ~ {end_date} ({days}일)")
            logger.info("")

            # 1. 투자자별 순매수 수집
            logger.info("1️⃣ 투자자별 순매수 데이터 수집 중...")
            self._collect_investor_net_buying(start_date, end_date)

            # 2. 대차잔고 수집
            logger.info("")
            logger.info("2️⃣ 대차잔고 데이터 수집 중...")
            self._collect_short_balance(start_date, end_date)

            # 3. 완료
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ 시장 수급 데이터 수집 완료!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            self.db.rollback()

    def _collect_investor_net_buying(self, start_date, end_date):
        """투자자별 순매수 데이터 수집"""

        # KOSPI 대표 종목만 수집 (전체 수집 시 시간 오래 걸림)
        logger.info("   📥 KOSPI 대표 종목 조회 중...")

        # 시가총액 상위 100개 종목만 수집
        stmt = text("""
            SELECT code FROM stocks
            WHERE market = 'KOSPI' AND market_cap IS NOT NULL
            ORDER BY market_cap DESC
            LIMIT 100
        """)

        result = self.db.execute(stmt)
        stock_codes = [row.code for row in result]

        logger.info(f"   총 {len(stock_codes)}개 종목 처리 예정")
        logger.info("")

        success_count = 0
        fail_count = 0
        total = len(stock_codes)

        for idx, code in enumerate(stock_codes, 1):
            try:
                # 진행률
                if idx % 10 == 0 or idx == total:
                    progress = int((idx / total) * 50)
                    bar = "█" * progress + "░" * (50 - progress)
                    percent = (idx / total) * 100
                    print(f"\r   [{bar}] {percent:.1f}% ({idx}/{total})", end="", flush=True)

                # pykrx로 투자자별 순매수 조회
                df = stock.get_market_trading_value_by_date(
                    start_date.strftime("%Y%m%d"),
                    end_date.strftime("%Y%m%d"),
                    code
                )

                if df is None or len(df) == 0:
                    fail_count += 1
                    continue

                # DB에 저장
                for trade_date, row in df.iterrows():
                    query = text("""
                        INSERT INTO investor_net_buying
                        (date, stock_code, foreign_net, institution_net, individual_net)
                        VALUES (:date, :stock_code, :foreign_net, :institution_net, :individual_net)
                        ON CONFLICT (date, stock_code) DO UPDATE SET
                            foreign_net = EXCLUDED.foreign_net,
                            institution_net = EXCLUDED.institution_net,
                            individual_net = EXCLUDED.individual_net
                    """)

                    self.db.execute(query, {
                        'date': trade_date.date(),
                        'stock_code': code,
                        'foreign_net': int(row.get('외국인', 0)),
                        'institution_net': int(row.get('기관', 0)),
                        'individual_net': int(row.get('개인', 0))
                    })

                success_count += 1

                # 주기적 커밋
                if idx % 10 == 0:
                    self.db.commit()

                # API 호출 제한 (초당 5건)
                time.sleep(0.2)

            except Exception as e:
                fail_count += 1
                logger.debug(f"   ⚠️  {code} 처리 실패: {e}")
                continue

        print()  # 줄바꿈
        self.db.commit()
        logger.info("")
        logger.info(f"   ✅ 성공: {success_count}개, 실패: {fail_count}개")

    def _collect_short_balance(self, start_date, end_date):
        """대차잔고 데이터 수집"""

        logger.info("   📥 최근 대차잔고 데이터 조회 중...")

        try:
            # pykrx로 전체 종목 대차잔고 조회 (최근 1일)
            today = end_date.strftime("%Y%m%d")

            df = stock.get_shorting_value_by_ticker(today)

            if df is None or len(df) == 0:
                logger.warning("   ⚠️  대차잔고 데이터 없음")
                return

            saved_count = 0

            for ticker, row in df.iterrows():
                try:
                    query = text("""
                        INSERT INTO short_balance
                        (date, stock_code, balance_qty, balance_amount, balance_ratio)
                        VALUES (:date, :stock_code, :balance_qty, :balance_amount, :balance_ratio)
                        ON CONFLICT (date, stock_code) DO UPDATE SET
                            balance_qty = EXCLUDED.balance_qty,
                            balance_amount = EXCLUDED.balance_amount,
                            balance_ratio = EXCLUDED.balance_ratio
                    """)

                    self.db.execute(query, {
                        'date': end_date,
                        'stock_code': ticker,
                        'balance_qty': int(row.get('잔고수량', 0)),
                        'balance_amount': int(row.get('잔고금액', 0)),
                        'balance_ratio': float(row.get('잔고율', 0.0))
                    })

                    saved_count += 1

                except Exception as e:
                    logger.debug(f"   ⚠️  {ticker} 저장 실패: {e}")
                    continue

            self.db.commit()
            logger.info(f"   ✅ {saved_count}개 종목 대차잔고 저장 완료")

        except Exception as e:
            logger.error(f"   ❌ 대차잔고 수집 실패: {e}")
            import traceback
            traceback.print_exc()


def main():
    """메인 함수"""
    try:
        # 명령행 인자로 일수 지정 가능
        days = 30
        if len(sys.argv) > 1:
            days = int(sys.argv[1])

        initializer = MarketFlowInitializer()
        initializer.run(days=days)
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
