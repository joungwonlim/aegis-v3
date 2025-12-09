# AEGIS v3.2 - Database Design Specification

> 데이터베이스 상세 설계서 (v3.0 구조 + v2.0 디테일 통합)

---

## 0. 데이터 단위 규약 (Critical)

> **Fetcher 데이터 입력 시 반드시 준수할 단위 규약**

| 데이터 유형 | 단위 | 예시 | 주의사항 |
|-------------|------|------|----------|
| **주가 (Price)** | 원 (KRW) | `52300` | 소수점 없음, Integer |
| **거래량 (Volume)** | 주 (shares) | `1234567` | BigInteger |
| **수급 (Net Buy)** | 주 (shares) | `50000`, `-30000` | **금액(원) 아님!** pykrx 기준 |
| **시가총액** | 원 (KRW) | `300000000000000` | BigInteger (삼성전자 ~300조) |
| **수익률** | % (백분율) | `5.23`, `-2.1` | Float, 100 곱한 값 |
| **환율** | 원/달러 | `1380.50` | Float |
| **지수** | 포인트 | `2650.25` | Float |
| **비율** | 소수 (0~1) | `0.15` | 15%는 0.15로 저장 |

### 수급 데이터 단위 통일 규칙

```python
# ❌ 잘못된 예 (금액 단위)
foreigner_net_buy = 50_000_000_000  # 500억 원 (X)

# ✅ 올바른 예 (수량 단위)
foreigner_net_buy = 1_000_000  # 100만 주 (O)

# Fetcher에서 데이터 입력 시:
# - pykrx: get_market_trading_volume_by_investor() → 주 단위 (그대로 사용)
# - KIS API: 금액 단위로 오면 → 종가로 나눠서 주 단위로 변환
```

---

## 1. 스키마 구조 (6 Schemas)

```
┌─────────────────────────────────────────────────────────────┐
│                    AEGIS v3.2 Database                       │
├─────────────────────────────────────────────────────────────┤
│  [SCHEMA 1] MARKET     - 시장 데이터 (연료)                   │
│  [SCHEMA 2] ACCOUNT    - 자산 관리 (지갑)                     │
│  [SCHEMA 3] BRAIN      - AI 분석 (두뇌)                       │
│  [SCHEMA 4] TRADE      - 매매 기록 (행동)                     │
│  [SCHEMA 5] SYSTEM     - 시스템 관제 (관제탑)                 │
│  [SCHEMA 6] ANALYTICS  - 백테스트 (연구소)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. [SCHEMA 1] MARKET - 시장 데이터

### 2.1 `stocks` - 종목 마스터

| 컬럼 | 타입 | 단위 | 설명 | Source |
|------|------|------|------|--------|
| `code` | String(20) | - | **PK.** 종목코드 (예: 005930) | KRX |
| `name` | String(100) | - | 종목명 | KRX |
| `market` | String(10) | - | KOSPI / KOSDAQ | KRX |
| `sector` | String(100) | - | 업종 | KRX |
| `market_cap` | BigInteger | **원** | 시가총액 | pykrx |
| `is_kosdaq150` | Boolean | - | 코스닥150 편입 여부 | KRX |
| `theme_tags` | String(255) | - | AI 테마 태그 (#AI #반도체) | Brain |
| `overhang_ratio` | Float | **0~1** | CB/BW 희석 비율 (0.15 = 15%) | DART |
| `is_active` | Boolean | - | 거래 가능 여부 | KRX |

**인덱스:**
```sql
CREATE INDEX idx_stock_sector ON stocks(sector);
CREATE INDEX idx_stock_market_cap ON stocks(market_cap);
CREATE INDEX idx_stock_market_active ON stocks(market, is_active);
```

---

### 2.2 `daily_prices` - 일별 시세 + 수급

> **핵심 테이블: Type-D (수급 전략)의 데이터 소스**

| 컬럼 | 타입 | 단위 | 설명 | Source |
|------|------|------|------|--------|
| `stock_code` | String(20) | - | **PK.** FK → stocks.code | - |
| `date` | Date | - | **PK.** 거래일 | - |
| `open` | Integer | **원** | 시가 | pykrx |
| `high` | Integer | **원** | 고가 | pykrx |
| `low` | Integer | **원** | 저가 | pykrx |
| `close` | Integer | **원** | 종가 | pykrx |
| `volume` | BigInteger | **주** | 거래량 | pykrx |
| `change_rate` | Float | **%** | 등락률 (5.23 = +5.23%) | pykrx |
| `foreigner_net_buy` | BigInteger | **주** | 외국인 순매수 | pykrx |
| `institution_net_buy` | BigInteger | **주** | 기관계 순매수 | pykrx |
| `pension_net_buy` | BigInteger | **주** | 연기금 순매수 (가중치 +30) | pykrx |
| `financial_invest_net` | BigInteger | **주** | 금융투자 순매수 (가중치 +5) | pykrx |
| `insurance_net_buy` | BigInteger | **주** | 보험 순매수 | pykrx |
| `trust_net_buy` | BigInteger | **주** | 투신 순매수 (가중치 +15) | pykrx |
| `program_net_buy` | BigInteger | **주** | 프로그램 순매수 | pykrx |
| `corporate_net_buy` | BigInteger | **주** | 기타법인 순매수 (가중치 +10) | pykrx |

**수급 데이터 Fetcher 규칙:**
```python
# pykrx 사용 시 (권장)
from pykrx import stock
df = stock.get_market_trading_volume_by_investor(date, date, code)
# → 이미 "주" 단위로 반환됨, 그대로 저장

