# =========================
# file: main.py
# =========================

import asyncio
import json
import uuid
import time
import os
from typing import Dict, Any, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from llama_cpp import Llama

app = FastAPI()

# =========================
# file: config.py
# =========================

BATCH_SIZE = 16
BATCH_WAIT_MS = 50
MAX_OUTPUT_TOKENS = 256

# =========================
# file: in_memory_store.py
# =========================

job_queue: asyncio.Queue = asyncio.Queue()
results: Dict[str, Any] = {}
cache: Dict[str, Any] = {}
usage: Dict[str, List[float]] = {}  # user -> timestamps

# =========================
# file: utils.py
# =========================


def generate_job_id():
    return str(uuid.uuid4())


def sse(event, data):
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def chunk_text(text: str, chunk_size=6):
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i : i + chunk_size])


# =========================
# file: rate_limit.py
# =========================


def enforce_rate_limit(api_key: str, limit_per_minute=60):
    now = time.time()
    window = 60

    if api_key not in usage:
        usage[api_key] = []

    usage[api_key] = [t for t in usage[api_key] if now - t < window]

    if len(usage[api_key]) >= limit_per_minute:
        raise HTTPException(429, "Rate limit exceeded")

    usage[api_key].append(now)


# =========================
# file: prompt_builder.py
# =========================


def build_prompt(task: str, payload: Dict[str, Any]) -> str:
    if task == "extract":
        schema = payload.get("schema", {})
        fields = "\n".join([f"- {k}: {v}" for k, v in schema.items()])
        return f"Extract fields:\n{fields}\nText:\n{payload['text']}\nReturn JSON only."

    if task == "classify":
        labels = payload.get("labels", [])
        return f"Classify into one of {labels}:\n{payload['text']}"

    if task == "summarize":
        return f"Summarize:\n{payload['text']}"

    if task == "rewrite":
        return f"Rewrite:\n{payload['text']}"

    raise ValueError("Unknown task")


# =========================
# file: model_engine.py
# =========================

# Global engine instance
engine = None


def get_engine():
    global engine
    if engine is None:
        # Auto-detect best model in models/
        model_files = [
            f for f in os.listdir("models") if f.endswith(".gguf")
        ]
        if not model_files:
            raise RuntimeError("No .gguf models found in models/ directory")

        # Pick the first one (usually qwen2.5-1.5b-instruct-q4_0.gguf)
        model_path = os.path.join("models", model_files[0])

        engine = Llama(
            model_path=model_path,
            n_gpu_layers=-1,  # use metal (gpu) on mac, falls back to cpu
            n_ctx=2048,
            verbose=False,
        )
    return engine


async def llm_batch(prompts: List[str]) -> List[str]:
    llm = get_engine()

    def generate(p):
        # Synchronous llama-cpp call
        res = llm.create_completion(
            prompt=p, max_tokens=MAX_OUTPUT_TOKENS, stop=["\n", "User:"]
        )
        return res["choices"][0]["text"].strip()

    # Offload to threads to not block the FastAPI loop
    return await asyncio.gather(*(asyncio.to_thread(generate, p) for p in prompts))


# =========================
# file: validator.py
# =========================


def validate_output(task: str, output: str) -> str:
    # simple pass-through for now
    return output


# =========================
# file: worker.py
# =========================


async def worker_loop():
    while True:
        batch = []

        try:
            job = await asyncio.wait_for(job_queue.get(), timeout=0.1)
            batch.append(job)
        except asyncio.TimeoutError:
            continue

        start = time.time()
        while len(batch) < BATCH_SIZE and (time.time() - start) < (
            BATCH_WAIT_MS / 1000
        ):
            try:
                job = job_queue.get_nowait()
                batch.append(job)
            except:
                break

        prompts = [j["prompt"] for j in batch]

        outputs = await llm_batch(prompts)

        for job, output in zip(batch, outputs):
            validated = validate_output(job["task"], output)
            results[job["job_id"]] = validated


# =========================
# file: api.py
# =========================


@app.post("/v1/execute")
async def execute(request: Request):
    body = await request.json()

    api_key = request.headers.get("Authorization", "anon")

    enforce_rate_limit(api_key)

    task = body.get("task")
    input_data = body.get("input", {})
    config = body.get("config", {})

    stream = config.get("stream", False)

    prompt = build_prompt(task, input_data)

    cache_key = f"{task}:{prompt}"
    if cache_key in cache:
        return {"status": "completed", "data": cache[cache_key]}

    job_id = generate_job_id()

    job = {"job_id": job_id, "task": task, "prompt": prompt, "created_at": time.time()}

    await job_queue.put(job)

    if not stream:
        result = await wait_for_result(job_id, timeout=2)
        if result:
            cache[cache_key] = result
            return {"status": "completed", "data": result}

        return {"status": "queued", "job_id": job_id}

    return StreamingResponse(stream_sse(job_id), media_type="text/event-stream")


# =========================
# file: streaming.py
# =========================


async def wait_for_result(job_id: str, timeout=5):
    start = time.time()
    while time.time() - start < timeout:
        if job_id in results:
            return results[job_id]
        await asyncio.sleep(0.05)
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
        await asyncio.sleep(0.03)

    yield sse("end", {"status": "completed"})


# =========================
# file: startup.py
# =========================


@app.on_event("startup")
async def startup():
    asyncio.create_task(worker_loop())
