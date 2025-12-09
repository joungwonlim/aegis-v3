# AEGIS v3.1 데이터 소싱 문서

## 1. 한국투자증권 KIS API

### 개요
한국투자증권의 KIS API를 통해 실시간 시세, 포트폴리오 관리, 주문 체결 기능을 제공합니다.

### API 엔드포인트
```
# REST API
기본 URL: https://openapi.koreainvestment.com:9443

# 주요 엔드포인트
1. 시세 조회: /uapi/domestic-stock/v1/quotations/inquire-price
2. 잔고 조회: /uapi/domestic-stock/v1/trading/inquire-balance
3. 주문: /uapi/domestic-stock/v1/trading/order-cash
4. 체결 조회: /uapi/domestic-stock/v1/trading/inquire-ccnl

# WebSocket
실시간 시세: ws://ops.koreainvestment.com:21000
실시간 체결: ws://ops.koreainvestment.com:31000
```

### 인증 방법
```python
import requests
import json
from datetime import datetime

class KISAuth:
    def __init__(self, appkey, appsecret):
        self.appkey = appkey
        self.appsecret = appsecret
        self.base_url = "https://openapi.koreainvestment.com:9443"
        
    def get_access_token(self):
        """접근 토큰 발급"""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "appsecret": self.appsecret
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(body))
        return response.json()["access_token"]
```

### Rate Limit
- REST API: 분당 200회, 초당 10회
- WebSocket: 계정당 최대 100개 종목 구독
- 일일 주문: 계좌별 제한 있음 (VIP 등급에 따라 상이)

### Python 수집 코드 예시
```python
import websocket
import json
import threading
from kis_auth import KISAuth

class KISRealtimeData:
    def __init__(self, auth):
        self.auth = auth
        self.ws = None
        self.is_connected = False
        
    def connect_websocket(self, tr_id="H0STCNT0", tr_key="005930"):
        """WebSocket 연결 및 실시간 데이터 수신"""
        ws_url = "ws://ops.koreainvestment.com:21000"
        
        def on_message(ws, message):
            data = json.loads(message)
            # 데이터 처리 로직
            self.process_realtime_data(data)
            
        def on_error(ws, error):
            print(f"WebSocket Error: {error}")
            self.reconnect()
            
        def on_close(ws, close_status_code, close_msg):
            print("WebSocket closed")
            self.is_connected = False
            
        def on_open(ws):
            # 인증 및 구독 요청
            auth_msg = {
                "header": {
                    "approval_key": self.auth.get_access_token(),
                    "custtype": "P",
                    "tr_type": "1",
                    "content-type": "utf-8"
                },
                "body": {
                    "input": {
                        "tr_id": tr_id,
                        "tr_key": tr_key
                    }
                }
            }
            ws.send(json.dumps(auth_msg))
            self.is_connected = True
            
        self.ws = websocket.WebSocketApp(ws_url,
                                        on_open=on_open,
                                        on_message=on_message,
                                        on_error=on_error,
                                        on_close=on_close)
        
        # WebSocket 스레드 실행
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()
    
    def get_daily_price(self, stock_code, period="D"):
        """일별 시세 조회"""
        url = f"{self.auth.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.auth.get_access_token()}",
            "appkey": self.auth.appkey,
            "appsecret": self.auth.appsecret,
            "tr_id": "FHKST03010100"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": stock_code,
            "FID_PERIOD_DIV_CODE": period,
            "FID_ORG_ADJ_PRC": "0"
        }
        
        response = requests.get(url, headers=headers, params=params)
        return response.json()
```

### 데이터 갱신 주기
- 실시간 시세: 틱별 (실시간)
- 일별 시세: 장 종료 후 30분 내
- 포트폴리오: 실시간 (체결 시 즉시 반영)

### 장애 대응 방안
1. **재시도 로직**: 3회 재시도 후 에러 핸들링
2. **폴백 소스**: 실시간 연결 실패 시 REST API로 폴백
3. **연결 모니터링**: heartbeat 메커니즘 구현
4. **로드 밸런싱**: VIP/일반 계정 분리 사용

