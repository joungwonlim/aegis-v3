"""
AEGIS v3.0 - Global Market Data Fetcher
EXTERNAL_DATA_SOURCES.md 기반 전체 글로벌 시장 데이터 수집
"""
import yfinance as yf
import logging
from typing import Dict, Optional

logger = logging.getLogger("GlobalFetcher")


class GlobalMarketFetcher:
    """
    전체 글로벌 시장 데이터 수집
    EXTERNAL_DATA_SOURCES.md의 모든 티커 커버
    """

    # 티커 매핑: DB 컬럼명 -> YFinance 티커
    TICKER_MAP = {
        # 환율/통화
        "dollar_index": "DX-Y.NYB",      # 달러 인덱스
        "us_krw": "KRW=X",               # 원/달러
        "cnh": "CNH=X",                  # 위안화 역외
        "jpy_krw": "JPYKRW=X",           # 엔/원

        # 변동성/공포 지표
        "vix": "^VIX",                   # VIX 공포지수
        "move_index": "^MOVE",           # MOVE Index
        "tnx": "^TNX",                   # 미국 10년물 금리
        "hyg": "HYG",                    # 하이일드 채권 ETF

        # 미국 지수 & 선물
        "nasdaq": "^IXIC",               # Nasdaq Composite
        "sp500": "^GSPC",                # S&P 500
        "dow": "^DJI",                   # 다우존스
        "russell2000": "^RUT",           # 러셀 2000
        "sp500_futures": "ES=F",         # S&P 500 선물
        "nasdaq_futures": "NQ=F",        # 나스닥 100 선물

        # 반도체 섹터
        "sox": "^SOX",                   # 반도체 지수
        "taiwan_index": "^TWII",         # 대만 가권지수
        "micron": "MU",                  # 마이크론
        "amd": "AMD",                    # AMD
        "tsm": "TSM",                    # TSMC
        "asml": "ASML",                  # ASML
        "nvda": "NVDA",                  # 엔비디아

        # 2차전지/에너지
        "lit_etf": "LIT",                # 리튬&배터리 ETF
        "alb": "ALB",                    # 앨버말 리튬
        "tsla": "TSLA",                  # 테슬라
        "ura_etf": "URA",                # 우라늄 ETF

        # 방산
        "lmt": "LMT",                    # 록히드마틴
        "rtx": "RTX",                    # RTX 레이시온

        # 조선/해운
        "bdry": "BDRY",                  # 건화물 운임 ETF

        # 원자재
        "wti": "CL=F",                   # WTI 원유
        "brent": "BZ=F",                 # 브렌트유
        "copper": "HG=F",                # 구리
        "gold": "GC=F",                  # 금

        # 미국 섹터 ETF
        "xlk": "XLK",                    # Technology
        "xlf": "XLF",                    # Financials
        "xle": "XLE",                    # Energy
        "xlv": "XLV",                    # Healthcare
        "xly": "XLY",                    # Consumer Discretionary
        "xli": "XLI",                    # Industrials
        "xlb": "XLB",                    # Materials

        # 국가/지역 ETF
        "ewy": "EWY",                    # MSCI 한국 ETF
        "fxi": "FXI",                    # 중국 A50 ETF
        "inda": "INDA",                  # 인도 ETF

        # M7 빅테크
        "aapl": "AAPL",                  # 애플
        "msft": "MSFT",                  # 마이크로소프트
        "googl": "GOOGL",                # 구글
        "meta": "META",                  # 메타
        "amzn": "AMZN",                  # 아마존

        # 기타
        "btc": "BTC-USD",                # 비트코인
    }

    def __init__(self):
        logger.info("✅ GlobalMarketFetcher initialized")

    def get_all_global_data(self) -> Dict[str, Optional[float]]:
        """
        전체 글로벌 데이터 수집

        Returns:
            dict: {
                "dollar_index": 104.5,
                "cnh": 7.25,
                "nasdaq": 15000.0,
                ...
            }
        """
        result = {}
        total = len(self.TICKER_MAP)
        success = 0
        fail = 0

        logger.info(f"📊 {total}개 티커 데이터 수집 시작...")

        for idx, (col_name, ticker) in enumerate(self.TICKER_MAP.items(), 1):
            try:
                # YFinance로 데이터 조회
                data = yf.Ticker(ticker).history(period="5d")

                if len(data) == 0:
                    logger.debug(f"⚠️  No data for {col_name} ({ticker})")
                    result[col_name] = None
                    fail += 1
                    continue

                # 최근 종가
                latest_close = data["Close"].iloc[-1]
                result[col_name] = round(float(latest_close), 2)
                success += 1

                # 진행 상황
                if idx % 10 == 0 or idx == total:
                    logger.info(f"   진행: {idx}/{total} ({success}개 성공, {fail}개 실패)")

            except Exception as e:
                logger.debug(f"❌ Failed to fetch {col_name} ({ticker}): {e}")
                result[col_name] = None
                fail += 1

        logger.info(f"✅ 수집 완료: {success}개 성공, {fail}개 실패")
        return result

    def get_ticker_data(self, col_name: str) -> Optional[float]:
        """
        특정 티커 데이터만 조회

        Args:
            col_name: DB 컬럼명 (예: "dollar_index", "nasdaq")

        Returns:
            float or None
        """
        ticker = self.TICKER_MAP.get(col_name)
        if not ticker:
            logger.warning(f"⚠️  Unknown column: {col_name}")
            return None

        try:
            data = yf.Ticker(ticker).history(period="5d")
            if len(data) == 0:
                return None

            latest_close = data["Close"].iloc[-1]
            return round(float(latest_close), 2)

        except Exception as e:
            logger.error(f"❌ Failed to fetch {col_name} ({ticker}): {e}")
            return None


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)

    fetcher = GlobalMarketFetcher()

    print("\n" + "="*60)
    print("📊 Global Market Data Test")
    print("="*60)

    data = fetcher.get_all_global_data()

    print("\n✅ 수집된 데이터:")
    for key, value in data.items():
        if value is not None:
            print(f"   {key}: {value}")
