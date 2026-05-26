import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator

# --- Authentication Schemas ---

class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128, description="Password must be 8-128 characters.")
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password has reasonable complexity."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    priority: int
    created_at: datetime

class TokenUser(BaseModel):
    id: str
    email: str
    priority: int

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: TokenUser

# --- Conversation Schemas ---

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"
    
    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str:
        """Validate conversation title."""
        if v is None:
            return "New Conversation"
        if len(v.strip()) == 0:
            return "New Conversation"
        if len(v) > 200:
            raise ValueError("Title must be 200 characters or less.")
        return v.strip()

class ConversationUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    
    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate conversation title on update."""
        if len(v.strip()) == 0:
            raise ValueError("Title cannot be empty or whitespace only.")
        return v.strip()

class ConversationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

# --- Message Schemas ---

class ChatMessageCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    conversation_id: uuid.UUID
    message: str = Field(..., min_length=1, max_length=4000, description="User message content.")
    model_type: str = Field(default="default", description="Model type: 'default', 'fast', or 'reasoning'")
    
    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message content."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty or whitespace only.")
        if len(v) > 4000:
            raise ValueError("Message cannot exceed 4000 characters.")
        return v.strip()
    
    @field_validator("model_type")
    @classmethod
    def validate_model_type(cls, v: str) -> str:
        """Validate model_type is one of the allowed types."""
        allowed_types = {"default", "fast", "reasoning"}
        if v.lower() not in allowed_types:
            raise ValueError(f"model_type must be one of {allowed_types}. Got: '{v}'")
        return v.lower()

class MessageResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    model_used: Optional[str] = None
    provider_used: Optional[str] = None
    created_at: datetime

class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]

# --- Admin Analytics Schemas ---

class UsageCount(BaseModel):
    label: str
    count: int

class DailyRequestCount(BaseModel):
    date: str
    count: int

class AdminAnalyticsResponse(BaseModel):
    total_users: int
    total_chats: int
    provider_usage: List[UsageCount]
    model_usage: List[UsageCount]
    daily_requests: List[DailyRequestCount]
