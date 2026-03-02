"""Question model for Tebak Kata game."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.app.models.enums import Category, Difficulty, QuestionSource, enum_values
from src.database.session import Base

if TYPE_CHECKING:
    from src.app.models.game import Game


class Question(Base):
    """Stores generated/manual question records."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    word: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    answer: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[Category] = mapped_column(
        SQLEnum(
            Category,
            name="category",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    difficulty: Mapped[Difficulty] = mapped_column(
        SQLEnum(
            Difficulty,
            name="difficulty",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
    )
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    source: Mapped[QuestionSource] = mapped_column(
        SQLEnum(
            QuestionSource,
            name="questionsource",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=QuestionSource.LLM,
    )
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    games: Mapped[list[Game]] = relationship("Game", back_populates="question")

    def __repr__(self):
        return (
            f"<Question(id={self.id}, word='{self.word}', answer='{self.answer}', "
            f"category={self.category})>"
        )
