"""Tests for game service helpers."""

from unittest.mock import Mock, patch

from src.app.services.game.service import GameService
from src.app.services.game import service as game_service_module


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

    def test_start_game_blocked_when_player_unverified(self):
        """Unverified starter should not be able to start game."""
        self.service.read.get_active_game = Mock(return_value=None)
        self.service._is_player_verified = Mock(return_value=False)

        game, message = self.service.start_game(
            chat_id=123,
            starter_telegram_id=456,
            starter_username="u",
            starter_full_name="U",
            category=None,
        )

        assert game is None
        assert "belum terverifikasi" in message

    def test_submit_answer_blocked_when_player_unverified(self):
        """Unverified player should not be able to submit answer."""
        self.service.read.get_active_game = Mock(return_value=Mock())
        self.service._is_player_verified = Mock(return_value=False)

        is_correct, message, points = self.service.submit_answer(
            chat_id=123,
            telegram_id=456,
            username="u",
            full_name="U",
            answer="jawab",
        )

        assert is_correct is False
        assert points == 0
        assert "belum terverifikasi" in message

    def test_use_hint_blocked_when_player_unverified(self):
        """Unverified player should not be able to use hint."""
        self.service.read.get_active_game = Mock(return_value=Mock())
        self.service._is_player_verified = Mock(return_value=False)

        success, message = self.service.use_hint(chat_id=123, telegram_id=456)

        assert success is False
        assert "belum terverifikasi" in message

    def test_is_player_verified_admin_allowlist_bypass(self):
        """Configured admin username should bypass player verification flag."""
        with patch.object(game_service_module.env, "is_admin_username", return_value=True):
            with patch.object(
                game_service_module.PlayerRepository,
                "get_or_create_by_telegram_id",
            ) as mock_get_or_create:
                assert self.service._is_player_verified(telegram_id=123, username="admin")
                mock_get_or_create.assert_not_called()

    def test_is_player_verified_non_admin_reads_player_flag(self):
        """Non-admin users should follow players.is_verified state."""
        player = Mock(is_verified=False)
        with patch.object(game_service_module.env, "is_admin_username", return_value=False):
            with patch.object(
                game_service_module.PlayerRepository,
                "get_or_create_by_telegram_id",
                return_value=player,
            ):
                assert self.service._is_player_verified(telegram_id=123, username="user") is False
