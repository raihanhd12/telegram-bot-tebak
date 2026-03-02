"""Game model for Tebak Kata game."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.app.models.enums import Category, GameStatus, enum_values
from src.database.session import Base

if TYPE_CHECKING:
    from src.app.models.game_player import GamePlayer
    from src.app.models.question import Question


class Game(Base):
    """Represents one active/completed game session in a chat."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    category: Mapped[Category] = mapped_column(
        SQLEnum(
            Category,
            name="category",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    status: Mapped[GameStatus] = mapped_column(
        SQLEnum(
            GameStatus,
            name="gamestatus",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=GameStatus.ACTIVE,
        index=True,
    )
    current_hint_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    question: Mapped[Question] = relationship("Question", back_populates="games")
    game_players: Mapped[list[GamePlayer]] = relationship(
        "GamePlayer",
        back_populates="game",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Game(id={self.id}, chat_id={self.chat_id}, status={self.status})>"
