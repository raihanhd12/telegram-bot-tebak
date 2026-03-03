"""
Game service create module

Handles creating games and processing answers.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from src.app.models import Category, Game, GameStatus, Player
from src.app.repositories.game import GameRepository
from src.app.repositories.game_player import GamePlayerRepository
from src.app.repositories.player import PlayerRepository
from src.app.repositories.question import QuestionRepository
from src.app.services.game.modules.validators import GameValidators


class GameCreateService:
    """Service for creating games and handling answers"""

    def __init__(
        self,
        db: Session,
        game_timeout: int = 60,
        hint_penalty: float = 0.5,
        max_hints: int = 3,
    ):
        """
        Initialize the create service.

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

    def start_game(
        self,
        chat_id: int,
        starter_telegram_id: int,
        starter_username: Optional[str],
        starter_full_name: Optional[str],
        category: Optional[Category] = None,
    ) -> Tuple[Optional[Game], Player, bool]:
        """
        Start a new game in a chat.

        Args:
            chat_id: Telegram chat ID
            starter_telegram_id: Telegram ID of the user starting the game
            starter_username: Username of the starter
            starter_full_name: Full name of the starter
            category: Optional category filter

        Returns:
            Tuple of (Game, starter Player, was_created)
            - was_created is True if a new game was created, False if reused
        """
        # Check for existing active game
        existing_game = GameRepository.get_active_game_by_chat(self.db, chat_id)

        if existing_game and GameValidators.validate_game_not_expired(existing_game):
            # Game already exists and is active
            starter = PlayerRepository.get_or_create_by_telegram_id(
                self.db,
                starter_telegram_id,
                username=starter_username,
                full_name=starter_full_name,
            )
            return existing_game, starter, False

        # Get or create starter player
        starter = PlayerRepository.get_or_create_by_telegram_id(
            self.db,
            starter_telegram_id,
            username=starter_username,
            full_name=starter_full_name,
        )

        # Get a fresh question
        question = QuestionRepository.get_fresh_question(self.db, category)

        if not question:
            return None, starter, False

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self.game_timeout)

        # Create new game
        game = GameRepository.create_game(
            self.db,
            chat_id=chat_id,
            question_id=question.id,
            category=question.category,
            status=GameStatus.ACTIVE,
            expires_at=expires_at,
        )

        # Add starter to game players
        GamePlayerRepository.create(
            self.db,
            game_id=game.id,
            player_id=starter.id,
        )

        # Mark question as used
        QuestionRepository.mark_as_used(self.db, question)

        return game, starter, True

    def submit_answer(
        self,
        game: Game,
        player: Player,
        user_answer: str,
    ) -> Tuple[bool, int, str]:
        """
        Submit an answer for a game.

        Args:
            game: The active game
            player: The player submitting the answer
            user_answer: The user's answer

        Returns:
            Tuple of (is_correct, points_earned, message)
        """
        # Validate game is still active
        if not GameValidators.validate_game_active(game):
            return False, 0, "Game ini sudah tidak aktif."

        # Validate game hasn't expired
        if not GameValidators.validate_game_not_expired(game):
            # Mark as expired
            GameRepository.set_status(self.db, game, GameStatus.EXPIRED)
            return False, 0, "Game ini sudah kadaluarsa."

        # Get the question
        question = QuestionRepository.get_by_id(self.db, game.question_id)
        if not question:
            return False, 0, "Soal tidak ditemukan."

        # Check if player already answered
        game_player = GamePlayerRepository.get_by_game_and_player(
            self.db, game.id, player.id
        )

        if game_player and game_player.has_answered:
            return False, 0, "Kamu sudah menjawab soal ini!"

        # Validate answer
        is_correct = GameValidators.validate_answer(user_answer, question.answer)

        if not is_correct:
            return False, 0, "Jawaban salah! Coba lagi."

        # Calculate points (apply hint penalty)
        points = GameValidators.validate_points_after_hint(
            question.points, game.current_hint_count, self.hint_penalty
        )

        # Create or update game_player
        if not game_player:
            game_player = GamePlayerRepository.create(
                self.db,
                game_id=game.id,
                player_id=player.id,
            )

        # Mark as answered
        GamePlayerRepository.mark_answered(self.db, game_player, points)

        # Update player stats
        PlayerRepository.add_score(self.db, player, points)
        PlayerRepository.increment_games_played(self.db, player)
        PlayerRepository.increment_games_won(self.db, player)

        message = (
            f"✅ Jawaban benar! +{points} poin\n\n"
            f"🧩 Pertanyaan: {question.word}\n"
            f"🎯 Jawaban: {question.answer}"
        )
        if question.hint:
            message += f"\n💬 Keterangan: {question.hint}"

        return True, points, message

    def ensure_player_in_game(
        self,
        game: Game,
        telegram_id: int,
        username: Optional[str],
        full_name: Optional[str],
    ) -> Player:
        """
        Ensure a player is registered in the game.

        Args:
            game: The active game
            telegram_id: Player's Telegram ID
            username: Player's username
            full_name: Player's full name

        Returns:
            Player object
        """
        player = PlayerRepository.get_or_create_by_telegram_id(
            self.db,
            telegram_id,
            username=username,
            full_name=full_name,
        )

        # Create game_player if not exists
        game_player = GamePlayerRepository.get_by_game_and_player(
            self.db, game.id, player.id
        )

        if not game_player:
            GamePlayerRepository.create(
                self.db,
                game_id=game.id,
                player_id=player.id,
            )

        return player
