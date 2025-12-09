# AI Visualizer - Independent Project Setup

> **기존 AEGIS v2와 분리된 독립 프로젝트 생성 가이드**

## 🎯 목표

- 새 PostgreSQL database (visualizer_db)
- 새 FastAPI backend (port 8001)
- 새 React frontend (port 5174)
- Docker Compose로 통합

---

## 📁 프로젝트 구조

```
~/Dev/aegis-visualizer/              ← 새 프로젝트 루트
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   └── env.py
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── control.py           ← 관제 API
│   │   │   └── visualizer.py        ← 시각화 API
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── visualizer.py        ← SQLAlchemy 모델
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── batch_executor.py
│   │   │   └── signal_processor.py
│   │   ├── database.py
│   │   └── main.py
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── visualizer/
│   │   │   │   ├── MainVisualizer.tsx
│   │   │   │   ├── ParticleSystem.tsx
│   │   │   │   ├── Globe3D.tsx
│   │   │   │   └── BrainCore.tsx
│   │   │   └── control/
│   │   │       ├── BatchList.tsx
│   │   │       ├── PerformanceCharts.tsx
│   │   │       └── LogViewer.tsx
│   │   ├── hooks/
│   │   │   ├── useVisualizerData.ts
│   │   │   ├── useVisualizerSocket.ts
│   │   │   └── useParticleWorker.ts
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   ├── socket.ts
│   │   │   └── particles/
│   │   ├── workers/
│   │   │   └── particle.worker.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── vite-env.d.ts
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── Dockerfile
│   └── .env
│
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## 🚀 Step-by-Step 생성

### Step 1: 프로젝트 루트 생성

```bash
# 새 프로젝트 디렉토리
cd ~/Dev
mkdir aegis-visualizer
cd aegis-visualizer

# Git 초기화
git init
```

### Step 2: Backend 생성

```bash
# Backend 디렉토리
mkdir -p backend/app/{api,models,services}
mkdir -p backend/alembic/versions

cd backend
```

#### requirements.txt

```txt
# requirements.txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
asyncpg==0.30.0
alembic==1.14.0
pydantic==2.10.4
pydantic-settings==2.7.0
python-socketio==5.12.0
python-engineio==4.11.2
python-dotenv==1.0.1
psycopg2-binary==2.9.10
```

#### .env

```bash
# .env
DATABASE_URL=postgresql://visualizer_admin:visualizer2024@localhost:5433/visualizer
SECRET_KEY=your-secret-key-change-in-production
DEBUG=True
CORS_ORIGINS=http://localhost:5173,http://localhost:5174
```

#### app/main.py

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import socketio

from app.api import control, visualizer
from app.database import engine, Base

# Socket.IO
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*'
)
socket_app = socketio.ASGIApp(sio)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        # 테이블 자동 생성 (개발용, 프로덕션에서는 Alembic 사용)
        # await conn.run_sync(Base.metadata.create_all)
        pass
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
app.include_router(visualizer.router, prefix="/api/visualizer", tags=["visualizer"])

# Socket.IO mount
app.mount("/socket.io", socket_app)


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

#### app/database.py

```python
# app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://visualizer_admin:visualizer2024@localhost:5433/visualizer"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # SQL 로깅 (개발용)
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

#### app/models/visualizer.py

```python
# app/models/visualizer.py
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

    # 관계
    batch = relationship('AnalysisBatch', back_populates='steps')


# ... (나머지 모델들 - DATABASE_SCHEMA.md 참조)
```

#### app/api/control.py

```python
# app/api/control.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.models.visualizer import AnalysisBatch

router = APIRouter()


@router.get("/batches")
async def list_batches(
    status: str = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """실행 중인 배치 목록"""
    # TODO: 구현
    return {"batches": []}


@router.post("/batch/start")
async def start_batch(
    trigger_type: str = "MANUAL",
    db: AsyncSession = Depends(get_db),
):
    """새 배치 시작"""
    # TODO: 구현
    return {"message": "Batch started"}
```

#### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Step 3: Frontend 생성

```bash
cd ~/Dev/aegis-visualizer

# Vite로 React + TypeScript 프로젝트 생성
pnpm create vite frontend -- --template react-ts

cd frontend
pnpm install
```

#### 추가 패키지 설치

