"""Tests for game update service hint helpers."""

from unittest.mock import Mock

from src.app.services.game.modules.update import GameUpdateService


class TestGameUpdateService:
    """Test hint reveal helpers."""

    def setup_method(self):
        self.service = GameUpdateService(db=Mock())

    def test_reveal_mask_progress(self):
        """Hint mask should reveal progressively from left to right."""
        assert self.service._reveal_random_char("AYAM", 1) == "AY__"
        assert self.service._reveal_random_char("AYAM", 2) == "AYAM"

    def test_newly_revealed_positions(self):
        """Should report newly opened letter positions for each hint."""
        assert self.service._get_newly_revealed_positions("AYAM", 1) == [(1, "A"), (2, "Y")]
        assert self.service._get_newly_revealed_positions("AYAM", 2) == [(3, "A"), (4, "M")]

    def test_newly_revealed_positions_ignore_spaces(self):
        """Position numbering should ignore spaces/symbols."""
        assert self.service._get_newly_revealed_positions("AIR MATA", 1) == [(1, "A"), (2, "I")]
