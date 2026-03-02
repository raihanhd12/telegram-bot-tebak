"""
Game repository

CRUD helpers for Game model. Manages active game sessions.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.app.models import Game, GameStatus


class GameRepository:
    """Repository for Game model"""

    @staticmethod
    def _enum_value(value: Any) -> Any:
        """Normalize enum-like values to raw DB values."""
        return value.value if hasattr(value, "value") else value

    @staticmethod
    def get_by_id(db: Session, game_id: int) -> Optional[Game]:
        """Get game by ID"""
        return db.query(Game).filter(Game.id == game_id).first()

    @staticmethod
    def get_active_game_by_chat(db: Session, chat_id: int) -> Optional[Game]:
        """Get active game in a specific chat"""
        return (
            db.query(Game)
            .filter(
                Game.chat_id == chat_id,
                Game.status == GameRepository._enum_value(GameStatus.ACTIVE),
            )
            .first()
        )

    @staticmethod
    def list_games(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        chat_id: Optional[int] = None,
        status: Optional[GameStatus] = None,
    ) -> List[Game]:
        """List games with optional filters"""
        query = db.query(Game)

        if chat_id:
            query = query.filter(Game.chat_id == chat_id)

        if status:
            query = query.filter(Game.status == GameRepository._enum_value(status))

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def create_game(db: Session, **kwargs: Any) -> Game:
        """Create a new game"""
        game = Game(**kwargs)
        db.add(game)
        db.commit()
        db.refresh(game)
        return game

    @staticmethod
    def update_game(db: Session, game: Game, update_data: Dict[str, Any]) -> Game:
        """Update an existing game"""
        for key, value in update_data.items():
            setattr(game, key, value)
        db.add(game)
        db.commit()
        db.refresh(game)
        return game

    @staticmethod
    def set_status(db: Session, game: Game, status: GameStatus) -> Game:
        """Set game status"""
        game.status = status
        db.add(game)
        db.commit()
        db.refresh(game)
        return game

    @staticmethod
    def increment_hint_count(db: Session, game: Game) -> Game:
        """Increment hint count"""
        game.current_hint_count += 1
        db.add(game)
        db.commit()
        db.refresh(game)
        return game

    @staticmethod
    def set_expires_at(db: Session, game: Game, expires_at: Any) -> Game:
        """Set game expiration time"""
        game.expires_at = expires_at
        db.add(game)
        db.commit()
        db.refresh(game)
        return game

    @staticmethod
    def delete_game(db: Session, game: Game) -> None:
        """Delete a game (cascades to game_players)"""
        db.delete(game)
        db.commit()

    @staticmethod
    def cleanup_expired_games(db: Session) -> int:
        """
        Mark games as expired if they have passed their expiration time.

        Returns:
            Number of games marked as expired
        """
        from datetime import datetime, timezone

        count = (
            db.query(Game)
            .filter(
                Game.status == GameRepository._enum_value(GameStatus.ACTIVE),
                Game.expires_at < datetime.now(timezone.utc),
            )
            .update({"status": GameRepository._enum_value(GameStatus.EXPIRED)})
        )
        db.commit()
        return count
