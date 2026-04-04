from typing import Dict, Any

class LLMTask:
    """Base class for all LLM tasks."""
    name: str = ""

    def build_prompt(self, payload: Dict[str, Any]) -> str:
        """Construct the prompt from the input payload."""
        raise NotImplementedError("Task must implement build_prompt")
