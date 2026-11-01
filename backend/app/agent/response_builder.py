import re
import uuid
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.user import User
from app.agent.models import (
    ToolCallRecord,
    ToolResultRecord,
    ProposalPreview,
    ChatResponse,
)
from app.agent.tool_executor import ToolExecutor


class ResponseBuilder:
    """
    Synthesizes and structures agent responses, extracts proposal metadata,
    and provides deterministic fallback generation when external LLM providers
    are unreachable, unconfigured, or quota-constrained.
    """

    @classmethod
    def extract_proposal_preview(
        cls,
        tool_results: List[ToolResultRecord],
    ) -> Optional[ProposalPreview]:
        """
        Scans executed tool results for allocation proposal outputs and builds
        a structured ProposalPreview.
        """
        for res in tool_results:
            if not res.success or not res.output:
                continue

            # Check if this tool produced a proposal
            if res.tool_name in ("run_allocation_optimizer", "prepare_redistribution_proposal", "get_allocation_proposal"):
                out = res.output

                # Find proposal_id if present
                raw_id = out.get("proposal_id")
                prop_id = None
                if raw_id:
                    try:
                        prop_id = uuid.UUID(str(raw_id))
                    except (ValueError, TypeError):
                        pass

                summary = out.get("summary", {})
                allocations = out.get("allocations", [])

                total_allocated = float(summary.get("total_allocated_kg", out.get("total_allocated_kg", 0.0)))
                total_unallocated = float(summary.get("total_unallocated_kg", out.get("total_unallocated_kg", 0.0)))
                total_unmet = float(summary.get("total_unmet_demand_kg", out.get("total_unmet_demand_kg", 0.0)))
                solver_status = str(summary.get("solver_status", out.get("solver_status", "UNKNOWN")))
                item_count = int(summary.get("total_allocation_count", len(allocations)))

                # Formulate a clear explanation
                explanation = out.get("explanation")
                if not explanation:
                    explanation = (
                        f"Allocated {total_allocated:.1f} kg across {item_count} redistribution transfers. "
                        f"Unallocated surplus: {total_unallocated:.1f} kg. Unmet demand: {total_unmet:.1f} kg. "
                        f"Solver status: {solver_status}."
                    )

                return ProposalPreview(
                    proposal_id=prop_id,
                    status=out.get("status", "PENDING_REVIEW"),
                    banner="DRAFT PROPOSAL — AWAITING HUMAN APPROVAL",
                    total_allocated_kg=round(total_allocated, 2),
                    total_unallocated_kg=round(total_unallocated, 2),
                    total_unmet_demand_kg=round(total_unmet, 2),
                    solver_status=solver_status,
                    item_count=item_count,
                    explanation=explanation,
                )

        return None

    @classmethod
    def build_deterministic_fallback(
        cls,
        user_text: str,
        user: User,
        db: Session,
    ) -> Tuple[str, List[ToolCallRecord], List[ToolResultRecord], Optional[ProposalPreview]]:
        """
        Rule-based intent dispatcher and response builder that guarantees operational continuity
        even when external AI providers are offline or rate-limited.
        """
        text_lower = user_text.lower()
        role = user.role.value if hasattr(user.role, "value") else str(user.role)

        tool_calls: List[ToolCallRecord] = []
        tool_results: List[ToolResultRecord] = []
        response_lines: List[str] = [
            "> [!NOTE]\n"
            "> **Deterministic Assistance Mode:** The AI redistribution copilot is operating in resilient "
            "deterministic fallback mode using verified backend tools."
        ]

        # 1. OPTIMIZATION & PROPOSAL INTENTS
        if any(w in text_lower for w in ["optimize", "allocation", "optimizer", "proposal", "distribute", "redistribute"]):
            if role in ("COORDINATOR", "ADMIN"):
                call_id = f"fallback_{uuid.uuid4().hex[:8]}"
                tool_calls.append(ToolCallRecord(
                    call_id=call_id,
                    tool_name="prepare_redistribution_proposal",
                    arguments={},
                ))
                res = ToolExecutor.execute(
                    db=db,
                    current_user=user,
                    tool_name="prepare_redistribution_proposal",
                    arguments={},
                    call_id=call_id,
                )
                tool_results.append(res)

                if res.success:
                    summary = res.output.get("summary", {})
                    response_lines.append("\n### Deterministic Allocation Proposal Generated")
                    response_lines.append(
                        f"- **Status:** DRAFT PROPOSAL — AWAITING HUMAN APPROVAL\n"
                        f"- **Solver Status:** `{summary.get('solver_status', 'N/A')}`\n"
                        f"- **Total Food Allocated:** {summary.get('total_allocated_kg', 0):.1f} kg\n"
                        f"- **Unallocated Surplus:** {summary.get('total_unallocated_kg', 0):.1f} kg\n"
                        f"- **Unmet Demand:** {summary.get('total_unmet_demand_kg', 0):.1f} kg\n"
                        f"- **Redistribution Transfers:** {summary.get('total_allocation_count', 0)} items"
                    )
                    response_lines.append(
                        "\n*Please review this proposal in the Coordinator Optimization dashboard before confirming transfers.*"
                    )
                else:
                    response_lines.append(f"\nUnable to generate proposal: {res.error}")
            else:
                response_lines.append(
                    "\nOnly Coordinators and Administrators are authorized to run global network optimization and prepare draft proposals."
                )

        # 2. SURPLUS QUERY INTENTS
        elif any(w in text_lower for w in ["surplus", "inventory", "available food", "what food", "listings"]):
            call_id = f"fallback_{uuid.uuid4().hex[:8]}"
            tool_calls.append(ToolCallRecord(
                call_id=call_id,
                tool_name="get_available_surplus",
                arguments={"limit": 10},
            ))
            res = ToolExecutor.execute(
                db=db,
                current_user=user,
                tool_name="get_available_surplus",
                arguments={"limit": 10},
                call_id=call_id,
            )
            tool_results.append(res)

            if res.success:
                items = res.output.get("items", [])
                response_lines.append(f"\n### Active Surplus Inventory ({res.output.get('total_count', len(items))} batches found)")
                if not items:
                    response_lines.append("No active surplus batches currently registered.")
                else:
                    response_lines.append("| Title | Category | Available (kg) | Storage | Remaining Time |")
                    response_lines.append("| :--- | :--- | :--- | :--- | :--- |")
                    for item in items[:10]:
                        hrs = item.get("remaining_hours")
                        rem_str = f"{hrs:.1f} hrs" if hrs is not None else "N/A"
                        response_lines.append(
                            f"| {item.get('title', 'N/A')} | {item.get('category', 'N/A')} | {item.get('quantity_kg', 0):.1f} | {item.get('storage_condition', 'N/A')} | {rem_str} |"
                        )
            else:
                response_lines.append(f"\nError querying surplus: {res.error}")

        # 3. DEMAND QUERY INTENTS
        elif any(w in text_lower for w in ["demand", "requests", "receiver need", "hunger", "who needs"]):
            call_id = f"fallback_{uuid.uuid4().hex[:8]}"
            tool_calls.append(ToolCallRecord(
                call_id=call_id,
                tool_name="get_active_demand",
                arguments={"limit": 10},
            ))
            res = ToolExecutor.execute(
                db=db,
                current_user=user,
                tool_name="get_active_demand",
                arguments={"limit": 10},
                call_id=call_id,
            )
            tool_results.append(res)

            if res.success:
                items = res.output.get("items", [])
                response_lines.append(f"\n### Active Receiver Demands ({res.output.get('total_count', len(items))} requests found)")
                if not items:
                    response_lines.append("No active demand requests currently registered.")
                else:
                    response_lines.append("| Title | Category | Quantity (kg) | Priority | Max Transit (km) |")
                    response_lines.append("| :--- | :--- | :--- | :--- | :--- |")
                    for item in items[:10]:
                        response_lines.append(
                            f"| {item.get('title', 'N/A')} | {item.get('category', 'N/A')} | {item.get('quantity_kg', 0):.1f} | Priority {item.get('priority', 'N/A')} | {item.get('max_distance_km', 'N/A')} km |"
                        )
            else:
                response_lines.append(f"\nError querying demand: {res.error}")

        # 4. ROUTE OR DISTANCE INTENT
        elif any(w in text_lower for w in ["route", "distance", "transit time", "travel"]):
            response_lines.append(
                "\nTo calculate road distances and travel times, please provide the origin and destination coordinates "
                "or specify listing and receiver IDs. All routing, transit durations, and delivery buffers represent "
                "operational logistics estimates, not food-safety certifications."
            )

        # 5. CANDIDATE COMPATIBILITY / SELECTION EXPLANATION INTENT
        elif any(w in text_lower for w in ["why", "explain", "selected", "compatible", "match", "candidate"]):
            response_lines.append(
                "\nReceiver candidates are evaluated based on product category alignment, storage compatibility, "
                "and estimated delivery-time margin. All routing and perishability values represent operational "
                "logistics estimates and do not constitute food-safety certifications."
            )

        # 6. GENERAL REDISTRIBUTION GUIDANCE
        else:
            response_lines.append(
                "\nHow can I help you coordinate food redistribution today?\n\n"
                "- **View Available Surplus:** Ask *'What surplus food is available?'*\n"
                "- **View Receiver Demands:** Ask *'What active demands are registered?'*\n"
                "- **Run Allocation Optimizer:** Ask *'Run allocation optimization to match surplus with demand'* (Coordinators)\n"
                "- **Check Shelf-Life Urgency:** Ask to calculate urgency for a specific listing\n"
            )

        proposal_preview = cls.extract_proposal_preview(tool_results)
        final_text = "\n".join(response_lines)
        return final_text, tool_calls, tool_results, proposal_preview
