from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.suppliers import router as suppliers_router
from app.api.v1.receivers import router as receivers_router
from app.api.v1.surplus import router as surplus_router
from app.api.v1.demand import router as demand_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.geospatial import router as geospatial_router
from app.api.v1.matching import router as matching_router
from app.api.v1.optimization import router as optimization_router
from app.api.v1.agent import router as agent_router
from app.api.v1.transactions import router as transactions_router
from app.api.v1.verifications import router as verifications_router
from app.api.deps import require_role
from app.models.user import User
from fastapi import Depends

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(auth_router)
api_v1_router.include_router(suppliers_router)
api_v1_router.include_router(receivers_router)
api_v1_router.include_router(surplus_router)
api_v1_router.include_router(demand_router)
api_v1_router.include_router(intelligence_router)
api_v1_router.include_router(geospatial_router)
api_v1_router.include_router(matching_router)
api_v1_router.include_router(optimization_router)
api_v1_router.include_router(agent_router)
api_v1_router.include_router(transactions_router)
api_v1_router.include_router(verifications_router)


# RBAC test verification route for coordinators and admins
@api_v1_router.get(
    "/protected/coordinator-area",
    tags=["Authorization Verification"],
    summary="Coordinator & Admin protected endpoint",
)
def coordinator_area(
    current_user: User = Depends(require_role("COORDINATOR", "ADMIN")),
):
    return {
        "message": f"Welcome {current_user.email}, authorized as {current_user.role}.",
        "access": "GRANTED",
    }
