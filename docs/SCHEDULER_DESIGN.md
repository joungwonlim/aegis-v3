# AEGIS v3.0 Scheduler Design

> 한국 증시 자동 매매 시스템의 핵심 스케줄러 설계 문서
> APScheduler 기반 크론 작업 관리

---

## 0. 개요

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AEGIS Scheduler Architecture                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │   Pre-      │    │   Market    │    │   Post-     │                 │
│  │   Market    │───▶│   Hours     │───▶│   Market    │                 │
│  │  07:00-09:00│    │  09:00-15:30│    │  15:30-20:00│                 │
│  └─────────────┘    └─────────────┘    └─────────────┘                 │
│         │                  │                  │                         │
│         ▼                  ▼                  ▼                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │ • 매크로    │    │ • 자동매매  │    │ • 일봉수집  │                 │
│  │ • 글로벌    │    │ • 포트폴리오│    │ • 수급정리  │                 │
│  │ • 갭스캔    │    │ • 리밸런싱  │    │ • 일일마감  │                 │
│  └─────────────┘    └─────────────┘    └─────────────┘                 │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Weekend Schedule (Sat-Sun)                   │   │
│  │  토: 미국장 정리, GARCH, AI 전략 | 일: 주간리포트, 선물체크     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. 시장 운영 시간

### 1.1 KRX (한국거래소) - 정규장

| 구분 | 시간 | 설명 |
|-----|------|------|
| 프리마켓 | 08:00 ~ 09:00 | 동시호가 |
| 정규장 | 09:00 ~ 15:30 | 본장 거래 |
| 애프터마켓 | 15:30 ~ 16:00 | 장후 동시호가 |

### 1.2 NXT (대체거래소) - 연장 거래

| 구분 | 시간 | 설명 |
|-----|------|------|
| 프리마켓 | 08:00 ~ 09:00 | NXT 전용 거래 |
| KRX 동시 | 09:00 ~ 15:30 | KRX와 병행 |
| 애프터마켓 | 15:30 ~ 20:00 | NXT 연장 거래 |

### 1.3 현재 구현 상태

```python
# 현재 (NXT 미구현)
TRADING_HOURS = {
    "start": "09:00",
    "end": "15:30",
    "scheduler_end": "15:59"  # 15시대까지만 실행
}

# 향후 (NXT 구현 후)
TRADING_HOURS_NXT = {
    "start": "08:00",      # NXT 프리마켓
    "end": "20:00",        # NXT 애프터마켓
    "scheduler_end": "20:10"
}
```

---

## 2. 일일 스케줄 타임라인

