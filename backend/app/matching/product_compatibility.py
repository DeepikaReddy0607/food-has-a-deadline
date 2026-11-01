import re
from typing import Optional, List, Dict, Any, Set
from app.matching.models import ProductCompatibilityResult, ProductMatchLevel

# Hierarchy ranking for food conditions
CONDITION_RANKS: Dict[str, float] = {
    "EXCELLENT": 3.0,
    "GOOD": 2.0,
    "IMPERFECT": 2.0,
    "RIPE": 1.5,
    "FAIR": 1.0,
    "IMMINENT_DECAY": 0.5,
    "ANY": 0.0,
}

# Common commercial and quality descriptor modifiers to ignore when finding core commodity noun
DESCRIPTIVE_MODIFIERS: Set[str] = {
    "fresh",
    "organic",
    "crisp",
    "ripe",
    "raw",
    "local",
    "premium",
    "farm",
    "natural",
    "whole",
    "sliced",
    "chopped",
}

# Naturally vegan / vegetarian categories
PLANT_BASED_CATEGORIES: Set[str] = {"FRUITS", "VEGETABLES", "GRAINS"}
VEGETARIAN_CATEGORIES: Set[str] = {"FRUITS", "VEGETABLES", "GRAINS", "DAIRY", "BAKERY"}


