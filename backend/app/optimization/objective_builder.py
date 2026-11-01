import uuid
from typing import Dict, Tuple, Optional
from ortools.sat.python import cp_model

from app.optimization.allocation_problem import AllocationProblem, EligibleEdge


class ObjectiveBuilder:
    """
    Constructs a weighted multi-component integer objective function for CP-SAT.
    Prioritizes:
      1. Maximizing total food salvaged (base salvage reward).
      2. Urgency: salvaging near-deadline food first (CRITICAL > HIGH > MODERATE > LOW).
      3. Receiver priority: fulfilling vulnerable/high-capacity community facilities.
      4. Estimated delivery-time margin: rewarding deliveries with comfortable buffer.
      5. Minimizing transit waste: penalizing excessive road distance.
    """

    # Urgency bonus per unit
    URGENCY_WEIGHTS = {
        "CRITICAL": 500,
        "HIGH": 300,
        "MODERATE": 150,
        "LOW": 50,
    }

    # Receiver priority multiplier (Priority 1..5 -> 50..250 points)
    PRIORITY_MULTIPLIER = 50

    # Base reward ensuring maximizing food volume strictly dominates all secondary preferences
    # Secondary weights span [-400, +850]; BASE_SALVAGE_REWARD >> 1250 ensures lexicographic priority
    BASE_SALVAGE_REWARD = 100_000

    # Distance penalty: 5 points per road km (capped at 500 points)
    DISTANCE_PENALTY_PER_KM = 5
    MAX_DISTANCE_PENALTY = 500

    # Slack bonus: 1 point per 10 minutes of shelf life margin (capped at 100 points)
    SLACK_BONUS_PER_10_MINS = 1
    MAX_SLACK_BONUS = 100

    @classmethod
    def calculate_unit_coefficient(cls, edge: EligibleEdge, base_reward: Optional[int] = None) -> int:
        """
        Computes the integer objective coefficient C_sr for one unit of flow (hundredths of a kg).
        Uses base_reward if provided, otherwise defaults to BASE_SALVAGE_REWARD.
        """
        # 1. Base salvage reward
        coeff = cls.BASE_SALVAGE_REWARD if base_reward is None else base_reward

        # 2. Urgency bonus
        coeff += cls.URGENCY_WEIGHTS.get(edge.urgency, 100)

        # 3. Receiver priority bonus
        priority = max(1, min(5, edge.receiver_priority))
        coeff += priority * cls.PRIORITY_MULTIPLIER

        # 4. Shelf-life slack bonus
        if edge.shelf_life_slack_minutes > 0:
            slack_pts = int(edge.shelf_life_slack_minutes / 10.0) * cls.SLACK_BONUS_PER_10_MINS
            coeff += min(cls.MAX_SLACK_BONUS, slack_pts)

        # 5. Distance penalty
        dist_penalty = int(edge.road_distance_km * cls.DISTANCE_PENALTY_PER_KM)
        coeff -= min(cls.MAX_DISTANCE_PENALTY, dist_penalty)

        return coeff

    @classmethod
    def build_objective(
        cls,
        model: cp_model.CpModel,
        problem: AllocationProblem,
        flow_vars: Dict[Tuple[uuid.UUID, uuid.UUID], cp_model.IntVar],
    ) -> None:
        """
        Sets model.Maximize with linear terms sum(C_sr * x_sr).
        Enforces a mathematically dominant base salvage reward scaled to the maximum possible
        problem volume, guaranteeing true lexicographic hierarchy:
        1 unit (0.01 kg) of extra volume strictly dominates all cumulative secondary preferences.
        """
        # Calculate maximum possible volume across the entire problem (in hundredths of a kg)
        max_possible_volume = min(
            sum(s.available_hundredths_kg for s in problem.surplus_nodes.values()) if problem.surplus_nodes else 0,
            sum(d.requested_hundredths_kg for d in problem.demand_nodes.values()) if problem.demand_nodes else 0,
        )

        # Secondary bonuses/penalties span from -400 to +850 per unit (a range of 1,250 points).
        # To strictly guarantee that maximizing total food volume dominates ALL secondary preferences
        # (i.e. 1 unit = 0.01 kg extra food always outweighs the worst-case cumulative secondary score),
        # the base salvage reward must satisfy: base_salvage_reward > 1,250 * max_possible_volume.
        # We enforce a safe dominant base reward of 2,000 * max_possible_volume + 100,000.
        dominant_base_reward = max(cls.BASE_SALVAGE_REWARD, 2_000 * max_possible_volume + 100_000)

        objective_terms = []
        for key, var in flow_vars.items():
            edge = problem.eligible_edges[key]
            unit_coeff = cls.calculate_unit_coefficient(edge, base_reward=dominant_base_reward)
            objective_terms.append(unit_coeff * var)

        if objective_terms:
            model.Maximize(sum(objective_terms))
        else:
            model.Maximize(0)
