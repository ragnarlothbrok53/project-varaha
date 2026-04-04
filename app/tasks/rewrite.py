from typing import Dict, Any
from .base import LLMTask

class RewriteTask(LLMTask):
    name = "rewrite"
    
    def build_prompt(self, payload: Dict[str, Any]) -> str:
        text = payload.get("text", "")
        return (
            "<|im_start|>system\nYou are a helpful writing assistant.<|im_end|>\n"
            f"<|im_start|>user\nRewrite the following text for better clarity and engagement:\n\n{text}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
