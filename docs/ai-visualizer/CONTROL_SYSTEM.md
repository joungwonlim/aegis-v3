# Control System Specification

> **백엔드 핸들링 가능한 관제 시스템 설계**

## 📋 목차

1. [개요](#개요)
2. [시스템 구성](#시스템-구성)
3. [모니터링 대시보드](#모니터링-대시보드)
4. [백엔드 API](#백엔드-api)
5. [코드 예제](#코드-예제)

---

## 개요

### 목적

AI 시각화 시스템의 **운영 및 관리**를 위한 관제 시스템:
- 실행 중인 배치 실시간 모니터링
- 성능 지표 추적 (처리 시간, 에러율)
- 수동 개입 (중지, 재시작, 재실행)
- 히스토리 분석 및 디버깅

### 주요 기능

```
┌─────────────────────────────────────────────────────────────────────┐
│                    관제 시스템 기능 맵                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [1] 실시간 모니터링                                                │
│  ──────────────────────────────────────────────────────────────    │
│  • 현재 실행 중인 배치 목록                                         │
│  • 각 배치의 진행 단계 (FETCH → FLASH → PRO)                        │
│  • 처리 시간, 남은 시간 예측                                        │
│  • 에러/경고 즉시 알림                                              │
│                                                                     │
│  [2] 성능 분석                                                      │
│  ──────────────────────────────────────────────────────────────    │
│  • 평균 처리 시간 (단계별)                                          │
│  • AI 모델 응답 시간 (Flash vs Pro)                                 │
│  • 데이터베이스 쿼리 성능                                           │
│  • WebSocket 지연 시간                                              │
│                                                                     │
│  [3] 수동 제어                                                      │
│  ──────────────────────────────────────────────────────────────    │
│  • 배치 시작/중지/재시작                                            │
│  • 특정 단계 스킵                                                   │
│  • 강제 종료 (Emergency Stop)                                       │
│  • 설정 변경 (파티클 수, 애니메이션 속도)                           │
│                                                                     │
│  [4] 히스토리 관리                                                  │
│  ──────────────────────────────────────────────────────────────    │
│  • 과거 배치 검색 (날짜, 상태)                                      │
│  • 타임라인 재생                                                    │
│  • 로그 다운로드 (CSV, JSON)                                        │
│  • 에러 분석 리포트                                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 시스템 구성

### 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Control System Architecture                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Frontend - Control Dashboard]                                     │
│  ──────────────────────────────────────────────────────────────    │
│  React + TailwindCSS + shadcn/ui                                    │
│  • BatchList (실행 목록)                                            │
│  • PerformanceCharts (성능 그래프)                                  │
│  • LogViewer (실시간 로그)                                          │
│  • ManualControls (수동 제어 버튼)                                  │
│                                                                     │
│           │ ▲                                                       │
│           │ │ REST API + WebSocket                                  │
│           ▼ │                                                       │
│                                                                     │
│  [Backend - Control API]                                            │
│  ──────────────────────────────────────────────────────────────    │
│  FastAPI + Socket.IO                                                │
│  • GET /api/control/batches (목록)                                  │
│  • POST /api/control/batch/start (시작)                             │
│  • POST /api/control/batch/{id}/stop (중지)                         │
│  • WS /control (실시간 스트림)                                      │
│                                                                     │
│           │ ▲                                                       │
│           │ │ SQLAlchemy + asyncpg                                  │
│           ▼ │                                                       │
│                                                                     │
│  [Database - Control Tables]                                        │
│  ──────────────────────────────────────────────────────────────    │
│  PostgreSQL 16                                                      │
│  • control_events (제어 이벤트 로그)                                │
│  • performance_metrics (성능 메트릭)                                │
│  • error_logs (에러 로그)                                           │
│                                                                     │
│           │ ▲                                                       │
│           │ │ LISTEN/NOTIFY                                         │
│           ▼ │                                                       │
│                                                                     │
│  [Worker - Brain Executor]                                          │
│  ──────────────────────────────────────────────────────────────    │
│  Python + Celery (선택)                                             │
│  • 배치 실행 (비동기)                                               │
│  • 진행 상황 DB 업데이트                                            │
│  • 에러 핸들링 & 재시도                                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 모니터링 대시보드

### 1. 배치 목록 화면

```typescript
// src/components/control/BatchList.tsx
import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { AnalysisBatch } from '@/types';

export function BatchList() {
  const { data: batches, isLoading } = useQuery({
    queryKey: ['control', 'batches'],
    queryFn: async () => {
      const response = await fetch('/api/control/batches');
      return response.json() as Promise<AnalysisBatch[]>;
    },
    refetchInterval: 2000, // 2초마다 갱신
  });

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">실행 중인 배치</h2>
        <Button onClick={() => startNewBatch()}>
          새 배치 시작
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {batches?.map((batch) => (
          <BatchCard key={batch.id} batch={batch} />
        ))}
      </div>
    </div>
  );
}

function BatchCard({ batch }: { batch: AnalysisBatch }) {
  const statusColor = {
    RUNNING: 'bg-yellow-500',
    COMPLETED: 'bg-green-500',
    FAILED: 'bg-red-500',
    PAUSED: 'bg-gray-500',
  }[batch.status];

  const progress = calculateProgress(batch);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Batch {batch.id.slice(0, 8)}</span>
          <Badge className={statusColor}>{batch.status}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {/* 진행률 */}
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>진행률</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* 현재 단계 */}
          <div className="text-sm">
            <span className="text-gray-500">현재 단계:</span>{' '}
            <span className="font-medium">{batch.current_step}</span>
          </div>

          {/* 경과 시간 */}
          <div className="text-sm">
            <span className="text-gray-500">경과 시간:</span>{' '}
            <span className="font-medium">
              {formatElapsedTime(batch.started_at)}
            </span>
          </div>

          {/* 제어 버튼 */}
          <div className="flex gap-2 pt-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => viewBatch(batch.id)}
            >
              상세보기
            </Button>
            {batch.status === 'RUNNING' && (
              <Button
                size="sm"
                variant="destructive"
                onClick={() => stopBatch(batch.id)}
              >
                중지
              </Button>
            )}
            {batch.status === 'PAUSED' && (
              <Button
                size="sm"
                onClick={() => resumeBatch(batch.id)}
              >
                재개
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### 2. 성능 차트

```typescript
// src/components/control/PerformanceCharts.tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useQuery } from '@tanstack/react-query';

export function PerformanceCharts() {
  const { data: metrics } = useQuery({
    queryKey: ['control', 'metrics'],
    queryFn: async () => {
      const response = await fetch('/api/control/metrics?period=1h');
      return response.json();
    },
    refetchInterval: 5000,
  });

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {/* 처리 시간 차트 */}
      <Card>
        <CardHeader>
          <CardTitle>단계별 처리 시간</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={metrics?.processing_time}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis label={{ value: '시간 (ms)', angle: -90 }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="fetch"
                stroke="#8884d8"
                name="Fetch"
              />
              <Line
                type="monotone"
                dataKey="flash"
                stroke="#82ca9d"
                name="Flash Filter"
              />
              <Line
                type="monotone"
                dataKey="pro"
                stroke="#ffc658"
                name="Pro Reasoning"
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* 에러율 차트 */}
      <Card>
        <CardHeader>
          <CardTitle>에러율</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={metrics?.error_rate}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis label={{ value: '에러율 (%)', angle: -90 }} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="rate"
                stroke="#ff4444"
                name="에러율"
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}
```

### 3. 실시간 로그 뷰어

```typescript
// src/components/control/LogViewer.tsx
import { useEffect, useRef, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useVisualizerSocket } from '@/hooks/useVisualizerSocket';

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR';
  message: string;
  metadata?: any;
}

export function LogViewer({ batchId }: { batchId: string }) {
  const { socket } = useVisualizerSocket(batchId);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const unsubscribe = socket.on<LogEntry>('log', (log) => {
      setLogs((prev) => [...prev, log].slice(-100)); // 최근 100개만 유지
    });

    return unsubscribe;
  }, [socket]);

  useEffect(() => {
    // 새 로그 추가 시 자동 스크롤
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <Card className="h-[600px] flex flex-col">
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>실시간 로그</span>
          <Badge variant="outline">{logs.length} entries</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto">
        <div className="space-y-1 font-mono text-sm">
          {logs.map((log) => (
            <LogEntry key={log.id} log={log} />
          ))}
          <div ref={logEndRef} />
        </div>
      </CardContent>
    </Card>
  );
}

function LogEntry({ log }: { log: LogEntry }) {
  const levelColor = {
    INFO: 'text-blue-600',
    WARNING: 'text-yellow-600',
    ERROR: 'text-red-600',
  }[log.level];

  return (
    <div className="flex items-start gap-2 py-1 hover:bg-gray-50">
      <span className="text-gray-500 text-xs">
        {new Date(log.timestamp).toLocaleTimeString()}
      </span>
      <Badge variant="outline" className={levelColor}>
        {log.level}
      </Badge>
      <span className="flex-1">{log.message}</span>
    </div>
  );
}
```

---

## 백엔드 API

### 1. FastAPI 엔드포인트

```python
# src/api/control.py
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import asyncio

from database import get_db
from models import AnalysisBatch, ControlEvent
from services.batch_executor import BatchExecutor

router = APIRouter(prefix="/api/control", tags=["control"])

# ============================================================================
# REST API
# ============================================================================

@router.get("/batches")
async def list_batches(
    status: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> List[AnalysisBatch]:
    """
    실행 중인 배치 목록 조회

    Args:
        status: 필터 (RUNNING, COMPLETED, FAILED, PAUSED)
        limit: 최대 개수

    Returns:
        배치 목록 (최신순)
    """
    query = db.query(AnalysisBatch).order_by(AnalysisBatch.started_at.desc())

    if status:
        query = query.filter(AnalysisBatch.status == status)

    batches = await query.limit(limit).all()
    return batches


@router.post("/batch/start")
async def start_batch(
    trigger_type: str = "MANUAL",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    새 배치 시작

    Args:
        trigger_type: MANUAL or SCHEDULED

    Returns:
        생성된 배치 정보
    """
    executor = BatchExecutor(db)
    batch = await executor.start_new_batch(trigger_type)

    # 제어 이벤트 로그
    await log_control_event(
        db,
        event_type="BATCH_START",
        batch_id=batch.id,
        metadata={"trigger_type": trigger_type},
    )

    return {
        "batch_id": str(batch.id),
        "status": "RUNNING",
        "message": "Batch started successfully",
    }


@router.post("/batch/{batch_id}/stop")
async def stop_batch(
    batch_id: str,
    reason: str = "USER_REQUEST",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    배치 중지

    Args:
        batch_id: 배치 UUID
        reason: 중지 이유

    Returns:
        중지 결과
    """
    batch = await db.query(AnalysisBatch).filter_by(id=batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    if batch.status != "RUNNING":
        raise HTTPException(status_code=400, detail="Batch is not running")

    # 중지 처리
    batch.status = "PAUSED"
    batch.updated_at = datetime.utcnow()
    await db.commit()

    # 제어 이벤트 로그
    await log_control_event(
        db,
        event_type="BATCH_STOP",
        batch_id=batch.id,
        metadata={"reason": reason},
    )

    return {
        "batch_id": str(batch.id),
        "status": "PAUSED",
        "message": "Batch stopped successfully",
    }


@router.post("/batch/{batch_id}/resume")
async def resume_batch(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    배치 재개
    """
    batch = await db.query(AnalysisBatch).filter_by(id=batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    if batch.status != "PAUSED":
        raise HTTPException(status_code=400, detail="Batch is not paused")

    # 재개 처리
    executor = BatchExecutor(db)
    await executor.resume_batch(batch)

    return {
        "batch_id": str(batch.id),
        "status": "RUNNING",
        "message": "Batch resumed successfully",
    }


@router.get("/metrics")
async def get_metrics(
    period: str = "1h",  # 1h, 6h, 24h, 7d
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    성능 메트릭 조회

    Returns:
        {
            "processing_time": [...],
            "error_rate": [...],
            "throughput": [...],
        }
    """
    from datetime import timedelta

    period_map = {
        "1h": timedelta(hours=1),
        "6h": timedelta(hours=6),
        "24h": timedelta(days=1),
        "7d": timedelta(days=7),
    }

    start_time = datetime.utcnow() - period_map.get(period, timedelta(hours=1))

    # 집계 쿼리 (성능 최적화)
    metrics = await aggregate_metrics(db, start_time)

    return metrics


# ============================================================================
# WebSocket
# ============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, batch_id: str):
        await websocket.accept()
        if batch_id not in self.active_connections:
            self.active_connections[batch_id] = []
        self.active_connections[batch_id].append(websocket)

    def disconnect(self, websocket: WebSocket, batch_id: str):
        self.active_connections[batch_id].remove(websocket)

    async def broadcast(self, batch_id: str, message: dict):
        if batch_id in self.active_connections:
            for connection in self.active_connections[batch_id]:
                await connection.send_json(message)

manager = ConnectionManager()


@router.websocket("/ws/{batch_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    batch_id: str,
):
    """
    실시간 배치 상태 스트리밍

    Events:
        - step:start
        - step:complete
        - log
        - error
    """
    await manager.connect(websocket, batch_id)

    try:
        while True:
            # 클라이언트로부터 메시지 수신 (ping/pong)
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(websocket, batch_id)


# ============================================================================
# Helper Functions
# ============================================================================

async def log_control_event(
    db: AsyncSession,
    event_type: str,
    batch_id: str,
    metadata: dict = None,
):
    """제어 이벤트 로깅"""
    event = ControlEvent(
        event_type=event_type,
        batch_id=batch_id,
        metadata=metadata,
        timestamp=datetime.utcnow(),
    )
    db.add(event)
    await db.commit()


async def aggregate_metrics(db: AsyncSession, start_time: datetime) -> dict:
    """성능 메트릭 집계"""
    from sqlalchemy import func

    # 단계별 평균 처리 시간
    processing_time = await db.query(
        func.date_trunc('minute', AnalysisStep.started_at).label('timestamp'),
        func.avg(AnalysisStep.processing_time_ms).label('avg_time'),
        AnalysisStep.step_name,
    ).filter(
        AnalysisStep.started_at >= start_time
    ).group_by(
        func.date_trunc('minute', AnalysisStep.started_at),
        AnalysisStep.step_name,
    ).all()

    # 에러율
    error_rate = await db.query(
        func.date_trunc('minute', AnalysisStep.started_at).label('timestamp'),
        (func.count(AnalysisStep.error_message) * 100.0 / func.count(*)).label('rate'),
    ).filter(
        AnalysisStep.started_at >= start_time
    ).group_by(
        func.date_trunc('minute', AnalysisStep.started_at),
    ).all()

    return {
        "processing_time": [
            {
                "timestamp": row.timestamp.isoformat(),
                "step": row.step_name,
                "avg_ms": float(row.avg_time or 0),
            }
            for row in processing_time
        ],
        "error_rate": [
            {
                "timestamp": row.timestamp.isoformat(),
                "rate": float(row.rate or 0),
            }
            for row in error_rate
        ],
    }
```

### 2. Batch Executor

```python
# src/services/batch_executor.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import asyncio
from datetime import datetime

from models import AnalysisBatch, AnalysisStep
from brain import BrainOrchestrator


class BatchExecutor:
    """배치 실행 관리자"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_new_batch(self, trigger_type: str) -> AnalysisBatch:
        """새 배치 시작"""
        batch = AnalysisBatch(
            started_at=datetime.utcnow(),
            status="RUNNING",
            trigger_type=trigger_type,
        )
        self.db.add(batch)
        await self.db.commit()
        await self.db.refresh(batch)

        # 비동기로 실행 (백그라운드)
        asyncio.create_task(self._execute_batch(batch))

        return batch

    async def _execute_batch(self, batch: AnalysisBatch):
        """배치 실행 (내부)"""
        try:
            brain = BrainOrchestrator(self.db, batch.id)

            # Phase 1: Fetch
            await self._execute_step(batch, "FETCH", brain.fetch_data)

            # Phase 2: Flash Filter
            await self._execute_step(batch, "FLASH_FILTER", brain.flash_filter)

            # Phase 3: Pro Reasoning
            await self._execute_step(batch, "PRO_REASON", brain.pro_reasoning)

            # 완료
            batch.status = "COMPLETED"
            batch.completed_at = datetime.utcnow()
            await self.db.commit()

        except Exception as e:
            batch.status = "FAILED"
            batch.error_message = str(e)
            await self.db.commit()
            raise

    async def _execute_step(
        self,
        batch: AnalysisBatch,
        step_name: str,
        func,
    ):
        """단계 실행 및 로깅"""
        step = AnalysisStep(
            batch_id=batch.id,
            step_name=step_name,
            started_at=datetime.utcnow(),
        )
        self.db.add(step)
        await self.db.commit()

        try:
            start_time = asyncio.get_event_loop().time()

            # 실행
            result = await func()

            end_time = asyncio.get_event_loop().time()

            # 결과 저장
            step.completed_at = datetime.utcnow()
            step.processing_time_ms = int((end_time - start_time) * 1000)
            step.input_count = result.get("input_count")
            step.output_count = result.get("output_count")
            await self.db.commit()

            # WebSocket 브로드캐스트
            await self._broadcast_event(batch.id, "step:complete", {
                "step_name": step_name,
                "processing_time_ms": step.processing_time_ms,
                "input_count": step.input_count,
                "output_count": step.output_count,
            })

        except Exception as e:
            step.error_message = str(e)
            await self.db.commit()
            raise

    async def _broadcast_event(self, batch_id: str, event_type: str, data: dict):
        """WebSocket 이벤트 브로드캐스트"""
        from api.control import manager

        await manager.broadcast(batch_id, {
            "event": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        })

    async def resume_batch(self, batch: AnalysisBatch):
        """중지된 배치 재개"""
        batch.status = "RUNNING"
        await self.db.commit()

        # 중단된 단계부터 재개
        asyncio.create_task(self._execute_batch(batch))
```

---

## 다음 단계

1. **데이터베이스 스키마**: [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) 참조
2. **프론트엔드 구현**: TECH_STACK.md 기반 개발
3. **테스트**: Batch 실행 → 관제 시스템 모니터링

---

**작성일**: 2025-12-08
**작성자**: wonny
**버전**: 1.0.0
