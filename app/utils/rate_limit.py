import time
from fastapi import HTTPException
from ..core.worker import usage
from .config import API_KEY_RATE_LIMIT

def enforce_rate_limit(api_key: str, limit_per_minute: int = API_KEY_RATE_LIMIT):
    now = time.time()
    window = 60

    if api_key not in usage:
        usage[api_key] = []

    # Clean up old timestamps
    usage[api_key] = [t for t in usage[api_key] if now - t < window]

    if len(usage[api_key]) >= limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    usage[api_key].append(now)
