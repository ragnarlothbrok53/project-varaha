import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from .api.routes import router
from .api.auth import router as auth_router
from .core.worker import worker_loop
from .core.engine import init_all_pools
from .data.manager import init_db
from .utils.logger import setup_logging, logger
from .utils.config import get_settings

# Initialize settings
settings = get_settings()

# Initialize production logging
setup_logging()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the database, engine pool, and background worker
    logger.info("Initializing metrics database...")
    init_db()
    
    from .data.manager import get_user_by_email, create_user, create_api_key, validate_api_key
    import bcrypt
    if not get_user_by_email("admin@varaha.ai"):
        pwd_hash = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode('utf-8')
        create_user("admin-123", "admin@varaha.ai", pwd_hash, "Admin User")
        logger.info("Created default admin user: admin@varaha.ai / admin")
    
    if not validate_api_key("admin-key"):
        create_api_key("admin-key", "admin-123", "Default Key", "qwen", 0.1, "", "")

    logger.info("Initializing high-performance Engine Pools...")
    await init_all_pools()

    logger.info("Starting background worker loop...")
    asyncio.create_task(worker_loop())
    yield
    # Shutdown logic can go here
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    description="A high-performance batching proxy for local LLM inference",
    version=settings.app_version,
    lifespan=lifespan,
)

# Add rate limiting exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files & Frontend
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
@limiter.limit("10/minute")  # Rate limit the homepage
async def serve_home(request: Request):
    with open("app/static/index.html", "r") as f:
        return f.read()


app.include_router(router)
app.include_router(auth_router, prefix="/v1")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", 
        host=settings.host, 
        port=settings.port,
        reload=settings.debug
    )
