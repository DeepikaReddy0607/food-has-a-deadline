from typing import Dict, Any, List, Set


class ToolRegistry:
    """
    Central registry for all deterministic backend tools callable by the AI Agent.
    Defines schemas, parameter types, documentation, and RBAC authorization boundaries.
    """

    TOOLS_METADATA: Dict[str, Dict[str, Any]] = {
        "get_available_surplus": {
            "name": "get_available_surplus",
            "description": "Queries active supplier surplus food batches currently available in the network with remaining quantities and expiration deadlines.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "category": {
                        "type": "STRING",
                        "description": "Optional category filter: FRUITS, VEGETABLES, GRAINS, DAIRY, BAKERY, COOKED_FOOD, MEAT, OTHER.",
                    },
                    "max_remaining_hours": {
                        "type": "NUMBER",
                        "description": "Optional maximum remaining shelf life in hours.",
                    },
                    "limit": {
                        "type": "INTEGER",
                        "description": "Maximum number of listings to return (default 20, max 100).",
                    },
                },
            },
            "allowed_roles": {"SUPPLIER", "COORDINATOR", "ADMIN"},
        },
        "get_active_demand": {
            "name": "get_active_demand",
            "description": "Queries active receiver food demand requests currently open in the network.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "category": {
                        "type": "STRING",
                        "description": "Optional category filter.",
                    },
                    "min_priority": {
                        "type": "INTEGER",
                        "description": "Optional minimum receiver priority level (1 to 5).",
                    },
                    "limit": {
                        "type": "INTEGER",
                        "description": "Maximum number of demand requests to return (default 20, max 100).",
                    },
                },
            },
            "allowed_roles": {"RECEIVER", "COORDINATOR", "ADMIN"},
        },
        "calculate_urgency": {
            "name": "calculate_urgency",
            "description": "Calculates deterministic perishability decay, effective usable hours, and urgency classification using empirical baselines (Module 5).",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "estimated_deadline": {
                        "type": "STRING",
                        "description": "ISO 8601 expiration timestamp (required).",
                    },
                    "storage_condition": {
                        "type": "STRING",
                        "description": "Storage condition: AMBIENT, REFRIGERATED, or FROZEN.",
                    },
                    "food_condition": {
                        "type": "STRING",
                        "description": "Physical condition: EXCELLENT, GOOD, FAIR, RIPE, IMMINENT_DECAY, IMPERFECT.",
                    },
                    "harvest_or_prep_date": {
                        "type": "STRING",
                        "description": "Optional ISO 8601 harvest or preparation timestamp.",
                    },
                },
                "required": ["estimated_deadline", "storage_condition", "food_condition"],
            },
            "allowed_roles": {"SUPPLIER", "RECEIVER", "COORDINATOR", "ADMIN"},
        },
        "find_compatible_receivers": {
            "name": "find_compatible_receivers",
            "description": "Evaluates multi-factor compatibility (dietary, cold chain, geospatial, quantity) between a surplus batch and candidate receivers (Module 7).",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "listing_id": {
                        "type": "STRING",
                        "description": "UUID of the surplus listing to evaluate.",
                    },
                    "include_ineligible": {
                        "type": "BOOLEAN",
                        "description": "Whether to include disqualified candidates with explicit rejection reasons (default false).",
                    },
                },
                "required": ["listing_id"],
            },
            "allowed_roles": {"SUPPLIER", "COORDINATOR", "ADMIN"},
        },
        "find_compatible_surplus": {
            "name": "find_compatible_surplus",
            "description": "Evaluates multi-factor compatibility between a receiver demand request and available surplus inventory (Module 7).",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "demand_id": {
                        "type": "STRING",
                        "description": "UUID of the demand request to evaluate.",
                    },
                    "include_ineligible": {
                        "type": "BOOLEAN",
                        "description": "Whether to include disqualified candidates with rejection reasons (default false).",
                    },
                },
                "required": ["demand_id"],
            },
            "allowed_roles": {"RECEIVER", "COORDINATOR", "ADMIN"},
        },
        "calculate_route": {
            "name": "calculate_route",
            "description": "Queries driving road distance and transit duration between facility coordinates with automatic Haversine fallback (Module 6).",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "supplier_lat": {
                        "type": "NUMBER",
                        "description": "Origin supplier latitude (-90 to 90).",
                    },
                    "supplier_lon": {
                        "type": "NUMBER",
                        "description": "Origin supplier longitude (-180 to 180).",
                    },
                    "receiver_lat": {
                        "type": "NUMBER",
                        "description": "Destination receiver latitude (-90 to 90).",
                    },
                    "receiver_lon": {
                        "type": "NUMBER",
                        "description": "Destination receiver longitude (-180 to 180).",
                    },
                    "usable_deadline": {
                        "type": "STRING",
                        "description": "Optional ISO 8601 deadline to check temporal transit feasibility.",
                    },
                },
                "required": ["supplier_lat", "supplier_lon", "receiver_lat", "receiver_lon"],
            },
            "allowed_roles": {"SUPPLIER", "RECEIVER", "COORDINATOR", "ADMIN"},
        },
        "run_allocation_optimizer": {
            "name": "run_allocation_optimizer",
            "description": "Executes Google OR-Tools CP-SAT constrained optimization across active supply and demand to generate a redistribution proposal (Module 8).",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "surplus_listing_ids": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Optional subset of surplus listing UUIDs.",
                    },
                    "demand_request_ids": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Optional subset of demand request UUIDs.",
                    },
                    "timeout_seconds": {
                        "type": "NUMBER",
                        "description": "Solver execution timeout (default 5.0).",
                    },
                    "max_distance_km": {
                        "type": "NUMBER",
                        "description": "Optional maximum road distance threshold.",
                    },
                },
            },
            "allowed_roles": {"COORDINATOR", "ADMIN"},
        },
        "explain_allocation": {
            "name": "explain_allocation",
            "description": "Analyzes an allocation proposal, explaining urgency prioritization and diagnostic causes for any unmet demands.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "proposal_id": {
                        "type": "STRING",
                        "description": "UUID of the allocation proposal to explain.",
                    },
                },
                "required": ["proposal_id"],
            },
            "allowed_roles": {"COORDINATOR", "ADMIN"},
        },
        "get_allocation_proposal": {
            "name": "get_allocation_proposal",
            "description": "Retrieves the stored line items, solver status, and metrics of an existing allocation proposal by ID.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "proposal_id": {
                        "type": "STRING",
                        "description": "UUID of the stored proposal.",
                    },
                },
                "required": ["proposal_id"],
            },
            "allowed_roles": {"COORDINATOR", "ADMIN"},
        },
        "prepare_redistribution_proposal": {
            "name": "prepare_redistribution_proposal",
            "description": "Generates a draft allocation proposal for human coordinator authorization. Does NOT execute or commit redistribution.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "surplus_listing_ids": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Optional subset of surplus listings.",
                    },
                    "demand_request_ids": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Optional subset of demands.",
                    },
                    "timeout_seconds": {
                        "type": "NUMBER",
                        "description": "Optimization timeout (default 5.0).",
                    },
                },
            },
            "allowed_roles": {"COORDINATOR", "ADMIN"},
        },
    }

    @classmethod
    def get_tool_metadata(cls, tool_name: str) -> Dict[str, Any]:
        return cls.TOOLS_METADATA.get(tool_name, {})

    @classmethod
    def get_all_tool_names(cls) -> List[str]:
        return list(cls.TOOLS_METADATA.keys())

    @classmethod
    def get_declarations_for_role(cls, role: str) -> List[Dict[str, Any]]:
        """
        Filters tool declarations to only those authorized for the specified role.
        """
        declarations = []
        for name, meta in cls.TOOLS_METADATA.items():
            if role in meta["allowed_roles"]:
                declarations.append({
                    "name": meta["name"],
                    "description": meta["description"],
                    "parameters": meta["parameters"],
                })
        return declarations

    @classmethod
    def is_authorized(cls, tool_name: str, role: str) -> bool:
        meta = cls.TOOLS_METADATA.get(tool_name)
        if not meta:
            return False
        return role in meta["allowed_roles"]