### 2.1 평일 스케줄 (월-금)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          AEGIS Daily Timeline                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  07:00  ┌─────────────────────────────────────────────────────────────┐   │
│         │ 🌅 Pre-Market Phase                                          │   │
│  07:00  │  • fetcher_health_check    - Fetcher 상태 점검               │   │
│  07:20  │  • morning_deep_analysis   - AI 심층 분석 (DeepSeek-R1)  │   │
│  07:30  │  • global_leader_morning   - 글로벌 선행지표                 │   │
│  07:30  │  • macro_update            - 매크로 데이터 수집              │   │
│         └─────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  08:00  ┌─────────────────────────────────────────────────────────────┐   │
│         │ 🎯 Market Prep Phase                                         │   │
│  08:00  │  • macro_monitoring        - 매크로 모니터링 (1시간마다)     │   │
│  08:00  │  • monday_final_check      - 월요일 최종 체크               │   │
│  08:30  │  • alpha_morning_gap       - 갭 스캔                         │   │
│  08:30  │  • monday_strategy         - 월요일 전략 결정               │   │
│  08:30  │  • derivative_monitoring   - 외국인 선물 체크               │   │
│  08:50  │  • market_open             - 장 시작 준비                    │   │
│  08:55  │  • orchestrator_reset      - 오케스트레이터 리셋            │   │
│         └─────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  09:00  ┌─────────────────────────────────────────────────────────────┐   │
│         │ 📈 Trading Phase (09:00-15:30, NXT 후 09:00-20:00)          │   │
│   */1m  │  • portfolio_sync          - 포트폴리오 동기화              │   │
│   */1m  │  • portfolio_watchdog      - 손절/익절 감시                 │   │
│  */30s  │  • auto_trading            - 자동 매매 실행                  │   │
│   */5m  │  • intraday_analysis       - 장중 AI 분석 (DeepSeek-V3)│   │
│   */5m  │  • market_regime_check     - 시장 국면 판단                 │   │
│  */10m  │  • supply_data_sync        - 수급 데이터 수집               │   │
│  */10m  │  • hedge_management        - 인버스 헷지 관리               │   │
│  */10m  │  • orchestrator_execute    - 전략 통합 실행                 │   │
│  */15m  │  • dart_disclosure_scan    - DART 공시 스캔                 │   │
│  */20m  │  • alpha_sector_rotation   - 섹터 순환 체크                 │   │
│  */30m  │  • naver_theme_scan        - 네이버 테마 스캔               │   │
│  */30m  │  • data_fusion_scan        - 데이터 융합 분석               │   │
│  */30m  │  • system_health_log       - 시스템 상태 로그               │   │
│         │                                                              │   │
│  09:05  │  • morning_cash_check      - 현금 확보 체크                 │   │
│  09:05  │  • daily_status_log        - 일일 상태 로그                 │   │
│  09:05  │  • pair_trading_morning    - 페어 트레이딩 분석             │   │
│  10:00  │  • pair_trading_midmorning - 페어 트레이딩 체크             │   │
│  10:30  │  • global_leader_asia      - 아시아 선행지표                │   │
│  10:30  │  • ai_rebalancing          - AI 리밸런싱 1차 (DeepSeek-R1)   │   │
│  14:00  │  • ai_rebalancing          - AI 리밸런싱 2차 (DeepSeek-R1)   │   │
│  14:00  │  • pair_trading_afternoon  - 페어 트레이딩 마감             │   │
│  15:20  │  • cash_optimization       - 현금 파킹 (ETF)                │   │
│         └─────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  15:30  ┌─────────────────────────────────────────────────────────────┐   │
│         │ 🌙 Post-Market Phase                                         │   │
│  15:45  │  • daily_price_sync        - 일봉 데이터 수집               │   │
│  16:00  │  • supply_consensus_sync   - 수급 컨센서스 수집             │   │
│  16:10  │  • detailed_investors_sync - 세분화 투자자 데이터           │   │
│  16:30  │  • derivative_monitoring   - 외국인 선물 마감 체크          │   │
│  16:30  │  • db_backup_daily         - 일일 DB 백업                   │   │
│  18:00  │  • global_leader_europe    - 유럽 선행지표                  │   │
│  20:10  │  • daily_closing           - 일일 마감 처리                 │   │
│  21:00  │  • evening_deep_analysis   - 저녁 심층 분석 (DeepSeek-R1)    │   │
│         └─────────────────────────────────────────────────────────────┘   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 주말 스케줄

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          Weekend Schedule                                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  토요일 (Saturday)                                                         │
│  ─────────────────────────────────────────────────────────────────────    │
│  03:00  │  • db_backup_weekly        - 주간 Full DB 백업              │   │
│  07:00  │  • weekend_full_scan       - 미국장 전체 스캔 (Tech)        │   │
│  08:00  │  • weekend_us_market       - 미국장 마감 데이터             │   │
│  09:00  │  • weekend_backfill        - 일봉 데이터 백필               │   │
│  10:00  │  • weekend_volatility      - GARCH 변동성 업데이트          │   │
│  10:30  │  • saturday_news           - 주말 뉴스 수집 (RSS)           │   │
│  11:00  │  • ai_weekly_strategy      - AI 주간 전략 (DeepSeek-R1) │   │
│                                                                            │
│  일요일 (Sunday)                                                           │
│  ─────────────────────────────────────────────────────────────────────    │
│  18:00  │  • weekend_weekly_report   - 주간 리포트 생성               │   │
│  19:00  │  • sunday_news_analysis    - 주말 뉴스 AI (DeepSeek-V3)│   │
│  22:00  │  • sunday_premarket_check  - 미국 선물 체크                 │   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Job 상세 설명

