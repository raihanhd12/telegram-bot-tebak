"""
Game service validators

Validation logic for game operations.
"""
import re
from datetime import datetime, timezone
from typing import Optional

from src.app.models import Category, Game, GameStatus


class GameValidators:
    """Validators for game operations"""

    @staticmethod
    def validate_answer(user_answer: str, correct_answer: str) -> bool:
        """
        Validate if the user's answer matches the correct answer.

        Args:
            user_answer: The user's submitted answer
            correct_answer: The correct answer

        Returns:
            True if the answer is correct (case-insensitive, stripped)
        """
        # Normalize both answers to make matching more forgiving for TTS-style answers.
        normalized_user = GameValidators._normalize_answer(user_answer)
        normalized_correct = GameValidators._normalize_answer(correct_answer)

        return normalized_user == normalized_correct

    @staticmethod
    def _normalize_answer(text: str) -> str:
        """Normalize answer by removing spaces and punctuation."""
        lowered = text.strip().lower()
        return re.sub(r"[\W_]+", "", lowered, flags=re.UNICODE)

    @staticmethod
    def validate_hint_limit(game: Game, max_hints: int = 3) -> bool:
        """
        Validate if the game can still use hints.

        Args:
            game: The game instance
            max_hints: Maximum allowed hints

        Returns:
            True if hints can still be used
        """
        return game.current_hint_count < max_hints

    @staticmethod
    def validate_game_active(game: Optional[Game]) -> bool:
        """
        Validate if a game is active.

        Args:
            game: The game instance (can be None)

        Returns:
            True if the game exists and is active
        """
        return game is not None and game.status == GameStatus.ACTIVE

    @staticmethod
    def validate_game_not_expired(game: Game) -> bool:
        """
        Validate if a game has not expired.

        Args:
            game: The game instance

        Returns:
            True if the game has not expired yet
        """
        if game.expires_at is None:
            return True
        return game.expires_at > datetime.now(timezone.utc)

    @staticmethod
    def is_skip_allowed(game: Game, starter_telegram_id: int, user_telegram_id: int, is_admin: bool = False) -> bool:
        """
        Check if a user is allowed to skip the current game.

        Args:
            game: The game instance
            starter_telegram_id: Telegram ID of the user who started the game
            user_telegram_id: Telegram ID of the user trying to skip
            is_admin: Whether the user is an admin

        Returns:
            True if the user can skip the game
        """
        # Admins can always skip
        if is_admin:
            return True

        # The user who started the game can skip
        return user_telegram_id == starter_telegram_id

    @staticmethod
    def validate_category(category: Optional[str]) -> Optional[Category]:
        """
        Validate and convert category string to Category enum.

        Args:
            category: Category string (e.g., 'lucu', 'mind_blowing')

        Returns:
            Category enum value or None if invalid

        Raises:
            ValueError: If category is invalid
        """
        if category is None or not category.strip():
            return None

        category = category.lower().strip()

        # Handle various input formats
        if category in ["lucu", "lucu/", "funny"]:
            return Category.LUCU
        elif category in ["mind_blowing", "mindblowing", "mind", "mb"]:
            return Category.MIND_BLOWING
        else:
            raise ValueError(
                f"Invalid category: {category}. Valid options: 'lucu', 'mind_blowing'"
            )

    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Sanitize user input text to prevent issues.

        Args:
            text: Input text

        Returns:
            Sanitized text
        """
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text

    @staticmethod
    def validate_points_after_hint(original_points: int, hint_count: int, hint_penalty: float = 0.5) -> int:
        """
        Calculate points after using hints.

        Args:
            original_points: Original points for the question
            hint_count: Number of hints used
            hint_penalty: Penalty per hint (default 0.5 = 50%)

        Returns:
            Adjusted points after applying hint penalties
        """
        penalty_multiplier = 1 - (hint_count * hint_penalty)
        adjusted_points = int(original_points * max(0.1, penalty_multiplier))  # Minimum 10%
        return adjusted_points
