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
    created_at: datetime

class TokenUser(BaseModel):
    id: str
    email: str

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

# --- Governance Schemas ---

class AuditLogResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: uuid.UUID
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    event_type: str
    status: str
    provider_name: Optional[str] = None
    model_name: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    metadata: Optional[dict] = Field(None, validation_alias="meta_data")
    created_at: datetime

class UsageEventResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: uuid.UUID
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    provider_name: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: Optional[int] = None
    stream_duration_ms: Optional[int] = None
    retry_count: int
    status: str
    metadata: Optional[dict] = Field(None, validation_alias="meta_data")
    created_at: datetime

class DlpEventResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    rule_id: Optional[uuid.UUID] = None
    action: str
    match_count: int
    redacted_excerpt: Optional[str] = None
    metadata: Optional[dict] = Field(None, validation_alias="meta_data")
    created_at: datetime

class SecurityEventResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    event_type: str
    severity: str
    status: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[dict] = Field(None, validation_alias="meta_data")
    created_at: datetime

class ProviderPolicyRequest(BaseModel):
    organization_id: uuid.UUID
    provider_name: str
    is_enabled: bool = True
    allow_reasoning: bool = True
    max_cost_usd_per_day: Optional[float] = None
    max_cost_usd_per_request: Optional[float] = None

class ProviderPolicyResponse(ProviderPolicyRequest):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

class ModelPolicyRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    organization_id: uuid.UUID
    provider_name: str
    model_name: str
    is_enabled: bool = True
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0

class ModelPolicyResponse(ModelPolicyRequest):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

class DlpRuleRequest(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str
    pattern: str
    action: str
    severity: str = "medium"
    is_active: bool = True

class DlpRuleResponse(DlpRuleRequest):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

class RetentionPolicyRequest(BaseModel):
    organization_id: uuid.UUID
    data_type: str
    soft_delete_after_days: Optional[int] = None
    hard_delete_after_days: Optional[int] = None
    is_active: bool = True

class RetentionPolicyResponse(RetentionPolicyRequest):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
