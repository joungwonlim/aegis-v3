# Technology Stack Specification

> **반응형 + 고성능 AI 시각화를 위한 기술 스택**

## 📋 목차

1. [개요](#개요)
2. [프론트엔드 스택](#프론트엔드-스택)
3. [백엔드 스택](#백엔드-스택)
4. [반응형 설계](#반응형-설계)
5. [성능 최적화](#성능-최적화)
6. [코드 예제](#코드-예제)

---

## 개요

### 기술 선택 기준

| 기준 | 요구사항 | 선택 |
|-----|---------|------|
| **반응형** | 모바일 ~ 4K 대응 | TailwindCSS + Container Queries |
| **성능** | 60 FPS, 수천 개 파티클 | Canvas + WebGL + Worker |
| **실시간** | 50ms 이하 지연 | WebSocket + React Query |
| **개발 속도** | 빠른 프로토타이핑 | TypeScript + Vite + shadcn/ui |
| **유지보수** | 타입 안정성 | Full TypeScript Stack |

---

## 프론트엔드 스택

### Core Framework

```json
{
  "react": "^18.3.1",
  "typescript": "^5.6.3",
  "vite": "^6.0.1"
}
```

**선택 이유**:
- React 18: Concurrent Features (useTransition, useDeferredValue)
- TypeScript: 타입 안정성
- Vite: 초고속 HMR

### UI 라이브러리

```json
{
  "@radix-ui/react-*": "^latest",
  "tailwindcss": "^3.4.17",
  "framer-motion": "^11.15.0",
  "class-variance-authority": "^0.7.1",
  "clsx": "^2.1.1"
}
```

**구성**:
- shadcn/ui: 커스터마이징 가능한 컴포넌트
- TailwindCSS: 유틸리티 CSS + JIT
- Framer Motion: 60fps UI 애니메이션
- CVA: 반응형 variants

### 시각화 라이브러리

```json
{
  "@react-three/fiber": "^8.18.5",
  "@react-three/drei": "^9.122.4",
  "three": "^0.171.0",
  "react-konva": "^18.2.10",
  "konva": "^9.3.16"
}
```

**역할 분담**:
- **Three.js**: 3D 배경 (지구본, 라이팅)
- **Konva**: 2D 파티클 (성능 최적)
- **Drei**: Three.js 헬퍼

### 데이터 페칭

```json
{
  "@tanstack/react-query": "^5.62.11",
  "axios": "^1.7.9",
  "socket.io-client": "^4.8.1"
}
```

**전략**:
- React Query: 캐싱 + 자동 재시도
- Axios: REST API
- Socket.IO: 실시간 스트리밍

---

## 백엔드 스택

### Web Framework

```python
# requirements.txt
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-socketio==5.12.0
python-engineio==4.11.2
```

**FastAPI 선택 이유**:
- 자동 API 문서 (OpenAPI)
- WebSocket 내장
- Pydantic 검증
- 비동기 처리

### Database

```python
sqlalchemy==2.0.36
asyncpg==0.30.0
alembic==1.14.0
```

**PostgreSQL 16 기능 활용**:
- UUID v7 (시간 정렬)
- JSONB (유연한 스키마)
- Partial Index (성능)
- LISTEN/NOTIFY (실시간)

### 데이터 처리

```python
pandas==2.2.3
numpy==2.2.1
pydantic==2.10.4
```

---

## 반응형 설계

### 1. Breakpoints

```typescript
// src/lib/responsive.ts
export const breakpoints = {
  mobile: 640,    // 0-640px
  tablet: 768,    // 641-768px
  laptop: 1024,   // 769-1024px
  desktop: 1280,  // 1025-1280px
  '4k': 1920,     // 1281px+
} as const;

export type Breakpoint = keyof typeof breakpoints;

export function useBreakpoint(): Breakpoint {
  const [breakpoint, setBreakpoint] = useState<Breakpoint>('desktop');

  useEffect(() => {
    const handleResize = () => {
      const width = window.innerWidth;
      if (width < breakpoints.mobile) setBreakpoint('mobile');
      else if (width < breakpoints.tablet) setBreakpoint('tablet');
      else if (width < breakpoints.laptop) setBreakpoint('laptop');
      else if (width < breakpoints.desktop) setBreakpoint('desktop');
      else setBreakpoint('4k');
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return breakpoint;
}
```

### 2. Canvas 반응형

```typescript
// src/components/visualizer/ResponsiveCanvas.tsx
import { useEffect, useRef } from 'react';
import { Stage, Layer } from 'react-konva';
import { useBreakpoint } from '@/lib/responsive';

export function ResponsiveCanvas() {
  const breakpoint = useBreakpoint();
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  // 파티클 수 동적 조절
  const particleCount = useMemo(() => {
    switch (breakpoint) {
      case 'mobile': return 100;
      case 'tablet': return 500;
      case 'laptop': return 1000;
      case 'desktop': return 2500;
      case '4k': return 5000;
    }
  }, [breakpoint]);

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight,
        });
      }
    };

    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  return (
    <div ref={containerRef} className="w-full h-full">
      <Stage width={dimensions.width} height={dimensions.height}>
        <Layer>
          <ParticleSystem count={particleCount} />
        </Layer>
      </Stage>
    </div>
  );
}
```

### 3. TailwindCSS 설정

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss';
import tailwindAnimate from 'tailwindcss-animate';

export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      screens: {
        'xs': '480px',
        'sm': '640px',
        'md': '768px',
        'lg': '1024px',
        'xl': '1280px',
        '2xl': '1536px',
        '3xl': '1920px',
        '4k': '2560px',
      },
      container: {
        center: true,
        padding: {
          DEFAULT: '1rem',
          sm: '2rem',
          lg: '4rem',
          xl: '5rem',
          '2xl': '6rem',
        },
      },
    },
  },
  plugins: [tailwindAnimate],
} satisfies Config;
```

---

## 성능 최적화

### 1. Web Worker (파티클 계산)

```typescript
// src/workers/particle.worker.ts
export interface ParticleData {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  color: string;
  size: number;
}

self.onmessage = (e: MessageEvent<{
  particles: ParticleData[];
  deltaTime: number;
  width: number;
  height: number;
}>) => {
  const { particles, deltaTime, width, height } = e.data;

  // 무거운 계산을 Worker에서 수행
  const updated = particles.map(p => ({
    ...p,
    x: (p.x + p.vx * deltaTime) % width,
    y: (p.y + p.vy * deltaTime) % height,
  }));

  self.postMessage({ particles: updated });
};

// src/hooks/useParticleWorker.ts
import { useEffect, useRef } from 'react';
import ParticleWorker from '@/workers/particle.worker?worker';

export function useParticleWorker() {
  const workerRef = useRef<Worker>();

  useEffect(() => {
    workerRef.current = new ParticleWorker();
    return () => workerRef.current?.terminate();
  }, []);

  const updateParticles = useCallback((
    particles: ParticleData[],
    deltaTime: number,
    width: number,
    height: number
  ) => {
    return new Promise<ParticleData[]>((resolve) => {
      if (!workerRef.current) return resolve(particles);

      workerRef.current.onmessage = (e) => {
        resolve(e.data.particles);
      };

      workerRef.current.postMessage({ particles, deltaTime, width, height });
    });
  }, []);

  return { updateParticles };
}
```

### 2. Canvas Offscreen 렌더링

```typescript
// src/components/visualizer/OffscreenCanvas.tsx
import { useEffect, useRef } from 'react';

export function OffscreenCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const offscreenRef = useRef<OffscreenCanvas>();

  useEffect(() => {
    if (!canvasRef.current) return;

    // Offscreen Canvas로 백그라운드 렌더링
    offscreenRef.current = canvasRef.current.transferControlToOffscreen();

    const worker = new Worker(
      new URL('@/workers/render.worker.ts', import.meta.url),
      { type: 'module' }
    );

    worker.postMessage(
      { canvas: offscreenRef.current, width: 1920, height: 1080 },
      [offscreenRef.current]
    );

    return () => worker.terminate();
  }, []);

  return <canvas ref={canvasRef} className="w-full h-full" />;
}
```

### 3. React Query 캐싱 전략

```typescript
// src/lib/queryClient.ts
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5분
      gcTime: 1000 * 60 * 30,   // 30분 (이전 cacheTime)
      refetchOnWindowFocus: false,
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

// src/hooks/useVisualizerData.ts
import { useQuery } from '@tanstack/react-query';
import type { AnalysisBatch } from '@/types';

export function useVisualizerData(batchId: string) {
  return useQuery({
    queryKey: ['visualizer', batchId],
    queryFn: async () => {
      const response = await fetch(`/api/visualizer/${batchId}`);
      if (!response.ok) throw new Error('Failed to fetch');
      return response.json() as Promise<AnalysisBatch>;
    },
    // 실시간 모드: 500ms마다 폴링
    refetchInterval: 500,
    // 완료된 배치는 폴링 중지
    refetchIntervalInBackground: false,
    enabled: !!batchId,
  });
}
```

### 4. WebSocket 최적화

```typescript
// src/lib/socket.ts
import { io, Socket } from 'socket.io-client';

export class VisualizerSocket {
  private socket: Socket;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;

  constructor(private url: string) {
    this.socket = io(url, {
      transports: ['websocket'], // Long polling 비활성화
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      timeout: 20000,
    });

    this.setupListeners();
  }

  private setupListeners() {
    this.socket.on('connect', () => {
      console.log('Connected to visualizer');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', (reason) => {
      console.warn('Disconnected:', reason);
      if (reason === 'io server disconnect') {
        // 서버가 끊음 - 재연결 시도
        this.socket.connect();
      }
    });

    this.socket.on('connect_error', (error) => {
      this.reconnectAttempts++;
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('Max reconnect attempts reached');
        this.socket.disconnect();
      }
    });
  }

  // 이벤트 구독 (타입 안전)
  on<T = any>(event: string, callback: (data: T) => void) {
    this.socket.on(event, callback);
    return () => this.socket.off(event, callback); // Cleanup 함수 반환
  }

  emit(event: string, data: any) {
    this.socket.emit(event, data);
  }

  disconnect() {
    this.socket.disconnect();
  }
}

// src/hooks/useVisualizerSocket.ts
import { useEffect, useState } from 'react';
import { VisualizerSocket } from '@/lib/socket';

export function useVisualizerSocket(batchId: string) {
  const [socket] = useState(() => new VisualizerSocket('/visualizer'));
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');

  useEffect(() => {
    const unsubscribeStatus = socket.on('connect', () => {
      setStatus('connected');
      // 특정 배치 구독
      socket.emit('subscribe', { batchId });
    });

    const unsubscribeDisconnect = socket.on('disconnect', () => {
      setStatus('disconnected');
    });

    return () => {
      socket.emit('unsubscribe', { batchId });
      unsubscribeStatus();
      unsubscribeDisconnect();
      socket.disconnect();
    };
  }, [batchId, socket]);

  return { socket, status };
}
```

---

## 코드 예제

### 1. 파티클 시스템 (Konva)

```typescript
// src/components/visualizer/ParticleSystem.tsx
import { useEffect, useRef, useMemo } from 'react';
import { Circle, Group } from 'react-konva';
import { useParticleWorker } from '@/hooks/useParticleWorker';
import type { SignalLog } from '@/types';

interface ParticleSystemProps {
  signals: SignalLog[];
  width: number;
  height: number;
}

export function ParticleSystem({ signals, width, height }: ParticleSystemProps) {
  const groupRef = useRef(null);
  const { updateParticles } = useParticleWorker();
  const [particles, setParticles] = useState<ParticleData[]>([]);

  // 신호 → 파티클 변환
  const initialParticles = useMemo(() => {
    return signals.map((signal, i) => ({
      id: signal.id,
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (signal.sentiment_score || 0) * 100, // 긍정일수록 빠름
      vy: Math.random() * 50 - 25,
      color: signal.sentiment === 'POSITIVE' ? '#00ff00' : '#ff0000',
      size: Math.abs(signal.sentiment_score || 0) * 10,
    }));
  }, [signals, width, height]);

  useEffect(() => {
    setParticles(initialParticles);
  }, [initialParticles]);

  // 애니메이션 루프
  useEffect(() => {
    let frameId: number;
    let lastTime = performance.now();

    const animate = async (currentTime: number) => {
      const deltaTime = (currentTime - lastTime) / 1000; // 초 단위
      lastTime = currentTime;

      // Worker에서 계산
      const updated = await updateParticles(particles, deltaTime, width, height);
      setParticles(updated);

      frameId = requestAnimationFrame(animate);
    };

    frameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameId);
  }, [particles, updateParticles, width, height]);

  return (
    <Group ref={groupRef}>
      {particles.map((p) => (
        <Circle
          key={p.id}
          x={p.x}
          y={p.y}
          radius={p.size}
          fill={p.color}
          opacity={0.6}
          shadowBlur={10}
          shadowColor={p.color}
        />
      ))}
    </Group>
  );
}
```

### 2. Three.js 지구본

```typescript
// src/components/visualizer/Globe3D.tsx
import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';