# KIS API 사용 시 (금액 → 주 변환 필요)
net_buy_krw = api_response['ntby_qty']  # 순매수금액 (원)
close_price = api_response['stck_clpr']  # 종가
net_buy_shares = net_buy_krw // close_price  # 주 단위로 변환
```

**인덱스 (성능 최적화):**
```sql
-- 기본 조회용
CREATE INDEX idx_daily_code_date ON daily_prices(stock_code, date);

-- 수급 신호 포착용 (Partial Index)
CREATE INDEX idx_daily_pension_signal
ON daily_prices(date, pension_net_buy)
WHERE pension_net_buy > 0;

CREATE INDEX idx_daily_foreign_signal
ON daily_prices(date, foreigner_net_buy)
WHERE foreigner_net_buy > 0;

-- 양매수 신호 (외국인 + 기관 동시 매수)
CREATE INDEX idx_daily_dual_buy
ON daily_prices(date)
WHERE foreigner_net_buy > 0 AND institution_net_buy > 0;
```

---

### 2.3 `market_candles` - 분봉 데이터

> **실시간 차트용 (TimescaleDB 하이퍼테이블 권장)**

| 컬럼 | 타입 | 단위 | 설명 | Source |
|------|------|------|------|--------|
| `time` | DateTime(tz) | - | **PK.** 캔들 시작 시간 | KIS |
| `symbol` | String(20) | - | **PK.** 종목코드 | KIS |
| `interval` | String(5) | - | **PK.** 1m, 5m, 15m, 1h, 1d | - |
| `open` | Float | **원** | 시가 | KIS |
| `high` | Float | **원** | 고가 | KIS |
| `low` | Float | **원** | 저가 | KIS |
| `close` | Float | **원** | 종가 | KIS |
| `volume` | BigInteger | **주** | 거래량 | KIS |

---

### 2.4 `market_macro` - 매크로 지표

| 컬럼 | 타입 | 단위 | 설명 | Source |
|------|------|------|------|--------|
| `date` | Date | - | **PK.** 날짜 | - |
| `us_krw` | Float | **원/달러** | 환율 (1380.50) | yfinance |
| `nasdaq` | Float | **포인트** | 나스닥 종합 | yfinance |
| `sox` | Float | **포인트** | 필라델피아 반도체 | yfinance |
| `vix` | Float | **포인트** | VIX 공포지수 | yfinance |
| `fear_greed` | Integer | **0~100** | CNN Fear & Greed | CNN API |

---

## 3. [SCHEMA 2] ACCOUNT - 자산 관리

### 3.1 `account_snapshots` - 계좌 히스토리

| 컬럼 | 타입 | 단위 | 설명 | Source |
|------|------|------|------|--------|
| `id` | Integer | - | **PK.** Auto Increment | - |
| `timestamp` | DateTime(tz) | - | 스냅샷 시간 | - |
| `deposit` | BigInteger | **원** | 예수금 | KIS |
| `total_asset` | BigInteger | **원** | 총 평가금액 | KIS |
| `net_profit_today` | BigInteger | **원** | 당일 실현손익 | KIS |
| `total_return_rate` | Float | **%** | 총 수익률 | 계산 |

---

### 3.2 `portfolio` - 보유 종목

| 컬럼 | 타입 | 단위 | 설명 | Source |
|------|------|------|------|--------|
| `stock_code` | String(20) | - | **PK.** 종목코드 | - |
| `stock_name` | String(100) | - | 종목명 | - |
| `quantity` | Integer | **주** | 보유 수량 | KIS |
| `avg_price` | Float | **원** | 평균 매입가 | KIS |
| `current_price` | Float | **원** | 현재가 | KIS |
| `profit_rate` | Float | **%** | 수익률 | 계산 |
| `bought_at` | DateTime(tz) | - | 최초 매수 시점 | 기록 |
| `pyramid_stage` | Integer | **0~3** | 피라미딩 단계 (0:정찰, 1:본대, 2:불타기) | Brain |
| `pyramid_target` | Float | **원** | 다음 피라미딩 목표가 | Brain |
| `max_price_reached` | Float | **원** | 보유 중 최고가 (트레일링 기준) | 계산 |
| `sell_stage` | Integer | **0~2** | 분할매도 단계 | Brain |
| `strategy_type` | String(50) | - | 전략 유형 (Type-D 등) | Brain |
| `ai_action` | String(20) | - | AI 조언 (HOLD/SELL) | Brain |
| `stop_loss_price` | Float | **원** | 손절가 | Brain |
| `target_price` | Float | **원** | 목표가 | Brain |
| `last_updated` | DateTime(tz) | - | 마지막 업데이트 | - |

---

## 4. [SCHEMA 3] BRAIN - AI 분석

### 4.1 `daily_picks` - 일일 추천 종목

| 컬럼 | 타입 | 단위 | 설명 |
|------|------|------|------|
| `id` | Integer | - | **PK.** |
| `date` | Date | - | 추천일 |
| `stock_code` | String(20) | - | 종목코드 |
| `strategy_name` | String(50) | - | 선정 전략 |
| `rank` | Integer | - | 우선순위 (1이 최우선) |
| `quant_score` | Integer | **0~100** | Quant 점수 |
| `ai_score` | Integer | **0~100** | AI 점수 |
| `expected_entry_price` | Float | **원** | 예상 진입가 |
| `ai_comment` | Text | - | AI 코멘트 |
| `is_executed` | Boolean | - | 실제 매수 여부 |

---

### 4.2 `daily_analysis_logs` - 분석 파이프라인 로그

| 컬럼 | 타입 | 단위 | 설명 |
|------|------|------|------|
| `id` | Integer | - | **PK.** |
| `date` | Date | - | 분석일 |
| `stock_code` | String(20) | - | 종목코드 |
| `step_1_quant_score` | Integer | **0~100** | 1단계: Quant 점수 |
| `step_2_ai_score` | Integer | **0~100** | 2단계: AI 점수 |
| `step_3_risk_check` | String(20) | - | 3단계: APPROVE/REJECT |
| `final_score` | Integer | **0~100** | 최종 점수 |
| `final_decision` | String(20) | - | BUY/HOLD/WAIT |
| `risk_analysis` | Text | - | DeepSeek 리스크 분석 |

---

### 4.3 `intel_feed` - 뉴스/공시 분석

| 컬럼 | 타입 | 단위 | 설명 | Source |
|------|------|------|------|--------|
| `id` | Integer | - | **PK.** | - |
| `created_at` | DateTime(tz) | - | 수집 시간 | - |
| `source` | String(20) | - | DART/NAVER/GOOGLE | Fetcher |
| `category` | String(50) | - | 공시유형/뉴스카테고리 | - |
| `title` | Text | - | 제목 | - |
| `stock_code` | String(20) | - | 관련 종목 | - |
| `sentiment_score` | Integer | **-100~100** | 감성 점수 | AI |
| `impact_level` | String(20) | - | HIGH/MEDIUM/LOW | AI |
| `ai_summary` | Text | - | AI 요약 | AI |

---

### 4.4 `market_regime` - 시장 국면

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `check_time` | DateTime(tz) | **PK.** 체크 시점 |
| `mode` | String(20) | IRON_SHIELD / VANGUARD / NORMAL |
| `vix_level` | Float | VIX 수치 |
| `trend_direction` | String(10) | UP / DOWN / SIDEWAYS |

---

## 5. [SCHEMA 4] TRADE - 매매 기록

> **Simple is Best**: 주문/체결 분리 대신 `trade_logs` 통합 테이블 사용

### 5.1 `trade_logs` - 매매 기록 (통합)

> **매수/매도 시점의 AI 판단 근거를 모두 기록 (한국전력 사태 방지)**

| 컬럼 | 타입 | 단위 | 설명 |
|------|------|------|------|
| `id` | Integer | - | **PK.** |
| `stock_code` | String(20) | - | FK → stocks.code |
| `trade_type` | String(10) | - | BUY / SELL |
| `buy_price` | Float | **원** | 매수가 |
| `sell_price` | Float | **원** | 매도가 (매도 시) |
| `quantity` | Integer | **주** | 수량 |
| `profit_rate` | Float | **%** | 수익률 (매도 시) |
| `reason` | Text | - | AI 매수/매도 이유 |
| `strategy` | String(50) | - | 매매 전략 (AI_SUPPLY, AI_SCORE, MANUAL) |
| `ai_score` | Integer | **0~100** | 매수 시점 AI 점수 |
| `decision_context` | JSONB | - | AI 판단 컨텍스트 (수급, 기술적지표, 매크로 등) |
| `pyramid_stage` | Integer | **0~3** | 피라미딩 단계 |
| `market_regime` | String(20) | - | 시장 국면 (BULL/BEAR/SIDEWAYS) |
| `confidence_score` | Float | **0~100** | AI 확신도 |
| `model_used` | String(50) | - | **🔴 v3.0 필수** 사용된 AI 모델 (deepseek-chat, deepseek-reasoner, opus) |
| `executed_at` | DateTime(tz) | - | 체결 시간 |

---

### 5.2 `trade_feedbacks` - 매매 피드백

> **Adaptive Score Optimizer가 학습하는 핵심 데이터**
> **핵심 원칙: "왜 샀는가? 왜 팔았는가? 결과는 어땠는가?"**

| 컬럼 | 타입 | 단위 | 설명 |
|------|------|------|------|
| `id` | Integer | - | **PK.** |
| `trade_log_id` | Integer | - | FK → trade_logs.id |
| `stock_code` | String(20) | - | 종목코드 |
| `is_success` | Boolean | - | 수익 여부 |
| `actual_profit_rate` | Float | **%** | 실제 수익률 |
| `holding_days` | Integer | **일** | 보유 기간 |
| `buy_reason_valid` | Boolean | - | 매수 이유가 유효했는가? |
| `sell_timing_score` | Integer | **1~10** | 매도 타이밍 점수 |
| `market_condition_at_buy` | String(50) | - | 매수 시점 시장 상황 |
| `market_condition_at_sell` | String(50) | - | 매도 시점 시장 상황 |
| `lessons_learned` | Text | - | 이번 거래에서 배운 점 |
| `improvement_suggestions` | Text | - | 시스템 개선 제안 |
| `optimal_sell_price` | Float | **원** | 최적 매도가 (사후 분석) |
| `missed_profit_rate` | Float | **%** | 놓친 수익률 (최고점 대비) |
| `risk_reward_ratio` | Float | - | 리스크/리워드 비율 |
| `ai_analysis` | JSONB | - | AI가 분석한 거래 피드백 |
| `feedback_applied` | Integer | - | **🔴 v3.0 필수** 점수 보정값 (+3, -2 등) |
| `analyzed_at` | DateTime(tz) | - | 분석 시점 |

---

## 6. [SCHEMA 5] SYSTEM - 시스템 관제

### 6.1 `system_config` - 설정

| Key | 설명 | 예시 값 |
|-----|------|---------|
| `AI_TRADING_ENABLED` | AI 자동매매 활성화 | `true` / `false` |
| `MAX_POSITION_SIZE` | 최대 포지션 비율 | `0.1` (10%) |
| `DAILY_LOSS_LIMIT` | 일일 손실 한도 | `0.015` (1.5%) |
| `TELEGRAM_NOTI` | 텔레그램 알림 | `true` / `false` |

---

### 6.2 `fetcher_health_logs` - Fetcher 상태

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | Integer | **PK.** |
| `fetcher_name` | String(50) | pykrx / kis / dart / yfinance |
| `status` | String(20) | OK / ERROR / SKIP |
| `records_count` | Integer | 수집된 레코드 수 |
| `last_run` | DateTime(tz) | 마지막 실행 시간 |
| `message` | Text | 에러 메시지 |

---

### 6.3 `strategy_states` - 전략 가중치

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `strategy_name` | String(50) | **PK.** Type-D, Type-E 등 |
| `current_weight` | Float | 현재 가중치 (0.5 ~ 1.5) |
| `win_streak` | Integer | 연속 성공 횟수 |
| `loss_streak` | Integer | 연속 실패 횟수 |
| `is_active` | Boolean | 활성화 여부 |

---

## 7. [SCHEMA 6] ANALYTICS - 백테스트

### 7.1 `backtest_results` - 백테스트 결과

| 컬럼 | 타입 | 단위 | 설명 |
|------|------|------|------|
| `id` | Integer | - | **PK.** |
| `strategy_name` | String(50) | - | 전략명 |
| `run_at` | DateTime(tz) | - | 실행 시간 |
| `start_date` | Date | - | 테스트 시작일 |
| `end_date` | Date | - | 테스트 종료일 |
| `total_return` | Float | **%** | 총 수익률 |
| `mdd` | Float | **%** | 최대 낙폭 |
| `win_rate` | Float | **%** | 승률 |
| `avg_return` | Float | **%** | 평균 수익률 |
| `sharpe_ratio` | Float | - | 샤프 비율 |
| `profit_factor` | Float | - | 손익비 |
| `grade` | String(10) | - | S/A/B/C/F |

---

## 8. ERD (Entity Relationship)

```
┌─────────────┐       ┌──────────────┐
│   stocks    │───┬───│ daily_prices │
└─────────────┘   │   └──────────────┘
       │          │
       │          │   ┌──────────────┐
       └──────────┼───│  portfolio   │
                  │   └──────────────┘
                  │
                  │   ┌──────────────┐
                  ├───│ daily_picks  │
                  │   └──────────────┘
                  │
                  │   ┌──────────────┐
                  └───│ trade_orders │───│ trade_executions │
                      └──────────────┘   └──────────────────┘
                             │
                             └───│ trade_feedbacks │
