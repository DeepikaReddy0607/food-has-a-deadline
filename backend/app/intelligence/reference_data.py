"""
Credible external reference data and empirical baselines for perishable food redistribution.

References documented:
1. USDA FoodKeeper Database (U.S. Department of Agriculture, Food Safety and Inspection Service)
   - Scope: Guidelines on storage life for refrigerated, frozen, and pantry foods.
   - URL: https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation/food-safety-basics/foodkeeper-app
   - Accessed: October 2026
   - Limitations: Shelf-life estimates assume optimal continuous storage conditions; real-world commercial surplus may experience temperature variations.

2. FDA Food Code 2022 (U.S. Food and Drug Administration)
   - Scope: Temperature Control for Safety (TCS) foods and time-temperature control thresholds.
   - Maximum holding times: 7 days for prepared refrigerated TCS foods held at 5°C (41°F) or below.
   - URL: https://www.fda.gov/food/fda-food-code/food-code-2022
   - Accessed: October 2026
   - Limitations: Designed for institutional and commercial kitchens; physical verification required.

3. WRAP UK Food Waste Reduction Roadmap & Date Labeling Guidance
   - Scope: Redistributing surplus food approaching Best Before and Use By dates safely.
   - URL: https://wrap.org.uk/resources/guide/surplus-food-redistribution-labelling-guidance
   - Accessed: October 2026
   - Limitations: Emphasizes that "Best Before" reflects sensory quality rather than microbiology, whereas "Use By" is a hard safety limit.
"""

from typing import Dict, Any

FOOD_SAFETY_DISCLAIMER: str = (
    "FOOD SAFETY DISCLAIMER: This platform provides operational urgency intelligence for logistics prioritization. "
    "It does NOT certify food as safe, detect microbial contamination, guarantee shelf life, replace statutory "
    "food safety inspections, or guarantee the accuracy of supplier-reported conditions. Receiving organizations "
    "must physically inspect all food upon handover."
)

REFERENCE_SOURCES: Dict[str, Dict[str, Any]] = {
    "USDA_FOODKEEPER": {
        "title": "USDA FoodKeeper Guidance",
        "publisher": "U.S. Department of Agriculture (FSIS)",
        "url": "https://www.fsis.usda.gov/food-safety/safe-food-handling-and-preparation/food-safety-basics/foodkeeper-app",
        "last_accessed": "2026-10",
        "key_principle": "Provides baseline shelf-life ranges across ambient, refrigerated, and frozen storage under uninterrupted cold-chain conditions.",
    },
    "FDA_FOOD_CODE": {
        "title": "FDA Food Code 2022 — Temperature Control for Safety",
        "publisher": "U.S. Food and Drug Administration",
        "url": "https://www.fda.gov/food/fda-food-code/food-code-2022",
        "last_accessed": "2026-10",
        "key_principle": "Mandates temperature thresholds (<= 5°C for refrigeration, <= -18°C for freezing) and strict time windows for TCS foods.",
    },
    "WRAP_UK": {
        "title": "WRAP Surplus Food Redistribution Date Labeling Guidance",
        "publisher": "Waste and Resources Action Programme (UK)",
        "url": "https://wrap.org.uk/resources/guide/surplus-food-redistribution-labelling-guidance",
        "last_accessed": "2026-10",
        "key_principle": "Distinguishes between safety cut-offs and visual quality; encourages redistribution before degradation occurs.",
    },
}

FOOD_CATEGORY_GUIDELINES: Dict[str, Dict[str, Any]] = {
    "FRUITS": {
        "typical_storage": "AMBIENT / REFRIGERATED",
        "sensitivity": "Ethylene production and mechanical damage accelerate decay; ripe produce requires priority handling.",
        "source": "USDA_FOODKEEPER",
    },
    "VEGETABLES": {
        "typical_storage": "REFRIGERATED",
        "sensitivity": "Moisture loss, wilting, and chilling injury risks; requires controlled humidity and cool temperatures.",
        "source": "USDA_FOODKEEPER",
    },
    "GRAINS": {
        "typical_storage": "AMBIENT",
        "sensitivity": "Moisture and pest susceptibility; relatively stable shelf life under dry ambient conditions.",
        "source": "USDA_FOODKEEPER",
    },
    "DAIRY": {
        "typical_storage": "REFRIGERATED",
        "sensitivity": "Strict cold chain required (<= 4°C). Highly perishable once broken; prompt redistribution required.",
        "source": "FDA_FOOD_CODE",
    },
    "BAKERY": {
        "typical_storage": "AMBIENT / FROZEN",
        "sensitivity": "Starch retrogradation (staling) and mold growth; freezing halts staling but ambient items decay within 2-4 days.",
        "source": "USDA_FOODKEEPER",
    },
    "COOKED_FOOD": {
        "typical_storage": "REFRIGERATED / FROZEN",
        "sensitivity": "High risk TCS food. Strict 2-hour ambient cut-off during cooling; 3-4 days maximum refrigeration life.",
        "source": "FDA_FOOD_CODE",
    },
    "OTHER": {
        "typical_storage": "VARIABLE",
        "sensitivity": "Depends on specific product; supplier-declared usable deadline is the authoritative limit.",
        "source": "WRAP_UK",
    },
}
