"""
Main API router combining all endpoints.
"""
from fastapi import APIRouter
from backend.api import chat, models, rag, config

api_router = APIRouter()

api_router.include_router(chat.router)
api_router.include_router(models.router)
api_router.include_router(rag.router)
api_router.include_router(config.router)

