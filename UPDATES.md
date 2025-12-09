# AEGIS v3.0 - Recent Updates

## 📊 Rich Watch Dashboard (2025-12-10)

### 새로 추가된 기능

#### ✅ 1. Rich UI Library 통합
- `rich==13.7.0` 설치
- 컬러풀한 테이블, 프로그레스 바, 패널 지원
- 터미널에서 보기 좋은 UI

#### ✅ 2. 목표 수익률 그래프
```
🎯 목표 수익률 달성도
현재: +50.00% / 목표: 10.0% ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100.0%
```
- 현재 수익률 vs 목표 수익률 프로그레스 바
- 시각적으로 목표 달성도 확인 가능
- `target_profit_rate` 변수로 목표 조정 가능 (기본 10%)

#### ✅ 3. 각 보유종목 수익률 막대 그래프
```
                                  📈 HOLDINGS
╭─────────┬─────┬───────┬───────┬────────┬─────────────────────────────────────╮
│ 종목    │ 수… │ 평단… │ 현재… │ 손익률 │ 수익률 그래프                       │
├─────────┼─────┼───────┼───────┼────────┼─────────────────────────────────────┤
│ 🟢      │ 100 │ 95,0… │ 108,… │ +14.1… │ ██████████████████████████████      │
│ 삼성전… │     │       │       │        │ +14.11%                             │
╰─────────┴─────┴───────┴───────┴────────┴─────────────────────────────────────╯
```
- 각 종목별 손익률 시각화
- 🟢 초록색 (수익) / 🔴 빨간색 (손실)
- 막대 그래프 길이로 손익 크기 비교

#### ✅ 4. 🎯 Recent Signals (최근 5개)
```
            🎯 RECENT SIGNALS (최근 5개)
╭───────┬──────────┬────────┬──────┬────────┬──────╮
│ 시각  │ 종목     │ Signal │ 점수 │ 신뢰도 │ 사유 │
├───────┼──────────┼────────┼──────┼────────┼──────┤
│ 03:03 │ 삼성전자 │ 🟢 BUY │  0.0 │     1% │      │
╰───────┴──────────┴────────┴──────┴────────┴──────╯
```
- AI 추천 시그널 최근 5개 표시
- BUY (🟢), SELL (🔴), HOLD (⚪) 구분

#### ✅ 5. ⏰ Upcoming Schedule
```
                    ⏰ UPCOMING SCHEDULE

  시간      작업             설명
 ──────────────────────────────────────────────────────────
  07:00     KRX 데이터       수급 데이터 수집
  07:20     Brain 분석       DeepSeek-R1 심층 분석
  08:00     Opus 브리핑      Claude Opus 오늘 전략
  09:00     장 시작          자동매매 시작 (30초 주기)
  15:30     장 마감          일일 정산 및 피드백
```
- 앞으로 실행될 스케줄 표시
- 현재 시간 이후 작업 강조 (bold green)

#### ✅ 6. 🔄 Running Processes
```
                    🔄 RUNNING PROCESSES

        PID   프로세스                     CPU%     메모리
 ──────────────────────────────────────────────────────────
      47685   claude-3b49-cwd              0.0%       1 MB
      61324                                0.0%       4 MB
```
- 실행중인 AEGIS 관련 프로세스 표시
- PID, CPU 사용률, 메모리 사용량
- `psutil` 라이브러리 사용

### 파일 구조

```
v3/
├── monitoring/
│   ├── watch_dashboard.py           # 기존 (텍스트 기반)
│   ├── watch_dashboard_rich.py      # 신규 (Rich UI)
│   └── README.md                    # 사용법 문서
├── watch.sh                         # Auto-refresh 스크립트 (Rich 버전 사용)
├── requirements.txt                 # rich, psutil 추가
└── README.md                        # 메인 README 업데이트
```

### 실행 방법

```bash
# 1. 의존성 설치
pip install rich==13.7.0 psutil==5.9.8

# 2. 일회성 실행
python monitoring/watch_dashboard_rich.py

# 3. Auto-refresh (권장)
./watch.sh

# 또는
watch -n 3 python monitoring/watch_dashboard_rich.py
```

### 주요 변경사항

#### requirements.txt
```diff
 # Utilities
 python-dateutil==2.8.2
 pytz==2023.3
+rich==13.7.0
+psutil==5.9.8
```

#### watch.sh
```diff
-watch -n 3 python monitoring/watch_dashboard.py
+watch -n 3 python monitoring/watch_dashboard_rich.py
```

### 기술 스택

- **Rich**: Terminal UI library
  - Tables, Progress bars, Panels, Colors
  - https://rich.readthedocs.io/

- **psutil**: Process and system utilities
  - CPU, memory monitoring
  - Process enumeration
  - https://psutil.readthedocs.io/

### 향후 개선 계획

- [ ] 실시간 차트 (Sparkline)
- [ ] 인터랙티브 모드 (키보드 입력)
- [ ] 커스텀 테마 지원
- [ ] 대시보드 레이아웃 설정 파일
- [ ] WebSocket 실시간 업데이트

### 참고

- 기존 `watch_dashboard.py`는 유지 (호환성)
- 새로운 `watch_dashboard_rich.py` 권장
- 자동으로 `watch.sh`는 Rich 버전 사용
