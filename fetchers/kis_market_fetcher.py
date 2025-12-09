"""
AEGIS v3.0 - KIS Market Data Fetcher
한국투자증권 API로 시장 데이터 수집
- 외국인 선물 누적 순매수
- 프로그램 비차익 순매수
- KOSPI200 베이시스
"""
import requests
import logging
from datetime import datetime, date
from typing import Dict, Optional
from app.config import settings

logger = logging.getLogger("KISMarketFetcher")


class KISMarketFetcher:
    """
    KIS API로 시장 수급 데이터 수집
    """

    def __init__(self):
        self.app_key = settings.kis_app_key
        self.app_secret = settings.kis_app_secret
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.token = None
        logger.info("✅ KISMarketFetcher initialized")

    def _get_access_token(self) -> str:
        """액세스 토큰 발급"""
        if self.token:
            return self.token

        # KIS 토큰 발급 API
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        try:
            response = requests.post(url, headers=headers, json=data)

            # 상세 에러 로깅
            if response.status_code != 200:
                logger.error(f"❌ KIS API 응답 오류: {response.status_code}")
                logger.error(f"   응답 내용: {response.text}")

                # 403 에러는 일반적으로 장 마감 후 발생
                if response.status_code == 403:
                    logger.warning("⚠️  KIS API 접근 거부 (장 마감 후이거나 API 키 문제)")
                    return None

                response.raise_for_status()

            result = response.json()
            self.token = result.get("access_token")

            if self.token:
                logger.info("✅ KIS 액세스 토큰 발급 완료")
            else:
                logger.error("❌ 토큰이 응답에 없음")

            return self.token

        except Exception as e:
            logger.error(f"❌ KIS 토큰 발급 실패: {e}")
            return None

    def get_foreign_futures_net(self) -> Optional[int]:
        """
        외국인 선물 누적 순매수 조회

        Returns:
            int: 외국인 선물 누적 순매수 (계약 수)
        """
        try:
            token = self._get_access_token()
            if not token:
                logger.warning("⚠️  토큰 없음, 외국인 선물 조회 건너뜀")
                return None

            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-investor-trend"
            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKIF03020100"  # 선물옵션 투자자별 매매동향
            }

            params = {
                "FID_COND_MRKT_DIV_CODE": "F",  # F: 선물
                "FID_INPUT_ISCD": "101"  # 101: KOSPI200 선물
            }

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("rt_cd") == "0":
                # 외국인 누적 순매수 추출
                output = data.get("output", [])
                if output and len(output) > 0:
                    foreign_net = int(output[0].get("frgn_ntby_qty", 0))
                    logger.info(f"📊 외국인 선물 누적 순매수: {foreign_net:,}계약")
                    return foreign_net

            logger.warning("⚠️  외국인 선물 데이터 없음")
            return None

        except Exception as e:
            logger.error(f"❌ 외국인 선물 조회 실패: {e}")
            return None

    def get_program_net(self) -> Optional[int]:
        """
        프로그램 비차익 순매수 조회

        Returns:
            int: 프로그램 비차익 순매수 (백만원)
        """
        try:
            token = self._get_access_token()
            if not token:
                logger.warning("⚠️  토큰 없음, 프로그램 매매 조회 건너뜀")
                return None

            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/program-trade-trend"
            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKST01010600"  # 프로그램 매매 동향
            }

            params = {
                "FID_COND_MRKT_DIV_CODE": "J",  # J: 전체
                "FID_INPUT_DATE_1": date.today().strftime("%Y%m%d")
            }

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("rt_cd") == "0":
                output = data.get("output", [])
                if output and len(output) > 0:
                    # 비차익 순매수 추출
                    non_arb_net = int(output[0].get("ntby_qty", 0))
                    logger.info(f"📊 프로그램 비차익 순매수: {non_arb_net:,}백만원")
                    return non_arb_net

            logger.warning("⚠️  프로그램 매매 데이터 없음")
            return None

        except Exception as e:
            logger.error(f"❌ 프로그램 매매 조회 실패: {e}")
            return None

    def get_kospi200_basis(self) -> Dict[str, Optional[float]]:
        """
        KOSPI200 베이시스 계산

        Returns:
            dict: {
                "spot": float,      # 현물 지수
                "futures": float,   # 선물 가격
                "basis": float      # 베이시스 (선물-현물)
            }
        """
        try:
            token = self._get_access_token()
            if not token:
                logger.warning("⚠️  토큰 없음, KOSPI200 베이시스 조회 건너뜀")
                return {
                    "spot": None,
                    "futures": None,
                    "basis": None
                }

            # 1. KOSPI200 현물 지수 조회
            spot_url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            spot_headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKUP03500100"  # KOSPI200 현물 시세
            }

            spot_params = {
                "FID_COND_MRKT_DIV_CODE": "U",  # U: 업종
                "FID_INPUT_ISCD": "0001"  # 0001: KOSPI200
            }

            spot_response = requests.get(spot_url, headers=spot_headers, params=spot_params)
            spot_response.raise_for_status()
            spot_data = spot_response.json()

            spot_index = None
            if spot_data.get("rt_cd") == "0":
                output = spot_data.get("output", {})
                spot_index = float(output.get("bstp_nmix_prpr", 0))  # 현재가

            # 2. KOSPI200 선물 가격 조회
            futures_url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            futures_headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKIF03010200"  # KOSPI200 선물 시세
            }

            futures_params = {
                "FID_COND_MRKT_DIV_CODE": "J",  # J: 선물
                "FID_INPUT_ISCD": "101"  # 101: KOSPI200 선물
            }

            futures_response = requests.get(futures_url, headers=futures_headers, params=futures_params)
            futures_response.raise_for_status()
            futures_data = futures_response.json()

            futures_price = None
            if futures_data.get("rt_cd") == "0":
                output = futures_data.get("output", {})
                futures_price = float(output.get("last_prpr", 0))  # 현재가

            # 3. 베이시스 계산
            basis = None
            if spot_index and futures_price:
                basis = futures_price - spot_index

            logger.info(f"📊 KOSPI200 현물: {spot_index}, 선물: {futures_price}, 베이시스: {basis}")

            return {
                "spot": spot_index,
                "futures": futures_price,
                "basis": basis
            }

        except Exception as e:
            logger.error(f"❌ KOSPI200 베이시스 조회 실패: {e}")
            return {
                "spot": None,
                "futures": None,
                "basis": None
            }

    def get_all_market_data(self) -> Dict:
        """
        전체 시장 데이터 조회

        Returns:
            dict: {
                "foreign_futures_net": int,
                "program_net": int,
                "kospi200_spot": float,
                "kospi200_futures": float,
                "basis": float
            }
        """
        logger.info("📊 KIS 시장 데이터 수집 시작...")

        result = {}

        # 1. 외국인 선물
        result["foreign_futures_net"] = self.get_foreign_futures_net()

        # 2. 프로그램 비차익
        result["program_net"] = self.get_program_net()

        # 3. KOSPI200 베이시스
        basis_data = self.get_kospi200_basis()
        result["kospi200_spot"] = basis_data.get("spot")
        result["kospi200_futures"] = basis_data.get("futures")
        result["basis"] = basis_data.get("basis")

        logger.info("✅ KIS 시장 데이터 수집 완료")
        return result


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)

    fetcher = KISMarketFetcher()

    print("\n" + "="*60)
    print("📊 KIS Market Data Test")
    print("="*60)

    data = fetcher.get_all_market_data()

    print("\n✅ 수집된 데이터:")
    for key, value in data.items():
        print(f"   {key}: {value}")
