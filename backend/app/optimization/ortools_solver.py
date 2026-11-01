import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional
from ortools.sat.python import cp_model

from app.optimization.allocation_problem import AllocationProblem, to_kg
from app.optimization.constraint_builder import ConstraintBuilder
from app.optimization.objective_builder import ObjectiveBuilder


@dataclass
class SolverResult:
    status: str  # OPTIMAL | FEASIBLE | INFEASIBLE | MODEL_INVALID | TIMEOUT
    solve_time_ms: float
    objective_value: Optional[float]
    allocations_kg: Dict[Tuple[uuid.UUID, uuid.UUID], float] = field(default_factory=dict)
    num_variables: int = 0
    num_constraints: int = 0


class OrtoolsSolver:
    """
    Executes Google OR-Tools CP-SAT solver against an AllocationProblem.
    Enforces deterministic timeout limits, deterministic multithreading,
    and extracts solved integer flows into decimal kilogram allocations.
    """

    @classmethod
    def solve(
        cls,
        problem: AllocationProblem,
        timeout_seconds: float = 5.0,
        random_seed: int = 42,
    ) -> SolverResult:
        model = cp_model.CpModel()

        # Build decision variables and conservation constraints
        flow_vars, constraint_count = ConstraintBuilder.build_variables_and_constraints(
            model=model,
            problem=problem,
        )

        # Build weighted integer objective
        ObjectiveBuilder.build_objective(
            model=model,
            problem=problem,
            flow_vars=flow_vars,
        )

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = float(timeout_seconds)
        solver.parameters.random_seed = random_seed
        solver.parameters.num_workers = 1  # Guaranteed deterministic solution trajectory

        start_time = time.perf_counter()
        raw_status = solver.Solve(model)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        status_mapping = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            cp_model.MODEL_INVALID: "MODEL_INVALID",
            cp_model.UNKNOWN: "UNKNOWN",
        }
        status_str = status_mapping.get(raw_status, "UNKNOWN")

        allocations_kg: Dict[Tuple[uuid.UUID, uuid.UUID], float] = {}
        obj_val: Optional[float] = None

        if raw_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            obj_val = float(solver.ObjectiveValue())
            for key, var in flow_vars.items():
                val_centigrams = solver.Value(var)
                if val_centigrams > 0:
                    allocations_kg[key] = to_kg(val_centigrams)

        return SolverResult(
            status=status_str,
            solve_time_ms=elapsed_ms,
            objective_value=obj_val,
            allocations_kg=allocations_kg,
            num_variables=len(flow_vars),
            num_constraints=constraint_count,
        )
