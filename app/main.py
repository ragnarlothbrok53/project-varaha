import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .api import router
from .worker import worker_loop

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background worker
    print("Starting background worker loop...")
    asyncio.create_task(worker_loop())
    yield
    # Shutdown logic can go here
    print("Shutting down...")

app = FastAPI(
    title="Varaha LLM Proxy",
    description="A high-performance batching proxy for local LLM inference",
    lifespan=lifespan
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
