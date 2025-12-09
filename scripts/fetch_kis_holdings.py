"""
KIS API에서 보유종목 및 주문가능금액 조회
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers.kis_client import KISClient
from app.database import SessionLocal
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_and_display_holdings():
    """KIS에서 보유종목 및 주문가능금액 조회"""

    # KIS Client 초기화
    kis = KISClient()

    print("\n" + "="*80)
    print("🔍 KIS API - 보유종목 및 주문가능금액 조회")
    print("="*80 + "\n")

    try:
        # 1. 통합 잔고 조회 (KRX + NXT)
        print("📊 보유종목 조회 중...")
        holdings = kis.get_combined_balance()

        if not holdings:
            print("❌ 보유종목이 없습니다.\n")
        else:
            print(f"✅ 보유종목: {len(holdings)}개\n")

            # 테이블 헤더
            print("┌" + "─"*10 + "┬" + "─"*20 + "┬" + "─"*10 + "┬" + "─"*12 + "┬" + "─"*12 + "┬" + "─"*12 + "┐")
            print("│ 종목코드 │       종목명         │   수량   │   평균단가   │    현재가    │   평가손익   │")
            print("├" + "─"*10 + "┼" + "─"*20 + "┼" + "─"*10 + "┼" + "─"*12 + "┼" + "─"*12 + "┼" + "─"*12 + "┤")

            total_valuation = 0
            total_profit = 0

            for stock in holdings:
                code = stock.get("pdno", "")
                name = stock.get("prdt_name", "")[:18]
                quantity = int(stock.get("hldg_qty", 0))
                avg_price = float(stock.get("pchs_avg_pric", 0))
                current_price = float(stock.get("prpr", 0))
                profit = float(stock.get("evlu_pfls_amt", 0))
                profit_rate = float(stock.get("evlu_pfls_rt", 0))

                valuation = quantity * current_price
                total_valuation += valuation
                total_profit += profit

                # 손익률 색상
                profit_sign = "+" if profit >= 0 else ""

                print(f"│ {code:8} │ {name:18} │ {quantity:8,} │ {avg_price:10,.0f} │ {current_price:10,.0f} │ {profit_sign}{profit:10,.0f} │")

            print("└" + "─"*10 + "┴" + "─"*20 + "┴" + "─"*10 + "┴" + "─"*12 + "┴" + "─"*12 + "┴" + "─"*12 + "┘")

            # 합계
            total_profit_rate = (total_profit / (total_valuation - total_profit) * 100) if (total_valuation - total_profit) > 0 else 0
            print(f"\n📈 총 평가액: ₩{total_valuation:,.0f}")
            print(f"{'📈' if total_profit >= 0 else '📉'} 총 평가손익: {'+' if total_profit >= 0 else ''}{total_profit:,.0f}원 ({'+' if total_profit_rate >= 0 else ''}{total_profit_rate:.2f}%)\n")

        # 2. 주문가능금액 조회
        print("\n💰 주문가능금액 조회 중...")

        # output2에서 예수금 정보 가져오기
        # get_balance 메서드는 output1만 반환하므로 직접 API 호출 필요
        access_token = kis.get_access_token()

        import requests
        url = f"{kis.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {access_token}",
            "appkey": kis.app_key,
            "appsecret": kis.app_secret,
            "tr_id": "TTTC8434R"  # KRX
        }
        params = {
            "CANO": kis.account_number,
            "ACNT_PRDT_CD": kis.account_code,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "N",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            output2 = data.get("output2", [{}])[0]

            # 예수금 및 주문가능금액
            deposit = float(output2.get("dnca_tot_amt", 0))  # 예수금총액
            orderable_cash = float(output2.get("nrcvb_buy_amt", 0))  # 미수없는매수금액
            total_asset = float(output2.get("tot_evlu_amt", 0))  # 총평가금액

            print(f"✅ 예수금총액: ₩{deposit:,.0f}")
            print(f"✅ 주문가능금액: ₩{orderable_cash:,.0f}")
            print(f"✅ 총평가금액: ₩{total_asset:,.0f}\n")

        else:
            logger.error(f"❌ 주문가능금액 조회 실패: {response.text}")

        print("="*80)
        print("✅ 조회 완료")
        print("="*80 + "\n")

    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    fetch_and_display_holdings()
