import os
import asyncio
from typing import List
from llama_cpp import Llama
from .config import MAX_OUTPUT_TOKENS

# Global engine instance
_engine = None

def get_engine() -> Llama:
    global _engine
    if _engine is None:
        # Check models/ directory
        models_dir = os.path.join(os.getcwd(), "models")
        if not os.path.exists(models_dir):
            raise RuntimeError(f"Models directory not found at: {models_dir}")
             
        model_files = [f for f in os.listdir(models_dir) if f.endswith(".gguf")]
        if not model_files:
            raise RuntimeError(f"No .gguf models found in: {models_dir}")

        # Pick the first one (usually qwen or tinyllama)
        model_path = os.path.join(models_dir, sorted(model_files)[0])

        _engine = Llama(
            model_path=model_path,
            n_gpu_layers=-1,  # use metal (gpu) on mac, falls back to cpu
            n_ctx=2048,
            verbose=False,
        )
    return _engine

async def llm_batch(prompts: List[str]) -> List[str]:
    engine = get_engine()

    def generate(p: str):
        # We handle single generation in a thread
        res = engine.create_completion(
            prompt=p, max_tokens=MAX_OUTPUT_TOKENS, stop=["\n", "User:"]
        )
        return res["choices"][0]["text"].strip()

    # Offload to threads to not block the FastAPI loop
    return await asyncio.gather(*(asyncio.to_thread(generate, p) for p in prompts))
