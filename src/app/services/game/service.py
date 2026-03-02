"""
Game Service

Facade service that provides access to all game-related operations.
"""

from typing import Optional

from sqlalchemy.orm import Session

from src.app.models import Category, Game
from src.app.repositories.question import QuestionRepository
from src.app.services.game.modules import (
    GameCreateService,
    GameReadService,
    GameUpdateService,
    GameValidators,
)


class GameService:
    """
    Main game service facade.

    Provides a unified interface for all game operations.
    """

    def __init__(
        self,
        db: Session,
        game_timeout: int = 60,
        hint_penalty: float = 0.5,
        max_hints: int = 3,
    ):
        """
        Initialize the game service.

        Args:
            db: Database session
            game_timeout: Game timeout in seconds (default: 60)
            hint_penalty: Penalty per hint as decimal (default: 0.5 = 50%)
            max_hints: Maximum hints per game (default: 3)
        """
        self.db = db
        self.game_timeout = game_timeout
        self.hint_penalty = hint_penalty
        self.max_hints = max_hints

        # Initialize sub-services
        self.create = GameCreateService(db, game_timeout, hint_penalty, max_hints)
        self.read = GameReadService(db)
        self.update = GameUpdateService(db, game_timeout, hint_penalty, max_hints)

    # ============ Game Operations ============

    def start_game(
        self,
        chat_id: int,
        starter_telegram_id: int,
        starter_username: Optional[str],
        starter_full_name: Optional[str],
        category: Optional[str] = None,
    ) -> tuple[Optional[Game], str]:
        """
        Start a new game.

        Args:
            chat_id: Telegram chat ID
            starter_telegram_id: ID of user starting the game
            starter_username: Username of starter
            starter_full_name: Full name of starter
            category: Optional category ('lucu' or 'mind_blowing')

        Returns:
            Tuple of (Game, formatted_message) or (None, error_message)
        """
        try:
            validated_category = GameValidators.validate_category(category)
        except ValueError as e:
            return None, f"❌ Kategori tidak valid: {e}\n\nPilih: *lucu* atau *mind_blowing*"

        # Check for fresh questions
        fresh_count = QuestionRepository.count_active_questions(self.db, validated_category)

        if fresh_count == 0:
            return (
                None,
                "❌ Tidak ada soal tersedia untuk kategori ini.\n\n"
                "Admin bisa gunakan /refresh untuk generate soal baru.",
            )

        game, player, was_created = self.create.start_game(
            chat_id=chat_id,
            starter_telegram_id=starter_telegram_id,
            starter_username=starter_username,
            starter_full_name=starter_full_name,
            category=validated_category,
        )

        if not game:
            return None, "❌ Gagal memulai game. Silakan coba lagi."

        # Get question details
        question = QuestionRepository.get_by_id(self.db, game.question_id)
        if not question:
            return None, "❌ Soal tidak ditemukan."

        message = self._format_game_start(question, was_created)
        return game, message

    def submit_answer(
        self,
        chat_id: int,
        telegram_id: int,
        username: Optional[str],
        full_name: Optional[str],
        answer: str,
    ) -> tuple[bool, str, int]:
        """
        Submit an answer for the active game.

        Args:
            chat_id: Telegram chat ID
            telegram_id: Player's Telegram ID
            username: Player's username
            full_name: Player's full name
            answer: The player's answer

        Returns:
            Tuple of (is_correct, message, points_earned)
        """
        game = self.read.get_active_game(chat_id)

        if not game:
            return False, "❌ Tidak ada game aktif. Ketik /tebak untuk mulai!", 0

        # Get or create player
        player = self.create.ensure_player_in_game(game, telegram_id, username, full_name)

        # Submit answer
        is_correct, points, message = self.create.submit_answer(game, player, answer)

        # If correct, complete the game
        if is_correct:
            self.update.complete_game(game)

            # Add fun messages based on streak
            if player.current_streak > 1:
                streak_msg = f"\n🔥 Streak: {player.current_streak}! Luar biasa!"
                message += streak_msg

            # Add badges for achievements
            badges = self._get_badges(player)
            if badges:
                message += f"\n\n{badges}"

        return is_correct, message, points

    def skip_game(
        self, chat_id: int, user_telegram_id: int, is_admin: bool = False
    ) -> tuple[bool, str]:
        """
        Skip the current game.

        Args:
            chat_id: Telegram chat ID
            user_telegram_id: ID of user trying to skip
            is_admin: Whether the user is an admin

        Returns:
            Tuple of (success, message)
        """
        game = self.read.get_active_game(chat_id)

        if not game:
            return False, "❌ Tidak ada game aktif untuk dilewati."

        # For now, allow anyone to skip
        # TODO: Track who started the game and restrict skip
        message = self.update.skip_game(game)
        return True, message

    def use_hint(self, chat_id: int) -> tuple[bool, str]:
        """
        Use a hint for the current game.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Tuple of (success, message)
        """
        game = self.read.get_active_game(chat_id)

        if not game:
            return False, "❌ Tidak ada game aktif."

        success, message, _ = self.update.use_hint(game)
        return success, message

    def get_leaderboard(self, chat_id: Optional[int] = None, limit: int = 5) -> str:
        """
        Get formatted leaderboard.

        Args:
            chat_id: Optional chat ID (future: per-chat leaderboards)
            limit: Maximum players to show

        Returns:
            Formatted leaderboard message
        """
        leaderboard = self.read.get_leaderboard(chat_id=chat_id, limit=limit)
        return self.read.format_leaderboard(leaderboard)

    def get_active_game(self, chat_id: int) -> Optional[Game]:
        """Get the active game in a chat"""
        return self.read.get_active_game(chat_id)

    def expire_game(self, game: Game) -> str:
        """Expire a game (called by timeout handler)"""
        return self.update.expire_game(game)

    # ============ Helper Methods ============

    def _format_game_start(self, question, was_new: bool) -> str:
        """Format game start message"""
        category_emoji = "😂" if question.category == Category.LUCU else "🤯"

        header = (
            f"🎮 *TEBAK KATA* {category_emoji}\n\n"
            if was_new
            else f"🔄 *Game Masih Aktif* {category_emoji}\n\n"
        )

        word_display = " ".join(list(question.word.upper()))

        message = (
            f"{header}"
            f"📝 *Tebak kata ini:*\n\n"
            f"`{word_display}`\n\n"
            f"📌 Kategori: *{self._format_category(question.category)}*\n"
            f"💰 Poin: *{question.points}*\n"
            f"⏱️ Waktu: *{self.game_timeout} detik*\n\n"
            f"Ketik jawabanmu langsung di chat!\n"
            f"Ketik /hint untuk bantuan."
        )

        if not was_new:
            message = (
                f"{header}"
                f"Game masih aktif! Kata yang harus ditebak:\n\n"
                f"`{word_display}`\n\n"
                f"⏱️ Sisa waktu: cek status game"
            )

        return message

    def _format_category(self, category: Category) -> str:
        """Format category for display"""
        if category == Category.LUCU:
            return "😂 Lucu"
        elif category == Category.MIND_BLOWING:
            return "🤯 Mind Blowing"
        return str(category)

    def _get_badges(self, player) -> str:
        """Get badges for a player"""
        badges = []

        if player.total_score >= 1000:
            badges.append("🏆 *Raja Tebak Kata*")
        if player.current_streak >= 5:
            badges.append("🔥 *On Fire!*")
        if player.current_streak >= 10:
            badges.append("⚡ *Legendary*")
        if player.games_won >= 10:
            badges.append("🧠 *Jenius*")

        return " | ".join(badges) if badges else ""
