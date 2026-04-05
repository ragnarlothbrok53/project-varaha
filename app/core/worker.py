import asyncio
from typing import Dict, Any, List
from .engine import llm_batch_on_model
from ..data.manager import store_metrics
from ..utils.logger import logger

# Shared in-memory store
job_queue: asyncio.Queue = asyncio.Queue()
results: Dict[str, Any] = {}
cache: Dict[str, Any] = {}
usage: Dict[str, List[float]] = {}  # user -> timestamps

def validate_output(task: str, output: str) -> str:
    # simple pass-through for now
    return output

async def process_job(job: Dict[str, Any]):
    """Process an individual job asynchronously via the specific model pool."""
    try:
        model_id = job.get("model", "qwen")
        req = {"prompt": job["prompt"], "temperature": job.get("temperature", 0.1)}
        res = await llm_batch_on_model([req], model_id=model_id)
        result_data = res[0]
        
        output = result_data["output"]
        metrics = result_data["metrics"]
        
        logger.info(f"⚡ Job {job['job_id'][:8]} | TTFT: {metrics['ttft_ms']}ms | TPS: {metrics['tps']}")
        
        validated = validate_output(job["task"], output)
        results[job["job_id"]] = {"data": validated, "metrics": metrics}
        
        # Persistent Metrics with full Request/Response and Prompt/Completion logging
        store_metrics(
            job_id=job["job_id"], 
            team_id=job["team_id"], 
            metrics=metrics,
            input_text=job["prompt"],
            output_text=output,
            request_payload=job.get("request_payload"),
            response_json={"status": "completed", "data": validated}
        )
    except Exception as e:
        logger.error(f"Error processing job {job.get('job_id', 'unknown')}: {e}", exc_info=True)
        results[job["job_id"]] = f"Error: {e}"

async def worker_loop():
    logger.info("Starting continuous batching worker loop...")
    while True:
        # Continually consume from the queue and spawn tasks
        # Each task will wait on the engine-level Semaphore independently
        job = await job_queue.get()
        asyncio.create_task(process_job(job))
