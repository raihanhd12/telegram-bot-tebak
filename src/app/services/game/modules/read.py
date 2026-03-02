"""
Game service read module

Handles reading game data, leaderboards, and active games.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from src.app.models import Category, Game, GameStatus
from src.app.repositories.game import GameRepository
from src.app.repositories.player import PlayerRepository
from src.app.services.game.modules.validators import GameValidators


class GameReadService:
    """Service for reading game data"""

    def __init__(self, db: Session):
        """
        Initialize the read service.

        Args:
            db: Database session
        """
        self.db = db

    def get_active_game(self, chat_id: int) -> Optional[Game]:
        """
        Get the active game in a chat.

        Args:
            chat_id: Telegram chat ID

        Returns:
            Game object or None if no active game
        """
        game = GameRepository.get_active_game_by_chat(self.db, chat_id)

        # Validate game is still valid
        if game and not GameValidators.validate_game_active(game):
            return None

        if game and not GameValidators.validate_game_not_expired(game):
            # Mark as expired
            GameRepository.set_status(self.db, game, GameStatus.EXPIRED)
            return None

        return game

    def get_leaderboard(
        self, chat_id: Optional[int] = None, limit: int = 5
    ) -> List[dict]:
        """
        Get the leaderboard.

        Args:
            chat_id: Optional chat ID for filtering (future feature)
            limit: Maximum number of players to return

        Returns:
            List of dictionaries with player info and scores
        """
        players = PlayerRepository.get_leaderboard(self.db, chat_id=chat_id, limit=limit)

        leaderboard = []
        for idx, player in enumerate(players, start=1):
            leaderboard.append(
                {
                    "rank": idx,
                    "telegram_id": player.telegram_id,
                    "username": player.username or "Anonim",
                    "full_name": player.full_name,
                    "total_score": player.total_score,
                    "games_won": player.games_won,
                    "current_streak": player.current_streak,
                    "best_streak": player.best_streak,
                }
            )

        return leaderboard

    def format_leaderboard(self, leaderboard: List[dict]) -> str:
        """
        Format leaderboard for Telegram message.

        Args:
            leaderboard: List of player data dictionaries

        Returns:
            Formatted string for Telegram message
        """
        if not leaderboard:
            return "🏆 *Leaderboard Kosong*\n\nBelum ada skor yang tercatat. Jadilah yang pertama!"

        lines = ["🏆 *LEADERBOARD*", ""]

        for entry in leaderboard:
            rank_emoji = self._get_rank_emoji(entry["rank"])
            streak_emoji = "🔥" * min(entry["current_streak"], 5) if entry["current_streak"] > 0 else ""

            lines.append(
                f"{rank_emoji} *{entry['rank']}.* {entry['username']}"
            )
            lines.append(f"   └─ {entry['total_score']} poin {streak_emoji}")

        lines.append("")
        lines.append("_Gunakan /tebak untuk mulai bermain!_")

        return "\n".join(lines)

    def _get_rank_emoji(self, rank: int) -> str:
        """Get emoji for rank position"""
        emojis = {
            1: "🥇",
            2: "🥈",
            3: "🥉",
            4: "4️⃣",
            5: "5️⃣",
        }
        return emojis.get(rank, "🎖️")

    def get_game_info(self, game: Game) -> dict:
        """
        Get detailed information about a game.

        Args:
            game: Game object

        Returns:
            Dictionary with game information
        """
        from src.app.repositories.question import QuestionRepository

        question = QuestionRepository.get_by_id(self.db, game.question_id)

        return {
            "game_id": game.id,
            "chat_id": game.chat_id,
            "status": game.status.value,
            "category": game.category.value,
            "current_hint_count": game.current_hint_count,
            "word": question.word if question else None,
            "points": question.points if question else 0,
            "hint_available": game.current_hint_count < 3,
            "expires_at": game.expires_at.isoformat() if game.expires_at else None,
        }

    def get_player_stats(self, telegram_id: int) -> Optional[dict]:
        """
        Get statistics for a player.

        Args:
            telegram_id: Player's Telegram ID

        Returns:
            Dictionary with player stats or None if not found
        """
        player = PlayerRepository.get_by_telegram_id(self.db, telegram_id)

        if not player:
            return None

        return {
            "telegram_id": player.telegram_id,
            "username": player.username,
            "full_name": player.full_name,
            "total_score": player.total_score,
            "games_played": player.games_played,
            "games_won": player.games_won,
            "win_rate": (
                round(player.games_won / player.games_played * 100, 1)
                if player.games_played > 0
                else 0
            ),
            "current_streak": player.current_streak,
            "best_streak": player.best_streak,
        }