function RotatingGlobe() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.1; // 천천히 회전
    }
  });

  // 신호 위치 마커
  const markers = useMemo(() => {
    const positions = [
      { lat: 40.7128, lng: -74.0060, name: 'US' },    // 뉴욕
      { lat: 51.5074, lng: -0.1278, name: 'EU' },     // 런던
      { lat: 35.6762, lng: 139.6503, name: 'JP' },    // 도쿄
      { lat: 37.5665, lng: 126.9780, name: 'KR' },    // 서울
    ];

    return positions.map((pos) => {
      const phi = (90 - pos.lat) * (Math.PI / 180);
      const theta = (pos.lng + 180) * (Math.PI / 180);
      const radius = 2.1;

      return {
        position: [
          radius * Math.sin(phi) * Math.cos(theta),
          radius * Math.cos(phi),
          radius * Math.sin(phi) * Math.sin(theta),
        ] as [number, number, number],
        name: pos.name,
      };
    });
  }, []);

  return (
    <group>
      {/* 지구 */}
      <Sphere ref={meshRef} args={[2, 64, 64]}>
        <MeshDistortMaterial
          color="#0066ff"
          attach="material"
          distort={0.3}
          speed={2}
          roughness={0.4}
          metalness={0.8}
        />
      </Sphere>

      {/* 위치 마커 */}
      {markers.map((marker) => (
        <Sphere key={marker.name} position={marker.position} args={[0.05, 16, 16]}>
          <meshStandardMaterial color="#ffff00" emissive="#ffff00" emissiveIntensity={2} />
        </Sphere>
      ))}
    </group>
  );
}

