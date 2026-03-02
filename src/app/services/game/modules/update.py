"""
Game service update module

Handles updating game state: skip, hint, expire.
"""
import datetime
from datetime import timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.app.models import Category, Game, GameStatus
from src.app.repositories.game import GameRepository
from src.app.repositories.player import PlayerRepository
from src.app.repositories.question import QuestionRepository
from src.app.services.game.modules.validators import GameValidators


class GameUpdateService:
    """Service for updating game state"""

    def __init__(
        self,
        db: Session,
        game_timeout: int = 60,
        hint_penalty: float = 0.5,
        max_hints: int = 3,
    ):
        """
        Initialize the update service.

        Args:
            db: Database session
            game_timeout: Game timeout in seconds
            hint_penalty: Penalty multiplier per hint
            max_hints: Maximum allowed hints
        """
        self.db = db
        self.game_timeout = game_timeout
        self.hint_penalty = hint_penalty
        self.max_hints = max_hints

    def skip_game(self, game: Game, reveal_answer: bool = True) -> str:
        """
        Skip/expired the current game.

        Args:
            game: The active game
            reveal_answer: Whether to reveal the correct answer

        Returns:
            Message to send to the chat
        """
        if game.status != GameStatus.ACTIVE:
            return "Game ini sudah berakhir."

        # Mark game as expired
        GameRepository.set_status(self.db, game, GameStatus.EXPIRED)

        message = "⏰ *Game Dilewati!*\n\n"

        if reveal_answer:
            question = QuestionRepository.get_by_id(self.db, game.question_id)
            if question:
                message += f"Jawaban yang benar: *{question.answer}*\n\n"
                message += f"Kata: {question.word}\n"
                message += f"Kategori: {self._format_category(question.category)}"

        message += "\n\nKetik /tebak untuk main lagi!"

        return message

    def use_hint(self, game: Game) -> tuple[bool, str, Optional[str]]:
        """
        Use a hint for the current game.

        Args:
            game: The active game

        Returns:
            Tuple of (success, message, revealed_char)
        """
        # Validate game is still active
        if not GameValidators.validate_game_active(game):
            return False, "Game ini sudah tidak aktif.", None

        # Validate game hasn't expired
        if not GameValidators.validate_game_not_expired(game):
            GameRepository.set_status(self.db, game, GameStatus.EXPIRED)
            return False, "Game ini sudah kadaluarsa.", None

        # Check hint limit
        if not GameValidators.validate_hint_limit(game, self.max_hints):
            return False, "Hint sudah habis! Maksimal 3 hints per game.", None

        # Get the question
        question = QuestionRepository.get_by_id(self.db, game.question_id)
        if not question:
            return False, "Soal tidak ditemukan.", None

        # Increment hint count
        GameRepository.increment_hint_count(self.db, game)

        # Use the question's hint if available
        if question.hint:
            return True, f"💡 *Hint*: {question.hint}", None

        # Otherwise, reveal a character (simple implementation)
        revealed_char = self._reveal_random_char(question.answer, game.current_hint_count)
        hint_count = game.current_hint_count

        # Calculate remaining points
        original_points = question.points
        remaining_points = GameValidators.validate_points_after_hint(
            original_points, hint_count, self.hint_penalty
        )

        message = (
            f"💡 *Hint {hint_count}/{self.max_hints}*\n"
            f"{revealed_char}\n\n"
            f"Poin tersisa: {remaining_points} (dari {original_points})"
        )

        return True, message, revealed_char

    def expire_game(self, game: Game) -> str:
        """
        Mark a game as expired (used by timeout handler).

        Args:
            game: The game to expire

        Returns:
            Message to send to the chat
        """
        if game.status != GameStatus.ACTIVE:
            return ""

        # Mark as expired
        GameRepository.set_status(self.db, game, GameStatus.EXPIRED)

        question = QuestionRepository.get_by_id(self.db, game.question_id)

        message = "⏰ *Waktu Habis!*\n\n"

        if question:
            message += f"Jawaban yang benar: *{question.answer}*\n\n"
            message += f"Kata: {question.word}\n"

            # Check if anyone answered correctly
            from src.app.repositories.game_player import GamePlayerRepository

            winners = GamePlayerRepository.get_game_leaderboard(self.db, game.id, limit=3)

            if winners:
                message += "\n🏆 *Pemenang:*\n"
                for gp in winners:
                    if gp.player and gp.player.username:
                        message += f"  • {gp.player.username}: {gp.score} poin\n"
            else:
                message += "\nTidak ada yang jawab dengan benar. 😢"

        message += "\n\nKetik /tebak untuk main lagi!"

        return message

    def complete_game(self, game: Game) -> None:
        """
        Mark a game as completed (all done).

        Args:
            game: The game to complete
        """
        GameRepository.set_status(self.db, game, GameStatus.COMPLETED)

    def extend_game_time(self, game: Game, additional_seconds: int = 30) -> Game:
        """
        Extend the game time.

        Args:
            game: The game to extend
            additional_seconds: Seconds to add

        Returns:
            Updated game
        """
        if game.expires_at:
            new_expires_at = game.expires_at + datetime.timedelta(seconds=additional_seconds)
        else:
            new_expires_at = datetime.datetime.now(timezone.utc) + datetime.timedelta(seconds=additional_seconds)

        return GameRepository.set_expires_at(self.db, game, new_expires_at)

    def _format_category(self, category: Category) -> str:
        """Format category for display"""
        if category == Category.LUCU:
            return "😂 Lucu"
        elif category == Category.MIND_BLOWING:
            return "🤯 Mind Blowing"
        return str(category)

    def _reveal_random_char(self, answer: str, hint_count: int) -> str:
        """
        Create a masked answer with some characters revealed.

        Args:
            answer: The correct answer
            hint_count: Current hint count

        Returns:
            String with some characters revealed
        """
        chars = list(answer)
        revealed_count = min(hint_count, len(chars))

        # Reveal characters at regular intervals
        step = max(1, len(chars) // (revealed_count + 1))

        result = []
        for i, char in enumerate(chars):
            if i % step == 0 and i < revealed_count * step:
                result.append(char)
            else:
                result.append("_")

        return " ".join(result)
