"""
AEGIS v3.0 - Naver News Fetcher
네이버 금융 뉴스 수집 (주말 헤드라인)
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("NaverFetcher")


class NaverFetcher:
    """
    네이버 금융 뉴스 수집 (웹 스크래핑)
    """

    BASE_URL = "https://finance.naver.com/news/news_list.naver"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        logger.info("✅ NaverFetcher initialized")

    def get_weekend_news(self, max_articles=10):
        """
        주말 주요 뉴스 헤드라인 수집

        Args:
            max_articles: 최대 수집 기사 수

        Returns:
            str: 뉴스 헤드라인 요약 텍스트
        """
        try:
            # 네이버 금융 뉴스 속보 페이지
            url = f"{self.BASE_URL}?mode=LSS2D&section_id=101&section_id2=258"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 뉴스 제목 추출
            headlines = []
            news_items = soup.select("dt.articleSubject a")

            for i, item in enumerate(news_items[:max_articles]):
                title = item.get_text(strip=True)
                headlines.append(f"{i+1}. {title}")

            if not headlines:
                logger.warning("⚠️  No news headlines found")
                return "No recent news available."

            logger.info(f"📰 Collected {len(headlines)} news headlines")
            return "\n".join(headlines)

        except Exception as e:
            logger.error(f"❌ Failed to fetch Naver news: {e}")
            return "Failed to fetch news."

    def get_market_briefing(self):
        """
        증시 브리핑 수집 (증권사 리포트 요약)

        Returns:
            str: 브리핑 텍스트
        """
        try:
            # 증권사 리포트 페이지
            url = f"{self.BASE_URL}?mode=LSS3D&section_id=101&section_id2=258&section_id3=401"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            briefings = []
            items = soup.select("dt.articleSubject a")

            for i, item in enumerate(items[:5]):
                title = item.get_text(strip=True)
                briefings.append(f"- {title}")

            if not briefings:
                return "No market briefing available."

            logger.info(f"📊 Collected {len(briefings)} briefings")
            return "\n".join(briefings)

        except Exception as e:
            logger.error(f"❌ Failed to fetch briefing: {e}")
            return "Failed to fetch briefing."

    def get_sector_news(self, sector="반도체"):
        """
        특정 섹터 뉴스 수집

        Args:
            sector: 검색할 섹터 키워드 (예: "반도체", "2차전지", "바이오")

        Returns:
            str: 섹터 관련 뉴스 헤드라인
        """
        try:
            # 네이버 금융 뉴스 검색
            search_url = "https://finance.naver.com/news/news_search.naver"
            params = {
                "q": sector,
                "x": 0,
                "y": 0
            }

            response = requests.get(search_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            headlines = []
            items = soup.select("dt.articleSubject a")

            for i, item in enumerate(items[:5]):
                title = item.get_text(strip=True)
                headlines.append(f"- {title}")

            if not headlines:
                return f"No news for sector '{sector}'."

            logger.info(f"📰 Collected {len(headlines)} news for '{sector}'")
            return f"[{sector} 관련 뉴스]\n" + "\n".join(headlines)

        except Exception as e:
            logger.error(f"❌ Failed to fetch sector news: {e}")
            return f"Failed to fetch news for '{sector}'."

    def get_hot_themes(self, max_themes=20):
        """
        네이버 금융 인기 테마 수집

        Returns:
            list: [{
                "theme_name": str,
                "change_rate": float,
                "stocks": list[str]  # 대표 종목들
            }]
        """
        try:
            # 네이버 금융 테마 페이지
            url = "https://finance.naver.com/sise/theme.naver"

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            themes = []
            theme_items = soup.select("table.type_1 tr")[2:]  # 헤더 제외

            for item in theme_items[:max_themes]:
                try:
                    cols = item.select("td")
                    if len(cols) < 4:
                        continue

                    # 테마명
                    theme_link = cols[0].select_one("a")
                    if not theme_link:
                        continue

                    theme_name = theme_link.get_text(strip=True)

                    # 등락률
                    change_text = cols[3].get_text(strip=True)
                    change_rate = float(change_text.replace("%", "").replace("+", "").replace(",", ""))

                    # 테마 상세 페이지에서 대표 종목 수집
                    theme_url = "https://finance.naver.com" + theme_link.get("href")
                    stocks = self._get_theme_stocks(theme_url)

                    themes.append({
                        "theme_name": theme_name,
                        "change_rate": change_rate,
                        "stocks": stocks
                    })

                except Exception as e:
                    logger.debug(f"테마 파싱 실패: {e}")
                    continue

            logger.info(f"🔥 Collected {len(themes)} hot themes")
            return themes

        except Exception as e:
            logger.error(f"❌ Failed to fetch themes: {e}")
            return []

    def _get_theme_stocks(self, theme_url, max_stocks=5):
        """테마별 대표 종목 수집"""
        try:
            response = requests.get(theme_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            stocks = []
            stock_items = soup.select("table.type_5 tr")[2:]  # 헤더 제외

            for item in stock_items[:max_stocks]:
                try:
                    cols = item.select("td")
                    if len(cols) < 2:
                        continue

                    stock_name = cols[1].get_text(strip=True)
                    if stock_name:
                        stocks.append(stock_name)

                except Exception:
                    continue

            return stocks

        except Exception as e:
            logger.debug(f"테마 종목 수집 실패: {e}")
            return []


if __name__ == "__main__":
    # 테스트 코드
    logging.basicConfig(level=logging.INFO)

    fetcher = NaverFetcher()

    print("\n" + "="*60)
    print("📰 Weekend News Test")
    print("="*60)
    news = fetcher.get_weekend_news()
    print(news)

    print("\n" + "="*60)
    print("📊 Market Briefing Test")
    print("="*60)
    briefing = fetcher.get_market_briefing()
    print(briefing)

    print("\n" + "="*60)
    print("📰 Sector News Test (반도체)")
    print("="*60)
    sector_news = fetcher.get_sector_news("반도체")
    print(sector_news)
