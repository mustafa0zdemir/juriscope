from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.contracts import router as contracts_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.search import router as search_router
from app.api.v1.endpoints.upload import router as upload_router
from app.api.v1.endpoints.conversations import router as conversations_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(upload_router)
api_v1_router.include_router(contracts_router)
api_v1_router.include_router(search_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(conversations_router)
