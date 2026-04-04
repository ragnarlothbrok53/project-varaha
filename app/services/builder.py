from typing import Dict, Any
from ..tasks import SummarizeTask, ExtractTask, ClassifyTask, RewriteTask, ChatTask

# Registry of tasks
TASKS = {
    "summarize": SummarizeTask(),
    "extract": ExtractTask(),
    "classify": ClassifyTask(),
    "rewrite": RewriteTask(),
    "chat": ChatTask()
}

def build_prompt(task_name: str, payload: Dict[str, Any]) -> str:
    if task_name not in TASKS:
        raise ValueError(f"Task '{task_name}' not found. Available: {list(TASKS.keys())}")
    
    task_impl = TASKS[task_name]
    return task_impl.build_prompt(payload)
