from typing import List, Dict, Any, Optional

VALID_STORAGE_CONDITIONS = {
    "AMBIENT",
    "REFRIGERATED",
    "FROZEN",
}


class StorageAssessor:
    """
    Deterministic storage condition assessor.
    Evaluates temperature control requirements and cold-chain compliance alerts.
    """

    @staticmethod
    def assess(storage_condition: Optional[str]) -> Dict[str, Any]:
        warnings: List[str] = []
        norm = (storage_condition or "").strip().upper()

        if not norm:
            warnings.append(
                "DATA QUALITY WARNING: Storage condition is unspecified. Cold-chain requirements must be "
                "verified before vehicle dispatch."
            )
            return {
                "storage_condition": "UNKNOWN",
                "is_valid": False,
                "requires_cold_chain": False,
                "warnings": warnings,
                "notes": "Missing storage environment specification.",
            }

        if norm not in VALID_STORAGE_CONDITIONS:
            warnings.append(f"Unrecognized storage condition '{norm}'. On-site inspection required.")
            return {
                "storage_condition": norm,
                "is_valid": False,
                "requires_cold_chain": False,
                "warnings": warnings,
                "notes": f"Unrecognized storage condition: {norm}",
            }

        requires_cold_chain = False
        notes = ""

        if norm == "REFRIGERATED":
            requires_cold_chain = True
            warnings.append(
                "COLD CHAIN REQUIRED: Must maintain refrigeration between 2°C and 8°C. "
                "Note: Supplier label alone does not verify uninterrupted temperature control."
            )
            notes = "Refrigerated perishable item requiring active temperature maintenance."

        elif norm == "FROZEN":
            requires_cold_chain = True
            warnings.append(
                "FREEZER CHAIN REQUIRED: Must remain frozen at or below -18°C. "
                "Do not refreeze if thawing occurs during transit."
            )
            notes = "Frozen item requiring insulated or sub-zero vehicle transport."

        elif norm == "AMBIENT":
            notes = "Ambient temperature storage. Protect from direct heat, sunlight, and moisture."

        return {
            "storage_condition": norm,
            "is_valid": True,
            "requires_cold_chain": requires_cold_chain,
            "warnings": warnings,
            "notes": notes,
        }
