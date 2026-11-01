import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_active_user
from app.models.user import User
from app.agent.models import (
    ChatRequest,
    ChatResponse,
    ConversationSummary,
    ConversationDetailResponse,
    ConversationMessageResponse,
)
from app.agent.agent_service import AgentService
from app.agent.conversation_service import ConversationService
from app.agent.tool_registry import ToolRegistry

router = APIRouter(prefix="/agent", tags=["AI Redistribution Agent"])
_agent_service = AgentService()


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Chat with the AI Redistribution Agent",
    description="""
    Submits a natural language message to the AI Redistribution Agent.
    Coordinates Gemini tool orchestration across deterministic perishability,
    geospatial routing, matching, and OR-Tools optimization modules.
    Enforces strict safety guardrails, prompt injection protection, RBAC boundaries,
    and automatic deterministic fallback recovery when external AI is unavailable.
    """,
)
def chat_with_agent(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ChatResponse:
    return _agent_service.process_chat(
        db=db,
        user=current_user,
        request=request,
    )


@router.get(
    "/conversations",
    response_model=List[ConversationSummary],
    status_code=status.HTTP_200_OK,
    summary="List Conversations for Current User",
    description="Retrieves a list of conversation threads belonging to the authenticated user.",
)
def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[ConversationSummary]:
    conversations = ConversationService.list_user_conversations(
        db=db,
        user=current_user,
        limit=limit,
    )
    return [
        ConversationSummary(
            id=c.id,
            title=c.title,
            message_count=len(c.messages),
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in conversations
    ]


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Conversation Detail and History",
    description="Retrieves full chronological message history and executed tool calls for a conversation.",
)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ConversationDetailResponse:
    conv = ConversationService.get_conversation_detail(
        db=db,
        user=current_user,
        conversation_id=conversation_id,
    )
    return ConversationDetailResponse(
        id=conv.id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[
            ConversationMessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                tool_calls=m.tool_calls,
                tool_results=m.tool_results,
                proposal_id=m.proposal_id,
                created_at=m.created_at,
            )
            for m in conv.messages
        ],
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a Conversation Thread",
    description="Permanently deletes a conversation thread and its associated messages.",
)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    deleted = ConversationService.delete_conversation(
        db=db,
        user=current_user,
        conversation_id=conversation_id,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found or access denied.",
        )
    return {"deleted": True, "conversation_id": conversation_id}


@router.get(
    "/tools",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Authorized Agent Tools",
    description="Returns the list of tool definitions authorized for the authenticated user's role.",
)
def list_authorized_tools(
    current_user: User = Depends(get_current_active_user),
) -> List[Dict[str, Any]]:
    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    return ToolRegistry.get_declarations_for_role(role)
