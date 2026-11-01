import uuid
from typing import Dict, Tuple
from ortools.sat.python import cp_model

from app.optimization.allocation_problem import AllocationProblem, EligibleEdge


class ConstraintBuilder:
    """
    Builds CP-SAT decision variables and mandatory hard conservation constraints.
    Guarantees:
      1. Supply Conservation: sum_r x_{sr} <= Q_s
      2. Demand Conservation: sum_s x_{sr} <= D_r
      3. Non-negativity and upper bounds: 0 <= x_{sr} <= min(Q_s, D_r)
      4. Eligibility Gating: decision variables exist strictly for ELIGIBLE pairs.
    """

    @classmethod
    def build_variables_and_constraints(
        cls,
        model: cp_model.CpModel,
        problem: AllocationProblem,
    ) -> Tuple[Dict[Tuple[uuid.UUID, uuid.UUID], cp_model.IntVar], int]:
        """
        Creates integer flow variables and registers all linear conservation constraints.
        Returns:
            flow_vars: map from (surplus_id, demand_id) to CP-SAT IntVar.
            constraint_count: total number of hard constraints added to the model.
        """
        flow_vars: Dict[Tuple[uuid.UUID, uuid.UUID], cp_model.IntVar] = {}
        constraint_count = 0

        # 1. Create Decision Variables for Eligible Edges
        for (s_id, d_id), edge in problem.eligible_edges.items():
            var_name = f"flow_{str(s_id)[:8]}_{str(d_id)[:8]}"
            var = model.NewIntVar(0, edge.max_flow_hundredths_kg, var_name)
            flow_vars[(s_id, d_id)] = var

        # 2. Supply Conservation Constraint for every surplus listing
        for s_id, s_node in problem.surplus_nodes.items():
            incident_edges = problem.get_edges_for_surplus(s_id)
            if incident_edges:
                incident_vars = [flow_vars[(s_id, e.demand_id)] for e in incident_edges]
                model.Add(sum(incident_vars) <= s_node.available_hundredths_kg)
                constraint_count += 1

        # 3. Demand Conservation Constraint for every demand request
        for d_id, d_node in problem.demand_nodes.items():
            incident_edges = problem.get_edges_for_demand(d_id)
            if incident_edges:
                incident_vars = [flow_vars[(e.surplus_id, d_id)] for e in incident_edges]
                model.Add(sum(incident_vars) <= d_node.requested_hundredths_kg)
                constraint_count += 1

        return flow_vars, constraint_count
