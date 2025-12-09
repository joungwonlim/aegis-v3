"""
AEGIS v3.0 - KIS Auto Trading
한국투자증권 API 자동매매 시스템

Features:
- 자동 매수/매도
- 잔고 조회
- 주문 체결 확인
- 텔레그램 알림
"""
import os
import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import requests
from app.database import SessionLocal
from sqlalchemy import text

logger = logging.getLogger("KISTrader")


class KISTrader:
    """
    한국투자증권 자동매매

    API Docs: https://apiportal.koreainvestment.com/
    """

    def __init__(self):
        self.app_key = os.getenv("KIS_APP_KEY")
        self.app_secret = os.getenv("KIS_APP_SECRET")

        # 계좌번호 처리 (하이픈 제거)
        account_no = os.getenv("KIS_ACCOUNT_NO", "")
        self.account_no = account_no.replace("-", "").split("-")[0] if "-" in account_no else account_no[:8]
        self.account_code = os.getenv("KIS_ACCOUNT_CODE", "01")  # 종합계좌

        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.token = None
        self.db = SessionLocal()

        if not all([self.app_key, self.app_secret, self.account_no]):
            logger.warning("⚠️  KIS API 설정 누락 (APP_KEY, APP_SECRET, ACCOUNT_NO)")

        logger.info("✅ KISTrader initialized")

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    # ========================================
    # AUTHENTICATION
    # ========================================

    def get_access_token(self) -> Optional[str]:
        """액세스 토큰 발급"""

        if self.token:
            return self.token

        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                logger.error(f"❌ 토큰 발급 실패: {response.status_code}")
                logger.error(f"   응답: {response.text}")
                return None

            result = response.json()
            self.token = result.get("access_token")

            if self.token:
                logger.info("✅ 액세스 토큰 발급 완료")
            else:
                logger.error("❌ 토큰이 응답에 없음")

            return self.token

        except Exception as e:
            logger.error(f"❌ 토큰 발급 실패: {e}")
            return None

    # ========================================
    # ORDER EXECUTION
    # ========================================

    def buy(
        self,
        code: str,
        quantity: int,
        price: Optional[int] = None
    ) -> Dict:
        """
        매수 주문

        Args:
            code: 종목코드
            quantity: 수량
            price: 가격 (None이면 시장가)

        Returns:
            {
                "success": bool,
                "order_no": str,
                "message": str
            }
        """
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "토큰 발급 실패"}

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"

        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTC0802U",  # 현금 매수
            "custtype": "P"  # 개인
        }

        # 시장가 vs 지정가
        order_type = "01" if price else "01"  # 01: 시장가, 00: 지정가
        order_price = str(price) if price else "0"

        data = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_code,
            "PDNO": code,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": order_price
        }

        try:
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                logger.error(f"❌ 매수 실패: {response.status_code}")
                logger.error(f"   응답: {response.text}")
                return {
                    "success": False,
                    "message": f"API 오류: {response.status_code}"
                }

            result = response.json()

            if result.get("rt_cd") == "0":
                order_no = result.get("output", {}).get("ODNO", "")
                logger.info(f"✅ 매수 주문 성공: {code} {quantity}주 @ {price or '시장가'}")

                # DB에 주문 기록
                self._save_order(
                    code=code,
                    action="BUY",
                    quantity=quantity,
                    price=price,
                    order_no=order_no
                )

                return {
                    "success": True,
                    "order_no": order_no,
                    "message": "매수 주문 완료"
                }
            else:
                error_msg = result.get("msg1", "알 수 없는 오류")
                logger.error(f"❌ 매수 실패: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg
                }

        except Exception as e:
            logger.error(f"❌ 매수 실패: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    def sell(
        self,
        code: str,
        quantity: int,
        price: Optional[int] = None
    ) -> Dict:
        """
        매도 주문

        Args:
            code: 종목코드
            quantity: 수량
            price: 가격 (None이면 시장가)

        Returns:
            {
                "success": bool,
                "order_no": str,
                "message": str
            }
        """
        token = self.get_access_token()
        if not token:
            return {"success": False, "message": "토큰 발급 실패"}

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"

        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTC0801U",  # 현금 매도
            "custtype": "P"
        }

        order_type = "01" if price else "01"
        order_price = str(price) if price else "0"

        data = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_code,
            "PDNO": code,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": order_price
        }

        try:
            response = requests.post(url, headers=headers, json=data)

            if response.status_code != 200:
                logger.error(f"❌ 매도 실패: {response.status_code}")
                return {
                    "success": False,
                    "message": f"API 오류: {response.status_code}"
                }

            result = response.json()

            if result.get("rt_cd") == "0":
                order_no = result.get("output", {}).get("ODNO", "")
                logger.info(f"✅ 매도 주문 성공: {code} {quantity}주 @ {price or '시장가'}")

                self._save_order(
                    code=code,
                    action="SELL",
                    quantity=quantity,
                    price=price,
                    order_no=order_no
                )

                return {
                    "success": True,
                    "order_no": order_no,
                    "message": "매도 주문 완료"
                }
            else:
                error_msg = result.get("msg1", "알 수 없는 오류")
                logger.error(f"❌ 매도 실패: {error_msg}")
                return {
                    "success": False,
                    "message": error_msg
                }

        except Exception as e:
            logger.error(f"❌ 매도 실패: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    # ========================================
    # ACCOUNT INFO
    # ========================================

    def get_balance(self) -> Dict:
        """
        잔고 조회

        Returns:
            {
                "cash": float,
                "stocks": [
                    {
                        "code": str,
                        "name": str,
                        "quantity": int,
                        "avg_price": float,
                        "current_price": float,
                        "profit_rate": float
                    }
                ],
                "total_value": float
            }
        """
        token = self.get_access_token()
        if not token:
            return {"cash": 0, "stocks": [], "total_value": 0}

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"

        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "TTTC8434R"  # 잔고 조회
        }

        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_code,
            "AFHR_FLPR_YN": "N",  # 시간외 포함 여부
            "OFL_YN": "",
            "INQR_DVSN": "02",  # 조회구분
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }

        try:
            response = requests.get(url, headers=headers, params=params)

            if response.status_code != 200:
                logger.error(f"❌ 잔고 조회 실패: {response.status_code}")
                return {"cash": 0, "stocks": [], "total_value": 0}

            result = response.json()

            if result.get("rt_cd") != "0":
                logger.error(f"❌ 잔고 조회 실패: {result.get('msg1')}")
                return {"cash": 0, "stocks": [], "total_value": 0}

            # Parse holdings
            stocks = []
            for item in result.get("output1", []):
                if int(item.get("hldg_qty", 0)) > 0:
                    stocks.append({
                        "code": item.get("pdno"),
                        "name": item.get("prdt_name"),
                        "quantity": int(item.get("hldg_qty")),
                        "avg_price": float(item.get("pchs_avg_pric", 0)),
                        "current_price": float(item.get("prpr", 0)),
                        "profit_rate": float(item.get("evlu_pfls_rt", 0))
                    })

            # Cash
            output2 = result.get("output2", [{}])[0]
            cash = float(output2.get("dnca_tot_amt", 0))
            total_value = float(output2.get("tot_evlu_amt", 0))

            logger.info(f"✅ 잔고 조회 완료: 현금 {cash:,.0f}원, 보유 {len(stocks)}종목")

            return {
                "cash": cash,
                "stocks": stocks,
                "total_value": total_value
            }

        except Exception as e:
            logger.error(f"❌ 잔고 조회 실패: {e}")
            return {"cash": 0, "stocks": [], "total_value": 0}

    # ========================================
    # DATABASE
    # ========================================

    def _save_order(
        self,
        code: str,
        action: str,
        quantity: int,
        price: Optional[int],
        order_no: str
    ):
        """주문 기록 저장"""

        try:
            query = text("""
                INSERT INTO trade_orders
                (order_no, stock_code, action, quantity, price, status, created_at)
                VALUES
                (:order_no, :code, :action, :quantity, :price, 'PENDING', NOW())
            """)

            self.db.execute(query, {
                'order_no': order_no,
                'code': code,
                'action': action,
                'quantity': quantity,
                'price': price or 0
            })

            self.db.commit()
            logger.info(f"   💾 주문 기록 저장: {order_no}")

        except Exception as e:
            logger.error(f"   ❌ 주문 기록 저장 실패: {e}")
            self.db.rollback()