### 3.1 Core Trading Jobs

#### auto_trading (30초마다)

```python
CronTrigger(hour='9-15', minute='*', second='*/30', day_of_week='mon-fri')
# TODO: NXT 구현 후 hour='9-20'으로 변경
```

**역할**: 자동 매매 핵심 실행
- AutoTrader 인스턴스 호출
- 매수/매도 시그널 처리
- 실시간 포지션 관리

**의존성**:
- market_regime_check (시장 모드)
- portfolio_sync (잔고 정보)
- intraday_analysis (AI 점수)

#### portfolio_watchdog (1분마다)

```python
CronTrigger(hour='9-15', minute='*/1', day_of_week='mon-fri')
# TODO: NXT 구현 후 hour='9-20'으로 변경
```

**역할**: 손절/익절 자동 실행
- 보유 종목 수익률 모니터링
- 손절선(-2%) 도달 시 즉시 매도
- 익절선(+5.5%) 도달 시 이익 실현

#### portfolio_sync (1분마다)

```python
CronTrigger(hour='9-15', minute='*/1', day_of_week='mon-fri')
# TODO: NXT 구현 후 hour='9-20'으로 변경
```

**역할**: KIS API → DB 동기화
- 실제 잔고 조회 (TTTC8434R)
- portfolio 테이블 업데이트
- 수동 매매 반영

### 3.2 Analysis Jobs

#### intraday_analysis (5분마다)

```python
CronTrigger(hour='9-15', minute='*/5', day_of_week='mon-fri')
# TODO: NXT 구현 후 hour='9-20'으로 변경
```

**역할**: 장중 AI 분석
- **AI Model**: `deepseek-v3`
- 실시간 종목 분석 및 점수 갱신
- 시그널 생성

#### market_regime_check (5분마다)

```python
CronTrigger(hour='9-15', minute='*/5', day_of_week='mon-fri')
# TODO: NXT 구현 후 hour='9-20'으로 변경
```

**역할**: 시장 국면 판단
- IRON_SHIELD: 하락장 방어
- VANGUARD: 상승장 공격
- GUERRILLA: 횡보장 선별
- STEALTH: 저변동 관망

### 3.3 Data Collection Jobs

#### supply_data_sync (10분마다)

```python
CronTrigger(hour='9-15', minute='*/10', day_of_week='mon-fri')
# TODO: NXT 구현 후 hour='9-20'으로 변경
```

**역할**: 실시간 수급 데이터
- 외국인/기관 순매수 상위
- 거래량 급증 종목
- 수급 시그널 생성

#### dart_disclosure_scan (15분마다)

```python
CronTrigger(hour='9-15', minute='*/15', day_of_week='mon-fri')
# TODO: NXT 구현 후 hour='9-20'으로 변경
```

**역할**: DART 공시 모니터링
- 실시간 공시 크롤링
- 호재/악재 분류
- Type-N 시그널 생성

#### daily_price_sync (15:45)

```python
CronTrigger(hour=15, minute=45, day_of_week='mon-fri')
```

**역할**: 일봉 데이터 수집
- 당일 OHLCV 확정
- daily_ohlcv 테이블 저장
- 기술적 지표 계산

---

