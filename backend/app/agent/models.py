import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    User message input to the AI Redistribution Agent.
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Natural language instruction or inquiry regarding food redistribution.",
    )
    conversation_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional existing conversation ID to continue. If omitted, a new conversation is initialized.",
    )


class ToolCallRecord(BaseModel):
    """
    Audit log representation of a tool call executed during agent reasoning.
    """
    call_id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolResultRecord(BaseModel):
    """
    Structured outcome returned by a registered deterministic backend tool.
    """
    call_id: str
    tool_name: str
    output: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None


class ProposalPreview(BaseModel):
    """
    Standardized proposal presentation metadata embedded into agent responses.
    """
    proposal_id: Optional[uuid.UUID] = None
    status: str = Field(default="PENDING_REVIEW")
    banner: str = "DRAFT PROPOSAL — AWAITING HUMAN APPROVAL"
    total_allocated_kg: float
    total_unallocated_kg: float
    total_unmet_demand_kg: float
    solver_status: str
    item_count: int
    explanation: str


class ChatResponse(BaseModel):
    """
    Final agent response returned to the frontend.
    """
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    response_text: str
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    tool_results: List[ToolResultRecord] = Field(default_factory=list)
    proposal_preview: Optional[ProposalPreview] = None
    ai_provider: str = Field(default="Google Gemini")
    fallback_mode: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationMessageResponse(BaseModel):
    """
    Message item representation for conversation history retrieval.
    """
    id: uuid.UUID
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None
    proposal_id: Optional[uuid.UUID] = None
    created_at: datetime


class ConversationSummary(BaseModel):
    """
    Summary representation of a conversation thread.
    """
    id: uuid.UUID
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationDetailResponse(BaseModel):
    """
    Full conversation representation including chronological message history.
    """
    id: uuid.UUID
    title: str
    messages: List[ConversationMessageResponse]
    created_at: datetime
    updated_at: datetime
