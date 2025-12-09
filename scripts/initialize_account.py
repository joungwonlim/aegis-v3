"""
AEGIS v3.0 - Account Initialization
시스템 시작 시 필수 실행: KIS API → DB 동기화

실행 순서:
1. Access Token 발급
2. 잔고 & 보유종목 조회 → DB 동기화
3. 미체결 내역 확인
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers.kis_client import KISClient
from app.database import SessionLocal
from sqlalchemy import text
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_account():
    """
    [시스템 시작 시 필수 실행]
    1. 토큰 확인
    2. 잔고 및 보유종목 싱크 (Sync)
    3. 미체결 내역 확인
    """
    logger.info("🚀 System Initialization Started...")
    logger.info("="*80)

    db = SessionLocal()
    kis = KISClient()

    try:
        # ========================================
        # 1. Access Token 발급
        # ========================================
        logger.info("\n[Step 1] 🔑 Access Token 확인...")

        token = kis.get_access_token()
        if not token:
            logger.critical("⛔ 토큰 발급 실패! 시스템 종료.")
            return False

        logger.info("✅ Access Token 준비 완료")

        # ========================================
        # 2. 잔고 & 보유종목 동기화
        # ========================================
        logger.info("\n[Step 2] 💼 Portfolio Sync (KIS → DB)...")

        # 2-1. 보유종목 조회
        holdings = kis.get_combined_balance()
        logger.info(f"📊 KIS 보유종목: {len(holdings)}개")

        # 2-2. 예수금 정보 조회
        import requests
        url = f"{kis.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": kis.app_key,
            "appsecret": kis.app_secret,
            "tr_id": "TTTC8434R"
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
        if response.status_code != 200:
            logger.error(f"❌ 계좌 정보 조회 실패: {response.text}")
            return False

        data = response.json()
        output2 = data.get("output2", [{}])[0]

        deposit = float(output2.get("dnca_tot_amt", 0))  # 예수금총액
        orderable_cash = float(output2.get("nrcvb_buy_amt", 0))  # 주문가능금액
        total_asset = float(output2.get("tot_evlu_amt", 0))  # 총평가금액
        stock_value = float(output2.get("scts_evlu_amt", 0))  # 주식평가금액
        total_profit = float(output2.get("evlu_pfls_smtl_amt", 0))  # 평가손익

        logger.info(f"💰 예수금총액: ₩{deposit:,.0f}")
        logger.info(f"💰 주문가능금액: ₩{orderable_cash:,.0f}")
        logger.info(f"💰 총평가금액: ₩{total_asset:,.0f}")
        logger.info(f"📊 주식평가금액: ₩{stock_value:,.0f}")
        logger.info(f"📈 평가손익: ₩{total_profit:,.0f}")

        # 2-3. DB 동기화 - stock_assets 테이블 초기화
        logger.info("\n💾 DB 동기화 시작...")

        # 기존 데이터 삭제
        db.execute(text("DELETE FROM stock_assets"))
        logger.info("🗑️  기존 stock_assets 데이터 삭제")

        # 새 데이터 삽입
        insert_count = 0
        for stock in holdings:
            code = stock.get("pdno", "")
            name = stock.get("prdt_name", "")
            quantity = int(stock.get("hldg_qty", 0))
            avg_price = float(stock.get("pchs_avg_pric", 0))
            current_price = float(stock.get("prpr", 0))

            # 수량이 0보다 큰 것만 저장
            if quantity > 0:
                insert_query = text("""
                    INSERT INTO stock_assets (stock_code, quantity, avg_price, updated_at)
                    VALUES (:code, :quantity, :avg_price, :updated_at)
                """)

                db.execute(insert_query, {
                    'code': code,
                    'quantity': quantity,
                    'avg_price': avg_price,
                    'updated_at': datetime.now()
                })
                insert_count += 1
                logger.info(f"   ✅ {name} ({code}): {quantity}주 @ {avg_price:,.0f}원")

        db.commit()
        logger.info(f"✅ stock_assets 테이블 동기화 완료: {insert_count}개 종목")

        # 2-4. portfolio_summary 테이블 업데이트
        logger.info("\n💾 portfolio_summary 업데이트...")

        # 기존 데이터 삭제 후 신규 삽입
        db.execute(text("DELETE FROM portfolio_summary"))

        summary_query = text("""
            INSERT INTO portfolio_summary (cash, total_value, updated_at)
            VALUES (:cash, :total_value, :updated_at)
        """)

        db.execute(summary_query, {
            'cash': deposit,
            'total_value': total_asset,
            'updated_at': datetime.now()
        })
        db.commit()
        logger.info("✅ portfolio_summary 업데이트 완료")

        # ========================================
        # 3. 미체결 내역 확인
        # ========================================
        logger.info("\n[Step 3] 🔍 미체결 내역 확인...")

        unfilled_url = f"{kis.base_url}/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl"
        unfilled_headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": kis.app_key,
            "appsecret": kis.app_secret,
            "tr_id": "TTTC8036R"
        }
        unfilled_params = {
            "CANO": kis.account_number,
            "ACNT_PRDT_CD": kis.account_code,
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
            "INQR_DVSN_1": "0",
            "INQR_DVSN_2": "0"
        }

        unfilled_response = requests.get(unfilled_url, headers=unfilled_headers, params=unfilled_params)

        if unfilled_response.status_code == 200:
            unfilled_data = unfilled_response.json()
            unfilled_orders = unfilled_data.get("output", [])

            # 실제 미체결만 필터링 (정정취소가능수량 > 0)
            actual_unfilled = [order for order in unfilled_orders if int(order.get("psbl_qty", 0)) > 0]

            if actual_unfilled:
                logger.warning(f"⚠️  미체결 주문 {len(actual_unfilled)}건 존재!")
                for order in actual_unfilled:
                    logger.warning(f"   - {order.get('prdt_name')} ({order.get('pdno')}): {order.get('psbl_qty')}주 @ {order.get('ord_unpr')}원")
            else:
                logger.info("✅ 미체결 주문 없음. 클린 상태.")
        else:
            logger.error(f"❌ 미체결 조회 실패: {unfilled_response.text}")

        # ========================================
        # 완료
        # ========================================
        logger.info("\n" + "="*80)
        logger.info("✨ Initialization Complete. Ready to Trade.")
        logger.info("="*80)

        # 최종 요약
        print("\n" + "="*80)
        print("📋 초기화 완료 요약")
        print("="*80)
        print(f"💰 예수금: ₩{deposit:,.0f}")
        print(f"💰 주문가능금액: ₩{orderable_cash:,.0f}")
        print(f"📊 보유종목: {insert_count}개")
        print(f"📈 총평가금액: ₩{total_asset:,.0f}")
        print(f"📈 평가손익: ₩{total_profit:,.0f}")
        print(f"🔍 미체결: {len(actual_unfilled) if unfilled_response.status_code == 200 else '조회실패'}건")
        print("="*80 + "\n")

        return True

    except Exception as e:
        logger.error(f"❌ Initialization Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    success = initialize_account()

    if success:
        print("✅ 시스템 초기화 성공! AEGIS 준비 완료.")
    else:
        print("❌ 시스템 초기화 실패. 로그를 확인하세요.")
        sys.exit(1)
