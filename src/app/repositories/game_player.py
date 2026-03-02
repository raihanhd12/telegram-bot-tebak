"""
GamePlayer repository

CRUD helpers for GamePlayer model. Manages player participation in games.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.app.models import GamePlayer


class GamePlayerRepository:
    """Repository for GamePlayer model"""

    @staticmethod
    def get_by_id(db: Session, game_player_id: int) -> Optional[GamePlayer]:
        """Get GamePlayer by ID"""
        return db.query(GamePlayer).filter(GamePlayer.id == game_player_id).first()

    @staticmethod
    def get_by_game_and_player(db: Session, game_id: int, player_id: int) -> Optional[GamePlayer]:
        """Get GamePlayer by game_id and player_id"""
        return (
            db.query(GamePlayer)
            .filter(GamePlayer.game_id == game_id, GamePlayer.player_id == player_id)
            .first()
        )

    @staticmethod
    def get_or_create(db: Session, game_id: int, player_id: int) -> GamePlayer:
        """
        Get existing GamePlayer or create a new one.

        Args:
            db: Database session
            game_id: Game ID
            player_id: Player ID

        Returns:
            GamePlayer object (existing or newly created)
        """
        game_player = GamePlayerRepository.get_by_game_and_player(db, game_id, player_id)

        if not game_player:
            game_player = GamePlayerRepository.create(
                db,
                game_id=game_id,
                player_id=player_id,
            )

        return game_player

    @staticmethod
    def list_by_game(db: Session, game_id: int) -> List[GamePlayer]:
        """List all GamePlayers for a specific game"""
        return db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()

    @staticmethod
    def list_by_player(db: Session, player_id: int) -> List[GamePlayer]:
        """List all GamePlayers for a specific player"""
        return db.query(GamePlayer).filter(GamePlayer.player_id == player_id).all()

    @staticmethod
    def get_game_leaderboard(db: Session, game_id: int, limit: int = 5) -> List[GamePlayer]:
        """Get top players in a specific game by score"""
        return (
            db.query(GamePlayer)
            .filter(GamePlayer.game_id == game_id, GamePlayer.has_answered == True)
            .order_by(GamePlayer.score.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(db: Session, **kwargs: Any) -> GamePlayer:
        """Create a new GamePlayer"""
        game_player = GamePlayer(**kwargs)
        db.add(game_player)
        db.commit()
        db.refresh(game_player)
        return game_player

    @staticmethod
    def update(db: Session, game_player: GamePlayer, update_data: Dict[str, Any]) -> GamePlayer:
        """Update an existing GamePlayer"""
        for key, value in update_data.items():
            setattr(game_player, key, value)
        db.add(game_player)
        db.commit()
        db.refresh(game_player)
        return game_player

    @staticmethod
    def set_score(db: Session, game_player: GamePlayer, score: int) -> GamePlayer:
        """Set player score for this game"""
        game_player.score = score
        db.add(game_player)
        db.commit()
        db.refresh(game_player)
        return game_player

    @staticmethod
    def mark_answered(db: Session, game_player: GamePlayer, score: int = 0) -> GamePlayer:
        """Mark player as answered with score"""
        game_player.has_answered = True
        game_player.score = score
        game_player.answered_at = datetime.now(timezone.utc)
        db.add(game_player)
        db.commit()
        db.refresh(game_player)
        return game_player

    @staticmethod
    def delete(db: Session, game_player: GamePlayer) -> None:
        """Delete a GamePlayer"""
        db.delete(game_player)
        db.commit()
