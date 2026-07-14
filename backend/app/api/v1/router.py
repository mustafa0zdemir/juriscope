from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.contracts import router as contracts_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.upload import router as upload_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(upload_router)
api_v1_router.include_router(contracts_router)
