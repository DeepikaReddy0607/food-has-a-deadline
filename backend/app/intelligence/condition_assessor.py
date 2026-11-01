from typing import List, Dict, Any, Optional

VALID_CONDITIONS = {
    "EXCELLENT",
    "GOOD",
    "FAIR",
    "RIPE",
    "IMMINENT_DECAY",
    "IMPERFECT",
}


class ConditionAssessor:
    """
    Deterministic food condition assessor.
    Evaluates reported physical state and provides actionable handling warnings and safety verification requirements.
    """

    @staticmethod
    def assess(condition: Optional[str]) -> Dict[str, Any]:
        warnings: List[str] = []
        norm = (condition or "").strip().upper()

        if not norm:
            warnings.append("Food condition is unspecified; on-site inspection is required at pickup.")
            return {
                "condition": "UNKNOWN",
                "is_valid": False,
                "warnings": warnings,
                "requires_immediate_action": False,
                "notes": "Missing condition data.",
            }

        if norm not in VALID_CONDITIONS:
            warnings.append(f"Unrecognized condition '{norm}'; requires physical verification.")
            return {
                "condition": norm,
                "is_valid": False,
                "warnings": warnings,
                "requires_immediate_action": False,
                "notes": f"Unrecognized condition value: {norm}",
            }

        requires_immediate = False
        notes = ""

        if norm == "IMMINENT_DECAY":
            warnings.append(
                "HIGH PRIORITY: Food is reported in IMMINENT DECAY. Immediate dispatch, cooking, "
                "or processing is critical to prevent total loss. Must be physically inspected before recipient acceptance."
            )
            requires_immediate = True
            notes = "Advanced maturity / imminent spoilage reported."

        elif norm == "RIPE":
            warnings.append(
                "HANDLING WARNING: Produce is reported as RIPE. Handle gently during loading and transit "
                "to prevent bruising and rapid degradation."
            )
            notes = "Ripe produce ready for immediate consumption or cooking."

        elif norm == "IMPERFECT":
            # Imperfect must not automatically mean unsafe
            notes = "Imperfect appearance represents cosmetic variation or sizing anomalies; safe for consumption."

        elif norm == "FAIR":
            warnings.append("Food is reported in FAIR condition. Priority consumption upon delivery recommended.")
            notes = "Fair condition with moderate shelf life remaining."

        elif norm == "GOOD":
            notes = "Standard commercial grade fresh condition."

        elif norm == "EXCELLENT":
            notes = "Pristine harvest or newly prepared condition."

        return {
            "condition": norm,
            "is_valid": True,
            "warnings": warnings,
            "requires_immediate_action": requires_immediate,
            "notes": notes,
        }
