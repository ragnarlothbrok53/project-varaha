from typing import Dict, Any
from .base import LLMTask

class ExtractTask(LLMTask):
    name = "extract"
    
    def build_prompt(self, payload: Dict[str, Any]) -> str:
        text = payload.get("text", "")
        schema = payload.get("schema", {})
        fields = "\n".join([f"- {k}: {v}" for k, v in schema.items()])
        return (
            "<|im_start|>system\nYou are a helpful extraction assistant. Output RAW JSON ONLY. No markdown, no backticks. "
            "Use ISO 8601 for dates (YYYY-MM-DD). Use numbers for currency (no symbols).<|im_end|>\n"
            f"<|im_start|>user\nExtract the following fields from the text:\n{fields}\n\nText: {text}<|im_end|>\n"
            "<|im_start|>assistant\n{"
        )
