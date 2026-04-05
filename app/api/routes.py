import time
import asyncio
import uuid
import base64
import io
import sqlite3
import pypdf
import docx
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..core.worker import job_queue, results
from ..data.manager import (
    get_all_job_ids, get_job_metrics, validate_api_key,
    create_api_key, get_user_keys, get_metrics_by_key,
    deactivate_api_key
)
from ..utils.helpers import sse, chunk_text
from ..utils.config import get_settings
from ..services.builder import build_prompt
from .auth import verify_jwt
from .schemas import (
    ExecuteRequest, ChatCompletionRequest, APIKeyCreateRequest, 
    APIKeyUpdateRequest, ExecuteResponse, ErrorResponse
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)
settings = get_settings()

# --- Public/Inference Endpoints ---

@router.get("/v1/requests")
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}minute")
async def list_requests(request: Request):
    return {"requests": get_all_job_ids()}

@router.get("/v1/requests/{job_id}/metrics")
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}minute")
async def get_metrics(job_id: str, request: Request):
    metrics = get_job_metrics(job_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Request metrics not found")
    return {"job_id": job_id, "metrics": metrics}

@router.get("/v1/requests/key/{api_key}")
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}minute")
async def get_key_requests(api_key: str, user: dict = Depends(verify_jwt), request: Request = None):
    # Note: For production, we should enforce that api_key belongs to user["id"]
    return {"requests": get_metrics_by_key(api_key)}

@router.post("/v1/execute")
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}minute")
async def execute(execute_request: ExecuteRequest, request: Request):
    auth_header = request.headers.get("Authorization", "")
    api_key = auth_header.replace("Bearer ", "").strip()
    key_info = validate_api_key(api_key)
    
    if not key_info:
         raise HTTPException(status_code=401, detail="Unauthorized")
    if key_info["credits"] <= 0:
         raise HTTPException(status_code=402, detail="Insufficient credits")

    task = execute_request.task
    input_data = execute_request.input
    config = execute_request.config or {}
    stream = config.get("stream", False)

    # Intelligent Key Config Auto-Apply
    model = key_info.get("model_id", "qwen")
    temperature = key_info.get("temperature", 0.1)
    key_sys_prompt = key_info.get("system_prompt")
    key_rag_text = key_info.get("rag_text")

    if key_sys_prompt:
        input_data["system_prompt"] = key_sys_prompt

    # Process Knowledge Grounding (RAG Files)
    files = input_data.get("files", [])
    if files:
        rag_text = ""
        for f in files:
            try:
                fname = f.get("name", "")
                fdata = base64.b64decode(f.get("data", ""))
                parsed_text = ""
                if fname.lower().endswith(".pdf"):
                    reader = pypdf.PdfReader(io.BytesIO(fdata))
                    for page in reader.pages:
                        if page.extract_text():
                            parsed_text += page.extract_text() + "\n"
                elif fname.lower().endswith(".docx"):
                    doc = docx.Document(io.BytesIO(fdata))
                    for para in doc.paragraphs:
                        parsed_text += para.text + "\n"
                elif fname.lower().endswith(".txt"):
                    parsed_text = fdata.decode("utf-8")
                
                if parsed_text:
                    rag_text += f"\n--- Knowledge Document: {fname} ---\n{parsed_text}\n"
            except Exception as e:
                print(f"Error parsing RAG file {f.get('name')}: {e}")
                
        if rag_text or key_rag_text:
            combined_rag = (key_rag_text or "") + ("\n" if key_rag_text and rag_text else "") + rag_text
            text = input_data.get("text", "")
            input_data["text"] = f"Use the following knowledge documents as context to fulfill the user request:\n{combined_rag}\n\nUser Request:\n{text}"
    elif key_rag_text:
        text = input_data.get("text", "")
        input_data["text"] = f"Use the following knowledge documents as context to fulfill the user request:\n{key_rag_text}\n\nUser Request:\n{text}"

    try:
         prompt = build_prompt(task, input_data)
    except ValueError as e:
         raise HTTPException(status_code=400, detail=str(e))

    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id, 
        "user_id": key_info["user_id"],
        "api_key": api_key,
        "model": model,
        "task": task, 
        "prompt": prompt,
        "request_payload": execute_request.dict(),
        "created_at": time.time(),
        "temperature": temperature
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
    key_info = validate_api_key(api_key)
    
    if not key_info:
         raise HTTPException(status_code=401, detail="Unauthorized")
    if key_info["credits"] <= 0:
         raise HTTPException(status_code=402, detail="Insufficient credits")

    messages = body.get("messages", [])
    
    # Intelligent Key Config Auto-Apply for Chat
    model = key_info.get("model_id", "qwen")
    temperature = key_info.get("temperature", 0.1)
    key_sys_prompt = key_info.get("system_prompt")
    key_rag_text = key_info.get("rag_text")
    
    if key_rag_text:
        # Prepend context to the last user message
        for msg in reversed(messages):
            if msg.get("role") == "user":
                msg["content"] = f"Use the following knowledge documents as context to fulfill the user request:\n{key_rag_text}\n\nUser Request:\n{msg['content']}"
                break
                
    if key_sys_prompt:
        # Append or modify system instructions
        has_sys = False
        for msg in messages:
            if msg.get("role") == "system":
                msg["content"] = key_sys_prompt
                has_sys = True
                break
        if not has_sys:
            messages.insert(0, {"role": "system", "content": key_sys_prompt})
    
    # Map messages to our internal ChatTask
    try:
        prompt = build_prompt("chat", {"messages": messages})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Prompt Construction Error: {e}")

    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id, 
        "user_id": key_info["user_id"],
        "api_key": api_key,
        "model": model, 
        "task": "chat", 
        "prompt": prompt,
        "request_payload": body,
        "created_at": time.time(),
        "temperature": temperature
    }

    await job_queue.put(job)
    
    # Wait for result and format as OpenAI JSON
    res_dict = await wait_for_result(job_id)
    if not res_dict:
        raise HTTPException(status_code=500, detail="Inference node timeout")
        
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

