# AEGIS v3.0 - 하이브리드 동기화 전략

## 개요

WebSocket 실시간 데이터와 REST API 정기 동기화를 결합한 3단계 안전장치로 **데이터 불일치를 최대 1분 안에 자동 복구**합니다.

---

## 🏛️ 동기화 전략 (Synchronization Strategy)

### 1. ⚡ 이벤트 기반 동기화 (Event-Driven)

**트리거**: WebSocket 체결 알림 수신 시

**처리 흐름**:
```
WebSocket H0STCNI0 체결 통보 수신
  ↓
kis_fetcher.on_execution_notice() 호출
  ↓
1. trade_orders 상태 업데이트
2. trade_executions 기록
3. Portfolio DB 즉시 업데이트 (+/- 연산)
  ↓
3초 후 REST API 호출 (정산용)
```

**목적**:
- 빠른 UI 반영 (10~50ms 지연)
- 즉각적인 포트폴리오 업데이트

**구현 위치**: `fetchers/kis_fetcher.py:109-190`

---

### 2. 🛡️ 주기적 동기화 (Routine Sync - Safety Net)

**주기**: 1분마다 (장중 09:00~15:30)

**TR 코드**: `TTTC8434R` (주식잔고조회)

**처리 흐름**:
```
매분 00초 실행 (APScheduler)
  ↓
scheduler/main_scheduler.py:job_sync_account()
  ↓
1. KIS API에서 보유종목 조회 (get_combined_balance)
2. 예수금 정보 조회 (TTTC8434R)
3. stock_assets 테이블 DELETE → INSERT (Full Refresh)
4. portfolio_summary 테이블 업데이트
  ↓
변경사항 있을 때만 INFO 로그 출력
```

**목적**:
- WebSocket 패킷 유실 복구
- 네트워크 순간 단절 시 데이터 정합성 보장
- 최대 1분 안에 불일치 자동 복구

**API 제한 고려**: KIS API는 초당 20건 허용 → 1분에 1번 호출은 무부하

**구현 위치**: `scheduler/main_scheduler.py:138-242`

---

### 3. 🚨 비상 동기화 (Recovery)

**트리거**: WebSocket 재연결 시

**처리 흐름**:
```
ConnectionClosed 예외 발생
  ↓
websocket_manager.reconnect() 호출
  ↓
1. WebSocket 재연결
2. 🚨 즉시 REST API로 계좌 강제 동기화
3. 기존 구독 슬롯 전체 재구독
  ↓
Emergency sync completed
```

**목적**:
- 연결 끊김 중 발생한 체결 내역 복구
- 재연결 직후 데이터 무결성 확보

**구현 위치**: `fetchers/websocket_manager.py:397-432`

---

## 📊 데이터 흐름 타임라인

```
09:00:00 - [초기화] initialize_account.py 실행 → 기준점 설정
09:00:00 - [주기] job_sync_account() 실행
09:01:00 - [주기] job_sync_account() 실행
09:02:00 - [주기] job_sync_account() 실행
09:02:35 - [이벤트] WebSocket 체결 알림 → 즉시 DB 반영
09:02:38 - [이벤트] 3초 후 REST API 정산 확인
09:03:00 - [주기] job_sync_account() → 혹시 틀린 수량 있으면 자동 보정
09:04:00 - [주기] job_sync_account() 실행
09:05:12 - [비상] WebSocket 재연결 → 즉시 강제 동기화
09:05:15 - [이벤트] 재구독 완료 → 실시간 스트림 재개
```

---

## 🔧 구현 코드

### 1. 스케줄러 설정 (main_scheduler.py)

```python
# 09:00-15:30 - 1분마다 계좌 잔고 강제 동기화
self.scheduler.add_job(
    self.job_sync_account,
    CronTrigger(hour='9-15', minute='*'),  # 매분 00초마다 실행
    id="sync_account_safety"
)
```

### 2. 동기화 Job (main_scheduler.py)

```python
async def job_sync_account(self):
    """
    🛡️ 하이브리드 동기화: 1분마다 계좌 잔고 강제 동기화 (Safety Net)
    """
    try:
        logger.debug("🛡️ [Safety] Synchronizing Account Balance...")

        db = SessionLocal()
        try:
            # KIS에서 최신 보유종목 조회
            holdings = self.kis.get_combined_balance()

            # 예수금 정보 조회 (TTTC8434R)
            token = self.kis.get_access_token()
            response = requests.get(url, headers=headers, params=params)

            # DB 동기화 (Full Refresh)
            db.execute(text("DELETE FROM stock_assets"))

            for stock in holdings:
                if quantity > 0:
                    db.execute(insert_query, {...})

            db.commit()

            if changed_count > 0:
                logger.info(f"🛡️ Sync Complete: {changed_count}개 종목")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ Sync Failed: {e}")
```

### 3. 비상 동기화 (websocket_manager.py)

```python
async def reconnect(self):
    """
    🚨 WebSocket 재연결 (비상 동기화 포함)
    """
    await self.kis_client.connect_websocket()

    # 🚨 비상 동기화: REST API로 계좌 즉시 동기화
    logger.info("🚨 Emergency sync: Synchronizing account after reconnect...")
    try:
        await kis_fetcher.sync_portfolio()
        logger.info("✅ Emergency sync completed")
    except Exception as sync_error:
        logger.error(f"❌ Emergency sync failed: {sync_error}")

    # 기존 구독 전체 재구독
    await self.resubscribe_all()
```

---

## 📈 이점

1. **속도**: WebSocket으로 즉각 반응 (10~50ms)
2. **정확성**: REST API로 정기 검증 (1분마다)
3. **안정성**: 재연결 시 즉시 복구 (0초 지연)
4. **복원력**: 패킷 유실 자동 복구 (최대 1분)

---

## ⚠️ 주의사항

- KIS API 제한: 초당 20건 → 1분 주기는 안전
- 변경사항 없으면 DEBUG 레벨로 로그 출력
- 재연결 실패 시 10초 후 재시도
- DB 트랜잭션 실패 시 자동 롤백

---

## 🧪 테스트 시나리오

### 시나리오 1: 정상 체결
1. WebSocket 체결 알림 수신 → 즉시 DB 반영
2. 3초 후 REST API 정산
3. 다음 분 00초 → 주기 동기화로 재확인

### 시나리오 2: WebSocket 패킷 유실
1. 체결 발생했지만 WebSocket 알림 누락
2. 다음 분 00초 → 주기 동기화가 자동 감지
3. REST API에서 정확한 수량 가져와서 DB 보정

### 시나리오 3: 네트워크 순간 단절
1. ConnectionClosed 예외 발생
2. 재연결 로직 실행
3. 🚨 비상 동기화 즉시 실행 → 누락 데이터 복구
4. 기존 구독 재개

---

## 📝 관련 파일

- `scheduler/main_scheduler.py` - 주기적 동기화
- `fetchers/websocket_manager.py` - 비상 동기화
- `fetchers/kis_fetcher.py` - 이벤트 기반 동기화
- `scripts/initialize_account.py` - 초기 동기화

---

**마지막 업데이트**: 2025-12-10 03:15:53