# ========================================
# TELEGRAM NOTIFIER
# ========================================

class TelegramNotifier:
    """텔레그램 알림"""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not self.bot_token or not self.chat_id:
            logger.warning("⚠️  텔레그램 설정 누락 (BOT_TOKEN, CHAT_ID)")

    def send(self, message: str) -> bool:
        """메시지 전송"""

        if not self.bot_token or not self.chat_id:
            logger.warning("   ⚠️  텔레그램 미설정, 알림 건너뜀")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        data = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        try:
            response = requests.post(url, json=data)

            if response.status_code == 200:
                logger.info("   📱 텔레그램 알림 전송 완료")
                return True
            else:
                logger.error(f"   ❌ 텔레그램 전송 실패: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"   ❌ 텔레그램 전송 실패: {e}")
            return False

    def notify_buy(self, code: str, name: str, quantity: int, price: int):
        """매수 알림"""
        message = f"""
🔵 *매수 주문*

종목: {name} ({code})
수량: {quantity:,}주
가격: {price:,}원
금액: {price * quantity:,}원

시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_sell(self, code: str, name: str, quantity: int, price: int, profit_rate: float):
        """매도 알림"""
        emoji = "🟢" if profit_rate > 0 else "🔴" if profit_rate < 0 else "⚪"
        message = f"""
{emoji} *매도 주문*

종목: {name} ({code})
수량: {quantity:,}주
가격: {price:,}원
금액: {price * quantity:,}원
수익률: {profit_rate:+.2f}%

시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)

    def notify_error(self, error: str):
        """에러 알림"""
        message = f"""
❌ *에러 발생*

{error}

시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send(message)


# ========================================
# MAIN
# ========================================

def main():
    """테스트"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    trader = KISTrader()
    notifier = TelegramNotifier()

    # 잔고 조회
    balance = trader.get_balance()

    print("\n" + "=" * 60)
    print("💼 계좌 잔고")
    print("=" * 60)
    print(f"현금: {balance['cash']:,.0f}원")
    print(f"총 자산: {balance['total_value']:,.0f}원")
    print(f"보유 종목: {len(balance['stocks'])}개")

    if balance['stocks']:
        print("\n[보유 종목]")
        for stock in balance['stocks']:
            print(f"  - {stock['name']} ({stock['code']}): "
                  f"{stock['quantity']:,}주 @ {stock['avg_price']:,.0f}원 "
                  f"({stock['profit_rate']:+.2f}%)")

    print("=" * 60)


if __name__ == "__main__":
    main()
