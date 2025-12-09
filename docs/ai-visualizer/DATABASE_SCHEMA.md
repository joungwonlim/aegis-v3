# Database Schema Specification

> **AI 시각화 시스템 데이터베이스 설계**

## 📋 목차

1. [개요](#개요)
2. [테이블 구조](#테이블-구조)
3. [관계 다이어그램](#관계-다이어그램)
4. [인덱스 전략](#인덱스-전략)
5. [마이그레이션](#마이그레이션)

---

## 개요

### 설계 원칙

| 원칙 | 설명 |
|-----|------|
| **정규화** | 3NF 준수, 데이터 중복 최소화 |
| **성능** | 집계 쿼리 최적화, 파티셔닝 고려 |
| **확장성** | JSONB로 유연한 스키마 |
| **타임존** | 모든 timestamp는 UTC |
| **UUID** | Primary Key는 UUID v7 (시간 정렬) |

---

## 테이블 구조

### 1. analysis_batches (배치 실행)

```sql
-- 한 번의 분석 사이클 (2,500 → 3 종목)
CREATE TABLE analysis_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
        -- RUNNING, COMPLETED, FAILED, PAUSED
    trigger_type VARCHAR(20) NOT NULL,
        -- SCHEDULED, MANUAL
    error_message TEXT,
    metadata JSONB,
        -- { "version": "3.0", "config": {...} }
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_batches_status ON analysis_batches(status);
CREATE INDEX idx_batches_started_at ON analysis_batches(started_at DESC);
CREATE INDEX idx_batches_trigger_type ON analysis_batches(trigger_type);

-- 코멘트
COMMENT ON TABLE analysis_batches IS '배치 실행 단위';
COMMENT ON COLUMN analysis_batches.metadata IS '실행 설정 및 메타정보';
```

**예시 데이터**:
```json
{
    "id": "01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e",
    "started_at": "2025-12-08T06:00:00Z",
    "completed_at": "2025-12-08T06:05:23Z",
    "status": "COMPLETED",
    "trigger_type": "SCHEDULED",
    "metadata": {
        "version": "3.0",
        "flash_model": "gemini-2.0-flash",
        "pro_model": "gemini-2.5-pro"
    }
}
```

---

### 2. signal_sources (신호 소스 정의)

```sql
-- 글로벌 데이터 소스 마스터 테이블
CREATE TABLE signal_sources (
    id SERIAL PRIMARY KEY,
    source_code VARCHAR(50) UNIQUE NOT NULL,
        -- 'US_FED', 'US_SP500', 'EU_ECB', 'GOLD', 'WTI', etc.
    source_name VARCHAR(100) NOT NULL,
        -- '미국 연준 금리', 'S&P 500 지수', etc.
    category VARCHAR(50) NOT NULL,
        -- 'MACRO', 'COMMODITY', 'INDEX', 'CURRENCY', 'NEWS'
    region VARCHAR(50) NOT NULL,
        -- 'US', 'EU', 'ASIA', 'GLOBAL'
    icon VARCHAR(10),
        -- '🇺🇸', '🥇', '🛢️', '💱'
    position_x FLOAT,
        -- 시각화 기본 X 좌표 (0.0 ~ 1.0)
    position_y FLOAT,
        -- 시각화 기본 Y 좌표 (0.0 ~ 1.0)
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_sources_category ON signal_sources(category);
CREATE INDEX idx_sources_region ON signal_sources(region);
CREATE INDEX idx_sources_active ON signal_sources(is_active) WHERE is_active = TRUE;

-- 초기 데이터 (예시)
INSERT INTO signal_sources (source_code, source_name, category, region, icon, position_x, position_y) VALUES
    ('US_FED', '미국 연준 금리', 'MACRO', 'US', '🇺🇸', 0.2, 0.3),
    ('US_SP500', 'S&P 500', 'INDEX', 'US', '📈', 0.25, 0.35),
    ('EU_ECB', '유럽 중앙은행', 'MACRO', 'EU', '🇪🇺', 0.4, 0.2),
    ('GOLD', '금 가격', 'COMMODITY', 'GLOBAL', '🥇', 0.5, 0.5),
    ('WTI', 'WTI 유가', 'COMMODITY', 'GLOBAL', '🛢️', 0.6, 0.5),
    ('COPPER', '구리 가격', 'COMMODITY', 'GLOBAL', '🔶', 0.65, 0.55),
    ('JP_NIKKEI', '니케이 225', 'INDEX', 'ASIA', '🇯🇵', 0.7, 0.3),
    ('CN_SSE', '상해종합', 'INDEX', 'ASIA', '🇨🇳', 0.75, 0.4);
```

---

### 3. signal_logs (수집된 신호)

```sql
-- Fetcher가 수집한 글로벌 신호
CREATE TABLE signal_logs (
    id SERIAL PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES analysis_batches(id) ON DELETE CASCADE,
    source_code VARCHAR(50) NOT NULL REFERENCES signal_sources(source_code),
    signal_type VARCHAR(20) NOT NULL,
        -- 'NEWS', 'PRICE', 'INDICATOR', 'EVENT'
    title VARCHAR(500),
        -- 뉴스 제목 or 지표명
    content TEXT,
        -- 뉴스 본문 or 지표 설명
    sentiment VARCHAR(20),
        -- 'POSITIVE', 'NEGATIVE', 'NEUTRAL'
    sentiment_score FLOAT,
        -- -1.0 (매우 부정) ~ +1.0 (매우 긍정)
    impact_level VARCHAR(20),
        -- 'HIGH', 'MEDIUM', 'LOW'
    raw_value JSONB,
        -- 원본 데이터 (유연한 저장)
    fetched_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_signals_batch ON signal_logs(batch_id);
CREATE INDEX idx_signals_source ON signal_logs(source_code);
CREATE INDEX idx_signals_sentiment ON signal_logs(batch_id, sentiment);
CREATE INDEX idx_signals_impact ON signal_logs(batch_id, impact_level);

-- 예시 데이터
INSERT INTO signal_logs (batch_id, source_code, signal_type, title, sentiment, sentiment_score, impact_level) VALUES
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'US_FED', 'INDICATOR', 'Fed 금리 동결', 'POSITIVE', 0.7, 'HIGH'),
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'WTI', 'PRICE', 'WTI 5% 급등', 'NEGATIVE', -0.5, 'MEDIUM'),
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'GOLD', 'PRICE', '금 가격 사상 최고치', 'POSITIVE', 0.9, 'HIGH');
```

---

### 4. analysis_steps (단계별 진행)

```sql
-- 배치 내 각 단계 (FETCH, FLASH_FILTER, PRO_REASON)
CREATE TABLE analysis_steps (
    id SERIAL PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES analysis_batches(id) ON DELETE CASCADE,
    step_name VARCHAR(50) NOT NULL,
        -- 'FETCH', 'FLASH_FILTER', 'PRO_REASON'
    model_used VARCHAR(50),
        -- 'gemini-2.0-flash-exp', 'gemini-2.5-pro-preview'
    input_count INT,
        -- 입력 종목/신호 수
    output_count INT,
        -- 출력 종목/신호 수
    processing_time_ms INT,
        -- 처리 시간 (밀리초)
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB
);

-- 인덱스
CREATE INDEX idx_steps_batch ON analysis_steps(batch_id);
CREATE INDEX idx_steps_name ON analysis_steps(step_name);
CREATE INDEX idx_steps_started_at ON analysis_steps(started_at DESC);

-- 예시 데이터
INSERT INTO analysis_steps (batch_id, step_name, model_used, input_count, output_count, processing_time_ms, started_at, completed_at) VALUES
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'FETCH', NULL, 0, 2500, 8500, '2025-12-08T06:00:00Z', '2025-12-08T06:00:08Z'),
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'FLASH_FILTER', 'gemini-2.0-flash-exp', 2500, 50, 120000, '2025-12-08T06:00:08Z', '2025-12-08T06:02:08Z'),
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'PRO_REASON', 'gemini-2.5-pro-preview', 50, 3, 180000, '2025-12-08T06:02:08Z', '2025-12-08T06:05:08Z');
```

---

### 5. analysis_stocks (종목별 상세)

```sql
-- 각 단계에서 처리된 종목 정보
CREATE TABLE analysis_stocks (
    id SERIAL PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES analysis_batches(id) ON DELETE CASCADE,
    step_name VARCHAR(50) NOT NULL,
        -- 'FETCH', 'FLASH_FILTER', 'PRO_REASON'
    stock_code VARCHAR(20) NOT NULL,
        -- '005930' (삼성전자)
    stock_name VARCHAR(100),
        -- '삼성전자'
    status VARCHAR(20) NOT NULL,
        -- 'FETCHED', 'FILTERED', 'SELECTED'
    score NUMERIC(10, 4),
        -- 점수 (0.0000 ~ 100.0000)
    filter_reason TEXT,
        -- 왜 탈락했는지 / 왜 선정되었는지
    position_x FLOAT,
        -- 시각화 X 좌표 (옵션)
    position_y FLOAT,
        -- 시각화 Y 좌표 (옵션)
    metadata JSONB,
        -- 추가 정보
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_stocks_batch ON analysis_stocks(batch_id);
CREATE INDEX idx_stocks_batch_step ON analysis_stocks(batch_id, step_name);
CREATE INDEX idx_stocks_status ON analysis_stocks(batch_id, status);
CREATE INDEX idx_stocks_score ON analysis_stocks(batch_id, score DESC);

-- 예시 데이터
INSERT INTO analysis_stocks (batch_id, step_name, stock_code, stock_name, status, score, filter_reason) VALUES
    -- FETCH 단계: 2500개
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'FETCH', '005930', '삼성전자', 'FETCHED', 75.5, NULL),
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'FETCH', '000660', 'SK하이닉스', 'FETCHED', 82.3, NULL),
    -- ... (2498개 더)

    -- FLASH_FILTER 단계: 50개 (나머지는 FILTERED)
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'FLASH_FILTER', '005930', '삼성전자', 'PASSED', 75.5, '반도체 섹터 긍정, 미국 지표 호재'),
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'FLASH_FILTER', '000660', 'SK하이닉스', 'PASSED', 82.3, 'HBM 수요 증가, AI 반도체 호황'),
    -- ... (48개 더)

    -- PRO_REASON 단계: 3개 (나머지는 FILTERED)
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'PRO_REASON', '005930', '삼성전자', 'SELECTED', 75.5, '글로벌 반도체 수요 회복, 환율 호재, 기술적 지표 우수'),
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'PRO_REASON', '000660', 'SK하이닉스', 'SELECTED', 82.3, 'HBM 점유율 1위, AI 반도체 최대 수혜주'),
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 'PRO_REASON', '373220', 'LG에너지솔루션', 'SELECTED', 68.9, '전기차 수요 증가, 미국 IRA 수혜');
```

---

### 6. signal_stock_impacts (신호 → 종목 영향)

```sql
-- 어떤 신호가 어떤 종목에 영향을 줬는지
CREATE TABLE signal_stock_impacts (
    id SERIAL PRIMARY KEY,
    batch_id UUID NOT NULL REFERENCES analysis_batches(id) ON DELETE CASCADE,
    signal_id INT NOT NULL REFERENCES signal_logs(id) ON DELETE CASCADE,
    stock_code VARCHAR(20) NOT NULL,
    impact_type VARCHAR(20) NOT NULL,
        -- 'BOOST' (긍정), 'PENALTY' (부정), 'NEUTRAL'
    impact_score FLOAT,
        -- 점수 조정값 (-100.0 ~ +100.0)
    reasoning TEXT,
        -- AI 설명 (왜 이 신호가 이 종목에 영향?)
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_impacts_batch ON signal_stock_impacts(batch_id);
CREATE INDEX idx_impacts_signal ON signal_stock_impacts(signal_id);
CREATE INDEX idx_impacts_stock ON signal_stock_impacts(batch_id, stock_code);

-- 예시 데이터
INSERT INTO signal_stock_impacts (batch_id, signal_id, stock_code, impact_type, impact_score, reasoning) VALUES
    -- 삼성전자에 영향
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 1, '005930', 'BOOST', 15.0,
     'Fed 금리 동결로 반도체 투자 환경 개선, 달러 약세로 수출 경쟁력 향상'),
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 2, '005930', 'PENALTY', -5.0,
     'WTI 유가 상승으로 원자재 비용 증가, 제조 마진 압박'),
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 3, '005930', 'BOOST', 8.0,
     '금 가격 상승은 불확실성 증가를 의미하나, 안전자산으로 삼성전자 수혜'),

    -- SK하이닉스에 영향
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 1, '000660', 'BOOST', 20.0,
     'Fed 금리 동결로 AI 반도체 투자 가속화, HBM 수요 증가'),
    ('01932b75-8f0a-7c40-b5d4-2e8f3a1b9c7e', 2, '000660', 'NEUTRAL', 0.0,
     '유가 상승이 반도체 제조 비용에 미치는 영향 제한적');
```

---

### 7. control_events (제어 이벤트 로그)

```sql
-- 관제 시스템에서 발생한 수동 제어 이벤트
CREATE TABLE control_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
        -- 'BATCH_START', 'BATCH_STOP', 'BATCH_RESUME', 'CONFIG_CHANGE'
    batch_id UUID REFERENCES analysis_batches(id) ON DELETE SET NULL,
    user_id VARCHAR(100),
        -- 관리자 ID (옵션)
    metadata JSONB,
        -- 이벤트 상세 정보
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_events_type ON control_events(event_type);
CREATE INDEX idx_events_batch ON control_events(batch_id);
CREATE INDEX idx_events_timestamp ON control_events(timestamp DESC);
```

---

### 8. performance_metrics (성능 메트릭)

```sql
-- 성능 모니터링용 메트릭 (시계열)
CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    metric_type VARCHAR(50) NOT NULL,
        -- 'processing_time', 'error_rate', 'throughput', 'db_query_time'
    metric_name VARCHAR(100) NOT NULL,
        -- 'flash_filter_avg_ms', 'pro_reason_p95_ms', etc.
    value NUMERIC(20, 4) NOT NULL,
    unit VARCHAR(20),
        -- 'ms', '%', 'count'
    batch_id UUID REFERENCES analysis_batches(id) ON DELETE SET NULL,
    metadata JSONB,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 인덱스
CREATE INDEX idx_metrics_type ON performance_metrics(metric_type);
CREATE INDEX idx_metrics_timestamp ON performance_metrics(timestamp DESC);

-- 시계열 데이터 최적화 (선택: TimescaleDB Hypertable)
-- SELECT create_hypertable('performance_metrics', 'timestamp');
```

---

## 관계 다이어그램

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Entity Relationship                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  signal_sources (마스터)                                            │
│       │                                                             │
│       │ 1:N                                                         │
│       ▼                                                             │
│  signal_logs ─────┐                                                 │
│       │           │                                                 │
│       │ N:1       │ 1:N                                             │
│       ▼           ▼                                                 │
│  analysis_batches ◄── signal_stock_impacts                          │
│       │                    │                                        │
│       │ 1:N                │ N:1                                    │
│       ├────────────────────┴──────────┐                             │
│       │                               │                             │
│       ▼                               ▼                             │
│  analysis_steps              analysis_stocks                        │
│                                                                     │
│  control_events (독립)                                              │
│  performance_metrics (독립)                                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 인덱스 전략

### 1. 조회 패턴별 최적화

```sql
-- [패턴 1] 최근 배치 목록 조회
-- Query: SELECT * FROM analysis_batches ORDER BY started_at DESC LIMIT 20;
CREATE INDEX idx_batches_started_at ON analysis_batches(started_at DESC);

-- [패턴 2] 특정 배치의 모든 신호 조회
-- Query: SELECT * FROM signal_logs WHERE batch_id = ?;
CREATE INDEX idx_signals_batch ON signal_logs(batch_id);

-- [패턴 3] 특정 배치의 최종 선정 종목
-- Query: SELECT * FROM analysis_stocks WHERE batch_id = ? AND step_name = 'PRO_REASON' AND status = 'SELECTED';
CREATE INDEX idx_stocks_batch_step_status ON analysis_stocks(batch_id, step_name, status);

-- [패턴 4] 종목에 영향을 준 신호 추적
-- Query: SELECT * FROM signal_stock_impacts WHERE batch_id = ? AND stock_code = ?;
CREATE INDEX idx_impacts_batch_stock ON signal_stock_impacts(batch_id, stock_code);

-- [패턴 5] 성능 메트릭 시계열 조회
-- Query: SELECT * FROM performance_metrics WHERE metric_type = ? AND timestamp >= ?;
CREATE INDEX idx_metrics_type_timestamp ON performance_metrics(metric_type, timestamp DESC);
```

### 2. Partial Index (조건부 인덱스)

```sql
-- 실행 중인 배치만 빠르게 조회
CREATE INDEX idx_batches_running ON analysis_batches(started_at DESC)
WHERE status = 'RUNNING';

-- 활성 신호 소스만 인덱스
CREATE INDEX idx_sources_active ON signal_sources(category, region)
WHERE is_active = TRUE;
```

### 3. Covering Index (커버링 인덱스)

```sql
-- 집계 쿼리 최적화 (INDEX ONLY SCAN)
CREATE INDEX idx_steps_batch_times ON analysis_steps(batch_id, step_name)
INCLUDE (processing_time_ms, started_at, completed_at);
```

---

## 마이그레이션

### Alembic 마이그레이션 스크립트

```python
# alembic/versions/2025_12_08_ai_visualizer.py
"""
AI Visualizer Schema

Revision ID: abc123def456
Revises: previous_revision
Create Date: 2025-12-08 12:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'abc123def456'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None


def upgrade():
    # 1. analysis_batches
    op.create_table(
        'analysis_batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('status', sa.VARCHAR(20), nullable=False, server_default='RUNNING'),
        sa.Column('trigger_type', sa.VARCHAR(20), nullable=False),
        sa.Column('error_message', sa.TEXT(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('idx_batches_status', 'analysis_batches', ['status'])
    op.create_index('idx_batches_started_at', 'analysis_batches', ['started_at'], postgresql_ops={'started_at': 'DESC'})

    # 2. signal_sources
    op.create_table(
        'signal_sources',
        sa.Column('id', sa.INTEGER(), primary_key=True, autoincrement=True),
        sa.Column('source_code', sa.VARCHAR(50), unique=True, nullable=False),
        sa.Column('source_name', sa.VARCHAR(100), nullable=False),
        sa.Column('category', sa.VARCHAR(50), nullable=False),
        sa.Column('region', sa.VARCHAR(50), nullable=False),
        sa.Column('icon', sa.VARCHAR(10), nullable=True),
        sa.Column('position_x', sa.FLOAT(), nullable=True),
        sa.Column('position_y', sa.FLOAT(), nullable=True),
        sa.Column('is_active', sa.BOOLEAN(), nullable=False, server_default='TRUE'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
    )

    # 3. signal_logs
    op.create_table(
        'signal_logs',
        sa.Column('id', sa.INTEGER(), primary_key=True, autoincrement=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('analysis_batches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_code', sa.VARCHAR(50), sa.ForeignKey('signal_sources.source_code'), nullable=False),
        sa.Column('signal_type', sa.VARCHAR(20), nullable=False),
        sa.Column('title', sa.VARCHAR(500), nullable=True),
        sa.Column('content', sa.TEXT(), nullable=True),
        sa.Column('sentiment', sa.VARCHAR(20), nullable=True),
        sa.Column('sentiment_score', sa.FLOAT(), nullable=True),
        sa.Column('impact_level', sa.VARCHAR(20), nullable=True),
        sa.Column('raw_value', postgresql.JSONB(), nullable=True),
        sa.Column('fetched_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('idx_signals_batch', 'signal_logs', ['batch_id'])

    # 4. analysis_steps
    op.create_table(
        'analysis_steps',
        sa.Column('id', sa.INTEGER(), primary_key=True, autoincrement=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('analysis_batches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_name', sa.VARCHAR(50), nullable=False),
        sa.Column('model_used', sa.VARCHAR(50), nullable=True),
        sa.Column('input_count', sa.INTEGER(), nullable=True),
        sa.Column('output_count', sa.INTEGER(), nullable=True),
        sa.Column('processing_time_ms', sa.INTEGER(), nullable=True),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('error_message', sa.TEXT(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
    )
    op.create_index('idx_steps_batch', 'analysis_steps', ['batch_id'])

    # 5. analysis_stocks
    op.create_table(
        'analysis_stocks',
        sa.Column('id', sa.INTEGER(), primary_key=True, autoincrement=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('analysis_batches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_name', sa.VARCHAR(50), nullable=False),
        sa.Column('stock_code', sa.VARCHAR(20), nullable=False),
        sa.Column('stock_name', sa.VARCHAR(100), nullable=True),
        sa.Column('status', sa.VARCHAR(20), nullable=False),
        sa.Column('score', sa.NUMERIC(10, 4), nullable=True),
        sa.Column('filter_reason', sa.TEXT(), nullable=True),
        sa.Column('position_x', sa.FLOAT(), nullable=True),
        sa.Column('position_y', sa.FLOAT(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('idx_stocks_batch', 'analysis_stocks', ['batch_id'])
    op.create_index('idx_stocks_batch_step', 'analysis_stocks', ['batch_id', 'step_name'])

    # 6. signal_stock_impacts
    op.create_table(
        'signal_stock_impacts',
        sa.Column('id', sa.INTEGER(), primary_key=True, autoincrement=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('analysis_batches.id', ondelete='CASCADE'), nullable=False),
        sa.Column('signal_id', sa.INTEGER(), sa.ForeignKey('signal_logs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stock_code', sa.VARCHAR(20), nullable=False),
        sa.Column('impact_type', sa.VARCHAR(20), nullable=False),
        sa.Column('impact_score', sa.FLOAT(), nullable=True),
        sa.Column('reasoning', sa.TEXT(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('idx_impacts_batch', 'signal_stock_impacts', ['batch_id'])

    # 7. control_events
    op.create_table(
        'control_events',
        sa.Column('id', sa.INTEGER(), primary_key=True, autoincrement=True),
        sa.Column('event_type', sa.VARCHAR(50), nullable=False),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('analysis_batches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', sa.VARCHAR(100), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
    )

    # 8. performance_metrics
    op.create_table(
        'performance_metrics',
        sa.Column('id', sa.INTEGER(), primary_key=True, autoincrement=True),
        sa.Column('metric_type', sa.VARCHAR(50), nullable=False),
        sa.Column('metric_name', sa.VARCHAR(100), nullable=False),
        sa.Column('value', sa.NUMERIC(20, 4), nullable=False),
        sa.Column('unit', sa.VARCHAR(20), nullable=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('analysis_batches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('idx_metrics_timestamp', 'performance_metrics', ['timestamp'], postgresql_ops={'timestamp': 'DESC'})


def downgrade():
    op.drop_table('performance_metrics')
    op.drop_table('control_events')
    op.drop_table('signal_stock_impacts')
    op.drop_table('analysis_stocks')
    op.drop_table('analysis_steps')
    op.drop_table('signal_logs')
    op.drop_table('signal_sources')
    op.drop_table('analysis_batches')
```

### 마이그레이션 실행

```bash
# 마이그레이션 생성
alembic revision -m "ai_visualizer_schema"

# 마이그레이션 적용
alembic upgrade head

# 롤백 (필요 시)
alembic downgrade -1
```

---

## SQLAlchemy 모델

```python
# src/database/models.py
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database import Base


class AnalysisBatch(Base):
    __tablename__ = 'analysis_batches'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    completed_at = Column(TIMESTAMP)
    status = Column(String(20), nullable=False, default='RUNNING')
    trigger_type = Column(String(20), nullable=False)
    error_message = Column(Text)
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    # 관계
    steps = relationship('AnalysisStep', back_populates='batch', cascade='all, delete-orphan')
    signals = relationship('SignalLog', back_populates='batch', cascade='all, delete-orphan')
    stocks = relationship('AnalysisStock', back_populates='batch', cascade='all, delete-orphan')


class SignalSource(Base):
    __tablename__ = 'signal_sources'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_code = Column(String(50), unique=True, nullable=False)
    source_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    region = Column(String(50), nullable=False)
    icon = Column(String(10))
    position_x = Column(Float)
    position_y = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    # 관계
    signals = relationship('SignalLog', back_populates='source')


class SignalLog(Base):
    __tablename__ = 'signal_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('analysis_batches.id', ondelete='CASCADE'), nullable=False)
    source_code = Column(String(50), ForeignKey('signal_sources.source_code'), nullable=False)
    signal_type = Column(String(20), nullable=False)
    title = Column(String(500))
    content = Column(Text)
    sentiment = Column(String(20))
    sentiment_score = Column(Float)
    impact_level = Column(String(20))
    raw_value = Column(JSONB)
    fetched_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    # 관계
    batch = relationship('AnalysisBatch', back_populates='signals')
    source = relationship('SignalSource', back_populates='signals')
    impacts = relationship('SignalStockImpact', back_populates='signal', cascade='all, delete-orphan')


# ... (나머지 모델 생략)
```

---

## 다음 단계

1. **마이그레이션 실행**: `alembic upgrade head`
2. **초기 데이터 입력**: signal_sources 마스터 데이터
3. **Fetcher 수정**: signal_logs 저장 로직 추가
4. **Brain 수정**: analysis_steps, analysis_stocks 저장

---

**작성일**: 2025-12-08
**작성자**: wonny
**버전**: 1.0.0