---

## 2. pykrx (한국거래소)

### 개요
한국거래소의 공식 데이터를 수집하는 오픈소스 라이브러리

### 데이터 출처
- 기본 데이터: 한국거래소 공식 정보
- 백업 소스: KRX 공시시스템

### 인증 방법
```python
# pykrx는 별도의 인증이 필요없는 공개 데이터 사용
from pykrx import stock
```

### Rate Limit
- 공식 제한: 없음 (로컬 캐싱 권장)
- 권장 호출 빈도: 분당 30회 이하
- 일일 최대: 10,000회

### Python 수집 코드 예시
```python
from pykrx import stock
from pykrx import bond
from datetime import datetime, timedelta
import pandas as pd
import time

class PyKRXCollector:
    def __init__(self):
        self.cache = {}
        
    def collect_daily_data(self, ticker, start_date, end_date):
        """일별 시세 데이터 수집"""
        try:
            df = stock.get_market_ohlcv_by_date(
                start_date.strftime("%Y%m%d"),
                end_date.strftime("%Y%m%d"),
                ticker
            )
            return df
        except Exception as e:
            print(f"Error collecting data for {ticker}: {e}")
            return pd.DataFrame()
    
    def collect_institutional_flow(self, date):
        """기관/외국인 수급 데이터"""
        df = stock.get_market_net_purchases_of_equities(
            date.strftime("%Y%m%d"),
            date.strftime("%Y%m%d"),
            "KOSPI"
        )
        return df
    
    def collect_index_data(self, index_code, start_date, end_date):
        """지수 데이터 수집"""
        df = stock.get_index_ohlcv_by_date(
            start_date.strftime("%Y%m%d"),
            end_date.strftime("%Y%m%d"),
            index_code
        )
        return df
    
    def batch_collection_strategy(self, tickers, start_date, end_date):
        """배치 수집 전략"""
        results = {}
        
        # 1. 청크 분할 (50개씩)
        chunk_size = 50
        chunks = [tickers[i:i+chunk_size] 
                 for i in range(0, len(tickers), chunk_size)]
        
        for chunk in chunks:
            for ticker in chunk:
                try:
                    data = self.collect_daily_data(ticker, start_date, end_date)
                    results[ticker] = data
                    # Rate Limit 대기
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Failed to collect {ticker}: {e}")
                    continue
        
        return results
```

### 데이터 갱신 주기
- 일별 데이터: 장 종료 후 18:00
- 실시간: 제공하지 않음
- 지수 데이터: 1분 간격 (장 중)

### 장애 대응 방안
1. **로컬 캐싱**: 수집 데이터 SQLite/Parquet 저장
2. **재시도**: 5분 간격으로 실패한 데이터 재수집
3. **데이터 검증**: 수집 후 NaN/이상치 검증
4. **대체 데이터소스**: FinanceDataReader 백업

---

## 3. FinanceDataReader

### 개요
국내외 금융 데이터를 수집하는 Python 라이브러리

### API 엔드포인트
```
기본 출처:
- 야후 파이낸스 (해외주식)
- 나스닥 (미국주식)
- 한국거래소 (국내주식)
- 한국은행 (환율)
```

### 인증 방법
```python
# 별도 인증 없이 사용 가능
import FinanceDataReader as fdr
```

### Rate Limit
- 야후 파이낸스: 시간당 2,000회
- 한국거래소: 제한 없음
- 권장: 분당 100회 이하

