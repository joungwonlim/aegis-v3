"""
AEGIS v3.0 - DART Fetcher
재무 건전성 & 리스크 이벤트 감지

핵심 기능:
1. 재무 건전성: 매출액, 영업이익, 부채비율, ROE
2. 리스크 & 이벤트: CB, 유상증자, 횡령/배임 공시 감지
"""
import os
import logging
import OpenDartReader
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("AEGIS_DART")


class DartFetcher:
    """DART 전자공시 데이터 수집기"""

    def __init__(self):
        self.api_key = os.getenv("DART_API_KEY")
        if not self.api_key:
            logger.error("❌ DART_API_KEY is missing!")
            self.dart = None
        else:
            self.dart = OpenDartReader(self.api_key)
            logger.info("✅ DART API 초기화 완료")

        # 감시할 핵심 키워드
        self.risk_keywords = ["부도", "횡령", "배임", "소송", "거래정지", "관리종목", "상장폐지"]
        self.overhang_keywords = ["전환사채", "신주인수권", "유상증자", "감자"]
        self.good_keywords = ["무상증자", "수주", "공급계약", "최대주주변경", "공개매수"]

    def get_financial_summary(self, stock_code: str, year: int = None):
        """
        [재무 분석] 특정 종목의 핵심 재무 데이터를 가져와서 가공

        Args:
            stock_code: 6자리 종목코드 (예: 005930)
            year: 조회 연도 (기본값: 작년)

        Returns:
            dict: {
                "stock_code": str,
                "year": int,
                "revenue": float,          # 매출액
                "op_profit": float,        # 영업이익
                "net_income": float,       # 순이익
                "debt_ratio": float,       # 부채비율 (200% 넘으면 위험)
                "roe": float,              # ROE (높을수록 좋음)
                "op_margin": float,        # 영업이익률
                "is_deficit": bool         # 적자 여부
            }
        """
        if not self.dart:
            return None

        if not year:
            year = datetime.now().year - 1  # 작년 실적 기준

        try:
            # 사업보고서(11011) 기준 재무제표 조회
            df = self.dart.finstate(stock_code, year, reprt_code='11011')

            if df is None or df.empty:
                logger.warning(f"⚠️  {stock_code}: 재무 데이터 없음")
                return None

            # 필요한 데이터 추출 함수
            def get_value(account_nm):
                """계정과목명으로 금액 추출"""
                rows = df[df['account_nm'] == account_nm]
                if rows.empty:
                    return 0

                # 당기금액 추출 및 콤마 제거
                val = rows.iloc[0]['thstrm_amount']
                return float(val.replace(',', '')) if val else 0

            # 1. 핵심 지표 추출
            revenue = get_value('매출액')
            operating_profit = get_value('영업이익')
            net_income = get_value('당기순이익')
            total_assets = get_value('자산총계')
            total_liabilities = get_value('부채총계')
            total_equity = get_value('자본총계')

            # 2. 비율 계산 (퀀트 지표)
            debt_ratio = (total_liabilities / total_equity * 100) if total_equity > 0 else 9999
            profit_margin = (operating_profit / revenue * 100) if revenue > 0 else 0
            roe = (net_income / total_equity * 100) if total_equity > 0 else 0

            result = {
                "stock_code": stock_code,
                "year": year,
                "revenue": revenue,
                "op_profit": operating_profit,
                "net_income": net_income,
                "debt_ratio": round(debt_ratio, 2),
                "roe": round(roe, 2),
                "op_margin": round(profit_margin, 2),
                "is_deficit": operating_profit < 0
            }

            logger.info(f"📊 {stock_code} 재무 분석 완료: 부채비율 {debt_ratio:.2f}%, 영업이익 {operating_profit:,.0f}")
            return result

        except Exception as e:
            logger.error(f"❌ {stock_code} 재무 조회 실패: {e}")
            return None

    def check_recent_disclosures(self, stock_code: str, days: int = 7):
        """
        [이벤트 감지] 최근 N일간의 공시를 스캔하여 호재/악재 판별

        Args:
            stock_code: 종목코드
            days: 조회 기간 (기본 7일)

        Returns:
            list: [{
                "date": str,
                "title": str,
                "type": str,       # CRITICAL_RISK, OVERHANG_RISK, GOOD_NEWS
                "score": int,      # -100 ~ +100
                "link": str
            }]
        """
        if not self.dart:
            return []

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        try:
            # 최근 공시 목록 조회
            ds = self.dart.list(stock_code, start=start_date, end=end_date)

            if ds is None or ds.empty:
                return []

            analysis_results = []

            for _, row in ds.iterrows():
                title = row['report_nm']
                rcept_no = row['rcept_no']
                date = row['rcept_dt']

                signal_type = "NEUTRAL"
                score = 0

                # 1. 악재 필터 (Safety First)
                if any(k in title for k in self.risk_keywords):
                    signal_type = "CRITICAL_RISK"
                    score = -100
                elif any(k in title for k in self.overhang_keywords):
                    signal_type = "OVERHANG_RISK"
                    score = -50

                # 2. 호재 필터
                elif any(k in title for k in self.good_keywords):
                    if "유상증자" in title and "제3자" in title:
                        signal_type = "GOOD_NEWS"
                        score = 80
                    elif "공급계약" in title:
                        signal_type = "GOOD_NEWS"
                        score = 70
                    elif "무상증자" in title:
                        signal_type = "GOOD_NEWS"
                        score = 90

                if signal_type != "NEUTRAL":
                    analysis_results.append({
                        "date": date,
                        "title": title,
                        "type": signal_type,
                        "score": score,
                        "link": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                    })

            return analysis_results

        except Exception as e:
            logger.error(f"❌ {stock_code} 공시 조회 실패: {e}")
            return []


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)

    fetcher = DartFetcher()

    # 1. 재무 데이터 테스트 (삼성전자)
    print("\n" + "=" * 60)
    print("📊 재무 데이터 테스트")
    print("=" * 60)
    fin = fetcher.get_financial_summary("005930")  # 삼성전자
    if fin:
        print(f"종목코드: {fin['stock_code']}")
        print(f"연도: {fin['year']}")
        print(f"매출액: {fin['revenue']:,.0f}원")
        print(f"영업이익: {fin['op_profit']:,.0f}원")
        print(f"부채비율: {fin['debt_ratio']}%")
        print(f"ROE: {fin['roe']}%")
        print(f"영업이익률: {fin['op_margin']}%")
        print(f"적자 여부: {fin['is_deficit']}")

    # 2. 공시 스캔 테스트
    print("\n" + "=" * 60)
    print("📰 최근 중요 공시")
    print("=" * 60)
    news = fetcher.check_recent_disclosures("005930", days=30)
    if news:
        for n in news:
            print(f"\n날짜: {n['date']}")
            print(f"제목: {n['title']}")
            print(f"타입: {n['type']} (점수: {n['score']})")
            print(f"링크: {n['link']}")
    else:
        print("최근 주요 공시 없음")
