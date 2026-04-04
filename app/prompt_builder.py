from typing import Dict, Any

def build_prompt(task: str, payload: Dict[str, Any]) -> str:
    text = payload.get("text", "")
    if task == "extract":
        schema = payload.get("schema", {})
        fields = "\n".join([f"- {k}: {v}" for k, v in schema.items()])
        return f"Extract fields:\n{fields}\nText:\n{text}\nReturn JSON only."

    if task == "classify":
        labels = payload.get("labels", [])
        return f"Classify into one of {labels}:\n{text}"

    if task == "summarize":
        return f"Summarize:\n{text}"

    if task == "rewrite":
        return f"Rewrite:\n{text}"

    raise ValueError(f"Unknown task: {task}")
