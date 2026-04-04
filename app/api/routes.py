import time
import asyncio
import uuid
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any

from ..core.worker import job_queue, results, cache
from ..data.manager import (
    get_all_job_ids, get_job_metrics, validate_api_key,
    create_team, get_all_teams, create_api_key, 
    deactivate_api_key, get_team_keys
)
from ..utils.helpers import generate_job_id, sse, chunk_text
from ..services.builder import build_prompt
from ..services.compressor import compress
from ..utils.config import PROMPT_COMPRESSION

router = APIRouter()

# --- Public/Inference Endpoints ---

@router.get("/v1/requests")
async def list_requests():
    return {"requests": get_all_job_ids()}

@router.get("/v1/requests/{job_id}/metrics")
async def get_metrics(job_id: str):
    metrics = get_job_metrics(job_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Request metrics not found")
    return {"job_id": job_id, "metrics": metrics}

@router.post("/v1/execute")
async def execute(request: Request):
    body = await request.json()
    auth_header = request.headers.get("Authorization", "")
    api_key = auth_header.replace("Bearer ", "").strip()
    team = validate_api_key(api_key)
    
    if not team:
         raise HTTPException(status_code=401, detail="Unauthorized")
    if team["credits"] <= 0:
         raise HTTPException(status_code=402, detail="Insufficient credits")

    task = body.get("task")
    input_data = body.get("input", {})
    model = body.get("model", "qwen")
    config = body.get("config", {})
    stream = config.get("stream", False)

    try:
         prompt = build_prompt(task, input_data)
    except ValueError as e:
         raise HTTPException(400, str(e))

    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id, 
        "team_id": team["team_id"],
        "model": model,
        "task": task, 
        "prompt": prompt,
        "request_payload": body,
        "created_at": time.time()
    }

    await job_queue.put(job)

    if not stream:
        res_dict = await wait_for_result(job_id)
        if res_dict:
            return {"status": "completed", "data": res_dict["data"], "job_id": job_id, "metrics": res_dict["metrics"]}
        return {"status": "queued", "job_id": job_id}

    return StreamingResponse(stream_sse(job_id), media_type="text/event-stream")

# --- OpenAI Compatibility Layer ---

@router.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Drop-in OpenAI compatibility for any standard AI client."""
    body = await request.json()
    auth_header = request.headers.get("Authorization", "")
    api_key = auth_header.replace("Bearer ", "").strip()
    team = validate_api_key(api_key)
    
    if not team:
         raise HTTPException(status_code=401, detail="Unauthorized")
    if team["credits"] <= 0:
         raise HTTPException(status_code=402, detail="Insufficient credits")

    messages = body.get("messages", [])
    model = body.get("model", "qwen") # Map requested model to our pools
    
    # Map messages to our internal ChatTask
    try:
        prompt = build_prompt("chat", {"messages": messages})
    except Exception as e:
        raise HTTPException(400, f"Prompt Construction Error: {e}")

    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id, 
        "team_id": team["team_id"],
        "model": model, # qwen or tinyllama
        "task": "chat", 
        "prompt": prompt,
        "request_payload": body,
        "created_at": time.time()
    }

    await job_queue.put(job)
    
    # Wait for result and format as OpenAI JSON
    res_dict = await wait_for_result(job_id)
    if not res_dict:
        raise HTTPException(500, "Inference node timeout")
        
    m = res_dict["metrics"]
    return {
        "id": f"chatcmpl-{job_id[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": res_dict["data"]},
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": m.get("input_tokens", 0),
            "completion_tokens": m.get("output_tokens", 0),
            "total_tokens": m.get("input_tokens", 0) + m.get("output_tokens", 0)
        }
    }

# --- Admin Endpoints ---

def check_admin(request: Request):
    auth_header = request.headers.get("Authorization", "")
    api_key = auth_header.replace("Bearer ", "").strip()
    if api_key != "admin-key":
        raise HTTPException(status_code=403, detail="Admin access required")

@router.post("/v1/admin/teams")
async def admin_create_team(request: Request):
    check_admin(request); body = await request.json()
    create_team(body["id"], body["name"], body.get("credits", 1000.0))
    return {"message": f"Team {body['id']} provisioned"}

@router.get("/v1/admin/teams")
async def admin_list_teams(request: Request):
    check_admin(request); return {"teams": get_all_teams()}

@router.post("/v1/admin/keys")
async def admin_create_key(request: Request):
    check_admin(request); body = await request.json()
    create_api_key(body["key"], body["team_id"], body["name"])
    return {"message": "Key forged"}

@router.get("/v1/admin/keys/{team_id}")
async def admin_get_keys(team_id: str, request: Request):
    check_admin(request); return {"keys": get_team_keys(team_id)}

# --- Internal Helpers ---

async def wait_for_result(job_id: str, timeout: float = 30.0):
    start = time.time()
    while time.time() - start < timeout:
        if job_id in results:
            return results.pop(job_id)
        await asyncio.sleep(0.1)
    return None

async def stream_sse(job_id: str):
    yield sse("start", {"job_id": job_id})
    res_dict = await wait_for_result(job_id)
    if not res_dict:
        yield sse("error", {"message": "timeout"}); return
    yield sse("ready", {"queued": True})
    for chunk in chunk_text(res_dict["data"]):
        yield sse("chunk", {"delta": chunk})
        await asyncio.sleep(0.05)
    yield sse("end", {"status": "completed"})
