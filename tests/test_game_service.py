"""Tests for game service helpers."""

from unittest.mock import Mock

from src.app.services.game.service import GameService


class TestGameService:
    """Test helper formatting in GameService."""

    def setup_method(self):
        self.service = GameService(db=Mock())

    def test_format_answer_pattern_single_word(self):
        """Mask single-word answers."""
        assert self.service._format_answer_pattern("ayam") == "A**M"
        assert self.service._format_answer_pattern("ab") == "A*"
        assert self.service._format_answer_pattern("a") == "A"

    def test_format_answer_pattern_multi_word_and_symbols(self):
        """Mask multi-word answers while preserving separators."""
        assert self.service._format_answer_pattern("air mata") == "A*R M**A"
        assert self.service._format_answer_pattern("e-mail") == "E-***L"

    def test_start_game_blocked_when_active_game_exists(self):
        """Should not start a new round while active game exists."""
        self.service.read.get_active_game = Mock(return_value=Mock())

        game, message = self.service.start_game(
            chat_id=123,
            starter_telegram_id=456,
            starter_username="u",
            starter_full_name="U",
            category=None,
        )

        assert game is None
        assert "Masih ada soal aktif" in message
