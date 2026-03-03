"""Tests for question repository helpers."""

from src.app.models import Category, Difficulty, Question
from src.app.repositories.question import QuestionRepository


class TestQuestionRepository:
    """Question repository test cases."""

    def test_reset_question_pool(self, db_session):
        """Reset should reactivate and clear usage counters."""
        question = Question(
            word="APA ITU TES",
            answer="TES",
            category=Category.LUCU,
            difficulty=Difficulty.MEDIUM,
            hint="contoh",
            points=100,
            used_count=9,
            is_active=False,
        )
        db_session.add(question)
        db_session.commit()
        db_session.refresh(question)

        reset_count = QuestionRepository.reset_question_pool(db_session, Category.LUCU)
        db_session.refresh(question)

        assert reset_count >= 1
        assert question.used_count == 0
        assert question.is_active is True
        assert question.last_used_at is None
