import time
import asyncio
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from .worker import job_queue, results, cache
from .utils import generate_job_id, sse, chunk_text
from .prompt_builder import build_prompt
from .rate_limit import enforce_rate_limit

router = APIRouter()

async def wait_for_result(job_id: str, timeout: float = 10.0):
    start = time.time()
    while time.time() - start < timeout:
        if job_id in results:
            return results.pop(job_id)
        await asyncio.sleep(0.1)
    return None

async def stream_sse(job_id: str):
    yield sse("start", {"job_id": job_id})
    result = await wait_for_result(job_id)
    if not result:
        yield sse("error", {"message": "timeout"})
        return
    yield sse("ready", {"queued": True})
    for chunk in chunk_text(result):
        yield sse("chunk", {"delta": chunk})
        await asyncio.sleep(0.05)
    yield sse("end", {"status": "completed"})

@router.post("/v1/execute")
async def execute(request: Request):
    body = await request.json()
    api_key = request.headers.get("Authorization", "anon")
    enforce_rate_limit(api_key)

    task = body.get("task")
    input_data = body.get("input", {})
    config = body.get("config", {})
    stream = config.get("stream", False)

    if not task:
         raise HTTPException(400, "Task is required")

    try:
         prompt = build_prompt(task, input_data)
    except ValueError as e:
         raise HTTPException(400, str(e))

    # Check cache
    cache_key = f"{task}:{prompt}"
    if cache_key in cache:
        return {"status": "completed", "data": cache[cache_key], "cached": True}

    job_id = generate_job_id()
    job = {"job_id": job_id, "task": task, "prompt": prompt, "created_at": time.time()}

    await job_queue.put(job)

    if not stream:
        result = await wait_for_result(job_id)
        if result:
            cache[cache_key] = result
            return {"status": "completed", "data": result}
        return {"status": "queued", "job_id": job_id}

    return StreamingResponse(stream_sse(job_id), media_type="text/event-stream")
