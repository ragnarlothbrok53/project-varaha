import asyncio
import time
from typing import Dict, Any, List
from .config import BATCH_SIZE, BATCH_WAIT_MS
from .engine import llm_batch

# Shared in-memory store
job_queue: asyncio.Queue = asyncio.Queue()
results: Dict[str, Any] = {}
cache: Dict[str, Any] = {}
usage: Dict[str, List[float]] = {}  # user -> timestamps

def validate_output(task: str, output: str) -> str:
    # simple pass-through for now
    return output

async def worker_loop():
    while True:
        batch = []
        try:
            # Block until at least one job is available
            job = await asyncio.wait_for(job_queue.get(), timeout=1.0)
            batch.append(job)
        except asyncio.TimeoutError:
            continue

        # Try to gather more jobs for the batch
        start = time.time()
        while len(batch) < BATCH_SIZE and (time.time() - start) < (BATCH_WAIT_MS / 1000):
            try:
                job = job_queue.get_nowait()
                batch.append(job)
            except asyncio.QueueEmpty:
                break

        if not batch:
             continue

        # Batched inference
        prompts = [j["prompt"] for j in batch]
        outputs = await llm_batch(prompts)

        # Store results
        for job, output in zip(batch, outputs):
            validated = validate_output(job["task"], output)
            results[job["job_id"]] = validated
