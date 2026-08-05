"""TradingHelper — FastAPI application entry point.

Handles startup/shutdown via lifespan, CORS configuration,
and router registration.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, migrate_db
from app.routers import watchlist, market_data, positions, alerts, paper_trade, auth
from app.services.scanner import create_scheduler

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("tradinghelper")


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    settings = get_settings()

    # Initialize database tables
    logger.info("Initializing database...")
    await init_db()

    # Apply incremental schema migrations (idempotent — safe on every start)
    logger.info("Running schema migrations...")
    await migrate_db()

    # Start the background scanner
    logger.info("Starting background scanner...")
    scheduler = create_scheduler()
    scheduler.start()

    logger.info("✅ TradingHelper is ready!")
    logger.info(f"   Scanner: intraday every {settings.scan_interval_intraday_seconds}s")
    logger.info(f"   Scanner: long-term every {settings.scan_interval_longterm_seconds}s")

    yield

    # Shutdown
    logger.info("Shutting down scanner...")
    scheduler.shutdown(wait=False)
    logger.info("TradingHelper stopped.")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TradingHelper",
    description=(
        "Educational NSE stock tracking dashboard with 4-indicator confluence engine, "
        "charting, and break-even calculator."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(watchlist.router)
app.include_router(market_data.router)
app.include_router(positions.router)
app.include_router(alerts.router)
app.include_router(paper_trade.router)


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": "TradingHelper",
        "version": "1.0.0",
    }