export function Globe3D() {
  return (
    <div className="w-full h-full">
      <Canvas camera={{ position: [0, 0, 8], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1} />
        <RotatingGlobe />
        <OrbitControls enableZoom={false} enablePan={false} />
      </Canvas>
    </div>
  );
}
```

### 3. 실시간 데이터 연동

```typescript
// src/components/visualizer/RealtimeVisualizer.tsx
import { useVisualizerSocket } from '@/hooks/useVisualizerSocket';
import { useVisualizerData } from '@/hooks/useVisualizerData';
import { ParticleSystem } from './ParticleSystem';
import { Globe3D } from './Globe3D';
import type { AnalysisStep } from '@/types';

interface RealtimeVisualizerProps {
  batchId: string;
}

export function RealtimeVisualizer({ batchId }: RealtimeVisualizerProps) {
  const { data, isLoading } = useVisualizerData(batchId);
  const { socket, status } = useVisualizerSocket(batchId);
  const [currentStep, setCurrentStep] = useState<AnalysisStep | null>(null);

  // 실시간 이벤트 구독
  useEffect(() => {
    const unsubscribe = socket.on<AnalysisStep>('step:complete', (step) => {
      setCurrentStep(step);

      // 단계별 애니메이션 트리거
      switch (step.step_name) {
        case 'FETCH':
          // 파티클 생성 애니메이션
          break;
        case 'FLASH_FILTER':
          // 필터링 애니메이션
          break;
        case 'PRO_REASON':
          // 최종 선정 애니메이션
          break;
      }
    });

    return unsubscribe;
  }, [socket]);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!data) {
    return <ErrorMessage>데이터를 불러올 수 없습니다</ErrorMessage>;
  }

  return (
    <div className="relative w-full h-screen bg-black">
      {/* 3D 배경 */}
      <div className="absolute inset-0 z-0">
        <Globe3D />
      </div>

      {/* 2D 파티클 */}
      <div className="absolute inset-0 z-10">
        <ParticleSystem
          signals={data.signals}
          width={window.innerWidth}
          height={window.innerHeight}
        />
      </div>

      {/* UI 오버레이 */}
      <div className="absolute inset-0 z-20 pointer-events-none">
        <StepIndicator currentStep={currentStep} />
        <StatsPanel batch={data} />
      </div>

      {/* 연결 상태 표시 */}
      <div className="absolute top-4 right-4 z-30">
        <ConnectionStatus status={status} />
      </div>
    </div>
  );
}
```

### 4. 반응형 레이아웃

```typescript
// src/components/visualizer/ResponsiveLayout.tsx
import { useBreakpoint } from '@/lib/responsive';

