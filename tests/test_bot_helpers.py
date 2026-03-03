"""
Tests for bot utility functions
"""
from src.bot.utils.helpers import (
    bind_topic,
    build_scope_chat_id,
    format_streak_emoji,
    get_badges,
    get_bound_topic,
    get_response_emoji,
    is_topic_allowed,
    scramble_word,
    unbind_topic,
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

    def test_build_scope_chat_id_non_topic(self):
        """Non-topic messages should use raw chat ID scope."""
        assert build_scope_chat_id(-1001234567890, None) == -1001234567890

    def test_build_scope_chat_id_topic_stable(self):
        """Topic scope must be stable and isolated per topic."""
        scope_a = build_scope_chat_id(-1001234567890, 11)
        scope_b = build_scope_chat_id(-1001234567890, 12)
        assert scope_a != scope_b
        assert scope_a == build_scope_chat_id(-1001234567890, 11)

    def test_topic_binding(self):
        """Topic binding should allow only bound topic."""
        chat_id = -1009876543210
        assert is_topic_allowed(chat_id, 55) is True

        bind_topic(chat_id, 77)
        assert get_bound_topic(chat_id) == 77
        assert is_topic_allowed(chat_id, 77) is True
        assert is_topic_allowed(chat_id, 78) is False
        assert is_topic_allowed(chat_id, None) is False

        assert unbind_topic(chat_id) is True
        assert get_bound_topic(chat_id) is None
        assert is_topic_allowed(chat_id, 78) is True
