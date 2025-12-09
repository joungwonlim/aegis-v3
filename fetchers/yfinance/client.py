"""
AEGIS v3.0 - YFinance Client
미국장 데이터 수집 (Nasdaq, SOX, USD/KRW, WTI 등)
"""
import yfinance as yf
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("YFinanceFetcher")


class YFinanceFetcher:
    """
    YFinance를 사용한 글로벌 시장 데이터 수집
    """

    # 핵심 티커 매핑
    TICKERS = {
        "nasdaq": "^IXIC",      # Nasdaq Composite
        "sox": "^SOX",          # Semiconductor Index
        "us_krw": "KRW=X",      # USD/KRW Exchange Rate
        "wti": "CL=F",          # WTI Crude Oil
        "snp500": "^GSPC",      # S&P 500
        "vix": "^VIX",          # Volatility Index
    }

    def __init__(self):
        logger.info("✅ YFinanceFetcher initialized")

    def get_macro_data(self):
        """
        금요일 미국장 마감 데이터 수집

        Returns:
            dict: {
                "nasdaq_index": float,
                "nasdaq_change_pct": float,
                "sox_index": float,
                "sox_change_pct": float,
                "us_krw_rate": float,
                "us_krw_change_pct": float,
                "wti_oil": float,
                "wti_change_pct": float,
                "snp500_index": float,
                "vix_index": float
            }
        """
        result = {}

        for name, ticker in self.TICKERS.items():
            try:
                data = yf.Ticker(ticker).history(period="5d")
                if len(data) == 0:
                    logger.warning(f"⚠️  No data for {name} ({ticker})")
                    continue

                # 최근 종가
                latest_close = data["Close"].iloc[-1]

                # 변화율 계산
                if len(data) >= 2:
                    prev_close = data["Close"].iloc[-2]
                    change_pct = ((latest_close - prev_close) / prev_close) * 100
                else:
                    change_pct = 0.0

                result[f"{name}_index"] = round(float(latest_close), 2)
                result[f"{name}_change_pct"] = round(change_pct, 2)

                logger.info(f"📊 {name}: {latest_close:.2f} ({change_pct:+.2f}%)")

            except Exception as e:
                logger.error(f"❌ Failed to fetch {name}: {e}")

        return result

    def get_custom_tickers(self, tickers: list):
        """
        커스텀 티커 리스트 조회

        Args:
            tickers: ["BTC-USD", "CL=F", ...] 형태의 티커 리스트

        Returns:
            dict: {
                "BTC-USD": {"price": float, "change_pct": float},
                ...
            }
        """
        result = {}

        for ticker in tickers:
            try:
                data = yf.Ticker(ticker).history(period="5d")
                if len(data) == 0:
                    continue

                latest_close = data["Close"].iloc[-1]

                if len(data) >= 2:
                    prev_close = data["Close"].iloc[-2]
                    change_pct = ((latest_close - prev_close) / prev_close) * 100
                else:
                    change_pct = 0.0

                result[ticker] = {
                    "price": round(float(latest_close), 2),
                    "change_pct": round(change_pct, 2)
                }

                logger.info(f"📊 {ticker}: {latest_close:.2f} ({change_pct:+.2f}%)")

            except Exception as e:
                logger.error(f"❌ Failed to fetch {ticker}: {e}")

        return result

    def get_sector_etfs(self):
        """
        미국 섹터 ETF 데이터 수집

        Returns:
            dict: {
                "tech": {"ticker": "XLK", "price": float, "change_pct": float},
                "semicon": {"ticker": "SMH", "price": float, "change_pct": float},
                ...
            }
        """
        sectors = {
            "tech": "XLK",          # Technology Select Sector
            "semicon": "SMH",       # VanEck Semiconductor ETF
            "finance": "XLF",       # Financial Select Sector
            "energy": "XLE",        # Energy Select Sector
            "consumer": "XLY",      # Consumer Discretionary
        }

        result = {}

        for sector, ticker in sectors.items():
            try:
                data = yf.Ticker(ticker).history(period="5d")
                if len(data) == 0:
                    continue

                latest_close = data["Close"].iloc[-1]

                if len(data) >= 2:
                    prev_close = data["Close"].iloc[-2]
                    change_pct = ((latest_close - prev_close) / prev_close) * 100
                else:
                    change_pct = 0.0

                result[sector] = {
                    "ticker": ticker,
                    "price": round(float(latest_close), 2),
                    "change_pct": round(change_pct, 2)
                }

                logger.info(f"📊 {sector} ({ticker}): {latest_close:.2f} ({change_pct:+.2f}%)")

            except Exception as e:
                logger.error(f"❌ Failed to fetch {sector}: {e}")

        return result


if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)

    fetcher = YFinanceFetcher()

    print("\n" + "="*60)
    print("📊 Macro Data Test")
    print("="*60)
    macro = fetcher.get_macro_data()
    print(macro)

    print("\n" + "="*60)
    print("📊 Custom Tickers Test")
    print("="*60)
    custom = fetcher.get_custom_tickers(["BTC-USD", "CL=F"])
    print(custom)

    print("\n" + "="*60)
    print("📊 Sector ETFs Test")
    print("="*60)
    sectors = fetcher.get_sector_etfs()
    print(sectors)
