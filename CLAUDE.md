# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**AEGIS v3.0** - AI-Powered Automated Trading System for Korean Stock Market

A sophisticated trading system that combines quantitative analysis, AI decision-making (DeepSeek-V3/R1, Claude Opus), and adaptive learning to achieve consistent daily returns in the Korean stock market.

### Core Philosophy

```
"0.001%를 올리기 위해 끊임없이 고민한다"
"1% 수익을 목표로, 우리는 반드시 해낸다"
```

**Three Principles:**
1. **Profitability First** - Every design decision prioritizes returns
2. **AI Transparency** - All AI decisions must be traceable (model, reasoning, score, confidence)
3. **Adaptive Feedback** - Trade results continuously improve future decisions

---

## Architecture

### Tech Stack

```
┌─────────────────────────────────────────────────────┐
│  Frontend: Next.js 14 + shadcn/ui + TailwindCSS     │
│            TradingView Charts + TanStack Query      │
├─────────────────────────────────────────────────────┤
│  Backend:  FastAPI (Python Async)                   │
│            SQLAlchemy + Pydantic v2                 │
│            WebSocket for real-time updates          │
├─────────────────────────────────────────────────────┤
│  Database: PostgreSQL 15 + TimescaleDB              │
│            Hypertables for time-series data         │
├─────────────────────────────────────────────────────┤
│  AI:       DeepSeek-V3 (real-time analysis)         │
│            DeepSeek-R1 (deep reasoning)             │
│            Claude Opus (final decisions)            │
└─────────────────────────────────────────────────────┘
```

### AI Model Strategy

| Model | Role | Frequency | Cost |
|-------|------|-----------|------|
| **Rule-based** | Stop-loss/Take-profit | Real-time | Free |
| **DeepSeek-V3** | Real-time analysis, scoring | 30s interval | Low |
| **DeepSeek-R1** | Deep strategy analysis | 2x daily | Medium |
| **Claude Opus** | Final trading decisions | As needed | High |

---

## Development Phases

### Phase 1: Backend Only (Current Focus)

**Duration:** 1-2 months

**Goal:** Complete FastAPI backend with full trading logic, working without frontend.

**Stack:**
- FastAPI with async SQLAlchemy
- PostgreSQL 15 + TimescaleDB extension
- REST API + WebSocket
- Brain (AI decision module)
- Scheduler (APScheduler)
- KIS API integration

**User Interfaces during Phase 1:**
1. **Swagger UI** (auto-generated at `/docs`) - Recommended for API testing
2. **Streamlit** (temporary) - Quick dashboard if needed
3. **CLI scripts** - Command-line tools
4. **Claude Code** - Natural language interaction (current method)

**Key Commands:**
```bash
# Start backend server
uvicorn app.main:app --reload --port 8000

# View API documentation
open http://localhost:8000/docs

# Run scheduler (trading bot)
python -m scheduler.main_scheduler

# Run database migrations
alembic upgrade head

# Run tests
pytest tests/ -v
```

### Phase 2: Frontend (Future)

**Duration:** 2-3 months (after Phase 1 complete)

**Stack:**
- Next.js 14 (App Router)
- shadcn/ui + TailwindCSS
- TradingView Lightweight Charts (Canvas-based)
- TanStack Table + Virtual scrolling
- React Query for state management

**Note:** Backend will be complete and stable before starting frontend development.

---

## Database Design

### 6 Schemas

```
[SCHEMA 1] MARKET     - Market data (fuel)
[SCHEMA 2] ACCOUNT    - Asset management (wallet)
[SCHEMA 3] BRAIN      - AI analysis (brain)
[SCHEMA 4] TRADE      - Trading records (actions)
[SCHEMA 5] SYSTEM     - System monitoring (control tower)
[SCHEMA 6] ANALYTICS  - Backtesting (research lab)
```

### Critical: Data Units Convention

| Data Type | Unit | Example | Notes |
|-----------|------|---------|-------|
| **Price** | KRW (원) | `52300` | Integer, no decimals |
| **Volume** | Shares (주) | `1234567` | BigInteger |
| **Net Buy** | Shares (주) | `50000`, `-30000` | **NOT amount in KRW!** |
| **Market Cap** | KRW | `300000000000000` | BigInteger |
| **Return Rate** | % | `5.23`, `-2.1` | Float, multiply by 100 |
| **Exchange Rate** | KRW/USD | `1380.50` | Float |

**Important:** Supply data (foreigner_net_buy, institution_net_buy) must be in **SHARES**, not KRW amount!

### Key Tables

**Market Data:**
- `stocks` - Stock master data
- `daily_prices` - Daily OHLCV + supply data (8 supply columns)
- `market_candles` - Intraday candles (TimescaleDB hypertable)
- `market_macro` - Macro indicators (VIX, NASDAQ, SOX, USD/KRW)

**Trading:**
- `portfolio` - Current holdings with pyramid_stage, sell_stage
- `trade_logs` - All trades with AI reasoning, model_used, decision_context
- `trade_feedbacks` - Post-trade analysis for adaptive learning

**AI Brain:**
- `daily_picks` - AI stock recommendations
- `daily_analysis_logs` - Analysis pipeline logs
- `intel_feed` - News/disclosure analysis
- `market_regime` - Market condition tracking

---

## Brain Decision Logic

### Buy Decision Flow

```
Screener (filters)
  → Quant Score (60-90 pts: supply + technical)
  → DeepSeek-V3 Score (0-100 pts: context analysis)
  → Final Score = Quant×57% + AI×43%
  → 70+ points? → Safety Check
  → All checks pass? → BUY
```

