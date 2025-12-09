"""
AEGIS v3.0 - Margin Balance Fetcher
신용융자 잔고 데이터 수집 (네이버 금융)
"""
import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, Optional

logger = logging.getLogger("MarginFetcher")


class MarginBalanceFetcher:
    """
    신용융자 잔고 데이터 수집
    출처: 네이버 금융
    """

    BASE_URL = "https://finance.naver.com"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        logger.info("✅ MarginBalanceFetcher initialized")

    def get_margin_balance(self, stock_code: str) -> Optional[Dict]:
        """
        종목별 신용융자 잔고 조회

        Args:
            stock_code: 종목 코드

        Returns:
            dict: {
                "stock_code": str,
                "credit_balance": int,      # 신용잔고 (주)
                "credit_balance_rate": float,  # 신용잔고율 (%)
                "margin_balance": int,      # 융자잔고 (원)
                "margin_balance_rate": float   # 융자잔고율 (%)
            }
        """
        try:
            # 네이버 금융 종목 페이지
            url = f"{self.BASE_URL}/item/main.naver?code={stock_code}"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 신용융자 정보 파싱
            # (실제 네이버 금융 HTML 구조에 맞게 수정 필요)
            result = {
                "stock_code": stock_code,
                "credit_balance": 0,
                "credit_balance_rate": 0.0,
                "margin_balance": 0,
                "margin_balance_rate": 0.0
            }

            # TODO: 실제 파싱 로직 구현
            # 네이버 금융의 신용융자 정보는 Ajax로 로드되므로
            # API 엔드포인트를 직접 호출하거나 Selenium 사용 필요

            logger.info(f"📊 {stock_code} 신용융자 데이터 조회 완료")
            return result

        except Exception as e:
            logger.error(f"❌ {stock_code} 신용융자 조회 실패: {e}")
            return None

    def get_top_margin_stocks(self, limit=20) -> list:
        """
        신용잔고율 상위 종목 조회

        Args:
            limit: 조회할 종목 수

        Returns:
            list: [
                {
                    "stock_code": str,
                    "stock_name": str,
                    "credit_balance_rate": float
                },
                ...
            ]
        """
        try:
            # 네이버 금융 신용융자 상위 종목 페이지
            url = f"{self.BASE_URL}/sise/sise_credit_rate.naver"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            stocks = []

            # 테이블 파싱
            table = soup.select_one("table.type_1")
            if not table:
                logger.warning("⚠️  신용융자 테이블 없음")
                return []

            rows = table.select("tr")[2:]  # 헤더 제외

            for row in rows[:limit]:
                try:
                    cols = row.select("td")
                    if len(cols) < 2:
                        continue

                    # 종목명 & 코드
                    name_link = cols[1].select_one("a")
                    if not name_link:
                        continue

                    stock_name = name_link.get_text(strip=True)
                    href = name_link.get("href", "")
                    stock_code = href.split("code=")[-1] if "code=" in href else ""

                    # 신용잔고율
                    if len(cols) >= 5:
                        rate_text = cols[4].get_text(strip=True).replace("%", "").replace(",", "")
                        credit_rate = float(rate_text) if rate_text else 0.0

                        stocks.append({
                            "stock_code": stock_code,
                            "stock_name": stock_name,
                            "credit_balance_rate": credit_rate
                        })

                except Exception as e:
                    logger.debug(f"   ⚠️  행 파싱 실패: {e}")
                    continue

            logger.info(f"📰 신용잔고율 상위 {len(stocks)}개 종목 조회 완료")
            return stocks

        except Exception as e:
            logger.error(f"❌ 신용융자 상위 종목 조회 실패: {e}")
            return []


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)

    fetcher = MarginBalanceFetcher()

    print("\n" + "="*60)
    print("📊 Margin Balance Test")
    print("="*60)

    # 상위 종목 조회
    top_stocks = fetcher.get_top_margin_stocks(10)

    print("\n✅ 신용잔고율 상위 종목:")
    for stock in top_stocks:
        print(f"   {stock['stock_name']} ({stock['stock_code']}): {stock['credit_balance_rate']}%")
