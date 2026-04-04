import json
import uuid
from typing import Generator

def generate_job_id() -> str:
    return str(uuid.uuid4())

def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"

def chunk_text(text: str, chunk_size: int = 6) -> Generator[str, None, None]:
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i : i + chunk_size])
