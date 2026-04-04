from typing import Dict, Any
from .base import LLMTask

class ClassifyTask(LLMTask):
    name = "classify"
    
    def build_prompt(self, payload: Dict[str, Any]) -> str:
        text = payload.get("text", "")
        labels = payload.get("labels", [])
        return (
            "<|im_start|>system\nYou are a helpful classification assistant. Only output the most relevant label from the given list. "
            "Example: categories: [apple, orange], text: 'I love red fruit', Label: apple<|im_end|>\n"
            f"<|im_start|>user\nClassify the following text into one of these categories: {labels}\n\nText: {text}<|im_end|>\n"
            "<|im_start|>assistant\nLabel:"
        )
