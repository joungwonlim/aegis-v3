"""
AEGIS v3.0 - KIS API Client (WebSocket + REST)
한국투자증권 API 통합 클라이언트 (NXT 지원)
"""
import asyncio
import websockets
import json
import requests
import os
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class KISClient:
    """KIS API Client (WebSocket + REST)"""

    # 토큰 캐시 파일 경로
    TOKEN_CACHE_FILE = Path(__file__).parent.parent / ".cache" / "kis_token.json"

    # TR_ID 매핑 (KRX vs NXT)
    TR_ID_MAP = {
        "KRX": {
            "buy": "TTTC0802U",
            "sell": "TTTC0801U",
            "balance": "TTTC8434R",
            "unfilled": "TTTC8036R",
        },
        "NXT": {
            "buy": "TTTN0802U",
            "sell": "TTTN0801U",
            "balance": "TTTN8434R",
            "unfilled": "TTTN8036R",
        }
    }

    def __init__(self):
        self.app_key = settings.kis_app_key
        self.app_secret = settings.kis_app_secret
        self.account_number = settings.kis_cano  # 계좌번호 (8자리)
        self.account_code = settings.kis_acnt_prdt_cd  # 계좌상품코드 (2자리)
        self.ws_approval_key = settings.kis_ws_approval_key

        # REST API Base URL
        self.base_url = "https://openapi.koreainvestment.com:9443"

        # WebSocket URL (NXT)
        self.ws_url = "ws://ops.koreainvestment.com:21000"

        # 토큰 캐싱
        self.access_token = None
        self.token_expires_at = None  # 토큰 만료 시간

        self.ws_connection = None

    def _load_token_from_cache(self) -> bool:
        """
        파일에서 토큰 캐시 로드

        Returns:
            True if valid token loaded, False otherwise
        """
        try:
            if not self.TOKEN_CACHE_FILE.exists():
                return False

            with open(self.TOKEN_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)

            expires_at = datetime.fromisoformat(cache_data['expires_at'])

            # 만료 확인
            if datetime.now() < expires_at:
                self.access_token = cache_data['access_token']
                self.token_expires_at = expires_at
                logger.info(f"✅ 파일 캐시에서 토큰 로드 (만료: {expires_at.strftime('%Y-%m-%d %H:%M:%S')})")
                return True

            return False

        except Exception as e:
            logger.warning(f"⚠️  토큰 캐시 로드 실패: {e}")
            return False

    def _save_token_to_cache(self):
        """토큰을 파일에 저장"""
        try:
            # .cache 디렉토리 생성
            self.TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

            cache_data = {
                'access_token': self.access_token,
                'expires_at': self.token_expires_at.isoformat()
            }

            with open(self.TOKEN_CACHE_FILE, 'w') as f:
                json.dump(cache_data, f, indent=2)

            logger.info("✅ 토큰 파일 캐시 저장 완료")

        except Exception as e:
            logger.warning(f"⚠️  토큰 캐시 저장 실패: {e}")

    def get_access_token(self) -> str:
        """
        REST API 접근 토큰 발급 (파일 기반 캐싱)

        1. 파일 캐시 확인 → 유효하면 재사용
        2. 메모리 캐시 확인 → 유효하면 재사용
        3. 없거나 만료됨 → 새로 발급 → 파일에 저장

        Returns:
            access_token
        """
        # 1. 파일 캐시에서 로드 시도
        if self._load_token_from_cache():
            return self.access_token

        # 2. 메모리 캐시 확인
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                logger.info("✅ 메모리 캐시에서 토큰 재사용")
                return self.access_token

        # 3. 새 토큰 발급
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data["access_token"]

            # 만료 시간 계산 (기본 24시간)
            expires_in = token_data.get("expires_in", 86400)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)

            logger.info(f"✅ 새 토큰 발급 완료 (만료: {self.token_expires_at.strftime('%Y-%m-%d %H:%M:%S')})")

            # 파일에 저장
            self._save_token_to_cache()

            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {response.text}")

    def get_current_price(self, stock_code: str) -> Dict:
        """
        현재가 조회 (REST API)

        Args:
            stock_code: 종목코드

        Returns:
            현재가 정보
        """
        if not self.access_token:
            self.get_access_token()

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010100"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to get current price: {response.text}")

    def _get_approval_key(self):
        """
        WebSocket 접속용 Approval Key 자동 발급 (임시 키)
        매번 접속 시 새로 발급받아야 함 (유효기간 존재)
        """
        url = f"{self.base_url}/oauth2/Approval"
        headers = {
            "content-type": "application/json; charset=utf-8"
        }
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }

        try:
            response = requests.post(url, headers=headers, json=body)
            if response.status_code == 200:
                data = response.json()
                self.ws_approval_key = data.get("approval_key")
                print(f"✅ WebSocket Approval Key 자동 발급 성공 (유효기간: {data.get('expires_in')}초)")
                return True
            else:
                print(f"❌ Approval Key 발급 실패: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Approval Key 발급 오류: {e}")
            return False

    async def connect_websocket(self):
        """
        WebSocket 연결 (실시간 시세)
        접속 시마다 Approval Key 자동 발급
        """
        # 1. Approval Key 자동 발급 (임시 키, 매번 새로 받음)
        if not self.ws_approval_key or self.ws_approval_key == "your_websocket_approval_key":
            print("🔑 WebSocket Approval Key 자동 발급 중...")
            if not self._get_approval_key():
                print("⚠️  Approval Key 발급 실패. REST API만 사용합니다.")
                return False

        try:
            self.ws_connection = await websockets.connect(
                self.ws_url,
                ping_interval=20,
                ping_timeout=10
            )
            print("✅ KIS WebSocket Connected")

            # 승인 메시지 전송
            approval_msg = {
                "header": {
                    "approval_key": self.ws_approval_key,
                    "custtype": "P",
                    "tr_type": "1",
                    "content-type": "utf-8"
                }
            }
            await self.ws_connection.send(json.dumps(approval_msg))

        except Exception as e:
            print(f"❌ WebSocket connection failed: {e}")

    async def subscribe_realtime_price(self, stock_code: str):
        """
        실시간 시세 구독

        Args:
            stock_code: 종목코드
        """
        if not self.ws_connection:
            await self.connect_websocket()

        # 체결가 구독 (H0STCNT0)
        subscribe_msg = {
            "header": {
                "tr_id": "H0STCNT0",
                "tr_key": stock_code
            }
        }
        await self.ws_connection.send(json.dumps(subscribe_msg))
        print(f"📡 Subscribed to {stock_code}")

    async def listen_realtime_data(self, callback):
        """
        실시간 데이터 수신

        Args:
            callback: 데이터 처리 콜백 함수
        """
        if not self.ws_connection:
            raise Exception("WebSocket not connected")

        try:
            async for message in self.ws_connection:
                data = json.loads(message)
                await callback(data)
        except websockets.exceptions.ConnectionClosed:
            print("❌ WebSocket connection closed")
        except Exception as e:
            print(f"❌ Error in WebSocket listener: {e}")

    def buy_order(
        self,
        stock_code: str,
        quantity: int,
        price: int = 0,
        market: str = "KRX"
    ) -> Dict:
        """
        매수 주문 (REST API)

        Args:
            stock_code: 종목코드
            quantity: 수량
            price: 가격 (0이면 시장가, NXT는 시장가 불가)
            market: KRX or NXT

        Returns:
            주문 결과
        """
        if not self.access_token:
            self.get_access_token()

        # NXT 시장가 차단
        if market == "NXT" and price == 0:
            logger.warning(f"NXT는 시장가 불가 → 현재 호가로 주문")
            price = self._get_ask_price_1(stock_code)

        # TR_ID 선택
        tr_id = self.TR_ID_MAP[market]["buy"]

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }
        data = {
            "CANO": self.account_number,
            "ACNT_PRDT_CD": self.account_code,
            "PDNO": stock_code,
            "ORD_DVSN": "01" if price > 0 else "00",  # 01: 지정가, 00: 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(int(price)) if price > 0 else ""
        }

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        if response.status_code == 200:
            logger.info(f"✅ Buy order placed: {stock_code} {quantity}주 @ {price:,}원 ({market})")
        else:
            logger.error(f"❌ Buy order failed: {result}")

        return result

    def sell_order(
        self,
        stock_code: str,
        quantity: int,
        price: int = 0,
        market: str = "KRX"
    ) -> Dict:
        """
        매도 주문 (REST API)

        Args:
            stock_code: 종목코드
            quantity: 수량
            price: 가격 (0이면 시장가, NXT는 시장가 불가)
            market: KRX or NXT

        Returns:
            주문 결과
        """
        if not self.access_token:
            self.get_access_token()

        # NXT 시장가 차단
        if market == "NXT" and price == 0:
            logger.warning(f"NXT는 시장가 불가 → 현재 호가로 주문")
            price = self._get_bid_price_1(stock_code)

        # TR_ID 선택
        tr_id = self.TR_ID_MAP[market]["sell"]

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }
        data = {
            "CANO": self.account_number,
            "ACNT_PRDT_CD": self.account_code,
            "PDNO": stock_code,
            "ORD_DVSN": "01" if price > 0 else "00",
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(int(price)) if price > 0 else ""
        }

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        if response.status_code == 200:
            logger.info(f"✅ Sell order placed: {stock_code} {quantity}주 @ {price:,}원 ({market})")
        else:
            logger.error(f"❌ Sell order failed: {result}")

        return result

    def get_balance(self, market: str = "KRX") -> List[dict]:
        """
        잔고 조회 (REST API)

        Args:
            market: KRX or NXT

        Returns:
            잔고 리스트
        """
        if not self.access_token:
            self.get_access_token()

        tr_id = self.TR_ID_MAP[market]["balance"]

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id
        }
        params = {
            "CANO": self.account_number,
            "ACNT_PRDT_CD": self.account_code,
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
            balance_list = data.get("output1", [])
            logger.info(f"✅ Balance fetched: {len(balance_list)} stocks ({market})")
            return balance_list
        else:
            logger.error(f"❌ Balance fetch failed: {response.text}")
            raise Exception(f"Failed to get balance: {response.text}")

    def get_combined_balance(self) -> List[dict]:
        """
        통합 잔고 조회 (KRX + NXT)

        Returns:
            병합된 잔고 리스트
        """
        try:
            krx_balance = self.get_balance("KRX")
        except Exception as e:
            logger.warning(f"KRX balance fetch failed: {e}")
            krx_balance = []

        try:
            nxt_balance = self.get_balance("NXT")
        except Exception as e:
            logger.warning(f"NXT balance fetch failed: {e}")
            nxt_balance = []

        # 동일 종목 병합
        combined = {}
        for item in krx_balance + nxt_balance:
            code = item["pdno"]
            if code in combined:
                # 수량 합산, 평균단가 재계산
                combined[code] = self._merge_positions(combined[code], item)
            else:
                combined[code] = item

        result = list(combined.values())
        logger.info(f"✅ Combined balance: {len(result)} unique stocks")
        return result

    def _merge_positions(self, pos1: dict, pos2: dict) -> dict:
        """
        동일 종목의 포지션 병합

        Args:
            pos1: 첫 번째 포지션
            pos2: 두 번째 포지션

        Returns:
            병합된 포지션
        """
        qty1 = int(pos1.get("hldg_qty", 0))
        qty2 = int(pos2.get("hldg_qty", 0))
        price1 = float(pos1.get("pchs_avg_pric", 0))
        price2 = float(pos2.get("pchs_avg_pric", 0))

        total_qty = qty1 + qty2
        if total_qty > 0:
            avg_price = (qty1 * price1 + qty2 * price2) / total_qty
        else:
            avg_price = 0

        merged = pos1.copy()
        merged["hldg_qty"] = str(total_qty)
        merged["pchs_avg_pric"] = str(round(avg_price, 2))

        return merged

    def _get_ask_price_1(self, stock_code: str) -> int:
        """
        현재 매도1호가 조회 (NXT 시장가 대체용)

        Args:
            stock_code: 종목코드

        Returns:
            매도1호가
        """
        try:
            price_info = self.get_current_price(stock_code)
            ask_price = int(price_info.get("output", {}).get("askp1", 0))
            return ask_price if ask_price > 0 else int(price_info.get("output", {}).get("stck_prpr", 0))
        except Exception as e:
            logger.error(f"❌ Failed to get ask price: {e}")
            return 0

    def _get_bid_price_1(self, stock_code: str) -> int:
        """
        현재 매수1호가 조회 (NXT 시장가 대체용)

        Args:
            stock_code: 종목코드

        Returns:
            매수1호가
        """
        try:
            price_info = self.get_current_price(stock_code)
            bid_price = int(price_info.get("output", {}).get("bidp1", 0))
            return bid_price if bid_price > 0 else int(price_info.get("output", {}).get("stck_prpr", 0))
        except Exception as e:
            logger.error(f"❌ Failed to get bid price: {e}")
            return 0

    def get_top_gainers(self, limit: int = 50) -> List[dict]:
        """
        등락률 상위 조회 (REST API)

        Args:
            limit: 조회 개수

        Returns:
            등락률 상위 종목 리스트
        """
        if not self.access_token:
            self.get_access_token()

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/volume-rank"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010100"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20171",  # 등락률 상위
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "111111111",
            "FID_TRGT_EXLS_CLS_CODE": "000000",
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": "",
            "FID_INPUT_DATE_1": ""
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            stocks = data.get("output", [])[:limit]
            logger.info(f"✅ Top gainers: {len(stocks)} stocks")
            return stocks
        else:
            logger.error(f"❌ Failed to get top gainers: {response.text}")
            return []

    def get_top_volume(self, limit: int = 50) -> List[dict]:
        """
        거래량 상위 조회 (REST API)

        Args:
            limit: 조회 개수

        Returns:
            거래량 상위 종목 리스트
        """
        if not self.access_token:
            self.get_access_token()

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/volume-rank"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010400"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20172",  # 거래량 상위
            "FID_INPUT_ISCD": "0000",
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": "0",
            "FID_TRGT_CLS_CODE": "111111111",
            "FID_TRGT_EXLS_CLS_CODE": "000000",
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": "",
            "FID_INPUT_DATE_1": ""
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            stocks = data.get("output", [])[:limit]
            logger.info(f"✅ Top volume: {len(stocks)} stocks")
            return stocks
        else:
            logger.error(f"❌ Failed to get top volume: {response.text}")
            return []

    async def subscribe_execution_notice(self):
        """
        체결 통보 구독 (H0STCNI0)

        내 주문 체결 시 즉시 알림 (10~50ms)
        """
        if not self.ws_connection:
            await self.connect_websocket()

        if not self.ws_connection:
            logger.warning("⚠️  WebSocket not available, execution notice disabled")
            return

        # 체결 통보 구독
        subscribe_msg = {
            "header": {
                "approval_key": self.ws_approval_key,
                "custtype": "P",
                "tr_type": "1",
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "tr_id": "H0STCNI0",
                    "tr_key": self.account_number  # HTS ID 대신 account_number 사용
                }
            }
        }

        await self.ws_connection.send(json.dumps(subscribe_msg))
        logger.info("📡 Subscribed to execution notice (H0STCNI0)")

    async def close(self):
        """WebSocket 연결 종료"""
        if self.ws_connection:
            await self.ws_connection.close()
            logger.info("🛑 KIS WebSocket Closed")


# Singleton Instance
kis_client = KISClient()
