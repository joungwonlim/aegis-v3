"""
AEGIS v3.0 - FastAPI Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import health, portfolio, trades, analysis

# FastAPI App
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-Powered Automated Trading System for Korean Stock Market",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health.router)
app.include_router(portfolio.router)
app.include_router(trades.router)
app.include_router(analysis.router)


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    print(f"🚀 {settings.app_name} v{settings.app_version} Starting...")
    print(f"📊 AI Trading: {'Enabled' if settings.ai_trading_enabled else 'Disabled'}")
    print(f"📡 Swagger UI: http://localhost:8000/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    print("🛑 Shutting down...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"{settings.app_name} is running",
        "version": settings.app_version,
        "status": "healthy",
        "docs": "/docs"
    }