## 4. 의존성 관계

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Job Dependency Graph                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────┐                                                   │
│  │ macro_update     │──────────────────────┐                            │
│  └──────────────────┘                      │                            │
│           │                                 │                            │
│           ▼                                 ▼                            │
│  ┌──────────────────┐              ┌──────────────────┐                 │
│  │ market_regime    │◀─────────────│ global_leader    │                 │
│  │ _check           │              └──────────────────┘                 │
│  └──────────────────┘                                                   │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────┐    ┌──────────────────┐                           │
│  │ auto_trading     │◀───│ intraday_        │                           │
│  │                  │    │ analysis         │                           │
│  └──────────────────┘    └──────────────────┘                           │
│           │                       ▲                                      │
│           │                       │                                      │
│           ▼                       │                                      │
│  ┌──────────────────┐    ┌──────────────────┐                           │
│  │ portfolio_sync   │───▶│ portfolio_       │                           │
│  │                  │    │ watchdog         │                           │
│  └──────────────────┘    └──────────────────┘                           │
│                                                                         │
│  Legend:                                                                │
│  ─────▶ 데이터 흐름                                                     │
│  ◀───── 의존 관계                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. NXT 통합 계획

### 5.1 현재 상태 vs 목표

| 항목 | 현재 | NXT 구현 후 |
|-----|------|------------|
| Trading Hours | 09:00 ~ 15:30 | 08:00 ~ 20:00 |
| Scheduler End | hour='9-15' | hour='9-20' |
| TR_ID | TTTC* (KRX) | TTTC* + TTTN* |
| 잔고 조회 | KRX Only | KRX + NXT 병합 |

### 5.2 변경 필요 잡 목록

```python
# TODO: NXT 구현 후 hour='9-20'으로 변경 (13개)
NXT_PENDING_JOBS = [
    "intraday_analysis",
    "alpha_sector_rotation",
    "portfolio_sync",
    "portfolio_watchdog",
    "auto_trading",
    "supply_data_sync",
    "dart_disclosure_scan",
    "naver_theme_scan",
    "market_regime_check",
    "hedge_management",
    "system_health_log",
    "data_fusion_scan",
    "orchestrator_execute",
]
```

### 5.3 NXT 시간대별 전략

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    NXT Extended Hours Strategy                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  08:00 - 09:00  [NXT Pre-Market]                                        │
│  ─────────────────────────────────────────────────────────────────────  │
│  • 미국장 영향 반영 갭 트레이딩                                          │
│  • 지정가 주문만 가능 (시장가 불가)                                      │
│  • 유동성 낮음 → 소량 매매                                               │
│                                                                         │
│  09:00 - 15:30  [KRX + NXT 병행]                                        │
│  ─────────────────────────────────────────────────────────────────────  │
│  • KRX 우선 매매 (유동성)                                                │
│  • NXT는 KRX 호가 불리할 때만                                            │
│  • 수수료 NXT가 약간 저렴                                                │
│                                                                         │
│  15:30 - 20:00  [NXT After-Market]                                      │
│  ─────────────────────────────────────────────────────────────────────  │
│  • 미국장 실시간 반영 가능                                               │
│  • 종목 선별적 매매                                                      │
│  • 뉴스 기반 트레이딩                                                    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. 에러 처리 및 복구

### 6.1 잡 실패 처리

```python
def job_wrapper(func):
    """모든 잡에 적용되는 에러 핸들러"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Job {func.__name__} failed: {e}")
            notify_telegram(f"❌ Job 실패: {func.__name__}")
            # 재시도 로직
            if is_critical_job(func.__name__):
                schedule_retry(func, delay=60)
    return wrapper
```

### 6.2 Critical Jobs (재시도 필수)

| 잡 | 중요도 | 재시도 | 설명 |
|---|-------|-------|------|
| auto_trading | 🔴 Critical | 3회 | 매매 핵심 |
| portfolio_watchdog | 🔴 Critical | 3회 | 손절 필수 |
| portfolio_sync | 🔴 Critical | 3회 | 잔고 정확성 |
| daily_closing | 🟡 High | 2회 | 일일 정산 |