### Python 수집 코드 예시
```python
import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime, timedelta

class FDRCollector:
    def __init__(self):
        pass
    
    def collect_overseas_market(self, symbol, country='US'):
        """해외 시장 데이터 수집"""
        try:
            if country == 'US':
                df = fdr.DataReader(symbol, 'yahoo')
            elif country == 'KR':
                df = fdr.DataReader(symbol)
            else:
                df = fdr.DataReader(symbol, country=country)
            return df
        except Exception as e:
            print(f"Error collecting {symbol}: {e}")
            return pd.DataFrame()
    
    def collect_etf_data(self, etf_code):
        """ETF 데이터 수집"""
        # 한국 ETF
        df_kr = fdr.DataReader(etf_code)
        
        # 해외 ETF (예: SPY)
        df_us = fdr.DataReader('SPY', 'yahoo')
        
        return {
            'korea': df_kr,
            'us': df_us
        }
    
    def collect_exchange_rate(self, currency='USD/KRW'):
        """환율 정보 수집"""
        try:
            # 최근 1년 환율 데이터
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            df = fdr.DataReader(
                currency,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            return df
        except Exception as e:
            print(f"Error collecting exchange rate: {e}")
            return pd.DataFrame()
    
    def collect_multi_symbols(self, symbols):
        """다중 심볼 배치 수집"""
        data_dict = {}
        
        for symbol in symbols:
            try:
                data = fdr.DataReader(symbol)
                data_dict[symbol] = data
                
                # Rate Limit 고려
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Failed to collect {symbol}: {e}")
                continue
        
        return data_dict
```

### 데이터 갱신 주기
- 해외 주식: 실시간 (야후 기준)
- 국내 주식: 장 종료 후
- 환율: 일별 업데이트
- ETF: 실시간/일별 (시장에 따라 다름)

### 장애 대응 방안
1. **소스 분산**: 야후 실패 시 다른 데이터 소스 활용
2. **데이터 캐싱**: 수집 데이터 로컬 저장
3. **재시도 메커니즘**: 지수 백오프로 재시도
4. **프록시 서버**: IP 차단 시 대체

---

## 4. DART API

### 개요
금융감독원 공시시스템 API를 통한 기업 공시 정보 수집

### API 엔드포인트
```
기본 URL: https://opendart.fss.or.kr/api

# 주요 엔드포인트
1. 기업개황: /company.json
2. 공시목록: /list.json
3. 공시서류: /document.xml
4. 재무제표: /fnlttSinglAcnt.json
```

### 인증 방법
```python
import requests
import xml.etree.ElementTree as ET

class DARTAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://opendart.fss.or.kr/api"
    
    def authenticate(self):
        """DART API 인증"""
        # API Key를 모든 요청의 파라미터로 포함
        return f"crtfc_key={self.api_key}"
```

### Rate Limit
- 기본 제한: 분당 10,000건
- 일일 제한: 없음
- 권장: 분당 100회 미만으로 제한

### Python 수집 코드 예시
```python
import requests
import pandas as pd
from datetime import datetime
import time

class DARTCollector:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://opendart.fss.or.kr/api"
    
    def get_disclosure_list(self, corp_code, start_date, end_date):
        """공시 목록 조회"""
        url = f"{self.base_url}/list.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bgn_de': start_date,
            'end_de': end_date,
            'pblntf_ty': 'A',  # 모든 공시유형
            'page_no': '1',
            'page_count': '100'
        }
        
        response = requests.get(url, params=params)
        return response.json()
    
    def get_financial_statements(self, corp_code, bsns_year, reprt_code='11011'):
        """재무제표 데이터 조회"""
        url = f"{self.base_url}/fnlttSinglAcnt.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code,
            'bsns_year': bsns_year,
            'reprt_code': reprt_code,  # 1분기보고서: 11013, 반기보고서: 11012, ...
            'fs_div': 'OFS'  # 연결재무제표: CFS, 별도재무제표: OFS
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] == '000':
            return self._parse_financial_data(data['list'])
        else:
            print(f"Error: {data['message']}")
            return pd.DataFrame()
    
    def get_major_shareholders(self, corp_code):
        """주요주주 변동 현황"""
        url = f"{self.base_url}/majorstock.json"
        params = {
            'crtfc_key': self.api_key,
            'corp_code': corp_code
        }
        
        response = requests.get(url, params=params)
        return response.json()
    
    def _parse_financial_data(self, data_list):
        """재무제표 데이터 파싱"""
        df = pd.DataFrame(data_list)
        
        # 필요한 컬럼 선택 및 정제
        required_columns = [
            'sj_nm',  # 재무제표명
            'account_nm',  # 계정명
            'thstrm_amount',  # 당기금액
            'frmtrm_amount',  # 전기금액
            'bfefrmtrm_amount'  # 전전기금액
        ]
        
        return df[required_columns]
    
    def batch_collect_disclosures(self, corp_codes, days=7):
        """다중 기업 공시 정보 배치 수집"""
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        
        disclosures = {}
        
        for corp_code in corp_codes:
            try:
                data = self.get_disclosure_list(corp_code, start_date, end_date)
                disclosures[corp_code] = data['list']
                
                # Rate Limit 준수
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Failed to collect disclosures for {corp_code}: {e}")
                continue
        
        return disclosures
```

