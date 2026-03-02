"""
Question repository

CRUD helpers for Question model. Handles fetching and managing
questions for the game.
"""

from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.models import Category, Question


class QuestionRepository:
    """Repository for Question model"""

    @staticmethod
    def _enum_value(value: Any) -> Any:
        """Normalize enum-like values to raw DB values."""
        return value.value if hasattr(value, "value") else value

    @staticmethod
    def get_by_id(db: Session, question_id: int) -> Question | None:
        """Get question by ID"""
        return db.query(Question).filter(Question.id == question_id).first()

    @staticmethod
    def get_by_word(db: Session, word: str) -> Question | None:
        """Get question by word (scrambled letters)"""
        return db.query(Question).filter(Question.word == word).first()

    @staticmethod
    def get_fresh_question(
        db: Session, category: Category | None = None, max_used_count: int = 3
    ) -> Question | None:
        """
        Get a fresh question (unused or used less than max_used_count times).

        Args:
            db: Database session
            category: Optional category filter
            max_used_count: Maximum times a question can be reused

        Returns:
            Question object or None if no fresh questions available
        """
        query = db.query(Question).filter(Question.is_active, Question.used_count < max_used_count)

        if category:
            query = query.filter(Question.category == QuestionRepository._enum_value(category))

        return query.order_by(Question.used_count.asc(), Question.created_at.desc()).first()

    @staticmethod
    def get_random_question(db: Session, category: Category | None = None) -> Question | None:
        """Get a random active question"""
        import random

        query = db.query(Question).filter(Question.is_active)

        if category:
            query = query.filter(Question.category == QuestionRepository._enum_value(category))

        questions = query.all()
        return random.choice(questions) if questions else None

    @staticmethod
    def list_questions(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        category: Category | None = None,
        is_active: bool | None = None,
    ) -> list[Question]:
        """List questions with optional filters"""
        query = db.query(Question)

        if category:
            query = query.filter(Question.category == QuestionRepository._enum_value(category))

        if is_active is not None:
            query = query.filter(Question.is_active == is_active)

        return query.offset(skip).limit(limit).all()

    @staticmethod
    def create_question(db: Session, **kwargs: Any) -> Question:
        """Create a new question"""
        question = Question(**kwargs)
        db.add(question)
        db.commit()
        db.refresh(question)
        return question

    @staticmethod
    def bulk_create_questions(db: Session, questions_data: list[dict[str, Any]]) -> list[Question]:
        """
        Bulk create questions.

        Duplicate `word` values are skipped to avoid failing the whole batch
        on unique index violations.

        Args:
            db: Database session
            questions_data: List of dictionaries containing question data

        Returns:
            List of created Question objects
        """
        if not questions_data:
            return []

        # 1) Deduplicate incoming payload by `word` (preserve first occurrence).
        unique_payload: list[dict[str, Any]] = []
        seen_words: set[str] = set()
        for data in questions_data:
            word = str(data.get("word", "")).strip().upper()
            if not word or word in seen_words:
                continue
            seen_words.add(word)
            normalized = dict(data)
            normalized["word"] = word
            unique_payload.append(normalized)

        if not unique_payload:
            return []

        # 2) Skip rows that already exist in DB.
        candidate_words = [item["word"] for item in unique_payload]
        existing_words = {
            row[0] for row in db.query(Question.word).filter(Question.word.in_(candidate_words)).all()
        }
        to_insert_payload = [item for item in unique_payload if item["word"] not in existing_words]

        if not to_insert_payload:
            return []

        questions = [Question(**data) for data in to_insert_payload]
        db.add_all(questions)

        try:
            db.commit()
            for question in questions:
                db.refresh(question)
            return questions
        except IntegrityError:
            # 3) Concurrency-safe fallback: insert one by one, skip duplicates.
            db.rollback()
            created: list[Question] = []
            for data in to_insert_payload:
                question = Question(**data)
                try:
                    db.add(question)
                    db.commit()
                    db.refresh(question)
                    created.append(question)
                except IntegrityError:
                    db.rollback()
                    continue
            return created

    @staticmethod
    def update_question(db: Session, question: Question, update_data: dict[str, Any]) -> Question:
        """Update an existing question"""
        for key, value in update_data.items():
            setattr(question, key, value)
        db.add(question)
        db.commit()
        db.refresh(question)
        return question

    @staticmethod
    def mark_as_used(db: Session, question: Question) -> Question:
        """
        Mark a question as used by incrementing used_count and updating last_used_at.

        Args:
            db: Database session
            question: Question to mark as used

        Returns:
            Updated Question object
        """
        question.used_count += 1
        question.last_used_at = datetime.utcnow()
        db.add(question)
        db.commit()
        db.refresh(question)
        return question

    @staticmethod
    def deactivate_stale_questions(db: Session, max_used_count: int = 3) -> int:
        """
        Deactivate questions that have been used too many times.

        Args:
            db: Database session
            max_used_count: Maximum allowed usage count

        Returns:
            Number of questions deactivated
        """
        count = (
            db.query(Question)
            .filter(Question.used_count >= max_used_count, Question.is_active)
            .update({"is_active": False})
        )
        db.commit()
        return count

    @staticmethod
    def count_active_questions(db: Session, category: Category | None = None) -> int:
        """Count active questions, optionally by category"""
        query = db.query(Question).filter(Question.is_active)

        if category:
            query = query.filter(Question.category == QuestionRepository._enum_value(category))

        return query.count()

    @staticmethod
    def delete_question(db: Session, question: Question) -> None:
        """Delete a question"""
        db.delete(question)
        db.commit()