```bash
# UI & 시각화
pnpm add @react-three/fiber @react-three/drei three
pnpm add react-konva konva
pnpm add framer-motion

# 데이터 페칭
pnpm add @tanstack/react-query axios socket.io-client

# UI 라이브러리
pnpm add @radix-ui/react-dialog @radix-ui/react-tabs
pnpm add tailwindcss postcss autoprefixer
pnpm add class-variance-authority clsx tailwind-merge
pnpm add lucide-react

# 타입
pnpm add -D @types/three

# TailwindCSS 초기화
pnpm dlx tailwindcss init -p
```

#### .env

```bash
# .env
VITE_API_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001
```

#### vite.config.ts

```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  worker: {
    format: 'es',
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/socket.io': {
        target: 'ws://localhost:8001',
        ws: true,
      },
    },
  },
});
```

#### src/lib/api.ts

```typescript
// src/lib/api.ts
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';

export const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);
```

#### src/App.tsx

```typescript
// src/App.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { MainVisualizer } from './components/visualizer/MainVisualizer';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 30,
    },
  },
});

function App() {
  const [batchId] = useState('demo-batch-id');

  return (
    <QueryClientProvider client={queryClient}>
      <div className="w-full h-screen bg-black">
        <MainVisualizer batchId={batchId} />
      </div>
    </QueryClientProvider>
  );
}

export default App;
```

#### Dockerfile

```dockerfile
# Dockerfile
FROM node:20-slim

WORKDIR /app

RUN npm install -g pnpm

COPY package.json pnpm-lock.yaml ./
RUN pnpm install

COPY . .

EXPOSE 5173

CMD ["pnpm", "dev", "--host"]
```

### Step 4: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL Database
  db:
    image: postgres:16
    container_name: visualizer_db
    environment:
      POSTGRES_DB: visualizer
      POSTGRES_USER: visualizer_admin
      POSTGRES_PASSWORD: visualizer2024
      TZ: Asia/Seoul
    ports:
      - "5433:5432"
    volumes:
      - visualizer_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U visualizer_admin"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Backend API
  backend:
    build: ./backend
    container_name: visualizer_backend
    environment:
      DATABASE_URL: postgresql+asyncpg://visualizer_admin:visualizer2024@db:5432/visualizer
      CORS_ORIGINS: http://localhost:5173,http://localhost:5174
    ports:
      - "8001:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # Frontend
  frontend:
    build: ./frontend
    container_name: visualizer_frontend
    environment:
      VITE_API_URL: http://localhost:8001
      VITE_WS_URL: ws://localhost:8001
    ports:
      - "5174:5173"
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: pnpm dev --host

volumes:
  visualizer_data:
```

### Step 5: .gitignore

```bash
# .gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.env
venv/
*.egg-info/

# Node
node_modules/
dist/
.DS_Store

# Database
*.db
*.sqlite

# IDE
.vscode/
.idea/

# Docker
*.log
```

---

## 🚀 실행

### 1. Docker Compose로 전체 실행

```bash
cd ~/Dev/aegis-visualizer

# 전체 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

### 2. 개별 실행 (개발용)

#### Backend

```bash
cd backend

# 가상환경
python -m venv venv
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt

# DB 마이그레이션
alembic upgrade head

# 실행
uvicorn app.main:app --reload --port 8001
```

#### Frontend

```bash
cd frontend

# 패키지 설치
pnpm install

# 실행
pnpm dev
```

---

## ✅ 접속 확인

| 서비스 | URL | 설명 |
|-------|-----|------|
| Frontend | http://localhost:5174 | React 앱 |
| Backend API | http://localhost:8001 | FastAPI |
| API Docs | http://localhost:8001/docs | Swagger UI |
| Database | localhost:5433 | PostgreSQL |

---

## 🔧 Database 초기화

```bash
# psql 접속
psql -h localhost -p 5433 -U visualizer_admin -d visualizer

# 테이블 확인
\dt

# 종료
\q
```

---

## 📊 AEGIS v2와의 차이

| 항목 | AEGIS v2 | Visualizer |
|-----|----------|-----------|
| Database | aegis_v2 (port 5432) | visualizer (port 5433) |
| Backend | port 8000 | port 8001 |
| Frontend | - | port 5174 |
| 독립성 | - | ✅ 완전 독립 |

---

**작성일**: 2025-12-08
**작성자**: wonny
**버전**: 1.0.0