**Safety Checks:**
- Holdings < 5 positions
- Daily trades < 4
- Not Friday after 14:30
- Account loss < -2%
- Position size < 10%

### Sell Decision Flow

```
Profit Rate Check:
  ≤ -2.0%  → Stop Loss (sell all)
  +3.5%    → Take 50% profit
  +5.0%    → Enable Trailing Stop (track high - 2%)
  +8.0%    → Enhanced Trailing (aggressive)
```

**Trailing Stop Example:**
```
Buy at 10,000 → Reaches 10,500 (+5%) → Trailing ON
→ Peaks at 11,000 → Stop at 10,780 (11,000 - 2%)
→ Falls to 10,750 → SELL triggered
```

---

## AI Transparency Requirements

**CRITICAL:** Every AI decision must record:

```python
{
    "model_used": "deepseek-chat",  # or deepseek-reasoner, opus
    "reasoning": "5-day foreign net buy +1.5M shares, SOX +1.09%...",
    "score": 78,
    "confidence": 85,
    "timestamp": "2025-12-09T09:15:30",
    # Post-trade (after sell):
    "result": "WIN",
    "profit_rate": 2.3,
    "feedback_applied": +3  # Score adjustment
}
```

This prevents "black box" decisions and enables continuous learning.

---

## Naming Conventions

### Code Style
- Python: PEP 8, snake_case for functions/variables
- FastAPI: async/await for all DB operations
- SQL: snake_case for tables/columns
- TypeScript: camelCase for variables, PascalCase for components

### Git Commits (when needed)
```bash
# Format
<type>: <subject>

# Types: feat, fix, refactor, docs, test, chore
# Examples:
feat: add trailing stop logic to portfolio manager
fix: correct supply data unit conversion in fetcher
docs: update database schema documentation
```

---

## Common Development Tasks

### Backend Development

```bash
# Create new API endpoint
# Location: app/routers/

# Create new database model
# Location: app/models/
# After changes: alembic revision --autogenerate -m "description"

# Add new AI analysis
# Location: brain/

# Add new scheduler job
# Location: scheduler/main_scheduler.py
```

### Database Operations

```bash
# Create migration
alembic revision --autogenerate -m "add new table"

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1

# TimescaleDB hypertable conversion
# See: docs/DEVELOPMENT_PLAN.md section 3.3
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_portfolio.py -v
```

---

## Data Fetching Schedule

| Time | Task | Source | Frequency |
|------|------|--------|-----------|
| 06:00 | US market data | yfinance | Daily |
| 07:00 | KRX supply data | pykrx | Daily |
| 07:20 | BRAIN analysis | DeepSeek-R1 | Daily |
| 08:00 | Opus briefing | Claude Opus | Daily |
| 09:00-15:30 | Real-time trading | KIS WebSocket | Live |
| 16:00 | Daily settlement | DeepSeek-R1 | Daily |

---

## Safety Systems

### Circuit Breakers

```python
CIRCUIT_BREAKER_CONFIG = {
    'portfolio_max_loss': -5.0,      # -5% → stop all trading
    'position_stop_loss': -3.0,      # -3% → auto sell
    'max_trades_per_day': 20,
    'max_consecutive_losses': 3,     # 3 losses → pause buying
    'market_volatility_threshold': 2.0  # KOSPI ±2%
}
```

### Emergency Levels

- **🔴 CRITICAL**: System failure, -5% loss → Stop all, alert user
- **🟠 WARNING**: -3% position, API delay → Pause position, monitor
- **🟡 CAUTION**: Market volatility → Pause new buys

---

## Documentation Structure

```
docs/
├── README.md                    # Documentation index
├── CORE_PHILOSOPHY.md           # System philosophy
├── COMBAT_ARCHITECTURE.md       # Architecture details
├── DEVELOPMENT_PLAN.md          # v3.0 migration plan
├── PHASED_DEVELOPMENT.md        # Phase 1 & 2 details
├── DATABASE_DESIGN.md           # Database schema
├── BRAIN_SIMPLE.md              # AI decision logic
├── PYRAMIDING_STRATEGY.md       # Trading strategy
├── SAFETY_SYSTEM.md             # Safety mechanisms
├── SCHEDULER_DESIGN.md          # Job scheduling
└── KIS_API_SPECIFICATION.md     # KIS API reference
```

**Important:** Always read relevant documentation before making changes to ensure alignment with system design.

---

## Docker Setup (Future)

```yaml
# docker-compose.yml
services:
  db:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_DB: aegis_v3
      POSTGRES_USER: aegis
      POSTGRES_PASSWORD: aegis2024
    ports:
      - "5432:5432"

  backend:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
```

---

## Performance Goals

| Metric | Target |
|--------|--------|
| API response time | < 100ms |
| Chart rendering (10K candles) | < 1s |
| Table scroll (1K rows) | Smooth (virtual scrolling) |
| Real-time update latency | < 500ms |
| Daily return target | +1.0% |

---

## Critical Rules

1. **Never guess AI decisions** - Always record model, reasoning, score
2. **Supply data in SHARES** - Not KRW amount (see DATABASE_DESIGN.md)
3. **Read docs first** - Before implementing features, check docs/
4. **Safety first** - All trades go through safety checks
5. **Backend complete before Frontend** - Follow phased approach
6. **Test with Swagger UI** - Use http://localhost:8000/docs during Phase 1

---

**Version:** 3.0
**Last Updated:** 2025-12-09
**Project Status:** Phase 1 (Backend Development)
