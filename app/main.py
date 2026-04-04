import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .api.routes import router
from .core.worker import worker_loop
from .core.engine import init_all_pools
from .data.manager import init_db
from .utils.logger import setup_logging, logger

# Initialize production logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the database, engine pool, and background worker
    logger.info("Initializing metrics database...")
    init_db()
    
    logger.info("Initializing high-performance Engine Pools...")
    await init_all_pools()
    
    logger.info("Starting background worker loop...")
    asyncio.create_task(worker_loop())
    yield
    # Shutdown logic can go here
    logger.info("Shutting down...")

app = FastAPI(
    title="Varaha LLM Proxy",
    description="A high-performance batching proxy for local LLM inference",
    lifespan=lifespan
)

# Static Files & Frontend
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    with open("app/static/index.html", "r") as f:
        return f.read()

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
