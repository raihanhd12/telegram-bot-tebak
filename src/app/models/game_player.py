"""GamePlayer model for Tebak Kata game."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.database.session import Base

if TYPE_CHECKING:
    from src.app.models.game import Game
    from src.app.models.player import Player


class GamePlayer(Base):
    """Junction table for player participation in games."""

    __tablename__ = "game_players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_answered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    game: Mapped[Game] = relationship("Game", back_populates="game_players")
    player: Mapped[Player] = relationship("Player", back_populates="game_players")

    def __repr__(self):
        return (
            f"<GamePlayer(id={self.id}, game_id={self.game_id}, "
            f"player_id={self.player_id}, score={self.score})>"
        )
