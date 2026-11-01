import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.conversation import Conversation, ConversationMessage
from app.models.user import User


class ConversationService:
    """
    Manages persistence, retrieval, RBAC ownership, and context bounding for agent conversations.
    """

    @classmethod
    def get_or_create_conversation(
        cls,
        db: Session,
        user: User,
        conversation_id: Optional[uuid.UUID] = None,
        initial_title: Optional[str] = None,
    ) -> Conversation:
        if conversation_id:
            conv = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            ).first()
            if not conv:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Conversation {conversation_id} not found or access denied.",
                )
            return conv

        title = initial_title or "Redistribution Session"
        new_conv = Conversation(
            user_id=user.id,
            title=title[:120],
        )
        db.add(new_conv)
        db.flush()
        return new_conv

    @classmethod
    def list_user_conversations(
        cls,
        db: Session,
        user: User,
        limit: int = 50,
    ) -> List[Conversation]:
        return (
            db.query(Conversation)
            .filter(Conversation.user_id == user.id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .all()
        )

    @classmethod
    def get_conversation_detail(
        cls,
        db: Session,
        user: User,
        conversation_id: uuid.UUID,
    ) -> Conversation:
        conv = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
            .first()
        )
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found or access denied.",
            )
        return conv

    @classmethod
    def delete_conversation(
        cls,
        db: Session,
        user: User,
        conversation_id: uuid.UUID,
    ) -> bool:
        conv = (
            db.query(Conversation)
            .filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
            .first()
        )
        if not conv:
            return False

        db.delete(conv)
        db.commit()
        return True

    @classmethod
    def add_message(
        cls,
        db: Session,
        conversation: Conversation,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None,
        proposal_id: Optional[uuid.UUID] = None,
    ) -> ConversationMessage:
        now = datetime.now(timezone.utc)
        msg = ConversationMessage(
            conversation_id=conversation.id,
            role=role,
            content=content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            proposal_id=proposal_id,
            created_at=now,
        )
        db.add(msg)
        conversation.updated_at = now

        # Auto-title conversation on first user message if default
        if role == "user" and conversation.title.startswith("Redistribution Session"):
            clean_snippet = content.strip().split("\n")[0][:60]
            if clean_snippet:
                conversation.title = clean_snippet

        db.flush()
        return msg

    @classmethod
    def get_bounded_history(
        cls,
        db: Session,
        conversation_id: uuid.UUID,
        max_messages: int = 10,
    ) -> List[ConversationMessage]:
        """
        Retrieves the most recent chronological messages bounded by max_messages
        to prevent token exhaustion while maintaining recent context.
        """
        recent = (
            db.query(ConversationMessage)
            .filter(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(max_messages)
            .all()
        )
        recent.reverse()
        return recent
