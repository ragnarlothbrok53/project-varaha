from typing import Dict, Any
from .base import LLMTask

class SummarizeTask(LLMTask):
    name = "summarize"
    
    def build_prompt(self, payload: Dict[str, Any]) -> str:
        text = payload.get("text", "")
        return (
            "<|im_start|>system\nYou are a helpful assistant that summarizes text concisely.<|im_end|>\n"
            f"<|im_start|>user\nSummarize the following text:\n\n{text}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
