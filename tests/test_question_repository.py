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

    def test_count_fresh_questions_respects_usage_limit(self, db_session):
        """Fresh question counter should ignore exhausted rows."""
        fresh = Question(
            word="SOAL FRESH",
            answer="A",
            category=Category.LUCU,
            difficulty=Difficulty.MEDIUM,
            points=100,
            used_count=0,
            is_active=True,
        )
        exhausted = Question(
            word="SOAL EXHAUSTED",
            answer="B",
            category=Category.LUCU,
            difficulty=Difficulty.MEDIUM,
            points=100,
            used_count=1,
            is_active=True,
        )
        db_session.add_all([fresh, exhausted])
        db_session.commit()

        assert (
            QuestionRepository.count_fresh_questions(
                db_session,
                Category.LUCU,
                max_used_count=1,
            )
            == 1
        )
        assert (
            QuestionRepository.count_fresh_questions(
                db_session,
                Category.LUCU,
                max_used_count=2,
            )
            == 2
        )

    def test_bulk_create_questions_skips_canonical_duplicates(self, db_session):
        """Canonical duplicates should be skipped across payload and DB."""
        existing = Question(
            word="Apa itu kopi?",
            answer="KOPI",
            category=Category.LUCU,
            difficulty=Difficulty.MEDIUM,
            points=100,
        )
        db_session.add(existing)
        db_session.commit()

        payload = [
            {
                "word": "apa itu kopi",
                "answer": "Kopi juga",
                "category": Category.LUCU,
                "difficulty": Difficulty.MEDIUM,
                "points": 100,
            },
            {
                "word": "APA ITU KOPI!!!",
                "answer": "Kopi lagi",
                "category": Category.LUCU,
                "difficulty": Difficulty.MEDIUM,
                "points": 100,
            },
            {
                "word": "Apa itu teh?",
                "answer": "TEH",
                "category": Category.LUCU,
                "difficulty": Difficulty.MEDIUM,
                "points": 100,
            },
            {
                "word": "Apa itu teh",
                "answer": "TEH BANGET",
                "category": Category.LUCU,
                "difficulty": Difficulty.MEDIUM,
                "points": 100,
            },
        ]

        created = QuestionRepository.bulk_create_questions(db_session, payload)

        assert len(created) == 1
        assert created[0].word == "Apa itu teh?"