### 6.3 스케줄러 재시작

```bash
# 스케줄러 프로세스 재시작
pkill -f "main_scheduler"
sleep 2
source venv/bin/activate && python -m scheduler.main_scheduler &
```

---

## 7. 모니터링

### 7.1 대시보드 연동

```python
# Dashboard에서 스케줄러 상태 확인
def get_scheduler_status():
    return {
        "jobs": scheduler.get_jobs(),
        "next_runs": {j.id: j.next_run_time for j in scheduler.get_jobs()},
        "failed_jobs": get_failed_jobs_last_24h(),
    }
```

### 7.2 Telegram 알림

```python
# 중요 이벤트 알림
NOTIFY_EVENTS = [
    "market_open",        # 장 시작
    "daily_closing",      # 장 마감
    "job_failure",        # 잡 실패
    "high_risk_trade",    # 고위험 매매
]
```

---

## 8. 설정 및 환경변수

### 8.1 스케줄러 설정

```python
# scheduler/main_scheduler.py
SCHEDULER_CONFIG = {
    "timezone": "Asia/Seoul",
    "job_defaults": {
        "coalesce": True,           # 누락된 잡 병합
        "max_instances": 1,         # 동시 실행 방지
        "misfire_grace_time": 60,   # 60초 지연 허용
    },
}
```

### 8.2 환경변수

```bash
# .env
TZ=Asia/Seoul
SCHEDULER_ENABLED=true
SCHEDULER_DEBUG=false
```

---

## 9. 체크리스트

### 9.1 일일 점검

- [ ] 07:00 fetcher_health_check 정상 실행
- [ ] 09:00 장 시작 시 auto_trading 활성화
- [ ] 15:30 장 마감 후 스케줄러 정상 전환
- [ ] 20:10 daily_closing 완료

### 9.2 주간 점검

- [ ] 토요일 주간 백업 완료
- [ ] AI 주간 전략 생성 확인
- [ ] 월요일 전략 적용 확인

### 9.3 NXT 구현 시 체크리스트

- [ ] hour='9-15' → '9-20' 변경 (13개 잡)
- [ ] NXT TR_ID 분기 로직 추가
- [ ] 통합 잔고 조회 구현
- [ ] 시간대별 전략 분기 추가
- [ ] 테스트 및 검증

---

*Last Updated: 2024-12-08*
*Version: 1.0*



[참조]