export function ResponsiveLayout({ children }: { children: React.ReactNode }) {
  const breakpoint = useBreakpoint();

  return (
    <div className="w-full h-full">
      {/* 모바일: 세로 스택 */}
      {breakpoint === 'mobile' && (
        <div className="flex flex-col h-full">
          <div className="h-1/2">{children}</div>
          <div className="h-1/2 p-4">
            <ControlPanel compact />
          </div>
        </div>
      )}

      {/* 태블릿: 가로 분할 */}
      {breakpoint === 'tablet' && (
        <div className="flex h-full">
          <div className="w-2/3">{children}</div>
          <div className="w-1/3 p-4">
            <ControlPanel />
          </div>
        </div>
      )}

      {/* 데스크톱: 풀스크린 + 플로팅 */}
      {['laptop', 'desktop', '4k'].includes(breakpoint) && (
        <div className="relative w-full h-full">
          {children}
          <div className="absolute bottom-8 right-8 w-96">
            <ControlPanel floating />
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## 빌드 및 배포

### Vite 설정

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
  build: {
    target: 'esnext',
    rollupOptions: {
      output: {
        manualChunks: {
          'three': ['three', '@react-three/fiber', '@react-three/drei'],
          'konva': ['react-konva', 'konva'],
          'ui': ['framer-motion', '@radix-ui/react-dialog', '@radix-ui/react-tabs'],
        },
      },
    },
  },
  optimizeDeps: {
    include: ['three', 'konva'],
  },
});
```

### 환경 변수

```bash
# .env.development
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# .env.production
VITE_API_URL=https://api.aegis.com
VITE_WS_URL=wss://api.aegis.com
```

---

## 다음 단계

1. **개발 환경 설정**: `pnpm install` → `pnpm dev`
2. **컴포넌트 개발**: ParticleSystem → Globe3D → RealtimeVisualizer
3. **WebSocket 연동**: 백엔드 API와 통합
4. **성능 테스트**: Lighthouse + React DevTools Profiler
5. **반응형 테스트**: Chrome DevTools Device Mode

---

**작성일**: 2025-12-08
**작성자**: wonny
**버전**: 1.0.0
