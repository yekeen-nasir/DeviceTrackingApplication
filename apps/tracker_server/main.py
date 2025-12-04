"""FastAPI server for Tracker system."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from libs.core.config import load_config
from libs.core.logging import setup_logging
from .db import init_db, get_db
from .routers import auth, enroll, telemetry, commands, devices, reports

logger = setup_logging("tracker-server")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting Tracker server")
    init_db()
    yield
    # Shutdown
    logger.info("Shutting down Tracker server")

app = FastAPI(
    title="Tracker API",
    description="Device tracking system REST API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(enroll.router, prefix="/api/v1/enroll", tags=["enrollment"])
app.include_router(telemetry.router, prefix="/api/v1/telemetry", tags=["telemetry"])
app.include_router(commands.router, prefix="/api/v1", tags=["commands"])
app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Tracker API", "version": "1.0.0"}

@app.get("/healthz")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/ready")
async def ready():
    """Readiness check endpoint."""
    # Check database connectivity
    try:
        from .db import engine
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")

def run_server():
    """Run the server."""
    config = load_config(component="server")
    host = os.getenv("TRACKER_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("TRACKER_SERVER_PORT", "8000"))
    
    uvicorn.run(
        "apps.tracker_server.main:app",
        host=host,
        port=port,
        reload=os.getenv("TRACKER_ENV", "production") == "development",
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
        }
    )

if __name__ == "__main__":
    run_server()
