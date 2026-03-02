"""
Player repository

CRUD helpers for Player model. Manages player stats and scores.
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.app.models import Player


class PlayerRepository:
    """Repository for Player model"""

    @staticmethod
    def get_by_id(db: Session, player_id: int) -> Optional[Player]:
        """Get player by ID"""
        return db.query(Player).filter(Player.id == player_id).first()

    @staticmethod
    def get_by_telegram_id(db: Session, telegram_id: int) -> Optional[Player]:
        """Get player by Telegram ID"""
        return db.query(Player).filter(Player.telegram_id == telegram_id).first()

    @staticmethod
    def get_or_create_by_telegram_id(
        db: Session, telegram_id: int, username: Optional[str] = None, full_name: Optional[str] = None
    ) -> Player:
        """
        Get existing player by Telegram ID or create a new one.

        Args:
            db: Database session
            telegram_id: Telegram user ID
            username: Optional username (for new players)
            full_name: Optional full name (for new players)

        Returns:
            Player object (existing or newly created)
        """
        player = PlayerRepository.get_by_telegram_id(db, telegram_id)

        if not player:
            player = PlayerRepository.create_player(
                db,
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
            )
        # Update username and full_name if they changed
        elif username or full_name:
            update_data = {}
            if username and player.username != username:
                update_data["username"] = username
            if full_name and player.full_name != full_name:
                update_data["full_name"] = full_name
            if update_data:
                player = PlayerRepository.update_player(db, player, update_data)

        return player

    @staticmethod
    def list_players(db: Session, skip: int = 0, limit: int = 100) -> List[Player]:
        """List players"""
        return db.query(Player).offset(skip).limit(limit).all()

    @staticmethod
    def get_leaderboard(db: Session, chat_id: Optional[int] = None, limit: int = 5) -> List[Player]:
        """
        Get top players by total score.

        Args:
            db: Database session
            chat_id: Optional chat ID to filter players (future feature)
            limit: Maximum number of players to return

        Returns:
            List of players sorted by total score (descending)
        """
        # TODO: Add chat_id filtering when we implement per-chat leaderboards
        return db.query(Player).order_by(Player.total_score.desc()).limit(limit).all()

    @staticmethod
    def create_player(db: Session, **kwargs: Any) -> Player:
        """Create a new player"""
        player = Player(**kwargs)
        db.add(player)
        db.commit()
        db.refresh(player)
        return player

    @staticmethod
    def update_player(db: Session, player: Player, update_data: Dict[str, Any]) -> Player:
        """Update an existing player"""
        for key, value in update_data.items():
            setattr(player, key, value)
        db.add(player)
        db.commit()
        db.refresh(player)
        return player

    @staticmethod
    def add_score(db: Session, player: Player, points: int) -> Player:
        """
        Add score to player and update streak.

        Args:
            db: Database session
            player: Player to add score to
            points: Points to add

        Returns:
            Updated Player object
        """
        player.total_score += points
        player.current_streak += 1
        if player.current_streak > player.best_streak:
            player.best_streak = player.current_streak
        db.add(player)
        db.commit()
        db.refresh(player)
        return player

    @staticmethod
    def increment_games_played(db: Session, player: Player) -> Player:
        """Increment games played count"""
        player.games_played += 1
        db.add(player)
        db.commit()
        db.refresh(player)
        return player

    @staticmethod
    def increment_games_won(db: Session, player: Player) -> Player:
        """Increment games won count"""
        player.games_won += 1
        db.add(player)
        db.commit()
        db.refresh(player)
        return player

    @staticmethod
    def reset_streak(db: Session, player: Player) -> Player:
        """Reset current streak to 0"""
        player.current_streak = 0
        db.add(player)
        db.commit()
        db.refresh(player)
        return player

    @staticmethod
    def delete_player(db: Session, player: Player) -> None:
        """Delete a player"""
        db.delete(player)
        db.commit()