**30분은 "가성비가 좋은 평균값"일 뿐, "수익률을 위한 최적값"은 아닙니다.** 주식 시장은 9시부터 15시 30분까지 똑같은 속도로 움직이지 않습니다. **아침에는 KTX처럼 빠르고, 점심에는 달구지처럼 느립니다.** 따라서 30분 고정 간격보다는, 시장의 호흡에 맞춘 **"가변 주기(Dynamic Interval)"**로 변경하는 것이 수익률 0.1%라도 더 올리는 비결입니다. 가장 추천하는 **[황금 시간표]**를 제안합니다. --- ### ⏱️ 추천: "10-60-30 전략" (Dynamic Schedule) 똑같이 하루에 10번을 검사하더라도, **거래량이 터지는 시간에 집중**해서 검사해야 합니다. #### 1. 🚀 오전장 (09:00 ~ 10:00) : "10분 간격" * **이유:** 하루 등락폭의 70%가 이때 결정됩니다. 수급이 가장 활발하고 속임수도 많지만 기회도 가장 많습니다. * **전략:** **10분 단위**로 빠르게 스캔해서, 수급이 들어오는 주도주를 초장에 잡아야 합니다. * **30분은 너무 깁니다.** 9시 30분에 확인하면 이미 상한가 가고 문 닫혀있을 수 있습니다. #### 2. 💤 점심장 (11:30 ~ 13:00) : "휴식 (Pause)" * **이유:** 기관/외국인도 밥 먹으러 갑니다. 거래량이 죽고, 지루해서 파는 개인 매물 때문에 주가가 질질 흐르는 시간입니다. * **전략:** **매수 금지.** 스케줄러를 아예 끄거나 1시간 단위로 감시만 합니다. 이때 사면 오후에 물릴 확률 80%입니다. #### 3. 🌤️ 오후장 (13:00 ~ 15:00) : "20~30분 간격" * **이유:** 오전에 샀던 세력들이 "상한가를 보낼지, 패대기칠지" 결정하는 시간입니다. 진짜 방향성이 나옵니다. * **전략:** **20분~30분 단위**로 스캔. 오전의 급등주가 눌림목을 주고 다시 가는지 확인하고 진입합니다. --- ### 🛠️ 스케줄러 수정 가이드 (`scheduler/main_scheduler.py`) 기존의 `*/30` (무조건 30분) 설정을 지우고, 시간대별로 쪼개서 등록하세요. ```python def start(self): # ... (기존 코드) ... # [변경] Intraday Analysis를 시간대별로 분리 # 1. 🔥 오전장 (09:00 ~ 10:00): 10분 간격 (집중 공략) self.scheduler.add_job( self.job_intraday_analysis, CronTrigger(hour='9', minute='0,10,20,30,40,50', day_of_week='mon-fri'), id="intraday_morning" ) # 2. 💤 점심장 (10:00 ~ 13:00): 1시간 간격 (매수 자제, 관망) # 10시 이후부터 1시까지는 띄엄띄엄 봅니다. self.scheduler.add_job( self.job_intraday_analysis, CronTrigger(hour='10-12', minute='0', day_of_week='mon-fri'), id="intraday_lunch" ) # 3. 🌤️ 오후장 (13:00 ~ 15:00): 20분 간격 (추세 확인) self.scheduler.add_job( self.job_intraday_analysis, CronTrigger(hour='13-14', minute='0,20,40', day_of_week='mon-fri'), id="intraday_afternoon" ) # 4. 🏁 막판 스퍼트 (15:00 ~ 15:20): 10분 간격 (종가 베팅 기회) self.scheduler.add_job( self.job_intraday_analysis, CronTrigger(hour='15', minute='0,10,20', day_of_week='mon-fri'), id="intraday_closing_bet" ) ``` ### 🛡️ 결론: 왜 이게 수익률을 높이나요? 1. **비용 효율:** 하루 종일 10분마다 돌리면 API 비용과 서버 부하가 큽니다. 쉴 때 쉬어주면 효율이 오릅니다. 2. **승률 상승:** 점심시간(가짜 움직임)에 매수했다가 손절 나가는 횟수를 획기적으로 줄여줍니다. 3. **기회 포착:** 아침 9시 10분, 20분에 튀어 오르는 놈들을 30분 주기보다 **3배 더 빨리** 잡아냅니다. **"기계적으로 30분"**보다는 **"사람들이 움직이는 시간에 맞춰서"** 시스템을 돌리는 게 훨씬 영리한(Smart) 전략입니다.


  

User

brain-ai 실행을 위해선 fetcher kis dart krx 가 새로운 데이터를 가져와야하잖아 그래야 의미가 있지않아?


