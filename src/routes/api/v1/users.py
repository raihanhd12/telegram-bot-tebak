"""
User API Routes (Version 1)

RESTful API endpoints for user management.
"""

from fastapi import APIRouter, Depends, Query

from src.app.controllers.user import UserController
from src.app.schemas.user import UserCreate, UserUpdate
from src.config.security import validate_api_key

router = APIRouter(prefix="/users", tags=["users"])

# Initialize controller
user_controller = UserController()


@router.post("/", summary="Create a new user")
async def create_user(
    user_data: UserCreate,
    _api_key: str = Depends(validate_api_key),
):
    """
    Create a new user with the provided information

    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Password (min 8 characters)
    - **full_name**: Optional full name
    """
    return user_controller.create_user(user_data)


@router.get("/{user_id}", summary="Get user by ID")
async def get_user(
    user_id: int,
    _api_key: str = Depends(validate_api_key),
):
    """
    Retrieve a specific user by their ID
    """
    return user_controller.get_user(user_id)


@router.get("/", summary="Get list of users")
async def get_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    _api_key: str = Depends(validate_api_key),
):
    """
    Retrieve a paginated list of users

    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (1-1000)
    """
    return user_controller.get_users(skip=skip, limit=limit)


@router.put("/{user_id}", summary="Update user")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    _api_key: str = Depends(validate_api_key),
):
    """
    Update an existing user with the provided information

    - **username**: Updated username (optional)
    - **email**: Updated email address (optional)
    - **full_name**: Updated full name (optional)
    - **is_active**: Updated active status (optional)
    """
    return user_controller.update_user(user_id, user_data)


@router.delete("/{user_id}", summary="Delete user")
async def delete_user(
    user_id: int,
    _api_key: str = Depends(validate_api_key),
):
    """
    Delete a user by their ID
    """
    return user_controller.delete_user(user_id)
