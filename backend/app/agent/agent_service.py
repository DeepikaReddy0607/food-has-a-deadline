import logging
import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from google.genai import types

from app.models.user import User
from app.agent.models import (
    ChatRequest,
    ChatResponse,
    ToolCallRecord,
    ToolResultRecord,
    ProposalPreview,
)
from app.agent.safety_guard import SafetyGuard
from app.agent.tool_registry import ToolRegistry
from app.agent.tool_executor import ToolExecutor
from app.agent.gemini_provider import (
    GeminiProvider,
    GeminiError,
    GeminiUnavailableError,
    GeminiQuotaExceededError,
)
from app.agent.conversation_service import ConversationService
from app.agent.response_builder import ResponseBuilder

logger = logging.getLogger(__name__)


class AgentService:
    """
    Central orchestrator for the AI Redistribution Agent. Coordinates conversation persistence,
    Google Gen AI multi-turn function calling, deterministic tool dispatch, security guardrails,
    and automatic deterministic fallback recovery.
    """

    def __init__(self, gemini_provider: Optional[GeminiProvider] = None):
        self.gemini_provider = gemini_provider or GeminiProvider()

    def process_chat(
        self,
        db: Session,
        user: User,
        request: ChatRequest,
    ) -> ChatResponse:
        """
        Executes an authenticated multi-turn chat cycle with role-based tool orchestration.
        """
        # Step 1: Input sanitization & prompt injection verification
        is_safe, clean_text_or_err = SafetyGuard.sanitize_user_input(request.message)
        if not is_safe:
            conv = ConversationService.get_or_create_conversation(
                db=db,
                user=user,
                conversation_id=request.conversation_id,
            )
            # Record user input and rejection message
            user_msg = ConversationService.add_message(
                db=db,
                conversation=conv,
                role="user",
                content=request.message[:4000],
            )
            asst_msg = ConversationService.add_message(
                db=db,
                conversation=conv,
                role="assistant",
                content=clean_text_or_err,
            )
            db.commit()

            return ChatResponse(
                conversation_id=conv.id,
                message_id=asst_msg.id,
                response_text=clean_text_or_err,
                tool_calls=[],
                tool_results=[],
                proposal_preview=None,
                ai_provider="SafetyGuard",
                fallback_mode=True,
            )

        clean_text = clean_text_or_err

        # Step 2: Retrieve or initialize conversation thread
        conv = ConversationService.get_or_create_conversation(
            db=db,
            user=user,
            conversation_id=request.conversation_id,
        )

        # Step 3: Record the incoming user message
        user_msg = ConversationService.add_message(
            db=db,
            conversation=conv,
            role="user",
            content=clean_text,
        )

        user_role = user.role.value if hasattr(user.role, "value") else str(user.role)
        all_tool_calls: List[ToolCallRecord] = []
        all_tool_results: List[ToolResultRecord] = []
        final_text = ""
        proposal_preview: Optional[ProposalPreview] = None
        fallback_mode = False
        ai_provider = "Google Gemini"

        # Step 4: If Gemini is not configured, execute deterministic fallback immediately
        if not self.gemini_provider.is_available():
            logger.info("Gemini not configured; executing deterministic fallback for user %s", user.email)
            final_text, fb_calls, fb_results, fb_proposal = ResponseBuilder.build_deterministic_fallback(
                user_text=clean_text,
                user=user,
                db=db,
            )
            all_tool_calls.extend(fb_calls)
            all_tool_results.extend(fb_results)
            proposal_preview = fb_proposal
            fallback_mode = True
            ai_provider = "Deterministic Fallback"

        else:
            # Step 5: Format bounded conversation history for Gemini
            history_messages = ConversationService.get_bounded_history(
                db=db,
                conversation_id=conv.id,
                max_messages=10,
            )

            contents: List[types.Content] = []
            for h_msg in history_messages:
                role_label = "user" if h_msg.role == "user" else "model"
                contents.append(
                    types.Content(
                        role=role_label,
                        parts=[types.Part.from_text(text=h_msg.content or "")],
                    )
                )

            # Retrieve authorized tools for the user's role
            tool_decls = ToolRegistry.get_declarations_for_role(user_role)
            tools = [types.Tool(function_declarations=[types.FunctionDeclaration(**d) for d in tool_decls])] if tool_decls else None

            # Multi-turn tool execution loop (max 5 turns)
            try:
                for turn in range(5):
                    response = self.gemini_provider.generate_chat_turn(
                        contents=contents,
                        tools=tools,
                        system_instruction=SafetyGuard.SYSTEM_INSTRUCTIONS,
                    )

                    # Inspect if Gemini requested tool executions
                    if response.function_calls:
                        for fc in response.function_calls:
                            call_id = f"call_{uuid.uuid4().hex[:8]}"
                            fc_name = fc.name
                            fc_args = fc.args or {}

                            call_record = ToolCallRecord(
                                call_id=call_id,
                                tool_name=fc_name,
                                arguments=fc_args,
                            )
                            all_tool_calls.append(call_record)

                            res_record = ToolExecutor.execute(
                                db=db,
                                current_user=user,
                                tool_name=fc_name,
                                arguments=fc_args,
                                call_id=call_id,
                            )
                            all_tool_results.append(res_record)

                            # Append model turn and user tool response turn
                            contents.append(
                                types.Content(
                                    role="model",
                                    parts=[types.Part(function_call=fc)],
                                )
                            )
                            tool_payload = res_record.output if res_record.success else {"error": res_record.error}
                            contents.append(
                                types.Content(
                                    role="user",
                                    parts=[types.Part.from_function_response(
                                        name=fc_name,
                                        response={"result": tool_payload},
                                    )],
                                )
                            )
                    else:
                        # Final model completion text reached
                        final_text = response.text or ""
                        break

            except (GeminiQuotaExceededError, GeminiUnavailableError) as e:
                logger.warning("Gemini failed (%s); switching to deterministic fallback.", e)
                fb_text, fb_calls, fb_results, fb_proposal = ResponseBuilder.build_deterministic_fallback(
                    user_text=clean_text,
                    user=user,
                    db=db,
                )
                final_text = fb_text
                all_tool_calls.extend(fb_calls)
                all_tool_results.extend(fb_results)
                proposal_preview = fb_proposal
                fallback_mode = True
                ai_provider = (
                    "Deterministic Fallback (Gemini Quota Exceeded)"
                    if isinstance(e, GeminiQuotaExceededError)
                    else "Deterministic Fallback (Gemini Unavailable)"
                )
            except Exception as e:
                logger.error("Unhandled exception in agent loop: %s", e)
                fb_text, fb_calls, fb_results, fb_proposal = ResponseBuilder.build_deterministic_fallback(
                    user_text=clean_text,
                    user=user,
                    db=db,
                )
                final_text = fb_text
                all_tool_calls.extend(fb_calls)
                all_tool_results.extend(fb_results)
                proposal_preview = fb_proposal
                fallback_mode = True
                ai_provider = "Deterministic Fallback (Agent Error)"

        # Step 6: Post-process assistant output with safety guard
        final_text = SafetyGuard.validate_assistant_output(final_text)

        # Extract proposal preview if not already established
        if not proposal_preview:
            proposal_preview = ResponseBuilder.extract_proposal_preview(all_tool_results)

        # Step 7: Persist assistant message and tool records
        tool_calls_dict = [tc.model_dump() for tc in all_tool_calls] if all_tool_calls else None
        tool_results_dict = [tr.model_dump() for tr in all_tool_results] if all_tool_results else None

        prop_id = proposal_preview.proposal_id if proposal_preview else None
        asst_msg = ConversationService.add_message(
            db=db,
            conversation=conv,
            role="assistant",
            content=final_text,
            tool_calls=tool_calls_dict,
            tool_results=tool_results_dict,
            proposal_id=prop_id,
        )
        db.commit()

        return ChatResponse(
            conversation_id=conv.id,
            message_id=asst_msg.id,
            response_text=final_text,
            tool_calls=all_tool_calls,
            tool_results=all_tool_results,
            proposal_preview=proposal_preview,
            ai_provider=ai_provider,
            fallback_mode=fallback_mode,
        )
