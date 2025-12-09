#!/bin/bash
# AEGIS v3.0 - Quick Start Script

echo "🚀 AEGIS v3.0 Starting..."

# 1. Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Please copy .env.example to .env and fill in your API keys"
    exit 1
fi

# 2. Start Database
echo "🐘 Starting PostgreSQL + TimescaleDB..."
docker-compose up -d

# Wait for DB to be ready
sleep 5

# 3. Initialize Database
echo "📊 Initializing database..."
python -c "from app.database import init_db; init_db()"

# 4. Start FastAPI Server
echo "🌐 Starting FastAPI server..."
echo "📡 Swagger UI: http://localhost:8000/docs"
uvicorn app.main:app --reload --port 8000
