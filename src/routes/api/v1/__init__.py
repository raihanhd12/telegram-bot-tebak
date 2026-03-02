"""
V1 Routes Module

This module contains all routes for API version 1.
"""

from fastapi import APIRouter

from .users import router as users_router
from .users_ws import router as users_ws_router

router = APIRouter(prefix="/v1")

# Include domain routers
router.include_router(users_router)
router.include_router(users_ws_router)

__all__ = ["router"]