### 데이터 갱신 주기
- 실시간 공시: 즉시 업데이트
- 재무제표: 분기/반기/연간 보고서 제출 시
- 주요주주: 분기별 업데이트

### 장애 대응 방안
1. **에러 코드 처리**: DART API 에러 코드별 대응 로직
2. **재시도 메커니즘**: 일시적 장애 시 3회 재시도
3. **데이터 검증**: 수집 데이터 무결성 검증
4. **백업 저장소**: S3/데이터베이스에 이중 저장

---

## 5. 매크로 데이터

### 개요
한국은행 및 통계청의 경제 지표 데이터 수집

### 데이터 출처
1. **한국은행 경제통계시스템(ECOS)**
   - 기본 URL: https://ecos.bok.or.kr/api
   - 주요 데이터: 금리, 환율, 경제성장률

2. **한국은행 외환정보시스템**
   - 환율 실시간 정보

3. **통계청 KOSIS**
   - 소비자물가지수, 실업률 등

### 인증 방법
```python
class MacroDataCollector:
    def __init__(self, ecos_api_key):
        self.ecos_api_key = ecos_api_key
        self.ecos_url = "https://ecos.bok.or.kr/api"
```

### Rate Limit
- ECOS API: 일일 1,000회
- 실시간 환율: 분당 60회
- 권장: 분당 10회 이하

### Python 수집 코드 예시
```python
import requests
import pandas as pd
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

class MacroDataCollector:
    def __init__(self, ecos_api_key):
        self.ecos_api_key = ecos_api_key
        self.ecos_url = "https://ecos.bok.or.kr/api"
    
    def get_interest_rates(self):
        """금리 데이터 수집 (한국은행 기준금리)"""
        url = f"{self.ecos_url}/StatisticSearch/{self.ecos_api_key}/xml/kr/1/10/722Y001/D/20100101/20231231/0101000"
        
        response = requests.get(url)
        root = ET.fromstring(response.content)
        
        data = []
        for item in root.findall('.//row'):
            period = item.find('TIME').text
            rate = item.find('DATA_VALUE').text
            data.append({'date': period, 'interest_rate': float(rate)})
        
        return pd.DataFrame(data)
    
    def get_exchange_rates(self, currency_code='USD'):
        """환율 데이터 수집"""
        # 한국은행 환율 정보
        url = f"{self.ecos_url}/StatisticSearch/{self.ecos_api_key}/xml/kr/1/10/731Y001/D/20230101/20231231/{currency_code}"
        
        response = requests.get(url)
        root = ET.fromstring(response.content)
        
        data = []
        for item in root.findall('.//row'):
            period = item.find('TIME').text
            rate = item.find('DATA_VALUE').text
            data.append({'date': period, f'exchange_rate_{currency_code.lower()}': float(rate)})
        
        return pd.DataFrame(data)
    
    def get_economic_indicators(self):
        """경제지표 수집 (GDP, CPI 등)"""
        indicators = {
            'gdp': '200Y001',  # GDP 성장률
            'cpi': '901Y009',  # 소비자물가지수
            'unemployment': '901Y055',  # 실업률
        }
        
        result = {}
        for name, code in indicators.items():
            url = f"{self.ecos_url}/StatisticSearch/{self.ecos_api_key}/xml/kr/1/10/{code}/Q/2020Q1/2023Q4"
            
            response = requests.get(url)
            root = ET.fromstring(response.content)
            
            data = []
            for item in root.findall('.//row'):
                period = item.find('TIME').text
                value = item.find('DATA_VALUE').text
                data.append({'period': period, name: float(value)})
            
            result[name] = pd.DataFrame(data)
            
            # Rate Limit 고려
            time.sleep(0.5)
        
        return result
    
    def collect_all_macro_data(self):
        """모든 매크로 데이터 수집"""
        macro_data = {
            'interest_rates': self.get_interest_rates(),
            'exchange_rates': self.get_exchange_rates('USD'),
            'indicators': self.get_economic_indicators()
        }
        
        return macro_data
    
    def realtime_exchange_rate(self):
        """실시간 환율 정보 (한국은행)"""
        try:
            # 한국은행 실시간 환율 API
            url = "https://www.bok.or.kr/portal/schedule/exchange/exchangeJSON.do"
            params = {
                'dataGubun': '0',  # 0: 평균, 1: 매매기준율
                'searchDate': datetime.now().strftime('%Y%m%d')
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            return pd.DataFrame(data)
        except Exception as e:
            print(f"Error fetching realtime exchange rate: {e}")
            # 폴백: ECOS API 사용
            return self.get_exchange_rates()
```

