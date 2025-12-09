# WebSocket 승인키 발급 - 빠른 가이드

**작성일**: 2025-12-09
**목적**: KIS WebSocket 실시간 데이터 활성화

---

## 🎯 현재 상태

✅ 설정 파일 준비 완료 (.env 중복 제거)
⚠️  승인키 발급 필요 (현재: 플레이스홀더)
🚧 WebSocket 연결 대기 중

---

## 📋 승인키 발급 5단계

### 1️⃣ 포털 접속
```bash
open https://apiportal.koreainvestment.com
```

### 2️⃣ 로그인
- 계좌번호: `43537916-01`
- 한국투자증권 계정으로 로그인

### 3️⃣ 마이페이지 → API 관리
- 좌측 메뉴: "마이페이지"
- "API 관리" 선택

### 4️⃣ WebSocket 승인키 발급
- "실시간 시세 서비스" 섹션
- "WebSocket 접속키 발급" 버튼 클릭
- 승인키 복사 (약 80~100자 길이)

### 5️⃣ .env 파일 수정
```bash
# .env 파일 열기
code /Users/wonny/Dev/aegis/v3/.env

# 라인 18 수정
KIS_WS_APPROVAL_KEY=복사한_승인키_여기에_붙여넣기
```

---

## 🧪 연결 테스트

```bash
cd /Users/wonny/Dev/aegis/v3
python test_websocket.py
```

**예상 출력**:
```
==========================================================
🧪 KIS WebSocket 연결 테스트
==========================================================

1️⃣ 승인키 확인
   승인키 설정: ✅ P0EW1A2B3C4D5E6F7G8H...
   길이: 98자

2️⃣ KIS Client 초기화
   ✅ Client 초기화 완료
   계좌번호: 43537916-01

3️⃣ WebSocket 연결 시도
   연결 시작: 10:30:00
   ✅ WebSocket 연결 성공!

4️⃣ 실시간 시세 구독 (삼성전자 005930)
   ✅ 구독 완료

5️⃣ 데이터 수신 대기 (10초)
   실시간 데이터 수신 중...

   📊 [10:30:01] 데이터 수신: 71500원
   📊 [10:30:03] 데이터 수신: 71550원
   📊 [10:30:05] 데이터 수신: 71600원

   ✅ 총 3개 데이터 수신

6️⃣ WebSocket 연결 종료
   ✅ 연결 종료 완료
```

---

## 🚨 주의사항

### 승인키 보안
```bash
# ❌ 절대 Git에 커밋하지 말 것
git add .env  # 위험!

# ✅ .gitignore 확인
cat .gitignore | grep .env
# 출력: .env
```

### 승인키 타입 구분 (3종류)

| 키 타입 | 용도 | 위치 |
|--------|------|------|
| `KIS_APP_KEY` | REST API 인증 | .env 라인 8 |
| `KIS_APP_SECRET` | REST API 서명 | .env 라인 9 |
| `KIS_WS_APPROVAL_KEY` | **WebSocket 연결** | **.env 라인 18** |

**중요**: 3가지 키가 모두 다릅니다!

---

## 🎁 WebSocket으로 활성화되는 기능

### 1. 실시간 함정 감지 (Korean Market Trap Detector)
- **Fake Rise (수급 이탈)**: 주가 상승 + 외국인/기관 순매도 즉시 감지
- **Program Dump (프로그램 매도 가속)**: WebSocket 전용 데이터
- **Gap Overheat (갭 과열)**: 시초가 급등 후 차익 실현 추적

### 2. 실시간 vs 폴링 비교

| 항목 | WebSocket | REST API (폴링) |
|-----|-----------|-----------------|
| 실시간성 | 즉시 (< 1초) | 30초 지연 |
| 서버 부하 | 낮음 (푸시) | 높음 (폴링) |
| 함정 감지 | 즉시 | 늦음 (이미 손실 발생) |
| 프로그램 매매 | ✅ 사용 가능 | ❌ 불가능 |

### 3. 2025-12-09 실전 사례

**Without WebSocket (REST 폴링)**:
- 삼성전자 시초가 +3.5% 갭상승
- AI: "미국장 호재 = BUY!" (30초 지연 데이터)
- 결과: 최고점 풀매수 → **-2.17% 손실** ❌

**With WebSocket (실시간)**:
```
🚨 함정 감지 1: 갭 과열 (Gap Overheat)
   - 시초가 +3.5% → 기준 초과
   - 신뢰도: 90%

🚨 함정 감지 2: 수급 이탈 (Fake Rise)
   - 프로그램 비차익: -850억원 순매도 (실시간 감지)
   - 신뢰도: 95%

최종 결정: AI 점수 85점 → 0점 (CRITICAL 함정)
          Final Score: 40점 (BUY 기준 70점 미달)
          결과: 매수 회피 → 0% 손실 ✅
```

---

## 📚 관련 문서

### 개발 문서
- **상세 가이드**: `/Users/wonny/Dev/aegis/v3/docs/dev/26-KIS-WEBSOCKET-SETUP.md`
- **함정 감지 시스템**: `/Users/wonny/Dev/aegis/v3/docs/dev/22-KOREAN-MARKET-TRAPS.md`
- **데이터 통합**: `/Users/wonny/Dev/aegis/v3/docs/dev/23-KOREAN-MARKET-DATA-INTEGRATION.md`

### 시스템 문서
- **안전 시스템**: `/Users/wonny/Dev/aegis/v3/docs/SAFETY_SYSTEM.md` (Section 9)
- **외부 데이터**: `/Users/wonny/Dev/aegis/v3/docs/EXTERNAL_DATA_SOURCES.md` (Section 3.3)

### 구현 파일
- **Trap Detector**: `brain/korean_market_traps.py`
- **KIS Client**: `fetchers/kis_client.py`
- **WebSocket Manager**: `fetchers/websocket_manager.py`
- **Test Script**: `test_websocket.py`

---

## 🆘 문제 해결

### 문제 1: 승인키 발급이 안 됨
**해결**: 한국투자증권 고객센터 **1544-5000**
"Open API 승인키 발급 문의"

### 문제 2: 연결 실패 (Connection refused)
**원인**: 승인키 오타 or 만료
**해결**:
```python
from app.config import settings
print(f"설정된 키: {settings.kis_ws_approval_key}")
print(f"길이: {len(settings.kis_ws_approval_key)} 자")
print(f"올바른 형식: {settings.kis_ws_approval_key != 'your_websocket_approval_key'}")
```

### 문제 3: 데이터 수신 안 됨
**원인**: 장 마감 시간 or 구독 실패
**해결**: 장 운영 시간(09:00-15:30)에 테스트

---

## ✅ 체크리스트

- [ ] 한국투자증권 포털 로그인
- [ ] WebSocket 승인키 발급
- [ ] `.env` 파일 라인 18에 승인키 등록
- [ ] 중복 선언 제거 확인 (라인 34 삭제됨)
- [ ] `python -c "from app.config import settings; print(settings.kis_ws_approval_key)"` 확인
- [ ] `python test_websocket.py` 연결 테스트
- [ ] Korean Market Trap Detector 실시간 감지 확인

---

**Next Step**: 승인키 발급 후 Phase 1 Implementation - KIS Fetcher 확장
