"""
AEGIS v3.0 - Theme & News Data Initialization
테마 및 뉴스 데이터 수집

실행: source venv/bin/activate && python scripts/init_theme_data.py
소요시간: 1~2분
"""
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# .env 파일 로드
load_dotenv()

from app.database import SessionLocal
from fetchers.naver_fetcher import NaverFetcher
from sqlalchemy import text

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("THEME_INIT")


class ThemeDataInitializer:
    """테마 & 뉴스 데이터 초기화 매니저"""

    def __init__(self):
        self.db = SessionLocal()
        self.fetcher = NaverFetcher()

    def __del__(self):
        """세션 종료"""
        if hasattr(self, 'db'):
            self.db.close()

    def run(self):
        """전체 초기화 프로세스"""
        logger.info("=" * 60)
        logger.info("📰 테마 & 뉴스 데이터 수집 시작")
        logger.info("=" * 60)
        logger.info("")

        try:
            # 1. 테마 테이블 생성
            self._create_tables()

            # 2. 핫한 테마 수집
            logger.info("1️⃣ 인기 테마 수집 중...")
            themes = self.fetcher.get_hot_themes(max_themes=20)

            if themes:
                logger.info(f"   🔥 {len(themes)}개 테마 수집됨")
                logger.info("")

                # 3. DB에 저장
                logger.info("2️⃣ DB에 저장 중...")
                saved_count = self._save_themes(themes)
                logger.info(f"   ✅ {saved_count}개 테마 저장 완료")
            else:
                logger.warning("   ⚠️  테마 데이터 없음")

            # 4. 주요 뉴스 수집
            logger.info("")
            logger.info("3️⃣ 주요 뉴스 수집 중...")
            news = self.fetcher.get_weekend_news(max_articles=20)
            logger.info("   📰 뉴스 수집 완료")

            # 5. 완료
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ 테마 & 뉴스 데이터 수집 완료!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ 수집 실패: {e}")
            import traceback
            traceback.print_exc()

    def _create_tables(self):
        """테마 테이블 생성"""
        create_theme_table = """
        CREATE TABLE IF NOT EXISTS market_themes (
            id SERIAL PRIMARY KEY,
            theme_name VARCHAR(100) NOT NULL,
            change_rate FLOAT,
            top_stocks TEXT,
            collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """

        create_news_table = """
        CREATE TABLE IF NOT EXISTS news_articles (
            id SERIAL PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            source VARCHAR(100),
            published_at TIMESTAMP WITH TIME ZONE,
            category VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """

        self.db.execute(text(create_theme_table))
        self.db.execute(text(create_news_table))
        self.db.commit()
        logger.info("✅ 테이블 생성/확인 완료")

    def _save_themes(self, themes):
        """테마 데이터 저장"""
        saved_count = 0

        for theme in themes:
            try:
                # 대표 종목들을 쉼표로 연결
                top_stocks = ", ".join(theme['stocks'])

                # INSERT
                query = text("""
                    INSERT INTO market_themes (theme_name, change_rate, top_stocks)
                    VALUES (:theme_name, :change_rate, :top_stocks)
                """)

                self.db.execute(query, {
                    'theme_name': theme['theme_name'],
                    'change_rate': theme['change_rate'],
                    'top_stocks': top_stocks
                })

                saved_count += 1

            except Exception as e:
                logger.debug(f"테마 저장 실패 ({theme['theme_name']}): {e}")
                continue

        self.db.commit()
        return saved_count


def main():
    """메인 함수"""
    try:
        initializer = ThemeDataInitializer()
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
