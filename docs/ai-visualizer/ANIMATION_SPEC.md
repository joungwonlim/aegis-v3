# Animation Specification

> **프레젠테이션 퀄리티 애니메이션 설계**

## 📋 목차

1. [개요](#개요)
2. [애니메이션 타임라인](#애니메이션-타임라인)
3. [레이어 구조](#레이어-구조)
4. [파티클 시스템](#파티클-시스템)
5. [코드 예제](#코드-예제)

---

## 개요

### 목표

- **60 FPS** 유지 (모바일 30+ FPS)
- **인간이 인지 가능한** 데이터 흐름
- **프레젠테이션 퀄리티** 비주얼
- **데이터 무결성** (DB와 완벽히 동기화)

### 핵심 원칙

| 원칙 | 설명 |
|-----|------|
| **Data-Driven** | 모든 애니메이션은 실제 데이터 기반 |
| **Smooth** | ease-in-out, 부드러운 전환 |
| **Meaningful** | 색상/속도/방향이 의미 전달 |
| **Performant** | Canvas + WebGL + Worker |

---

## 애니메이션 타임라인

### 전체 타임라인 (15초)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ⏱️ TIMELINE (0:00 ~ 0:15)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [0:00 ~ 0:02] Phase 0: 초기화                                      │
│  ──────────────────────────────────────────────────────────────    │
│  • 어두운 화면에서 페이드인                                         │
│  • 3D 지구본 회전 시작                                              │
│  • 글로벌 소스 위치 마커 표시                                       │
│    (🇺🇸 미국, 🇪🇺 유럽, 🇯🇵 일본, 🇨🇳 중국, 🥇 금, 🛢️ 원유)         │
│                                                                     │
│  [0:02 ~ 0:05] Phase 1: 데이터 수집 (FETCH)                         │
│  ──────────────────────────────────────────────────────────────    │
│  • 각 소스에서 파티클 발사                                          │
│  • 긍정 신호: 🟢 Green/Cyan, 빠른 속도                              │
│  • 부정 신호: 🔴 Red/Orange, 느린 속도                              │
│  • 중립 신호: ⚪ White/Gray, 중간 속도                              │
│  • 파티클 옆에 키워드 라벨 (0.5초간 표시)                           │
│    예: "Fed 금리 동결", "WTI 급등", "금 최고치"                     │
│                                                                     │
│  [0:05 ~ 0:08] Phase 2: 신호 융합 (SIGNAL FUSION)                   │
│  ──────────────────────────────────────────────────────────────    │
│  • 모든 파티클이 중앙 Brain으로 수렴                                │
│  • 긍정 파티클: 밝게 빛나며 흡수됨                                  │
│  • 부정 파티클: 어둡게 변하며 튕겨나감 (소멸)                       │
│  • 중립 파티클: 흐릿하게 통과                                       │
│  • Brain 코어가 점점 밝아짐 (에너지 축적 효과)                      │
│  • 맥동(Pulse) 효과 (1초에 2회)                                     │
│                                                                     │
│  [0:08 ~ 0:10] Phase 3: Flash Filter (2500 → 50)                    │
│  ──────────────────────────────────────────────────────────────    │
│  • Brain 내부에 2,500개 종목 점들 표시                              │
│  • 빠른 회전 애니메이션 (3초에 5회전)                               │
│  • 필터링 효과: 점들이 빠르게 사라짐                                │
│  • 숫자 카운터: "2500 → 50" (0.5초간)                               │
│  • 최종 50개만 남고 정렬됨                                          │
│                                                                     │
│  [0:10 ~ 0:13] Phase 4: Pro Reasoning (50 → 3)                      │
│  ──────────────────────────────────────────────────────────────    │
│  • 50개 점들이 원형 배치                                            │
│  • 깊은 맥동 (1초에 1회, 더 강하게)                                 │
│  • 연결선이 3개 종목으로 수렴                                       │
│  • 나머지 47개는 흐릿해지며 소멸                                    │
│  • 3개 종목이 커지며 중앙으로                                       │
│                                                                     │
│  [0:13 ~ 0:15] Phase 5: 결과 발표 (FINAL)                           │
│  ──────────────────────────────────────────────────────────────    │
│  • Brain에서 3개의 광선(레이저) 발사                                │
│  • 각 광선 끝에 종목 카드 팝업 (0.2초 딜레이)                       │
│  • 카드 내용:                                                       │
│    - 종목명, 코드                                                   │
│    - 점수 (막대 그래프)                                             │
│    - 영향 받은 신호 (아이콘 3개)                                    │
│  • 카드에서 소스로 연결선 표시                                      │
│    예: 삼성전자 ←─ 🇺🇸 Fed ←─ 🥇 Gold                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 반응형 타임라인

| 디바이스 | 전체 시간 | 특이사항 |
|---------|---------|---------|
| 모바일 | 10초 | Flash/Pro 단계 간소화 |
| 태블릿 | 12초 | 파티클 수 감소 |
| 데스크톱 | 15초 | 풀 애니메이션 |
| 4K | 15초 | 고해상도 텍스처 |

---

## 레이어 구조

### Z-Index 레이어링

```typescript
// src/constants/layers.ts
export const LAYERS = {
  BACKGROUND: 0,      // 3D 지구본
  PARTICLES: 10,      // 2D 파티클
  CONNECTIONS: 20,    // 연결선
  BRAIN: 30,          // 중앙 Brain
  CARDS: 40,          // 결과 카드
  UI: 50,             // 버튼, 타이머
  OVERLAY: 60,        // 로딩, 에러
} as const;
```

### 레이어별 상세

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Layer Structure                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  [Layer 0] Background (Three.js)                                    │
│  ──────────────────────────────────────────────────────────────    │
│  • 3D 지구본 (회전)                                                 │
│  • 별 배경 (선택)                                                   │
│  • 그리드 (선택)                                                    │
│  • 렌더: WebGL                                                      │
│                                                                     │
│  [Layer 10] Particles (Konva)                                       │
│  ──────────────────────────────────────────────────────────────    │
│  • 신호 파티클 (원형, 발광)                                         │
│  • 종목 점 (작은 원)                                                │
│  • 렌더: Canvas 2D                                                  │
│  • 계산: Web Worker                                                 │
│                                                                     │
│  [Layer 20] Connections (SVG)                                       │
│  ──────────────────────────────────────────────────────────────    │
│  • 파티클 → Brain 연결선                                            │
│  • Brain → 카드 연결선                                              │
│  • 카드 → 소스 역추적 선                                            │
│  • 렌더: SVG Path (부드러운 곡선)                                   │
│                                                                     │
│  [Layer 30] Brain (Lottie or Canvas)                                │
│  ──────────────────────────────────────────────────────────────    │
│  • 중앙 코어 (발광, 맥동)                                           │
│  • 회전 링 (Flash 단계)                                             │
│  • 에너지 파동 (Pulse)                                              │
│                                                                     │
│  [Layer 40] Cards (React + Framer Motion)                           │
│  ──────────────────────────────────────────────────────────────    │
│  • 종목 카드 (3개)                                                  │
│  • 팝업 애니메이션 (scale + fade)                                   │
│  • 호버 효과                                                        │
│                                                                     │
│  [Layer 50] UI (React)                                              │
│  ──────────────────────────────────────────────────────────────    │
│  • 타이머 (0:05 / 0:15)                                             │
│  • 단계 인디케이터                                                  │
│  • 제어 버튼 (일시정지, 재생, 재시작)                               │
│                                                                     │
│  [Layer 60] Overlay (React)                                         │
│  ──────────────────────────────────────────────────────────────    │
│  • 로딩 스피너                                                      │
│  • 에러 메시지                                                      │
│  • 연결 끊김 알림                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 파티클 시스템

### 1. 파티클 생성

```typescript
// src/lib/particles/creator.ts
import type { SignalLog } from '@/types';

export interface Particle {
  id: string;
  type: 'signal' | 'stock';
  x: number;
  y: number;
  vx: number;  // 속도 X
  vy: number;  // 속도 Y
  color: string;
  size: number;
  opacity: number;
  glow: number;  // 발광 강도
  label?: string;
  metadata: any;
}

export function createSignalParticle(
  signal: SignalLog,
  sourcePosition: { x: number; y: number },
  targetPosition: { x: number; y: number },
  canvasSize: { width: number; height: number }
): Particle {
  // 감성에 따라 색상 결정
  const color = getColorBySentiment(signal.sentiment);

  // 감성 점수에 따라 속도 결정 (긍정일수록 빠름)
  const speed = 50 + (signal.sentiment_score || 0) * 100;

  // 방향 벡터
  const dx = targetPosition.x - sourcePosition.x;
  const dy = targetPosition.y - sourcePosition.y;
  const distance = Math.sqrt(dx * dx + dy * dy);

  return {
    id: signal.id.toString(),
    type: 'signal',
    x: sourcePosition.x,
    y: sourcePosition.y,
    vx: (dx / distance) * speed,
    vy: (dy / distance) * speed,
    color,
    size: 5 + Math.abs(signal.sentiment_score || 0) * 5,  // 5~10px
    opacity: 0.8,
    glow: 10,
    label: signal.title?.substring(0, 20),
    metadata: signal,
  };
}

function getColorBySentiment(sentiment: string | null): string {
  switch (sentiment) {
    case 'POSITIVE':
      return '#00ff88';  // Bright green
    case 'NEGATIVE':
      return '#ff4444';  // Bright red
    case 'NEUTRAL':
    default:
      return '#cccccc';  // Gray
  }
}
```

### 2. 파티클 물리 (Web Worker)

```typescript
// src/workers/particle-physics.worker.ts
import type { Particle } from '@/lib/particles/creator';

interface UpdateParams {
  particles: Particle[];
  deltaTime: number;
  targetPosition: { x: number; y: number };
  attractionForce: number;  // 인력 (0 ~ 1)
  damping: number;          // 감쇠 (0 ~ 1)
  bounds: { width: number; height: number };
}

self.onmessage = (e: MessageEvent<UpdateParams>) => {
  const { particles, deltaTime, targetPosition, attractionForce, damping, bounds } = e.data;

  const updated = particles.map((p) => {
    // 1. 인력 적용 (중앙 Brain으로)
    const dx = targetPosition.x - p.x;
    const dy = targetPosition.y - p.y;
    const distance = Math.sqrt(dx * dx + dy * dy);

    if (distance > 1) {
      const force = attractionForce / (distance * distance);
      p.vx += (dx / distance) * force * deltaTime;
      p.vy += (dy / distance) * force * deltaTime;
    }

    // 2. 감쇠 적용
    p.vx *= damping;
    p.vy *= damping;

    // 3. 위치 업데이트
    p.x += p.vx * deltaTime;
    p.y += p.vy * deltaTime;

    // 4. 경계 처리
    if (p.x < 0 || p.x > bounds.width || p.y < 0 || p.y > bounds.height) {
      // 화면 밖으로 나가면 소멸 (opacity = 0)
      p.opacity = Math.max(0, p.opacity - deltaTime * 2);
    }

    // 5. Brain 근접 시 흡수 효과
    if (distance < 50) {
      p.size *= 0.95;  // 작아짐
      p.opacity *= 0.9;  // 투명해짐

      // 긍정 신호는 밝아짐
      if (p.metadata.sentiment === 'POSITIVE') {
        p.glow = Math.min(50, p.glow * 1.1);
      }
    }

    return p;
  });

  // 소멸된 파티클 제거 (opacity < 0.01)
  const alive = updated.filter((p) => p.opacity > 0.01 && p.size > 0.5);

  self.postMessage({ particles: alive });
};
```

### 3. 파티클 렌더링 (Konva)

```typescript
// src/components/visualizer/ParticleRenderer.tsx
import { useEffect, useRef, useState, useMemo } from 'react';
import { Stage, Layer, Circle, Text, Group } from 'react-konva';
import { useParticlePhysics } from '@/hooks/useParticlePhysics';
import type { Particle } from '@/lib/particles/creator';

interface ParticleRendererProps {
  particles: Particle[];
  targetPosition: { x: number; y: number };
  attractionForce: number;
  width: number;
  height: number;
}

export function ParticleRenderer({
  particles: initialParticles,
  targetPosition,
  attractionForce,
  width,
  height,
}: ParticleRendererProps) {
  const [particles, setParticles] = useState(initialParticles);
  const { updateParticles } = useParticlePhysics();

  // 애니메이션 루프
  useEffect(() => {
    let animationId: number;
    let lastTime = performance.now();

    const animate = async (currentTime: number) => {
      const deltaTime = (currentTime - lastTime) / 1000;
      lastTime = currentTime;

      // Worker에서 물리 계산
      const updated = await updateParticles({
        particles,
        deltaTime,
        targetPosition,
        attractionForce,
        damping: 0.98,
        bounds: { width, height },
      });

      setParticles(updated);
      animationId = requestAnimationFrame(animate);
    };

    animationId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationId);
  }, [particles, targetPosition, attractionForce, width, height, updateParticles]);

  return (
    <Stage width={width} height={height}>
      <Layer>
        {particles.map((p) => (
          <ParticleNode key={p.id} particle={p} />
        ))}
      </Layer>
    </Stage>
  );
}

function ParticleNode({ particle }: { particle: Particle }) {
  return (
    <Group x={particle.x} y={particle.y}>
      {/* 발광 효과 (블러) */}
      <Circle
        radius={particle.size * 2}
        fill={particle.color}
        opacity={particle.opacity * 0.3}
        blur={particle.glow}
      />

      {/* 메인 파티클 */}
      <Circle
        radius={particle.size}
        fill={particle.color}
        opacity={particle.opacity}
        shadowBlur={particle.glow}
        shadowColor={particle.color}
      />

      {/* 라벨 (선택) */}
      {particle.label && particle.opacity > 0.5 && (
        <Text
          text={particle.label}
          x={particle.size + 5}
          y={-5}
          fontSize={10}
          fill="#ffffff"
          opacity={particle.opacity}
        />
      )}
    </Group>
  );
}
```

---

## 코드 예제

### 1. 메인 시각화 컴포넌트

```typescript
// src/components/visualizer/MainVisualizer.tsx
import { useState, useEffect } from 'react';
import { Globe3D } from './Globe3D';
import { ParticleRenderer } from './ParticleRenderer';
import { BrainCore } from './BrainCore';
import { ResultCards } from './ResultCards';
import { StepIndicator } from './StepIndicator';
import { useVisualizerSocket } from '@/hooks/useVisualizerSocket';
import { useVisualizerData } from '@/hooks/useVisualizerData';
import { createSignalParticle } from '@/lib/particles/creator';

interface MainVisualizerProps {
  batchId: string;
}

type AnimationPhase = 'INIT' | 'FETCH' | 'FUSION' | 'FLASH' | 'PRO' | 'FINAL';

export function MainVisualizer({ batchId }: MainVisualizerProps) {
  const { data, isLoading } = useVisualizerData(batchId);
  const { socket } = useVisualizerSocket(batchId);

  const [phase, setPhase] = useState<AnimationPhase>('INIT');
  const [particles, setParticles] = useState<Particle[]>([]);
  const [selectedStocks, setSelectedStocks] = useState<any[]>([]);

  // 단계 전환 로직
  useEffect(() => {
    const unsubscribe = socket.on('step:complete', (step) => {
      switch (step.step_name) {
        case 'FETCH':
          setPhase('FUSION');
          // 파티클 생성
          const newParticles = data?.signals.map((signal) =>
            createSignalParticle(
              signal,
              getSourcePosition(signal.source_code),
              { x: window.innerWidth / 2, y: window.innerHeight / 2 },
              { width: window.innerWidth, height: window.innerHeight }
            )
          ) || [];
          setParticles(newParticles);
          break;

        case 'FLASH_FILTER':
          setPhase('PRO');
          break;

        case 'PRO_REASON':
          setPhase('FINAL');
          setSelectedStocks(data?.stocks.filter((s) => s.status === 'SELECTED') || []);
          break;
      }
    });

    return unsubscribe;
  }, [socket, data]);

  // 자동 타이밍 (WebSocket 없이 테스트용)
  useEffect(() => {
    const timeline = [
      { time: 0, phase: 'INIT' as AnimationPhase },
      { time: 2000, phase: 'FETCH' as AnimationPhase },
      { time: 5000, phase: 'FUSION' as AnimationPhase },
      { time: 8000, phase: 'FLASH' as AnimationPhase },
      { time: 10000, phase: 'PRO' as AnimationPhase },
      { time: 13000, phase: 'FINAL' as AnimationPhase },
    ];

    const timeouts = timeline.map(({ time, phase }) =>
      setTimeout(() => setPhase(phase), time)
    );

    return () => timeouts.forEach(clearTimeout);
  }, []);

  if (isLoading) {
    return <LoadingScreen />;
  }

  return (
    <div className="relative w-full h-screen bg-black overflow-hidden">
      {/* Layer 0: 3D 배경 */}
      <div className="absolute inset-0 z-0">
        <Globe3D />
      </div>

      {/* Layer 10: 파티클 */}
      {phase !== 'INIT' && (
        <div className="absolute inset-0 z-10">
          <ParticleRenderer
            particles={particles}
            targetPosition={{ x: window.innerWidth / 2, y: window.innerHeight / 2 }}
            attractionForce={phase === 'FUSION' ? 500 : 0}
            width={window.innerWidth}
            height={window.innerHeight}
          />
        </div>
      )}

      {/* Layer 30: Brain */}
      <div className="absolute inset-0 z-30 flex items-center justify-center pointer-events-none">
        <BrainCore
          phase={phase}
          stockCount={
            phase === 'FLASH' ? 50 : phase === 'PRO' ? 3 : 0
          }
        />
      </div>

      {/* Layer 40: 결과 카드 */}
      {phase === 'FINAL' && (
        <div className="absolute inset-0 z-40 flex items-center justify-center gap-8">
          <ResultCards stocks={selectedStocks} />
        </div>
      )}

      {/* Layer 50: UI */}
      <div className="absolute top-8 left-1/2 -translate-x-1/2 z-50">
        <StepIndicator currentPhase={phase} />
      </div>
    </div>
  );
}

// Helper: 소스 위치 계산
function getSourcePosition(sourceCode: string): { x: number; y: number } {
  const positions: Record<string, { x: number; y: number }> = {
    'US_FED': { x: 200, y: 300 },
    'EU_ECB': { x: 400, y: 200 },
    'GOLD': { x: 600, y: 400 },
    'WTI': { x: 700, y: 500 },
    // ... (나머지 소스)
  };

  return positions[sourceCode] || { x: 500, y: 500 };
}
```

### 2. Brain 코어 애니메이션

```typescript
// src/components/visualizer/BrainCore.tsx
import { motion, AnimatePresence } from 'framer-motion';
import type { AnimationPhase } from './MainVisualizer';

interface BrainCoreProps {
  phase: AnimationPhase;
  stockCount: number;
}

export function BrainCore({ phase, stockCount }: BrainCoreProps) {
  return (
    <div className="relative w-64 h-64">
      {/* 중앙 코어 */}
      <motion.div
        className="absolute inset-0 rounded-full bg-gradient-radial from-cyan-400 to-blue-600"
        animate={{
          scale: phase === 'FUSION' ? [1, 1.1, 1] : 1,
          opacity: phase === 'INIT' ? 0.3 : 1,
        }}
        transition={{
          scale: {
            repeat: Infinity,
            duration: 0.5,
            ease: 'easeInOut',
          },
          opacity: {
            duration: 0.3,
          },
        }}
        style={{
          boxShadow: '0 0 60px rgba(0, 255, 255, 0.8)',
        }}
      />

      {/* 회전 링 (Flash 단계) */}
      <AnimatePresence>
        {phase === 'FLASH' && (
          <motion.div
            className="absolute inset-0 border-4 border-yellow-400 rounded-full"
            initial={{ opacity: 0, rotate: 0 }}
            animate={{
              opacity: 1,
              rotate: 360,
            }}
            exit={{ opacity: 0 }}
            transition={{
              rotate: {
                repeat: Infinity,
                duration: 0.6,
                ease: 'linear',
              },
            }}
          />
        )}
      </AnimatePresence>

      {/* 맥동 링 (Pro 단계) */}
      <AnimatePresence>
        {phase === 'PRO' && (
          <motion.div
            className="absolute inset-0 border-4 border-purple-400 rounded-full"
            animate={{
              scale: [1, 1.5, 1],
              opacity: [1, 0, 1],
            }}
            transition={{
              repeat: Infinity,
              duration: 1,
              ease: 'easeInOut',
            }}
          />
        )}
      </AnimatePresence>

      {/* 종목 수 표시 */}
      {stockCount > 0 && (
        <motion.div
          className="absolute inset-0 flex items-center justify-center"
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
        >
          <span className="text-6xl font-bold text-white">
            {stockCount}
          </span>
        </motion.div>
      )}
    </div>
  );
}
```

### 3. 결과 카드

```typescript
// src/components/visualizer/ResultCards.tsx
import { motion } from 'framer-motion';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface ResultCardsProps {
  stocks: any[];
}

export function ResultCards({ stocks }: ResultCardsProps) {
  return (
    <div className="flex gap-8">
      {stocks.map((stock, index) => (
        <motion.div
          key={stock.stock_code}
          initial={{ opacity: 0, scale: 0, y: 100 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{
            delay: index * 0.2,
            duration: 0.5,
            ease: 'easeOut',
          }}
        >
          <Card className="w-80 bg-gray-900 border-cyan-400 border-2">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="text-2xl text-white">{stock.stock_name}</span>
                <Badge variant="outline" className="text-lg">
                  {stock.stock_code}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {/* 점수 */}
              <div className="mb-4">
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">점수</span>
                  <span className="text-cyan-400 font-bold">
                    {stock.score.toFixed(2)}
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-3">
                  <motion.div
                    className="bg-gradient-to-r from-cyan-400 to-blue-500 h-3 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${stock.score}%` }}
                    transition={{ delay: index * 0.2 + 0.3, duration: 0.8 }}
                  />
                </div>
              </div>

              {/* 영향 신호 */}
              <div>
                <p className="text-sm text-gray-400 mb-2">영향 받은 신호</p>
                <div className="flex gap-2">
                  {stock.impacts?.slice(0, 3).map((impact: any) => (
                    <Badge
                      key={impact.signal_id}
                      variant={impact.impact_type === 'BOOST' ? 'default' : 'destructive'}
                      className="text-lg"
                    >
                      {impact.icon}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* 추론 */}
              <div className="mt-4">
                <p className="text-xs text-gray-500 leading-relaxed">
                  {stock.filter_reason}
                </p>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
```

---

## 성능 최적화 팁

### 1. 파티클 수 동적 조절

```typescript
// src/hooks/useAdaptiveParticleCount.ts
import { useState, useEffect } from 'react';

export function useAdaptiveParticleCount(
  baseCount: number
): number {
  const [particleCount, setParticleCount] = useState(baseCount);
  const [fps, setFps] = useState(60);

  useEffect(() => {
    let lastTime = performance.now();
    let frameCount = 0;

    const measureFps = () => {
      frameCount++;

      const currentTime = performance.now();
      if (currentTime >= lastTime + 1000) {
        const currentFps = (frameCount * 1000) / (currentTime - lastTime);
        setFps(currentFps);

        // FPS에 따라 파티클 수 조절
        if (currentFps < 30) {
          setParticleCount((prev) => Math.max(100, prev * 0.8));
        } else if (currentFps > 55) {
          setParticleCount((prev) => Math.min(baseCount, prev * 1.1));
        }

        frameCount = 0;
        lastTime = currentTime;
      }

      requestAnimationFrame(measureFps);
    };

    const id = requestAnimationFrame(measureFps);
    return () => cancelAnimationFrame(id);
  }, [baseCount]);

  return Math.round(particleCount);
}
```

### 2. 오프스크린 렌더링

```typescript
// src/hooks/useOffscreenCanvas.ts
import { useRef, useEffect } from 'react';

export function useOffscreenCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const offscreenRef = useRef<OffscreenCanvas>();
  const workerRef = useRef<Worker>();

  useEffect(() => {
    if (!canvasRef.current) return;

    // Offscreen Canvas로 전환
    offscreenRef.current = canvasRef.current.transferControlToOffscreen();

    // Worker에서 렌더링
    workerRef.current = new Worker(
      new URL('@/workers/canvas-renderer.worker.ts', import.meta.url),
      { type: 'module' }
    );

    workerRef.current.postMessage(
      {
        canvas: offscreenRef.current,
        width: window.innerWidth,
        height: window.innerHeight,
      },
      [offscreenRef.current]
    );

    return () => {
      workerRef.current?.terminate();
    };
  }, []);

  return canvasRef;
}
```

---

## 다음 단계

1. **프로토타입 개발**: Phase 1 (FETCH) 먼저 구현
2. **성능 테스트**: Chrome DevTools Performance 프로파일링
3. **반응형 테스트**: 모바일, 태블릿, 데스크톱 확인
4. **사용자 테스트**: 5명 이상에게 시연 후 피드백

---

**작성일**: 2025-12-08
**작성자**: wonny
**버전**: 1.0.0
