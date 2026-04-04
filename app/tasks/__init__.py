from .summarize import SummarizeTask
from .classify import ClassifyTask
from .extract import ExtractTask
from .rewrite import RewriteTask
from .chat import ChatTask

REGISTRY = {
    "summarize": SummarizeTask(),
    "classify": ClassifyTask(),
    "extract": ExtractTask(),
    "rewrite": RewriteTask(),
    "chat": ChatTask()
}

__all__ = ["SummarizeTask", "ClassifyTask", "ExtractTask", "RewriteTask", "ChatTask", "REGISTRY"]
