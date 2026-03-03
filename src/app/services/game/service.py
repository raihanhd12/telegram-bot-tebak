"""
Game Service

Facade service that provides access to all game-related operations.
"""

from typing import Optional

from sqlalchemy.orm import Session

import src.config.env as env
from src.app.models import Category, Game
from src.app.repositories.player import PlayerRepository
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
        max_used_count: int = 1,
    ):
        """
        Initialize the game service.

        Args:
            db: Database session
            game_timeout: Game timeout in seconds (default: 60)
            hint_penalty: Penalty per hint as decimal (default: 0.5 = 50%)
            max_hints: Maximum hints per game (default: 3)
            max_used_count: Maximum allowed question reuse count (default: 1)
        """
        self.db = db
        self.game_timeout = game_timeout
        self.hint_penalty = hint_penalty
        self.max_hints = max_hints
        self.max_used_count = max(1, int(max_used_count))

        # Initialize sub-services
        self.create = GameCreateService(
            db,
            game_timeout,
            hint_penalty,
            max_hints,
            max_used_count=self.max_used_count,
        )
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
            category: Optional category filter (internal use)

        Returns:
            Tuple of (Game, formatted_message) or (None, error_message)
        """
        active_game = self.read.get_active_game(chat_id)
        if active_game:
            return (
                None,
                "⚠️ Masih ada soal aktif di topic ini.\n"
                "Selesaikan dulu dengan jawab soal, atau pakai /skip.",
            )

        if not self._is_player_verified(
            starter_telegram_id,
            username=starter_username,
            full_name=starter_full_name,
        ):
            return None, self._get_verification_block_message()

        try:
            validated_category = GameValidators.validate_category(category)
        except ValueError as e:
            return None, f"❌ Kategori tidak valid: {e}"

        # Check for fresh questions
        fresh_count = QuestionRepository.count_fresh_questions(
            self.db,
            validated_category,
            max_used_count=self.max_used_count,
        )

        if fresh_count == 0:
            empty_msg = (
                "❌ Tidak ada soal tersedia.\n\nAdmin bisa gunakan /refresh untuk generate soal baru."
                if validated_category is None
                else "❌ Tidak ada soal tersedia untuk kategori ini.\n\n"
                "Admin bisa gunakan /refresh untuk generate soal baru."
            )
            return (
                None,
                empty_msg,
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
            return (
                False,
                "❌ Tidak ada game aktif di topic ini.\n"
                "Kemungkinan game sudah selesai/timeout, atau kamu kirim jawaban di topic berbeda.\n"
                "Ketik /tebak untuk mulai ronde baru.",
                0,
            )

        if not self._is_player_verified(telegram_id, username=username, full_name=full_name):
            return False, self._get_verification_block_message(), 0

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
        self,
        chat_id: int,
        user_telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
        is_admin: bool = False,
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

        if not self._is_player_verified(
            user_telegram_id,
            username=username,
            full_name=full_name,
        ):
            return False, self._get_verification_block_message()

        # For now, allow anyone to skip
        # TODO: Track who started the game and restrict skip
        message = self.update.skip_game(game)
        return True, message

    def use_hint(
        self,
        chat_id: int,
        telegram_id: int | None = None,
        username: str | None = None,
        full_name: str | None = None,
    ) -> tuple[bool, str]:
        """
        Use a hint for the current game.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Tuple of (success, message)
        """
        game = self.read.get_active_game(chat_id)

        if not game:
            return (
                False,
                "❌ Tidak ada game aktif di topic ini.\n"
                "Kemungkinan game sudah selesai/timeout, atau command dikirim di topic berbeda.",
            )

        if telegram_id is not None and not self._is_player_verified(
            telegram_id,
            username=username,
            full_name=full_name,
        ):
            return False, self._get_verification_block_message()

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
        answer_pattern = self._format_answer_pattern(question.answer)

        header = (
            f"🎮 TEBAK TTS {category_emoji}\n\n"
            if was_new
            else f"🔄 Game Masih Aktif {category_emoji}\n\n"
        )

        message = (
            f"{header}"
            f"🧩 Pertanyaan:\n{question.word}\n\n"
            f"🔎 Pola jawaban: {answer_pattern}\n"
            f"📌 Kategori: {self._format_category(question.category)}\n"
            f"💰 Poin: {question.points}\n"
            f"⏱️ Waktu: {self.game_timeout} detik\n\n"
            f"Ketik jawaban TTS kamu langsung di chat.\n"
            f"Gunakan /hint kalau buntu."
        )

        if not was_new:
            message = (
                f"{header}"
                f"Game masih aktif, pertanyaannya:\n\n"
                f"{question.word}\n\n"
                f"🔎 Pola jawaban: {answer_pattern}\n"
                f"⏱️ Sisa waktu: cek status game aktif."
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
            badges.append("🏆 Raja Tebak Kata")
        if player.current_streak >= 5:
            badges.append("🔥 On Fire!")
        if player.current_streak >= 10:
            badges.append("⚡ Legendary")
        if player.games_won >= 10:
            badges.append("🧠 Jenius")

        return " | ".join(badges) if badges else ""

    @staticmethod
    def _get_verification_block_message() -> str:
        """Unified message when player is not verified."""
        return "⛔ Akun kamu belum terverifikasi, jadi belum bisa main."

    def _is_player_verified(
        self,
        telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
    ) -> bool:
        """Check (or create) player record and return verification status."""
        if env.is_admin_username(username):
            return True

        player = PlayerRepository.get_or_create_by_telegram_id(
            self.db,
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
        )
        return bool(getattr(player, "is_verified", False))

    def _format_answer_pattern(self, answer: str) -> str:
        """Mask answer pattern like AYAM -> A**M to guide players."""
        return " ".join(self._mask_token(token) for token in answer.split())

    @staticmethod
    def _mask_token(token: str) -> str:
        """Mask a token while preserving non-alphanumeric chars."""
        chars = list(token)
        alnum_indexes = [idx for idx, ch in enumerate(chars) if ch.isalnum()]

        if not alnum_indexes:
            return token

        if len(alnum_indexes) == 1:
            chars[alnum_indexes[0]] = chars[alnum_indexes[0]].upper()
            return "".join(chars)

        if len(alnum_indexes) == 2:
            first, second = alnum_indexes
            chars[first] = chars[first].upper()
            chars[second] = "*"
            return "".join(chars)

        first, last = alnum_indexes[0], alnum_indexes[-1]
        chars[first] = chars[first].upper()
        chars[last] = chars[last].upper()
        for idx in alnum_indexes[1:-1]:
            chars[idx] = "*"

        return "".join(chars)
