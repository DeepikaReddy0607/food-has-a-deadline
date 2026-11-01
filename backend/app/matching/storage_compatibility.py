from typing import Optional, Dict, Any, List
from app.matching.models import StorageCompatibilityResult, StorageMatchLevel


class StorageCompatibilityEvaluator:
    """
    Deterministic evaluator for cold chain and storage requirement compatibility.
    Checks whether a receiving facility possesses the necessary physical cooling/freezing
    hardware to hold incoming surplus inventory safely.
    """

    @classmethod
    def evaluate(
        cls,
        surplus_storage: str,
        demand_storage: str,
        receiver_cold_storage: Optional[Dict[str, Any]] = None,
    ) -> StorageCompatibilityResult:
        warnings: List[str] = []
        norm_s = (surplus_storage or "").strip().upper()
        norm_d = (demand_storage or "").strip().upper()
        cold_capabilities = receiver_cold_storage or {}

        has_refrig = bool(cold_capabilities.get("refrigeration", False)) or norm_d in ("REFRIGERATED", "FROZEN")
        has_freezer = bool(cold_capabilities.get("freezer", False)) or norm_d == "FROZEN"

        match_level: StorageMatchLevel
        is_compatible: bool
        notes: str

        if not norm_s:
            match_level = "UNKNOWN"
            is_compatible = False
            warnings.append("Surplus listing storage condition is missing or unspecified.")
            notes = "Storage requirement indeterminate."
        elif norm_s == "AMBIENT":
            match_level = "COMPATIBLE"
            is_compatible = True
            notes = "Ambient surplus requires standard non-chilled storage, supported by all facilities."
        elif norm_s == "REFRIGERATED":
            if has_refrig:
                match_level = "COMPATIBLE"
                is_compatible = True
                notes = "Receiver provides active refrigeration storage (2°C - 8°C)."
            else:
                match_level = "INCOMPATIBLE"
                is_compatible = False
                warnings.append(
                    "COLD CHAIN FAILURE: Surplus requires refrigeration, but receiver profile lacks active refrigeration equipment."
                )
                notes = "Receiver incapable of maintaining refrigerated cold chain."
        elif norm_s == "FROZEN":
            if has_freezer:
                match_level = "COMPATIBLE"
                is_compatible = True
                notes = "Receiver possesses dedicated deep freeze storage (below -18°C)."
            else:
                match_level = "INCOMPATIBLE"
                is_compatible = False
                warnings.append(
                    "FREEZER DEFICIT: Surplus requires deep freezing, but receiver facility has no freezer equipment."
                )
                notes = "Receiver incapable of storing frozen inventory without thawing."
        else:
            match_level = "UNKNOWN"
            is_compatible = False
            warnings.append(f"Unrecognized storage requirement '{norm_s}'.")
            notes = f"Unsupported storage classification: {norm_s}."

        return StorageCompatibilityResult(
            match_level=match_level,
            is_compatible=is_compatible,
            required_storage=norm_s or "UNKNOWN",
            available_storage=norm_d or ("REFRIGERATED/FREEZER" if (has_refrig or has_freezer) else "AMBIENT"),
            receiver_has_cold_chain=(has_refrig or has_freezer),
            warnings=warnings,
            notes=notes,
        )