### 데이터 갱신 주기
- 기준금리: 한국은행 금융통화위원회 개최 시
- 환율: 실시간 (영업일 09:00~18:00)
- GDP: 분기별 (다음 분기 초)
- CPI: 월별 (다음 달 초)

### 장애 대응 방안
1. **다중 소스 활용**: 한국은행 실패 시 다른 금융사 API 사용
2. **캐싱 전략**: 일별 데이터 로컬 캐싱
3. **데이터 보정**: 결측치 선형 보간법 적용
4. **모니터링 알림**: 데이터 수집 실패 시 알림 발송

---

## 통합 데이터 수집 전략

### 1. 스케줄링 시스템
```python
import schedule
import time
from datetime import datetime

class AEGISDataScheduler:
    def __init__(self):
        self.collectors = {
            'kis': KISRealtimeData(auth),
            'pykrx': PyKRXCollector(),
            'fdr': FDRCollector(),
            'dart': DARTCollector(api_key),
            'macro': MacroDataCollector(ecos_api_key)
        }
    
    def setup_schedule(self):
        # 실시간 데이터 (장중)
        schedule.every(1).minutes.do(
            self.collect_realtime_data
        ).tag('realtime')
        
        # 일별 데이터 (장 종료 후)
        schedule.every().day.at("18:30").do(
            self.collect_daily_data
        ).tag('daily')
        
        # 재무제표 데이터 (월말)
        schedule.every().month.at("10:00").do(
            self.collect_financial_data
        ).tag('monthly')
    
    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)
```

### 2. 데이터 품질 관리
- **유효성 검증**: 이상치, 결측치 검증
- **일관성 검증**: 여러 소스 간 데이터 일관성 확인
- **타임스탬프**: 모든 데이터에 수집 시간 기록

### 3. 장애 복구 메커니즘
1. **우선순위 큐**: 중요한 데이터 먼저 수집
2. **백업 수집기**: 주요 데이터 소스별 백업 수집기
3. **자동 재시작**: 수집기 프로세스 모니터링 및 재시작

### 4. 모니터링 및 알림
- 데이터 수집 성공률 모니터링
- Rate Limit 위반 경고
- 데이터 지연 감지 및 알림

---

## 주의사항

1. **API 키 관리**: 환경변수 또는 시크릿 관리 시스템 사용
2. **Rate Limit 준수**: 모든 API의 Rate Limit 엄격 준수
3. **데이터 사용 정책**: 각 데이터 소스의 이용약관 준수
4. **에러 핸들링**: 모든 수집 함수에 try-except 적용
5. **로그 기록**: 모든 수집 활동 상세 로깅

---

*문서 버전: AEGIS v3.1 데이터 소싱 문서 (2024.01.15)*  
*최종 업데이트: 2024년 1월 15일*  
*담당자: 데이터 엔지니어링 팀*
