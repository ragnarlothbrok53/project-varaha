from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum


class TaskType(str, Enum):
    """Supported task types"""
    CHAT = "chat"
    EXTRACT = "extract"
    CLASSIFY = "classify"
    SUMMARIZE = "summarize"
    REWRITE = "rewrite"


class ModelType(str, Enum):
    """Supported model types"""
    QWEN = "qwen"
    TINYLLAMA = "tinyllama"


class ExecuteRequest(BaseModel):
    """Request model for task execution"""
    task: TaskType = Field(..., description="Type of task to execute")
    input: Dict[str, Any] = Field(..., description="Input data for the task")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Optional configuration")
    
    @validator('input')
    def validate_input(cls, v, values):
        task = values.get('task')
        if task == TaskType.CHAT:
            if 'text' not in v:
                raise ValueError('Chat task requires "text" field in input')
        elif task == TaskType.EXTRACT:
            if 'text' not in v or 'schema' not in v:
                raise ValueError('Extract task requires "text" and "schema" fields in input')
        elif task == TaskType.CLASSIFY:
            if 'text' not in v or 'labels' not in v:
                raise ValueError('Classify task requires "text" and "labels" fields in input')
        elif task == TaskType.SUMMARIZE:
            if 'text' not in v:
                raise ValueError('Summarize task requires "text" field in input')
        elif task == TaskType.REWRITE:
            if 'text' not in v:
                raise ValueError('Rewrite task requires "text" field in input')
        return v
    
    @validator('config')
    def validate_config(cls, v):
        if v is not None:
            # Validate config parameters
            if 'temperature' in v:
                temp = v['temperature']
                if not isinstance(temp, (int, float)) or temp < 0 or temp > 1:
                    raise ValueError('Temperature must be between 0 and 1')
            if 'max_tokens' in v:
                max_tokens = v['max_tokens']
                if not isinstance(max_tokens, int) or max_tokens < 1:
                    raise ValueError('Max tokens must be a positive integer')
        return v


class ChatCompletionRequest(BaseModel):
    """Request model for OpenAI-compatible chat completions"""
    model: ModelType = Field(default=ModelType.QWEN, description="Model to use")
    messages: List[Dict[str, str]] = Field(..., description="List of messages in the conversation")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=1.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(default=256, ge=1, le=2048, description="Maximum tokens to generate")
    stream: Optional[bool] = Field(default=False, description="Whether to stream the response")
    
    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError('Messages list cannot be empty')
        for message in v:
            if not isinstance(message, dict):
                raise ValueError('Each message must be a dictionary')
            if 'role' not in message or 'content' not in message:
                raise ValueError('Each message must have "role" and "content" fields')
            if message['role'] not in ['system', 'user', 'assistant']:
                raise ValueError('Message role must be one of: system, user, assistant')
        return v


class UserRegistrationRequest(BaseModel):
    """Request model for user registration"""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$', description="Valid email address")
    password: str = Field(..., min_length=8, max_length=100, description="Password (min 8 characters)")
    full_name: Optional[str] = Field(None, max_length=100, description="Full name")
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserLoginRequest(BaseModel):
    """Request model for user login"""
    email: str = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class APIKeyCreateRequest(BaseModel):
    """Request model for API key creation"""
    name: str = Field(..., min_length=1, max_length=100, description="Display name for the key")
    model_id: ModelType = Field(default=ModelType.QWEN, description="Default model for this key")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0, description="Default temperature")
    system_prompt: Optional[str] = Field(default="", max_length=2000, description="Default system prompt")
    rag_text: Optional[str] = Field(default="", max_length=5000, description="RAG context text")


class APIKeyUpdateRequest(BaseModel):
    """Request model for API key updates"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Display name for the key")
    model_id: Optional[ModelType] = Field(None, description="Default model for this key")
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0, description="Default temperature")
    system_prompt: Optional[str] = Field(None, max_length=2000, description="Default system prompt")
    rag_text: Optional[str] = Field(None, max_length=5000, description="RAG context text")


class PasswordResetRequest(BaseModel):
    """Request model for password reset"""
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$', description="Email address")


class PasswordResetConfirmRequest(BaseModel):
    """Request model for password reset confirmation"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


# Response Models
class BaseResponse(BaseModel):
    """Base response model"""
    success: bool = True
    message: str = "Operation completed successfully"


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ExecuteResponse(BaseModel):
    """Response model for task execution"""
    success: bool = True
    result: Optional[str] = Field(None, description="Task execution result")
    task_id: Optional[str] = Field(None, description="Task identifier")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")


class ChatCompletionResponse(BaseModel):
    """Response model for chat completions"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
