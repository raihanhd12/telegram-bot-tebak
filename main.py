from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from loguru import logger

import src.config.env as env
import src.config.logging as logging_config
from src.routes.api.v1 import router as v1_router

# Setup logging first
logging_config.setup_logging()
logger = logger.bind(module=__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events
    """
    # Startup - only show detailed logs in development
    if env.DEVELOPMENT:
        logger.info("🚀 FastAPI Service is starting up...")
        logger.info(f"📝 Documentation available at: http://{env.API_HOST}:{env.API_PORT}/docs")
        logger.info(f"🔗 API Base URL: http://{env.API_HOST}:{env.API_PORT}")

    yield  # Server is running

    # Shutdown
    if env.DEVELOPMENT:
        logger.info("⚡️ FastAPI Service is shutting down...")


# Initialize the FastAPI app
app = FastAPI(
    title="FastAPI Starter Template",
    description="A production-ready FastAPI template with best practices",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Add CORS middleware with environment-based configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=env.CORS_ORIGINS,
    allow_credentials=env.CORS_ALLOW_CREDENTIALS,
    allow_methods=env.CORS_ALLOW_METHODS,
    allow_headers=env.CORS_ALLOW_HEADERS,
)

# Include routers with prefix
app.include_router(v1_router, prefix="/api")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information"""
    return {
        "message": "FastAPI Starter Template",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json",
            "health": "/health",
            "api": "/api/v1",
        },
    }


@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "FastAPI Starter Template",
        "version": "1.0.0",
    }


@app.get("/test-websocket")
async def websocket_test_page():
    """Serve WebSocket test page"""
    return FileResponse("src/public/websocket_test.html")


if __name__ == "__main__":
    # Development vs Production configuration
    if env.PRODUCTION:
        # Production settings
        workers = env.WORKERS if hasattr(env, "WORKERS") else 4
        reload = False
        access_log = True
        log_level = "warning"
    else:
        # Development settings
        workers = 1
        reload = True
        access_log = True
        log_level = "info"

    uvicorn.run(
        "main:app",
        host=env.API_HOST,
        port=env.API_PORT,
        reload=reload,
        access_log=access_log,
        log_level=log_level,
        workers=workers,
    )