```

---

---

## 8. [SCHEMA 7] LEARNING - AI 학습 (Korean Market Traps)

> **v3.2 신규 추가: 한국 시장 함정 감지 및 AI 학습 시스템**

### 8.1 `trap_patterns` - 함정 패턴 학습

| 컬럼 | 타입 | 단위 | 설명 |
|------|------|------|------|
| `id` | Integer | - | **PK.** Auto Increment |
| `trap_type` | String(50) | - | **Unique.** 함정 타입 (fake_rise, gap_overheat, program_dump 등) |
| `weight` | Float | **0.0~1.0** | 가중치 (초기: 0.80, 학습으로 조정) |
| `total_count` | Integer | - | 전체 감지 횟수 |
| `correct_count` | Integer | - | 정확히 맞춘 횟수 |
| `accuracy` | Float | **%** | 정확도 (correct_count / total_count × 100) |
| `created_at` | DateTime(tz) | - | 생성 시간 |
| `updated_at` | DateTime(tz) | - | 마지막 업데이트 |

**10가지 함정 타입**:
```python
TRAP_TYPES = [
    "fake_rise",           # 수급 이탈 (95% 신뢰도)
    "gap_overheat",        # 갭 과열 (90% 신뢰도)
    "program_dump",        # 프로그램 매도 가속 (85% 신뢰도)
    "sell_on_news",        # 뉴스 후 음봉 (80% 신뢰도)
    "hollow_rise",         # 거래량 없는 상승 (75% 신뢰도)
    "resistance_wall",     # 매도벽 (70% 신뢰도)
    "sector_decouple",     # 섹터 디커플링 (65% 신뢰도)
    "fx_impact",           # 환율 쇼크 (60% 신뢰도)
    "ma_resistance",       # 장기 이평선 저항 (55% 신뢰도)
    "dilution_day"         # 오버행 상장 (90% 신뢰도)
]
```

**인덱스**:
```sql
CREATE UNIQUE INDEX idx_trap_type ON trap_patterns(trap_type);
CREATE INDEX idx_trap_accuracy ON trap_patterns(accuracy DESC);
```

---

### 8.2 `trade_feedback` - 거래 피드백 (함정 감지)

| 컬럼 | 타입 | 단위 | 설명 |
|------|------|------|------|
| `id` | Integer | - | **PK.** Auto Increment |
| `trade_date` | Date | - | 거래일 |
| `stock_code` | String(10) | - | 종목코드 |
| `stock_name` | String(100) | - | 종목명 |
| **[감지 정보]** | | | |
| `trap_detected` | Boolean | - | 함정 감지 여부 |
| `trap_type` | String(50) | - | 함정 타입 (FK → trap_patterns.trap_type) |
| `trap_confidence` | Float | **0.0~1.0** | 감지 신뢰도 |
| `trap_reason` | Text | - | 감지 이유 (로깅용) |
| **[결정 정보]** | | | |
| `avoided_buy` | Boolean | - | 매수 회피 여부 |
| `ai_recommendation` | String(20) | - | AVOID / WAIT / REDUCE_SIZE |
| **[실제 결과]** | | | |
| `actual_result` | String(20) | - | CORRECT (맞음) / WRONG (틀림) |
| `price_at_decision` | Integer | **원** | 결정 시점 가격 |
| `price_after_1h` | Integer | **원** | 1시간 후 가격 |
| `price_at_close` | Integer | **원** | 종가 |
| `price_change_pct` | Float | **%** | 실제 가격 변화율 |
| **[학습 메타데이터]** | | | |
| `learned` | Boolean | - | 학습 완료 여부 |
| `weight_before` | Float | **0.0~1.0** | 학습 전 가중치 |
| `weight_after` | Float | **0.0~1.0** | 학습 후 가중치 |
| `created_at` | DateTime(tz) | - | 생성 시간 |
| `updated_at` | DateTime(tz) | - | 마지막 업데이트 |

**학습 로직**:
```python
# CORRECT (함정 감지가 맞았을 때)
if actual_result == "CORRECT":
    new_weight = min(weight + 0.01, 0.99)  # 최대 0.99

