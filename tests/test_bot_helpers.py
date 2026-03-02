"""
Tests for bot utility functions
"""
from src.bot.utils.helpers import (
    format_streak_emoji,
    get_badges,
    get_response_emoji,
    scramble_word,
)


class TestBotHelpers:
    """Test bot utility functions"""

    def test_scramble_word_short(self):
        """Test scrambling short words (<=3 chars)"""
        assert scramble_word("abc") == "abc"
        assert scramble_word("ab") == "ab"

    def test_scramble_word_long(self):
        """Test scrambling longer words"""
        scrambled = scramble_word("indonesia")
        assert len(scrambled) == len("indonesia")
        assert sorted(scrambled) == sorted("indonesia")

    def test_get_response_emoji_correct(self):
        """Test response emoji for correct answers"""
        assert "🎉" in get_response_emoji(True, 200)
        assert "✅" in get_response_emoji(True, 50)

    def test_get_response_emoji_incorrect(self):
        """Test response emoji for incorrect answers"""
        assert get_response_emoji(False) == "❌"

    def test_format_streak_emoji(self):
        """Test streak emoji formatting"""
        assert format_streak_emoji(0) == ""
        assert format_streak_emoji(1) == "🔥"
        assert format_streak_emoji(3) == "🔥🔥🔥"
        # Max 5 fire emojis
        assert len(format_streak_emoji(10)) == 5  # "🔥🔥🔥🔥🔥"

    def test_get_badges(self):
        """Test badge awarding"""
        # No badges
        assert get_badges(0, 0, 0) == []

        # Raja Tebak Kata
        badges = get_badges(1000, 0, 0)
        assert any("Raja Tebak Kata" in b for b in badges)

        # On Fire
        badges = get_badges(0, 0, 5)
        assert any("On Fire" in b for b in badges)

        # Legendary
        badges = get_badges(0, 0, 10)
        assert any("Legendary" in b for b in badges)

        # Jenius
        badges = get_badges(0, 10, 0)
        assert any("Jenius" in b for b in badges)
