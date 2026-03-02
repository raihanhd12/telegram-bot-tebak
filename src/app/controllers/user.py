"""
User Controller

Handles all user CRUD operations.
"""

from typing import Any, Dict

from loguru import logger

import src.config.env as env
from src.app.controllers.base import BaseController
from src.app.schemas.user import UserCreate, UserResponse, UserUpdate
from src.app.services.user import UserService


class UserController(BaseController):
    """
    User Controller
    Handles HTTP requests for all User operations
    """

    def __init__(self):
        """Initialize controller with User service"""
        try:
            self.user_service = UserService()
            if env.DEVELOPMENT:
                logger.debug("✅ UserController initialized successfully")
        except Exception as e:
            logger.error(f"❌ Error initializing UserController: {e}")
            raise

    def create_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """
        Create a new user

        Args:
            user_data: UserCreate schema containing user information

        Returns:
            Standard API response with created user data
        """
        try:
            # Validate request
            self.validate_request_data(user_data, ["username", "email", "password"])

            # Create user through service
            user = self.user_service.create_user(user_data)

            if env.DEVELOPMENT:
                logger.debug("✅ User created successfully: %s", user.username)
            return self.success_response(
                data=UserResponse.model_validate(user),
                message="User created successfully",
                status_code=201,
            )

        except ValueError as e:
            # Map common validation/uniqueness errors to appropriate status codes
            msg = str(e)
            logger.warning(f"⚠️ Validation error: {msg}")
            if "already exists" in msg.lower():
                raise self.error_response(
                    message=msg, status_code=409, error_code="ALREADY_EXISTS"
                )
            else:
                raise self.error_response(
                    message=msg, status_code=400, error_code="VALIDATION_ERROR"
                )
        except Exception as e:
            # Let base controller handle generic errors
            raise self.handle_service_error(e, "Failed to create user")

    def get_user(self, user_id: int) -> Dict[str, Any]:
        """
        Get a user by ID

        Args:
            user_id: User ID

        Returns:
            Standard API response with user data
        """
        try:
            user = self.user_service.get_user(user_id)
            if not user:
                raise self.error_response(
                    message="User not found", status_code=404, error_code="NOT_FOUND"
                )

            return self.success_response(
                data=UserResponse.model_validate(user),
                message="User retrieved successfully",
            )

        except Exception as e:
            raise self.handle_service_error(e, "Failed to retrieve user")

    def get_users(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """
        Get list of users with pagination

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Standard API response with users list
        """
        try:
            users = self.user_service.get_users(skip=skip, limit=limit)
            users_response = [UserResponse.model_validate(user) for user in users]

            return self.success_response(
                data=users_response, message="Users retrieved successfully"
            )

        except Exception as e:
            raise self.handle_service_error(e, "Failed to retrieve users")

    def update_user(self, user_id: int, user_data: UserUpdate) -> Dict[str, Any]:
        """
        Update a user

        Args:
            user_id: User ID
            user_data: UserUpdate schema containing updated user information

        Returns:
            Standard API response with updated user data
        """
        try:
            user = self.user_service.update_user(user_id, user_data)
            if not user:
                raise self.error_response(
                    message="User not found", status_code=404, error_code="NOT_FOUND"
                )

            if env.DEVELOPMENT:
                logger.debug("✅ User updated successfully: %s", user.username)
            return self.success_response(
                data=UserResponse.model_validate(user),
                message="User updated successfully",
            )

        except ValueError as e:
            logger.warning(f"⚠️ Validation error: {e}")
            raise self.error_response(message=str(e), status_code=400)
        except Exception as e:
            raise self.handle_service_error(e, "Failed to update user")

    def delete_user(self, user_id: int) -> Dict[str, Any]:
        """
        Delete a user

        Args:
            user_id: User ID

        Returns:
            Standard API response confirming deletion
        """
        try:
            success = self.user_service.delete_user(user_id)
            if not success:
                raise self.error_response(
                    message="User not found", status_code=404, error_code="NOT_FOUND"
                )

            if env.DEVELOPMENT:
                logger.debug("✅ User deleted successfully: ID %s", user_id)
            return self.success_response(
                data={"deleted_user_id": user_id}, message="User deleted successfully"
            )
        except Exception as e:
            raise self.handle_service_error(e, "Failed to delete user")