# WRONG (함정 감지가 틀렸을 때)
if actual_result == "WRONG":
    new_weight = max(weight - 0.02, 0.30)  # 최소 0.30
```

**인덱스**:
```sql
CREATE INDEX idx_feedback_date_code ON trade_feedback(trade_date, stock_code);
CREATE INDEX idx_feedback_trap_type ON trade_feedback(trap_type) WHERE trap_detected = true;
CREATE INDEX idx_feedback_result ON trade_feedback(actual_result, trap_type);
CREATE INDEX idx_feedback_learned ON trade_feedback(learned) WHERE learned = false;
```

---

### 8.3 Korean Market Trap Detection 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                Korean Market Trap Detection Flow                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1️⃣ 실시간 데이터 수집                                          │
│     └─→ KIS Fetcher: 외국인/기관 순매수, 프로그램 매매         │
│     └─→ Market Fetcher: 신용잔고율, 베이시스                    │
│                                                                 │
│  2️⃣ Trap Detector 실행                                          │
│     └─→ 10가지 패턴 체크                                        │
│     └─→ trap_patterns 테이블에서 가중치 로드                    │
│     └─→ CRITICAL/HIGH/MEDIUM/LOW 판단                           │
│                                                                 │
│  3️⃣ 매수 결정                                                   │
│     └─→ CRITICAL trap → 매수 금지                               │
│     └─→ HIGH/MEDIUM trap → 조건 강화                            │
│     └─→ trade_feedback 테이블에 기록                            │
│                                                                 │
│  4️⃣ 실제 결과 수집 (1시간 후, 종가)                             │
│     └─→ price_after_1h, price_at_close 업데이트                │
│     └─→ actual_result 판단 (CORRECT / WRONG)                   │
│                                                                 │
│  5️⃣ AI 학습                                                     │
│     └─→ CORRECT: weight += 0.01                                │
│     └─→ WRONG: weight -= 0.02                                  │
│     └─→ trap_patterns 테이블 업데이트                           │
│     └─→ accuracy 재계산                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Fetcher → DB 매핑

| Fetcher | 대상 테이블 | 주기 | 단위 주의사항 |
|---------|-------------|------|---------------|
| `pykrx` | daily_prices | 일 1회 (장 마감) | 수급: **주 단위** (변환 불필요) |
| `kis` (시세) | market_candles | 실시간 | 가격: **원**, 수량: **주** |
| `kis` (잔고) | portfolio, account_snapshots | 실시간 | 금액: **원**, 수량: **주** |
| `kis` (한국시장) | **trade_feedback** | **실시간** | **외국인/기관 순매수 (주), 프로그램 매매** |
| `yfinance` | market_macro | 일 1회 | 환율: **원/달러**, 지수: **포인트** |
| `dart` | intel_feed | 5분 | - |
| `naver` | intel_feed, **trade_feedback** | 15분 | **신용잔고율** |

---

## 10. 마이그레이션 체크리스트

v2.0 → v3.2 마이그레이션 시 확인사항:

### 기본 테이블
- [ ] `daily_prices` 수급 컬럼 8개 모두 존재 확인
- [ ] `portfolio` 피라미딩 필드 5개 추가
- [ ] `market_candles` 신규 테이블 생성
- [ ] `account_snapshots` 신규 테이블 생성
- [ ] `market_regime` 신규 테이블 생성
- [ ] `trade_orders` / `trade_executions` 분리
- [ ] `strategy_states` 신규 테이블 생성

### 🇰🇷 Korean Market Trap Detection (v3.2 신규)
- [ ] **`trap_patterns` 신규 테이블 생성**
  - 10가지 함정 타입 초기 데이터 삽입
  - 가중치 초기값: 0.80
- [ ] **`trade_feedback` 신규 테이블 생성** (함정 감지용)
  - `trade_feedbacks`(기존)와 구분됨
  - 함정 감지 전용 피드백
- [ ] 인덱스 생성
  - `idx_trap_type` (UNIQUE)
  - `idx_trap_accuracy`
  - `idx_feedback_date_code`
  - `idx_feedback_trap_type` (partial)
  - `idx_feedback_result`
  - `idx_feedback_learned` (partial)

### 성능 최적화
- [ ] Partial Index 생성 (수급 신호용)
- [ ] TimescaleDB 하이퍼테이블 설정 (market_candles)
- [ ] Foreign Key 설정 (`trade_feedback.trap_type` → `trap_patterns.trap_type`)

### 초기 데이터 시드
```sql
-- trap_patterns 초기 데이터
INSERT INTO trap_patterns (trap_type, weight, total_count, correct_count, accuracy) VALUES
    ('fake_rise', 0.95, 0, 0, 0.0),
    ('gap_overheat', 0.90, 0, 0, 0.0),
    ('program_dump', 0.85, 0, 0, 0.0),
    ('sell_on_news', 0.80, 0, 0, 0.0),
    ('hollow_rise', 0.75, 0, 0, 0.0),
    ('resistance_wall', 0.70, 0, 0, 0.0),
    ('sector_decouple', 0.65, 0, 0, 0.0),
    ('fx_impact', 0.60, 0, 0, 0.0),
    ('ma_resistance', 0.55, 0, 0, 0.0),
    ('dilution_day', 0.90, 0, 0, 0.0);
```

---

*Last Updated: 2025-12-09*
*Version: 3.2 (Korean Market Traps Added)*
