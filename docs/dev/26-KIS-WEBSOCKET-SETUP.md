# KIS WebSocket 승인키 발급 및 설정

**작성일**: 2025-12-09 23:35:00
**작성자**: wonny
**목적**: WebSocket 승인키 발급 가이드 (실시간 시세용)

---

## 🎯 WebSocket 승인키가 필요한 이유

현재 `.env` 파일에 `KIS_WS_APPROVAL_KEY=your_websocket_approval_key`가 플레이스홀더로 되어 있습니다.

**WebSocket 승인키가 필요한 경우**:
- ✅ **실시간 체결가 모니터링** (Korean Market Trap Detector용)
- ✅ **실시간 호가 데이터** (Micro Optimization용)
- ✅ **외국인/기관 순매수 실시간 추적** (Fake Rise 감지용)
- ✅ **프로그램 매매 실시간 추적** (Program Dump 감지용)

**WebSocket 없이도 작동하는 기능**:
- 📊 일반 데이터 수집 (일봉, 수급)
- 💰 매수/매도 주문
- 📈 현재가 조회 (30초 폴링)

---

## 📋 승인키 발급 단계별 가이드

### Step 1: 한국투자증권 Open API 포털 접속

```
URL: https://apiportal.koreainvestment.com
```

브라우저에서 위 URL로 접속합니다.

---

### Step 2: 로그인

- 한국투자증권 계좌 정보로 로그인
- 계좌번호: `43537916-01` (기존 .env에 설정된 계좌)

---

### Step 3: 마이페이지 → API 관리

1. 좌측 메뉴에서 **"마이페이지"** 클릭
2. **"API 관리"** 메뉴 선택
3. 발급받은 API 키 목록 확인

---

### Step 4: WebSocket 승인키 발급

1. **"실시간 시세 서비스"** 섹션 찾기
2. **"WebSocket 접속키 발급"** 버튼 클릭
3. 승인키 즉시 발급 (승인 대기 없음)
4. 발급된 승인키 복사

**발급되는 키 형식**:
```
예시: P0EW1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U2V3W4X5Y6Z7A8B9C0D
(실제 키는 약 80~100자 길이의 영문/숫자 조합)
```

---

### Step 5: .env 파일에 등록

복사한 승인키를 `.env` 파일에 붙여넣기:

```bash
# Before
KIS_WS_APPROVAL_KEY=your_websocket_approval_key

# After (예시)
KIS_WS_APPROVAL_KEY=P0EW1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U2V3W4X5Y6Z7A8B9C0D
```

**편집 명령어**:
```bash
# 터미널에서 직접 편집
nano /Users/wonny/Dev/aegis/v3/.env

# 또는 VS Code에서 열기
code /Users/wonny/Dev/aegis/v3/.env
```

---

### Step 6: 설정 확인

AEGIS 재시작 후 WebSocket 연결 확인:

```bash
cd /Users/wonny/Dev/aegis/v3
python -c "
from app.config import settings
print(f'WebSocket Key: {settings.kis_ws_approval_key[:20]}...')
print(f'Status: {\"✅ 설정됨\" if settings.kis_ws_approval_key != \"your_websocket_approval_key\" else \"❌ 미설정\"}')"
```

**예상 출력**:
```
WebSocket Key: P0EW1A2B3C4D5E6F7G8H...
Status: ✅ 설정됨
```

---

## 🧪 WebSocket 연결 테스트

승인키 발급 후 실제 연결 테스트:

```python
# test_websocket.py
import asyncio
from fetchers.kis_client import KISClient

async def test_websocket():
    """WebSocket 연결 테스트"""
    client = KISClient()

    # 1. WebSocket 연결
    success = await client.connect_websocket()

    if success:
        print("✅ WebSocket 연결 성공!")

        # 2. 실시간 시세 구독 (삼성전자)
        await client.subscribe_realtime_price("005930")
        print("✅ 삼성전자 실시간 시세 구독 완료")

        # 3. 10초간 데이터 수신
        await asyncio.sleep(10)

        # 4. 연결 종료
        await client.disconnect_websocket()
        print("✅ WebSocket 연결 종료")
    else:
        print("❌ WebSocket 연결 실패")
        print("승인키를 확인해주세요.")

# 실행
asyncio.run(test_websocket())
```

**실행**:
```bash
cd /Users/wonny/Dev/aegis/v3
python test_websocket.py
```

---

## 🔧 Korean Market Trap Detector와의 통합

WebSocket 승인키 설정 후 활성화되는 기능:

### 1. 실시간 수급 이탈 감지 (Fake Rise)

**Before (REST API 폴링, 30초 지연)**:
```python
# 30초마다 체크 → 함정 감지 늦음
while True:
    foreign_net = kis_client.get_foreign_net_buy("005930")
    if foreign_net < 0:
        print("⚠️ 외국인 매도 (30초 전 데이터)")
    await asyncio.sleep(30)
```

**After (WebSocket 실시간, 즉시 감지)**:
```python
# 실시간 체결마다 체크 → 함정 감지 즉시
async def on_realtime_trade(data):
    foreign_net = data['foreign_net_buy']
    if foreign_net < 0 and data['price_change'] > 0:
        print("🚨 수급 이탈 (Fake Rise) 감지!")
        await trap_detector.detect_traps(...)
```

### 2. 프로그램 매도 가속 감지 (Program Dump)

**WebSocket 전용 기능**:
- 프로그램 매매는 실시간 데이터만 제공
- REST API로는 조회 불가

```python
async def on_program_trading(data):
    """프로그램 매매 실시간 수신"""
    if data['program_net_buy'] < 0 and data['slope'] < -0.3:
        print("🚨 프로그램 매도 가속 (Program Dump) 감지!")
```