class ProductCompatibilityEvaluator:
    """
    Deterministic evaluator for product and dietary compatibility between
    a SurplusListing and a DemandRequest.
    """

    @classmethod
    def evaluate(
        cls,
        surplus_category: str,
        surplus_item_name: str,
        surplus_condition: str,
        surplus_description: Optional[str],
        demand_category: str,
        demand_item_name: Optional[str],
        acceptable_condition: Optional[str],
        dietary_requirements: Optional[List[str]],
    ) -> ProductCompatibilityResult:
        warnings: List[str] = []
        dietary_flags: List[str] = []
        notes_parts: List[str] = []

        norm_s_cat = surplus_category.strip().upper()
        norm_d_cat = demand_category.strip().upper()
        norm_s_item = surplus_item_name.strip().lower()
        norm_d_item = (demand_item_name or "").strip().lower()

        # 1. Category Compatibility
        category_match = False
        if norm_d_cat in ("ANY", "ALL"):
            category_match = True
            notes_parts.append(f"Category '{norm_s_cat}' accepted by universal demand '{norm_d_cat}'.")
        elif norm_s_cat == norm_d_cat:
            category_match = True
            notes_parts.append(f"Direct category match: '{norm_s_cat}'.")
        else:
            category_match = False
            notes_parts.append(f"Category mismatch: surplus is '{norm_s_cat}', demand requested '{norm_d_cat}'.")

        # 2. Item Name Compatibility
        item_match: Optional[bool] = None
        match_level: ProductMatchLevel

        if not category_match:
            match_level = "INCOMPATIBLE"
            item_match = False
        elif not norm_d_item or norm_d_item in ("any", "all", ""):
            # Demand did not specify an item name, open to all items in category
            match_level = "CATEGORY_COMPATIBLE"
            item_match = True
            notes_parts.append(f"Generic category demand satisfies '{surplus_item_name}'.")
        elif norm_d_item == norm_s_item:
            match_level = "EXACT"
            item_match = True
            notes_parts.append(f"Exact item name match: '{surplus_item_name}'.")
        elif norm_d_item in norm_s_item or norm_s_item in norm_d_item:
            match_level = "SUBSET_COMPATIBLE"
            item_match = True
            notes_parts.append(f"Sub-string item match between '{surplus_item_name}' and '{demand_item_name}'.")
        else:
            # Check core commodity tokens excluding descriptive modifiers
            s_words = {w for w in re.findall(r"\w+", norm_s_item) if len(w) > 2 and w not in DESCRIPTIVE_MODIFIERS}
            d_words = {w for w in re.findall(r"\w+", norm_d_item) if len(w) > 2 and w not in DESCRIPTIVE_MODIFIERS}
            shared_core = s_words & d_words

            if shared_core:
                match_level = "SUBSET_COMPATIBLE"
                item_match = True
                notes_parts.append(
                    f"Core commodity match on {', '.join(sorted(shared_core))} between '{surplus_item_name}' and '{demand_item_name}'."
                )
            else:
                # Different specific items within the same category
                match_level = "AMBIGUOUS"
                item_match = False
                warnings.append(
                    f"REVIEW REQUIRED: Demand specifically requested '{demand_item_name}', but surplus offers '{surplus_item_name}'. "
                    "Human coordinator verification recommended before allocation."
                )
                notes_parts.append(f"Specific item disparity: '{surplus_item_name}' vs '{demand_item_name}'.")

        # 3. Dietary Requirements Check
        dietary_compatible = True
        requirements = [r.strip().upper() for r in (dietary_requirements or [])]
        combined_text = f"{norm_s_item} {(surplus_description or '').lower()}"

        for req in requirements:
            if req == "VEGETARIAN":
                if norm_s_cat not in VEGETARIAN_CATEGORIES:
                    dietary_compatible = False
                    dietary_flags.append(f"VIOLATION: Non-vegetarian category '{norm_s_cat}'.")
            elif req == "VEGAN":
                if norm_s_cat not in PLANT_BASED_CATEGORIES:
                    if norm_s_cat == "DAIRY":
                        dietary_compatible = False
                        dietary_flags.append("VIOLATION: Dairy product violates vegan requirement.")
                    elif norm_s_cat in ("BAKERY", "COOKED_FOOD"):
                        if "vegan" not in combined_text:
                            warnings.append(f"DIETARY AMBIGUITY: '{surplus_item_name}' ({norm_s_cat}) not verified vegan.")
                            if match_level != "INCOMPATIBLE":
                                match_level = "AMBIGUOUS"
                    else:
                        dietary_compatible = False
                        dietary_flags.append(f"VIOLATION: Category '{norm_s_cat}' violates vegan requirement.")
            elif req == "DAIRY_FREE":
                if norm_s_cat == "DAIRY" or "milk" in combined_text or "cheese" in combined_text or "butter" in combined_text:
                    dietary_compatible = False
                    dietary_flags.append("VIOLATION: Item contains or is categorized under dairy.")
            elif req == "GLUTEN_FREE":
                if norm_s_cat in ("BAKERY", "GRAINS") and "gluten-free" not in combined_text and "gluten free" not in combined_text:
                    warnings.append(f"GLUTEN WARNING: '{surplus_item_name}' ({norm_s_cat}) lacks explicit gluten-free declaration.")
                    if match_level != "INCOMPATIBLE":
                        match_level = "AMBIGUOUS"
            elif req in ("HALAL", "KOSHER"):
                if norm_s_cat in ("COOKED_FOOD", "OTHER") and req.lower() not in combined_text:
                    warnings.append(f"CERTIFICATION WARNING: '{surplus_item_name}' does not confirm {req} certification.")
                    if match_level != "INCOMPATIBLE":
                        match_level = "AMBIGUOUS"

        if not dietary_compatible:
            warnings.extend(dietary_flags)
            notes_parts.append(f"Dietary restriction failure: {', '.join(dietary_flags)}")

        # 4. Condition Compatibility
        condition_compatible = True
        acc_cond = (acceptable_condition or "FAIR").strip().upper()
        s_cond = (surplus_condition or "GOOD").strip().upper()

        acc_rank = CONDITION_RANKS.get(acc_cond, 1.0)
        s_rank = CONDITION_RANKS.get(s_cond, 2.0)

        if s_rank < acc_rank:
            condition_compatible = False
            warnings.append(
                f"CONDITION INCOMPATIBLE: Food condition '{s_cond}' (rank {s_rank}) falls below "
                f"receiver acceptable threshold '{acc_cond}' (rank {acc_rank})."
            )
            notes_parts.append(f"Condition unacceptable: {s_cond} < {acc_cond}.")
        else:
            notes_parts.append(f"Condition '{s_cond}' satisfies '{acc_cond}'.")

        # Overall boolean compatibility
        is_comp = category_match and dietary_compatible and condition_compatible and match_level != "INCOMPATIBLE"

        return ProductCompatibilityResult(
            match_level=match_level,
            is_compatible=is_comp,
            category_match=category_match,
            item_match=item_match,
            dietary_compatible=dietary_compatible,
            condition_compatible=condition_compatible,
            dietary_flags=dietary_flags,
            warnings=warnings,
            notes="; ".join(notes_parts),
        )
