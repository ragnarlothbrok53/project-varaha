from .base import LLMTask
from typing import Dict, Any, List

class ChatTask(LLMTask):
    """OpenAI-compatible Chat Completion task (ChatML)."""
    name: str = "chat"

    def build_prompt(self, payload: Dict[str, Any]) -> str:
        """Construct a ChatML prompt from a list of messages."""
        messages = payload.get("messages", [])
        prompt = ""
        
        # System message handling
        system_msg = next((m.get("content") for m in messages if m.get("role") == "system"), 
                        "You are Varaha, a high-performance AI assistant.")
        
        prompt += f"<|im_start|>system\n{system_msg}<|im_end|>\n"
        
        # Intersperse User/Assistant messages
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            if role in ["user", "assistant"]:
                prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
        
        # Prepend the final assistant start
        prompt += "<|im_start|>assistant\n"
        return prompt
