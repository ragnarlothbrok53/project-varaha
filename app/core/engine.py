import os
import asyncio
import time
from typing import List, Dict, Any, Optional
from llama_cpp import Llama
from ..utils.config import get_settings

# Dictionary of Engine Pools for different models
_engine_pools: Dict[str, asyncio.Queue] = {}
_initialized_models: set = set()

settings = get_settings()
# Model Definitions
MODELS = {
    "qwen": "models/qwen2.5-1.5b-instruct-q4_0.gguf",
    "tinyllama": "models/tinyllama-1.1b-chat-v1.0.Q2_K.gguf"
}

async def init_model_pool(model_id: str, pool_size: int = 1):
    """Initializes a specific model pool if not already exists."""
    global _engine_pools, _initialized_models
    
    if model_id in _initialized_models:
        return
        
    model_path = MODELS.get(model_id)
    if not model_path:
        raise ValueError(f"Unknown model identifier: {model_id}")
        
    if not os.path.exists(model_path):
        # Fallback to general model path or error
        print(f"⚠️ Model {model_id} not found at {model_path}. Skipping.")
        return

    print(f"🚀 Initializing Engine Pool for [{model_id}] (Size: {pool_size})...")
    
    queue = asyncio.Queue()
    for i in range(pool_size):
        engine = Llama(
            model_path=model_path,
            n_gpu_layers=-1, 
            n_ctx=4096,
            n_batch=512,
            n_threads=4,
            flash_attn=True,
            offload_kqv=True,
            cache=True,
            cache_type="lru",
            verbose=False,
        )
        await queue.put(engine)
    
    _engine_pools[model_id] = queue
    _initialized_models.add(model_id)

async def init_all_pools():
    """Bootstraps all available models on startup."""
    # We load Qwen by default, TinyLlama if available
    await init_model_pool("qwen", pool_size=1)
    if os.path.exists(MODELS["tinyllama"]):
        await init_model_pool("tinyllama", pool_size=1)

def generate_on_engine(engine: Llama, req: Dict[str, Any], model_id: str) -> Dict[str, Any]:
    p = req["prompt"]
    temperature = float(req.get("temperature", 0.1))
    
    # Handle pre-filled response prefixes (specific to Qwen/Instruct models)
    is_json_prefilled = p.endswith("<|im_start|>assistant\n{")
    
    start_time = time.time()
    ttft = None
    output_text = "{" if is_json_prefilled else ""
    tokens_generated = 0

    # Model-specific stop tokens
    stop_tokens = ["<|im_end|>", "<|im_start|>", "\nUser:", "</s>", "<|user|>"]

    stream = engine.create_completion(
        prompt=p,
        max_tokens=settings.MAX_OUTPUT_TOKENS,
        stop=stop_tokens,
        temperature=temperature,
        repeat_penalty=1.1,
        stream=True,
    )

    for chunk in stream:
        token_text = chunk["choices"][0].get("text", "")
        if ttft is None and token_text:
            ttft = (time.time() - start_time) * 1000
        output_text += token_text
        tokens_generated += 1

    total_duration = time.time() - start_time
    tps = tokens_generated / total_duration if total_duration > 0 else 0
    input_tokens = len(engine.tokenize(p.encode("utf-8")))

    return {
        "output": output_text.strip(),
        "metrics": {
            "model": model_id,
            "ttft_ms": round(ttft or 0, 2),
            "total_time_ms": round(total_duration * 1000, 2),
            "input_tokens": input_tokens,
            "output_tokens": tokens_generated,
            "tps": round(tps, 2),
        },
    }

async def llm_batch_on_model(requests: List[Dict[str, Any]], model_id: str = "qwen"):
    """Parallel batching via an engine pool for a specific model."""
    if model_id not in _initialized_models:
        await init_model_pool(model_id)

    queue = _engine_pools.get(model_id)
    if not queue:
        raise RuntimeError(f"Engine pool for {model_id} failed to initialize.")

    async def pooled_generate(r: Dict[str, Any]):
        engine = await queue.get()
        try:
            return await asyncio.to_thread(generate_on_engine, engine, r, model_id)
        finally:
            await queue.put(engine)
            
    return await asyncio.gather(*(pooled_generate(r) for r in requests))
