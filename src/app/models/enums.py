"""Shared enums for game-related models."""

from enum import StrEnum
from typing import Type


class Category(StrEnum):
    """Question category enum."""

    LUCU = "lucu"
    MIND_BLOWING = "mind_blowing"


class Difficulty(StrEnum):
    """Question difficulty enum."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionSource(StrEnum):
    """Question source enum."""

    LLM = "llm"
    MANUAL = "manual"


class GameStatus(StrEnum):
    """Game status enum."""

    ACTIVE = "active"
    EXPIRED = "expired"
    COMPLETED = "completed"


def enum_values(enum_cls: Type[StrEnum]) -> list[str]:
    """Return enum values for SQLAlchemy Enum value-based persistence."""
    return [member.value for member in enum_cls]
