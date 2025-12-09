# 🤖 Sonnet을 위한 AI Visualizer 개발 가이드

> **Claude Sonnet이 이 문서만 읽고 개발을 시작할 수 있도록 설계되었습니다.**

---

## 📋 목차

1. [시작하기 전에](#시작하기-전에)
2. [Phase 1: 프로젝트 생성](#phase-1-프로젝트-생성)
3. [Phase 2: Database 개발](#phase-2-database-개발)
4. [Phase 3: Backend API 개발](#phase-3-backend-api-개발)
5. [Phase 4: Frontend 기본 개발](#phase-4-frontend-기본-개발)
6. [Phase 5: 시각화 구현](#phase-5-시각화-구현)

---

## 시작하기 전에

### ✅ 읽어야 할 문서 순서

```
1차: 이 문서 (SONNET_DEV_GUIDE.md)        ← 지금 여기
2차: DATABASE_SCHEMA.md                    ← DB 개발할 때
3차: CONTROL_SYSTEM.md                     ← API 개발할 때
4차: TECH_STACK.md                         ← Frontend 기본
5차: ANIMATION_SPEC.md                     ← 시각화 구현
```

### 🎯 개발 철학

**한 번에 한 단계씩!**
- 각 Phase를 완료한 후 다음으로
- 코드를 복사-붙여넣기
- 테스트 후 커밋

---

## Phase 1: 프로젝트 생성

### 🎯 목표
빈 프로젝트를 생성하고 Docker Compose로 실행

### 📝 체크리스트
- [ ] 프로젝트 디렉토리 생성
- [ ] Docker Compose 설정
- [ ] Backend 기본 구조
- [ ] Frontend 기본 구조
- [ ] 접속 확인

### 🚀 실행

#### Step 1.1: 자동 스크립트 실행 (추천)

```bash
# 스크립트 위치 확인
ls ~/Dev/aegis/v2/docs/dev3/ai-visualizer/create_project.sh

# 실행
bash ~/Dev/aegis/v2/docs/dev3/ai-visualizer/create_project.sh

# 완료 메시지 확인
# ✅ 프로젝트 생성 완료!
# 📍 프로젝트 위치: ~/Dev/aegis-visualizer
```

#### Step 1.2: 프로젝트로 이동

```bash
cd ~/Dev/aegis-visualizer

# 구조 확인
tree -L 2 -I 'node_modules|venv|__pycache__'

# 예상 출력:
# .
# ├── backend/
# │   ├── app/
# │   ├── requirements.txt
# │   └── Dockerfile
# ├── frontend/
# │   ├── src/
# │   ├── package.json
# │   └── Dockerfile
# └── docker-compose.yml
```

#### Step 1.3: Docker Compose 실행

```bash
# 빌드 및 실행
docker-compose up -d

# 로그 확인 (10초 정도 대기)
docker-compose logs -f

# Ctrl+C로 로그 중단

# 컨테이너 상태 확인
docker-compose ps

# 예상 출력:
# NAME                  STATUS
# visualizer_db         Up (healthy)
# visualizer_backend    Up
# visualizer_frontend   Up
```

#### Step 1.4: 접속 테스트

```bash
# Backend API 테스트
curl http://localhost:8001/health

# 예상 출력:
# {"status":"healthy"}

# Frontend 테스트 (브라우저)
# http://localhost:5174
# "🚀 AEGIS Visualizer" 보이면 성공!

# API 문서
# http://localhost:8001/docs
```

### ✅ Phase 1 완료 조건

- [ ] `docker-compose ps`에서 모든 컨테이너 Up
- [ ] http://localhost:8001/health → `{"status":"healthy"}`
- [ ] http://localhost:5174 → Frontend 화면 보임
- [ ] http://localhost:8001/docs → Swagger UI 보임

### 🐛 문제 발생 시

```bash
# 컨테이너 중지
docker-compose down

# 볼륨 포함 완전 삭제
docker-compose down -v

# 재시작
docker-compose up -d --build
```

---

## Phase 2: Database 개발

### 🎯 목표
PostgreSQL에 8개 테이블 생성 및 초기 데이터 입력

### 📚 참조 문서
**DATABASE_SCHEMA.md** (28KB)를 읽어주세요.

### 📝 체크리스트
- [ ] Alembic 설정
- [ ] 마이그레이션 파일 생성
- [ ] 8개 테이블 생성
- [ ] 인덱스 추가
- [ ] 초기 데이터 입력
- [ ] 검증

### 🚀 실행

#### Step 2.1: Alembic 초기화

```bash
cd ~/Dev/aegis-visualizer/backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# Alembic 초기화 (이미 디렉토리 있으면 스킵)
alembic init alembic
```

#### Step 2.2: Alembic 설정 수정

**파일: `alembic.ini`**

```ini
# 기존:
# sqlalchemy.url = driver://user:pass@localhost/dbname

# 변경:
sqlalchemy.url = postgresql://visualizer_admin:visualizer2024@localhost:5433/visualizer
```

**파일: `alembic/env.py`**

```python
# 맨 위에 추가
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base
from app.models.visualizer import *  # 모든 모델 임포트

# target_metadata 수정
target_metadata = Base.metadata
```

#### Step 2.3: 마이그레이션 생성

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "create_visualizer_tables"

# 생성된 파일 확인
ls alembic/versions/

# 예: abc123_create_visualizer_tables.py
```

#### Step 2.4: 마이그레이션 파일 수정

**파일: `alembic/versions/xxx_create_visualizer_tables.py`**

**DATABASE_SCHEMA.md의 마이그레이션 스크립트를 복사-붙여넣기:**

```python
"""create visualizer tables

Revision ID: xxx
Revises:
Create Date: 2025-12-08

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'xxx'  # 자동 생성된 값 유지
down_revision = None
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
    op.create_index('idx_sources_category', 'signal_sources', ['category'])
    op.create_index('idx_sources_region', 'signal_sources', ['region'])

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
    op.create_index('idx_signals_source', 'signal_logs', ['source_code'])

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
    op.create_index('idx_steps_name', 'analysis_steps', ['step_name'])

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
    op.create_index('idx_impacts_signal', 'signal_stock_impacts', ['signal_id'])

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
    op.create_index('idx_events_type', 'control_events', ['event_type'])
    op.create_index('idx_events_timestamp', 'control_events', ['timestamp'], postgresql_ops={'timestamp': 'DESC'})

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
    op.create_index('idx_metrics_type', 'performance_metrics', ['metric_type'])
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

#### Step 2.5: 마이그레이션 실행

```bash
# 마이그레이션 적용
alembic upgrade head

# 성공 메시지 확인:
# INFO [alembic.runtime.migration] Running upgrade  -> xxx, create visualizer tables
```

#### Step 2.6: 테이블 확인

```bash
# psql 접속
psql -h localhost -p 5433 -U visualizer_admin -d visualizer

# 테이블 목록 확인
\dt

# 예상 출력:
#                    List of relations
#  Schema |          Name           | Type  |      Owner
# --------+-------------------------+-------+------------------
#  public | analysis_batches        | table | visualizer_admin
#  public | analysis_steps          | table | visualizer_admin
#  public | analysis_stocks         | table | visualizer_admin
#  public | control_events          | table | visualizer_admin
#  public | performance_metrics     | table | visualizer_admin
#  public | signal_logs             | table | visualizer_admin
#  public | signal_sources          | table | visualizer_admin
#  public | signal_stock_impacts    | table | visualizer_admin

# 특정 테이블 구조 확인
\d analysis_batches

# 종료
\q
```

#### Step 2.7: 초기 데이터 입력

**파일: `backend/scripts/seed_data.py` 생성**

```python
# backend/scripts/seed_data.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
from app.database import AsyncSessionLocal
from app.models.visualizer import SignalSource


async def seed_signal_sources():
    """신호 소스 초기 데이터"""
    sources = [
        {
            'source_code': 'US_FED',
            'source_name': '미국 연준 금리',
            'category': 'MACRO',
            'region': 'US',
            'icon': '🇺🇸',
            'position_x': 0.2,
            'position_y': 0.3,
        },
        {
            'source_code': 'US_SP500',
            'source_name': 'S&P 500',
            'category': 'INDEX',
            'region': 'US',
            'icon': '📈',
            'position_x': 0.25,
            'position_y': 0.35,
        },
        {
            'source_code': 'EU_ECB',
            'source_name': '유럽 중앙은행',
            'category': 'MACRO',
            'region': 'EU',
            'icon': '🇪🇺',
            'position_x': 0.4,
            'position_y': 0.2,
        },
        {
            'source_code': 'GOLD',
            'source_name': '금 가격',
            'category': 'COMMODITY',
            'region': 'GLOBAL',
            'icon': '🥇',
            'position_x': 0.5,
            'position_y': 0.5,
        },
        {
            'source_code': 'WTI',
            'source_name': 'WTI 유가',
            'category': 'COMMODITY',
            'region': 'GLOBAL',
            'icon': '🛢️',
            'position_x': 0.6,
            'position_y': 0.5,
        },
        {
            'source_code': 'COPPER',
            'source_name': '구리 가격',
            'category': 'COMMODITY',
            'region': 'GLOBAL',
            'icon': '🔶',
            'position_x': 0.65,
            'position_y': 0.55,
        },
        {
            'source_code': 'JP_NIKKEI',
            'source_name': '니케이 225',
            'category': 'INDEX',
            'region': 'ASIA',
            'icon': '🇯🇵',
            'position_x': 0.7,
            'position_y': 0.3,
        },
        {
            'source_code': 'CN_SSE',
            'source_name': '상해종합',
            'category': 'INDEX',
            'region': 'ASIA',
            'icon': '🇨🇳',
            'position_x': 0.75,
            'position_y': 0.4,
        },
    ]

    async with AsyncSessionLocal() as session:
        for data in sources:
            source = SignalSource(**data)
            session.add(source)

        await session.commit()
        print(f"✅ {len(sources)}개 신호 소스 생성 완료")


if __name__ == '__main__':
    asyncio.run(seed_signal_sources())
```

**실행:**

```bash
cd ~/Dev/aegis-visualizer/backend

# 스크립트 실행
python scripts/seed_data.py

# 확인
psql -h localhost -p 5433 -U visualizer_admin -d visualizer -c "SELECT source_code, source_name, icon FROM signal_sources;"

# 예상 출력:
#  source_code  |  source_name    | icon
# --------------+-----------------+------
#  US_FED       | 미국 연준 금리  | 🇺🇸
#  US_SP500     | S&P 500         | 📈
#  ...
```

### ✅ Phase 2 완료 조건

- [ ] `alembic upgrade head` 성공
- [ ] `\dt` 명령으로 8개 테이블 확인
- [ ] signal_sources에 8개 데이터 확인
- [ ] 모든 인덱스 생성 확인

---

## Phase 3: Backend API 개발

### 🎯 목표
FastAPI로 REST + WebSocket API 구현

### 📚 참조 문서
**CONTROL_SYSTEM.md** (28KB)를 읽어주세요.

### 📝 체크리스트
- [ ] 모델 클래스 완성
- [ ] API 라우터 생성
- [ ] WebSocket 구현
- [ ] 테스트

### 🚀 실행

#### Step 3.1: 모델 완성

**파일: `backend/app/models/visualizer.py` 수정**

```python
# backend/app/models/visualizer.py
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.database import Base


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

    batch = relationship('AnalysisBatch', back_populates='signals')
    source = relationship('SignalSource', back_populates='signals')


class AnalysisStep(Base):
    __tablename__ = 'analysis_steps'

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('analysis_batches.id', ondelete='CASCADE'), nullable=False)
    step_name = Column(String(50), nullable=False)
    model_used = Column(String(50))
    input_count = Column(Integer)
    output_count = Column(Integer)
    processing_time_ms = Column(Integer)
    started_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    completed_at = Column(TIMESTAMP)
    error_message = Column(Text)
    metadata = Column(JSONB)

    batch = relationship('AnalysisBatch', back_populates='steps')


class AnalysisStock(Base):
    __tablename__ = 'analysis_stocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('analysis_batches.id', ondelete='CASCADE'), nullable=False)
    step_name = Column(String(50), nullable=False)
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(100))
    status = Column(String(20), nullable=False)
    score = Column(Float)
    filter_reason = Column(Text)
    position_x = Column(Float)
    position_y = Column(Float)
    metadata = Column(JSONB)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    batch = relationship('AnalysisBatch', back_populates='stocks')


class SignalStockImpact(Base):
    __tablename__ = 'signal_stock_impacts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('analysis_batches.id', ondelete='CASCADE'), nullable=False)
    signal_id = Column(Integer, ForeignKey('signal_logs.id', ondelete='CASCADE'), nullable=False)
    stock_code = Column(String(20), nullable=False)
    impact_type = Column(String(20), nullable=False)
    impact_score = Column(Float)
    reasoning = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())


class ControlEvent(Base):
    __tablename__ = 'control_events'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False)
    batch_id = Column(UUID(as_uuid=True), ForeignKey('analysis_batches.id', ondelete='SET NULL'))
    user_id = Column(String(100))
    metadata = Column(JSONB)
    timestamp = Column(TIMESTAMP, nullable=False, server_default=func.now())


class PerformanceMetric(Base):
    __tablename__ = 'performance_metrics'

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_type = Column(String(50), nullable=False)
    metric_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20))
    batch_id = Column(UUID(as_uuid=True), ForeignKey('analysis_batches.id', ondelete='SET NULL'))
    metadata = Column(JSONB)
    timestamp = Column(TIMESTAMP, nullable=False, server_default=func.now())
```

#### Step 3.2: API 라우터 생성

**CONTROL_SYSTEM.md의 코드를 복사-붙여넣기:**

**파일: `backend/app/api/control.py`**

```python
# backend/app/api/control.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.visualizer import AnalysisBatch

router = APIRouter()


@router.get("/batches")
async def list_batches(
    status: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """실행 중인 배치 목록"""
    query = select(AnalysisBatch).order_by(AnalysisBatch.started_at.desc())

    if status:
        query = query.where(AnalysisBatch.status == status)

    query = query.limit(limit)

    result = await db.execute(query)
    batches = result.scalars().all()

    return {
        "batches": [
            {
                "id": str(batch.id),
                "status": batch.status,
                "trigger_type": batch.trigger_type,
                "started_at": batch.started_at.isoformat() if batch.started_at else None,
                "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
            }
            for batch in batches
        ]
    }


@router.post("/batch/start")
async def start_batch(
    trigger_type: str = "MANUAL",
    db: AsyncSession = Depends(get_db),
):
    """새 배치 시작"""
    batch = AnalysisBatch(
        trigger_type=trigger_type,
        status='RUNNING',
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)

    return {
        "batch_id": str(batch.id),
        "status": "RUNNING",
        "message": "Batch started successfully",
    }


@router.post("/batch/{batch_id}/stop")
async def stop_batch(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
):
    """배치 중지"""
    result = await db.execute(
        select(AnalysisBatch).where(AnalysisBatch.id == batch_id)
    )
    batch = result.scalar_one_or_none()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    if batch.status != "RUNNING":
        raise HTTPException(status_code=400, detail="Batch is not running")

    batch.status = "PAUSED"
    await db.commit()

    return {
        "batch_id": str(batch.id),
        "status": "PAUSED",
        "message": "Batch stopped successfully",
    }


@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy"}
```

#### Step 3.3: main.py에 라우터 등록

**파일: `backend/app/main.py` 수정**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import engine
from app.api import control  # 추가

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="AEGIS Visualizer API",
    description="AI Reasoning Visualizer Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(control.router, prefix="/api/control", tags=["control"])


@app.get("/")
def read_root():
    return {
        "message": "AEGIS Visualizer API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

#### Step 3.4: 테스트

```bash
# Backend 재시작 (Docker)
docker-compose restart backend

# 또는 로컬
cd ~/Dev/aegis-visualizer/backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8001
```

**API 테스트:**

```bash
# 1. 헬스 체크
curl http://localhost:8001/api/control/health

# 2. 배치 목록 (빈 배열)
curl http://localhost:8001/api/control/batches

# 3. 배치 시작
curl -X POST http://localhost:8001/api/control/batch/start?trigger_type=MANUAL

# 응답 예시:
# {
#   "batch_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "RUNNING",
#   "message": "Batch started successfully"
# }

# 4. 배치 목록 재조회 (1개 있음)
curl http://localhost:8001/api/control/batches

# 5. Swagger UI 확인
# http://localhost:8001/docs
```

### ✅ Phase 3 완료 조건

- [ ] 모든 API 엔드포인트 동작
- [ ] POST /batch/start → 배치 생성됨
- [ ] GET /batches → 목록 조회됨
- [ ] Swagger UI에서 테스트 가능

---

## Phase 4: Frontend 기본 개발

### 🎯 목표
React 기본 구조 + API 연동

### 📚 참조 문서
**TECH_STACK.md** (20KB)를 읽어주세요.

### 📝 체크리스트
- [ ] 패키지 설치
- [ ] API 클라이언트 설정
- [ ] React Query 설정
- [ ] 기본 컴포넌트
- [ ] API 연동 테스트

### 🚀 실행

#### Step 4.1: 패키지 설치

```bash
cd ~/Dev/aegis-visualizer/frontend

# 패키지 설치 (이미 package.json에 있음)
pnpm install

# 추가 패키지 (필요 시)
pnpm add @tanstack/react-query axios
pnpm add @radix-ui/react-dialog @radix-ui/react-tabs
pnpm add tailwindcss postcss autoprefixer
pnpm add lucide-react

# TailwindCSS 초기화
pnpm dlx tailwindcss init -p
```

#### Step 4.2: API 클라이언트 설정

**파일: `frontend/src/lib/api.ts` 생성**

```typescript
// frontend/src/lib/api.ts
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 타입 정의
export interface AnalysisBatch {
  id: string;
  status: 'RUNNING' | 'COMPLETED' | 'FAILED' | 'PAUSED';
  trigger_type: string;
  started_at: string;
  completed_at?: string;
}

// API 함수들
export const batchAPI = {
  list: async () => {
    const response = await api.get('/api/control/batches');
    return response.data;
  },

  start: async (trigger_type: string = 'MANUAL') => {
    const response = await api.post(`/api/control/batch/start?trigger_type=${trigger_type}`);
    return response.data;
  },

  stop: async (batchId: string) => {
    const response = await api.post(`/api/control/batch/${batchId}/stop`);
    return response.data;
  },
};
```

#### Step 4.3: React Query 설정

**파일: `frontend/src/App.tsx` 수정**

```typescript
// frontend/src/App.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { BatchList } from './components/BatchList';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 30,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="w-full min-h-screen bg-gray-900 text-white p-8">
        <h1 className="text-4xl font-bold mb-8">🚀 AEGIS Visualizer</h1>
        <BatchList />
      </div>
    </QueryClientProvider>
  );
}

export default App;
```

#### Step 4.4: 배치 목록 컴포넌트

**파일: `frontend/src/components/BatchList.tsx` 생성**

```typescript
// frontend/src/components/BatchList.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { batchAPI, type AnalysisBatch } from '../lib/api';

export function BatchList() {
  const queryClient = useQueryClient();

  // 배치 목록 조회
  const { data, isLoading, error } = useQuery({
    queryKey: ['batches'],
    queryFn: batchAPI.list,
    refetchInterval: 2000, // 2초마다 자동 갱신
  });

  // 배치 시작
  const startMutation = useMutation({
    mutationFn: batchAPI.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batches'] });
    },
  });

  // 배치 중지
  const stopMutation = useMutation({
    mutationFn: batchAPI.stop,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batches'] });
    },
  });

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div className="text-red-500">Error: {(error as Error).message}</div>;
  }

  const batches: AnalysisBatch[] = data?.batches || [];

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">배치 목록</h2>
        <button
          onClick={() => startMutation.mutate()}
          disabled={startMutation.isPending}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50"
        >
          {startMutation.isPending ? '시작 중...' : '새 배치 시작'}
        </button>
      </div>

      {batches.length === 0 ? (
        <div className="text-gray-400">배치가 없습니다. 새 배치를 시작하세요.</div>
      ) : (
        <div className="grid gap-4">
          {batches.map((batch) => (
            <div
              key={batch.id}
              className="p-4 bg-gray-800 rounded-lg border border-gray-700"
            >
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-sm text-gray-400">Batch ID</div>
                  <div className="font-mono text-sm">{batch.id}</div>
                </div>
                <div>
                  <span
                    className={`px-3 py-1 rounded text-sm ${
                      batch.status === 'RUNNING'
                        ? 'bg-yellow-600'
                        : batch.status === 'COMPLETED'
                        ? 'bg-green-600'
                        : batch.status === 'FAILED'
                        ? 'bg-red-600'
                        : 'bg-gray-600'
                    }`}
                  >
                    {batch.status}
                  </span>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div className="text-gray-400">Trigger Type</div>
                  <div>{batch.trigger_type}</div>
                </div>
                <div>
                  <div className="text-gray-400">Started At</div>
                  <div>{new Date(batch.started_at).toLocaleString()}</div>
                </div>
              </div>

              {batch.status === 'RUNNING' && (
                <div className="mt-4">
                  <button
                    onClick={() => stopMutation.mutate(batch.id)}
                    disabled={stopMutation.isPending}
                    className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm disabled:opacity-50"
                  >
                    {stopMutation.isPending ? '중지 중...' : '중지'}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

#### Step 4.5: 테스트

```bash
# Frontend 실행
cd ~/Dev/aegis-visualizer/frontend
pnpm dev

# 브라우저 열기
# http://localhost:5174
```

**테스트 시나리오:**
1. ✅ "새 배치 시작" 버튼 클릭
2. ✅ 배치 카드 생성 확인
3. ✅ Status가 "RUNNING" 확인
4. ✅ "중지" 버튼 클릭
5. ✅ Status가 "PAUSED"로 변경 확인

### ✅ Phase 4 완료 조건

- [ ] Frontend 화면에 배치 목록 표시
- [ ] "새 배치 시작" 버튼 동작
- [ ] "중지" 버튼 동작
- [ ] 2초마다 자동 갱신

---

## Phase 5: 시각화 구현

### 🎯 목표
파티클 시스템 + 애니메이션

### 📚 참조 문서
**ANIMATION_SPEC.md** (31KB)를 읽어주세요.

### 📝 체크리스트
- [ ] Three.js 3D 배경
- [ ] Konva 파티클 시스템
- [ ] Web Worker
- [ ] 애니메이션 타임라인
- [ ] 테스트

### 🚀 실행

**ANIMATION_SPEC.md의 코드를 단계별로 복사-붙여넣기**

이 Phase는 매우 크므로, ANIMATION_SPEC.md를 참조하면서 진행하세요.

---

## ✅ 전체 완료 확인

### 최종 체크리스트

- [ ] Phase 1: 프로젝트 생성 완료
- [ ] Phase 2: Database 8개 테이블 생성
- [ ] Phase 3: Backend API 동작
- [ ] Phase 4: Frontend 기본 동작
- [ ] Phase 5: 시각화 구현

### 접속 확인

```bash
# Backend
curl http://localhost:8001/health
curl http://localhost:8001/api/control/batches

# Frontend
open http://localhost:5174

# Database
psql -h localhost -p 5433 -U visualizer_admin -d visualizer -c "\dt"
```

---

## 🎉 완료!

모든 Phase를 완료했다면, 이제 AI Visualizer가 동작합니다!

다음 단계:
1. 실제 데이터 연동
2. 애니메이션 최적화
3. 관제 시스템 구현

**Happy Coding! 🚀**

---

**작성일**: 2025-12-08
**작성자**: wonny (for Claude Sonnet)
**버전**: 1.0.0
