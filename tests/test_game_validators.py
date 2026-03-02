"""
Tests for game validators
"""

import pytest

from src.app.models import Category
from src.app.services.game.modules.validators import GameValidators


class TestGameValidators:
    """Test game validation logic"""

    def test_validate_answer_correct(self):
        """Test answer validation with correct answer"""
        assert GameValidators.validate_answer("ucup", "UCUP") is True
        assert GameValidators.validate_answer("Ucup", "ucup") is True
        assert GameValidators.validate_answer("  ucup  ", "UCUP") is True

    def test_validate_answer_incorrect(self):
        """Test answer validation with incorrect answer"""
        assert GameValidators.validate_answer("ucup", "UCU") is False
        assert GameValidators.validate_answer("test", "wrong") is False

    def test_validate_hint_limit(self):
        """Test hint limit validation"""
        from unittest.mock import Mock

        game = Mock()
        game.current_hint_count = 0
        assert GameValidators.validate_hint_limit(game, 3) is True

        game.current_hint_count = 3
        assert GameValidators.validate_hint_limit(game, 3) is False

    def test_validate_category(self):
        """Test category validation"""
        assert GameValidators.validate_category("lucu") == Category.LUCU
        assert GameValidators.validate_category("mind_blowing") == Category.MIND_BLOWING
        assert GameValidators.validate_category("mindblowing") == Category.MIND_BLOWING

        with pytest.raises(ValueError):
            GameValidators.validate_category("invalid")

    def test_validate_points_after_hint(self):
        """Test point calculation after hints"""
        # Original 100 points, 1 hint, 0.5 penalty
        assert GameValidators.validate_points_after_hint(100, 0, 0.5) == 100
        assert GameValidators.validate_points_after_hint(100, 1, 0.5) == 50
        assert GameValidators.validate_points_after_hint(100, 2, 0.5) == 10  # minimum 10%

    def test_sanitize_text(self):
        """Test text sanitization"""
        assert GameValidators.sanitize_text("  test  ") == "test"
        assert GameValidators.sanitize_text("test   multiple   spaces") == "test multiple spaces"