### 3. 체결강도 실시간 계산 (Micro Optimization)

```python
async def on_execution(data):
    """실시간 체결 데이터"""
    buy_volume = data['buy_volume']
    sell_volume = data['sell_volume']
    power = (buy_volume / (buy_volume + sell_volume)) * 100

    if power < 100:
        print(f"⚠️ 체결강도 약함 ({power:.1f}%) - 가짜 상승 의심")
```

---

## 🚨 주의사항

### 1. 승인키 보안

```bash
# ❌ 절대 Git에 커밋하지 말 것
git add .env  # 위험!

# ✅ .gitignore에 포함되어 있는지 확인
cat .gitignore | grep .env
# 출력: .env
```

### 2. 승인키 타입 구분

| 키 타입 | 용도 | 위치 |
|--------|------|------|
| `KIS_APP_KEY` | REST API 인증 | .env 라인 8 |
| `KIS_APP_SECRET` | REST API 서명 | .env 라인 9 |
| `KIS_WS_APPROVAL_KEY` | **WebSocket 연결** | **.env 라인 18, 34** |

**중요**: 3가지 키가 모두 다름!

### 3. 중복 선언 제거

현재 `.env` 파일에 `KIS_WS_APPROVAL_KEY`가 2번 선언되어 있습니다:
- 라인 18: `KIS_WS_APPROVAL_KEY=your_websocket_approval_key`
- 라인 34: `KIS_WS_APPROVAL_KEY=your_websocket_approval_key`

**수정 필요**:
```bash
# 라인 34 삭제 (중복)
# 라인 18만 남기고 승인키 설정
```

---

## 📊 WebSocket vs REST API 비교

| 항목 | WebSocket | REST API (폴링) |
|-----|-----------|----------------|
| **실시간성** | 즉시 (< 1초) | 30초 지연 |
| **서버 부하** | 낮음 (푸시) | 높음 (폴링) |
| **승인키** | 필요 | 불필요 |
| **안정성** | 재연결 필요 | 매번 신규 연결 |
| **적용 기능** | Trap Detector, Micro Optimizer | 일반 데이터 수집 |

---

## 🎯 설정 후 확인 체크리스트

- [ ] 한국투자증권 포털 로그인
- [ ] WebSocket 승인키 발급
- [ ] `.env` 파일에 승인키 등록 (라인 18)
- [ ] `.env` 라인 34 중복 선언 제거
- [ ] `python -c "from app.config import settings; print(settings.kis_ws_approval_key)"` 확인
- [ ] `python test_websocket.py` 연결 테스트
- [ ] Korean Market Trap Detector 실시간 감지 확인

---

## 🆘 문제 해결

### 문제 1: 승인키 발급이 안 됨

**원인**: 계좌 미개설 or API 미신청

**해결**:
1. 한국투자증권 고객센터: **1544-5000**
2. "Open API 승인키 발급 문의"
3. 계좌번호 확인: `43537916-01`

### 문제 2: 연결 실패 (Connection refused)

**원인**: 승인키 오타 or 만료

**해결**:
```python
# 승인키 재확인
from app.config import settings
print(f"설정된 키: {settings.kis_ws_approval_key}")
print(f"길이: {len(settings.kis_ws_approval_key)} 자")
print(f"올바른 형식: {settings.kis_ws_approval_key != 'your_websocket_approval_key'}")
```

### 문제 3: 중복 선언으로 인한 오류

**증상**: `.env` 파일에 같은 키가 2번 선언됨

**해결**:
```bash
# 라인 34 삭제
sed -i '' '34d' /Users/wonny/Dev/aegis/v3/.env

# 확인
grep -n "KIS_WS_APPROVAL_KEY" /Users/wonny/Dev/aegis/v3/.env
# 출력: 18:KIS_WS_APPROVAL_KEY=<승인키>
```

---

## 📁 관련 파일

### 설정 파일
- `/Users/wonny/Dev/aegis/v3/.env` - 승인키 저장
- `/Users/wonny/Dev/aegis/v3/app/config.py` - 설정 로드

### 구현 파일
- `fetchers/kis_client.py` - WebSocket 연결 (라인 108-140)
- `fetchers/websocket_manager.py` - 실시간 데이터 구독
- `brain/korean_market_traps.py` - 실시간 함정 감지

### 문서
- `docs/KIS_WEBSOCKET_GUIDE.md` - 상세 가이드
- `docs/KIS_API_SPECIFICATION.md` - API 명세
- `docs/dev/22-KOREAN-MARKET-TRAPS.md` - 함정 감지 시스템

---

## 👤 작성자

- **Author**: wonny
- **Date**: 2025-12-09 23:35:00
- **Project**: AEGIS v3.0
- **Status**: Ready for WebSocket Setup

---

## ✅ 빠른 시작 (Quick Start)

```bash
# 1. 포털 접속
open https://apiportal.koreainvestment.com

# 2. 승인키 발급 후 복사

# 3. .env 편집
code /Users/wonny/Dev/aegis/v3/.env

# 4. 라인 18 수정
# KIS_WS_APPROVAL_KEY=복사한_승인키_붙여넣기

# 5. 라인 34 삭제 (중복)

# 6. 확인
cd /Users/wonny/Dev/aegis/v3
python -c "from app.config import settings; print('✅' if settings.kis_ws_approval_key != 'your_websocket_approval_key' else '❌')"

# 7. 테스트
python test_websocket.py
```

---

**Next Step**: 승인키 발급 후 Korean Market Trap Detector 실시간 감지 활성화
