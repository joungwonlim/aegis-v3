#!/bin/bash

# AEGIS Visualizer - 프로젝트 자동 생성 스크립트
# Usage: bash create_project.sh

set -e  # 에러 발생 시 중단

PROJECT_NAME="aegis-visualizer"
PROJECT_PATH="$HOME/Dev/$PROJECT_NAME"

echo "🚀 AEGIS Visualizer 프로젝트 생성 시작..."
echo "📍 위치: $PROJECT_PATH"

# 프로젝트 루트 생성
if [ -d "$PROJECT_PATH" ]; then
    echo "⚠️  프로젝트가 이미 존재합니다: $PROJECT_PATH"
    read -p "덮어쓰시겠습니까? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 취소되었습니다."
        exit 1
    fi
    rm -rf "$PROJECT_PATH"
fi

mkdir -p "$PROJECT_PATH"
cd "$PROJECT_PATH"

echo "✅ 프로젝트 루트 생성 완료"

# ============================================================================
# Backend 생성
# ============================================================================
echo ""
echo "📦 Backend 생성 중..."

mkdir -p backend/app/{api,models,services}
mkdir -p backend/alembic/versions

# requirements.txt
cat > backend/requirements.txt << 'EOF'
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
EOF

# .env
cat > backend/.env << 'EOF'
DATABASE_URL=postgresql+asyncpg://visualizer_admin:visualizer2024@localhost:5433/visualizer
SECRET_KEY=your-secret-key-change-in-production
DEBUG=True
CORS_ORIGINS=http://localhost:5173,http://localhost:5174
EOF

# app/__init__.py
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/models/__init__.py
touch backend/app/services/__init__.py

# app/main.py
cat > backend/app/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AEGIS Visualizer API",
    description="AI Reasoning Visualizer Backend",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
EOF

# app/database.py
cat > backend/app/database.py << 'EOF'
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://visualizer_admin:visualizer2024@localhost:5433/visualizer"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
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
EOF

# Dockerfile
cat > backend/Dockerfile << 'EOF'
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
EOF

echo "✅ Backend 생성 완료"

# ============================================================================
# Frontend 생성
# ============================================================================
echo ""
echo "📦 Frontend 생성 중..."

mkdir -p frontend

# package.json
cat > frontend/package.json << 'EOF'
{
  "name": "aegis-visualizer-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@tanstack/react-query": "^5.62.11",
    "axios": "^1.7.9",
    "socket.io-client": "^4.8.1",
    "@react-three/fiber": "^8.18.5",
    "@react-three/drei": "^9.122.4",
    "three": "^0.171.0",
    "react-konva": "^18.2.10",
    "konva": "^9.3.16",
    "framer-motion": "^11.15.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@types/three": "^0.171.0",
    "@vitejs/plugin-react": "^4.3.4",
    "typescript": "^5.6.3",
    "vite": "^6.0.1"
  }
}
EOF

# .env
cat > frontend/.env << 'EOF'
VITE_API_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001
EOF

# vite.config.ts
cat > frontend/vite.config.ts << 'EOF'
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
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
});
EOF

# tsconfig.json
cat > frontend/tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
EOF

# index.html
cat > frontend/index.html << 'EOF'
<!DOCTYPE html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AEGIS Visualizer</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
EOF

mkdir -p frontend/src
mkdir -p frontend/public

# src/main.tsx
cat > frontend/src/main.tsx << 'EOF'
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
EOF

# src/App.tsx
cat > frontend/src/App.tsx << 'EOF'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="w-full h-screen bg-black flex items-center justify-center">
        <div className="text-white text-4xl">
          🚀 AEGIS Visualizer
        </div>
      </div>
    </QueryClientProvider>
  );
}

export default App;
EOF

# src/index.css
cat > frontend/src/index.css << 'EOF'
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
EOF

# src/vite-env.d.ts
cat > frontend/src/vite-env.d.ts << 'EOF'
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_WS_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
EOF

# Dockerfile
cat > frontend/Dockerfile << 'EOF'
FROM node:20-slim

WORKDIR /app

RUN npm install -g pnpm

COPY package.json pnpm-lock.yaml ./
RUN pnpm install

COPY . .

EXPOSE 5173

CMD ["pnpm", "dev", "--host"]
EOF

echo "✅ Frontend 생성 완료"

# ============================================================================
# Docker Compose
# ============================================================================
echo ""
echo "🐳 Docker Compose 생성 중..."

cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
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

  backend:
    build: ./backend
    container_name: visualizer_backend
    environment:
      DATABASE_URL: postgresql+asyncpg://visualizer_admin:visualizer2024@db:5432/visualizer
    ports:
      - "8001:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    container_name: visualizer_frontend
    environment:
      VITE_API_URL: http://localhost:8001
    ports:
      - "5174:5173"
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  visualizer_data:
EOF

echo "✅ Docker Compose 생성 완료"

# ============================================================================
# .gitignore
# ============================================================================
cat > .gitignore << 'EOF'
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
EOF

# ============================================================================
# README
# ============================================================================
cat > README.md << 'EOF'
# AEGIS Visualizer

AI 추론 과정 시각화 시스템

## 빠른 시작

### Docker Compose (권장)

```bash
docker-compose up -d
```

### 개별 실행

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

#### Frontend
```bash
cd frontend
pnpm install
pnpm dev
```

## 접속

- Frontend: http://localhost:5174
- Backend API: http://localhost:8001
- API Docs: http://localhost:8001/docs
- Database: localhost:5433

## 문서

전체 설계 문서는 다음 경로에 있습니다:
`~/Dev/aegis/v2/docs/dev3/ai-visualizer/`
EOF

# Git 초기화
git init
git add .
git commit -m "Initial commit: AEGIS Visualizer project setup"

echo ""
echo "✅ 프로젝트 생성 완료!"
echo ""
echo "📍 프로젝트 위치: $PROJECT_PATH"
echo ""
echo "🚀 다음 단계:"
echo ""
echo "1. 프로젝트로 이동"
echo "   cd $PROJECT_PATH"
echo ""
echo "2. Docker Compose로 실행"
echo "   docker-compose up -d"
echo ""
echo "3. 접속 확인"
echo "   - Frontend: http://localhost:5174"
echo "   - Backend:  http://localhost:8001/docs"
echo ""
echo "🎉 Happy Coding!"
