"""
Main API router combining all endpoints.
"""
from fastapi import APIRouter
from backend.api import chat, models, rag, config, database, vendor, cache, admin, auth, vendor_api

api_router = APIRouter()

# Authentication routes (public)
api_router.include_router(auth.router)

# Admin routes (super admin only)
api_router.include_router(admin.router)

# Vendor-specific API routes (for separate frontend integration)
api_router.include_router(vendor_api.router)

# Public/vendor routes
api_router.include_router(chat.router)
api_router.include_router(models.router)
api_router.include_router(rag.router)
api_router.include_router(config.router)
api_router.include_router(database.router)
api_router.include_router(vendor.router)
api_router.include_router(cache.router)