# --- Management Endpoints ---

@router.post("/v1/admin/keys")
async def admin_create_key(request: Request, user: dict = Depends(verify_jwt)):
    body = await request.json()
    sys_p = body.get("system_prompt", "")
    files = body.get("files", [])
    rag_text = ""
    for f in files:
        try:
            fname = f.get("name", "")
            fdata = base64.b64decode(f.get("data", ""))
            parsed_text = ""
            if fname.lower().endswith(".pdf"):
                reader = pypdf.PdfReader(io.BytesIO(fdata))
                for page in reader.pages:
                    if page.extract_text():
                        parsed_text += page.extract_text() + "\n"
            elif fname.lower().endswith(".docx"):
                doc = docx.Document(io.BytesIO(fdata))
                for para in doc.paragraphs:
                    parsed_text += para.text + "\n"
            elif fname.lower().endswith(".txt"):
                parsed_text = fdata.decode("utf-8")
            if parsed_text:
                rag_text += f"\n--- Knowledge Document: {fname} ---\n{parsed_text}\n"
        except Exception as e:
            print(f"Error parsing key level RAG {f.get('name')}: {e}")
            
    create_api_key(
        key=body["key"], 
        user_id=user["id"], 
        name=body["name"], 
        model_id=body.get("model_id", "qwen"),
        temperature=body.get("temperature", 0.1),
        system_prompt=sys_p, 
        rag_text=rag_text
    )
    return {"message": "Key forged"}

@router.get("/v1/admin/keys")
async def get_keys(user: dict = Depends(verify_jwt)):
    return {"keys": get_user_keys(user["id"])}

@router.put("/v1/admin/keys/{api_key}")
async def admin_update_key(api_key: str, request: Request, user: dict = Depends(verify_jwt)):
    # First verify the key belongs to the user
    user_keys = get_user_keys(user["id"])
    key_exists = any(k["key"] == api_key for k in user_keys)
    
    if not key_exists:
        raise HTTPException(status_code=404, detail="Key not found or doesn't belong to user")
    
    body = await request.json()
    
    try:
        conn = sqlite3.connect("varaha_metrics.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE api_keys 
            SET name = ?, model_id = ?, temperature = ?, system_prompt = ?
            WHERE key = ?
        """, (
            body.get("name"),
            body.get("model_id", "qwen"),
            body.get("temperature", 0.1),
            body.get("system_prompt", ""),
            api_key
        ))
        
        conn.commit()
        conn.close()
        
        return {"message": "Key updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update key: {str(e)}")

@router.delete("/v1/admin/keys/{api_key}")
async def admin_delete_key(api_key: str, user: dict = Depends(verify_jwt)):
    # First verify the key belongs to the user
    user_keys = get_user_keys(user["id"])
    key_exists = any(k["key"] == api_key for k in user_keys)
    
    if not key_exists:
        raise HTTPException(status_code=404, detail="Key not found or doesn't belong to user")
    
    try:
        deactivate_api_key(api_key)
        return {"message": "Key deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete key: {str(e)}")

# --- Internal Helpers ---

async def wait_for_result(job_id: str, timeout: float = 60.0):
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