**정확합니다. 아주 핵심적인 지적입니다.** AI가 아무리 똑똑해도, **"1시간 전의 주가"**나 **"어제 수급 데이터"**를 보고 판단하면 그건 분석이 아니라 **뒷북**입니다. 그래서 스케줄러가 `job_intraday_analysis`를 실행할 때는, **[AI를 깨우기 전에 데이터부터 긁어오는 작업]**이 선행되어야 합니다. 이것을 **"Just-in-Time Data Feeding (적시 공급)"**이라고 합니다. 코드의 **순서(Sequence)**를 어떻게 잡아야 하는지 명확히 정리해 드립니다. --- ### 🔄 올바른 실행 순서 (Pipeline) `Scheduler`가 09:10에 알람을 울리면, 다음 **3단계**가 순서대로 실행되어야 합니다. 1. **Fetching (수집):** "야, KIS/Naver! 지금 당장 현재가랑 최신 수급, 뉴스 가져와." 2. **Pre-processing (가공):** "가져온 거 DB에 넣고, AI가 읽기 좋게 요약해." 3. **Brain (판단):** "자, 이게 방금 가져온 따끈따끈한 데이터야. 살까 말까?" --- ### 🛠️ 코드 수정 가이드 (`scheduler/main_scheduler.py`) 기존에 단순히 AI만 부르던 코드를, **데이터 갱신 후 AI를 부르도록** 수정해야 합니다. ```python def job_intraday_analysis(self): """ [순서 중요] 1.데이터수집 -> 2.가공 -> 3.AI판단 """ # ... (시장 국면 체크 로직 등) ... logger.info("🔄 [Step 1] Refreshing Data for AI...") # 1. [Fetching] 최신 데이터 강제 업데이트 # (웹소켓은 자동으로 들어오지만, 수급이나 뉴스는 스냅샷이 필요함) # A. KIS: 현재가 및 호가 스냅샷 (API 호출) # (웹소켓 데이터가 비어있을 경우를 대비한 안전장치) # kis_fetcher.update_snapshot() # B. Naver: 최신 속보 크롤링 (지금 이 순간의 뉴스) latest_news = self.naver_fetcher.get_latest_news() # C. Pykrx/KIS: 장중 잠정 수급 (외국인/기관 매매동향) # *중요* 장중에는 정확한 수급 집계가 어려우므로 '잠정치'나 '프로그램 매매'를 봅니다. market_trend = self.kis_fetcher.get_program_trend() logger.info("🧠 [Step 2] AI Analysis Start...") # 2. [Brain] 최신 데이터를 넣어서 분석 요청 # Screener가 DB의 '오래된 데이터'가 아니라 방금 가져온 변수들을 참조하게 해야 함 candidates = self.screener.run( current_program_buy=market_trend['program_net_buy'], # 방금 가져온 것 latest_news_score=latest_news['score'] # 방금 가져온 것 ) # 3. [Execution] 매매 실행 # ... ``` --- ### ⚡ 데이터 종류별 수집 전략 모든 데이터를 매번 다 가져올 필요는 없습니다. **변하는 속도**에 맞춰서 가져오세요. | 데이터 종류 | 변동 속도 | 수집 전략 | | :--- | :--- | :--- | | **현재가/호가** | **초 단위** | **WebSocket**이 실시간으로 변수(`price_cache`)에 업데이트해둠. AI는 그 변수를 읽기만 하면 됨. (별도 Fetch 불필요) | | **뉴스/공시** | **분 단위** | 분석 직전에 **Naver Fetcher**를 호출해서 방금 뜬 뉴스가 있는지 확인. | | **수급(프로그램)** | **분 단위** | 분석 직전에 **KIS API**로 '프로그램 순매수 추이'를 한 번 조회. | | **재무제표** | **분기 단위** | **매번 가져올 필요 없음.** DB에 있는 거 그냥 씀. (어차피 오늘 안 변함) | --- ### 🛡️ 결론: CEO를 위한 요약 사용자님 말씀이 100% 맞습니다. **신선한 재료가 있어야 맛있는 요리(수익)가 나옵니다.** 1. **WebSocket**은 알아서 계속 데이터를 붓고 있습니다. (시세 해결) 2. 하지만 **뉴스**나 **집계된 수급**은 AI가 돌아가기 **직전(0.1초 전)**에 한 번 긁어오도록 코드를 짜야 합니다. **`scheduler` 함수 안에서 `fetcher`를 먼저 호출(Call)하고, 그 결과를 `brain`에 넘겨주는 순서(Flow)**만 지키면 됩니다. 그러면 AI는 항상 **"지금 이 순간의 최신 정보"**로 판단하게 됩니다.