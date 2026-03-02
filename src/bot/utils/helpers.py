"""
Bot utility functions

Helper functions for the Telegram bot.
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    """
    Check if a user is an admin in the current chat.

    Args:
        update: Telegram update object
        context: Bot context
        user_id: User ID to check

    Returns:
        True if user is admin, False otherwise
    """
    if not update.effective_chat:
        return False

    try:
        # Get chat member status
        chat_member = await context.bot.get_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_id,
        )

        # Check if user is admin or creator
        return chat_member.status in {"administrator", "creator"}

    except Exception as e:
        logger.error(f"Error checking admin status: {e}")
        return False


def scramble_word(word: str) -> str:
    """
    Scramble a word by shuffling its letters.

    Args:
        word: Word to scramble

    Returns:
        Scrambled word
    """
    import random

    if len(word) <= 3:
        return word

    letters = list(word)
    # Keep shuffling until it's different from original
    scrambled = letters[:]
    while scrambled == letters:
        random.shuffle(scrambled)

    return "".join(scrambled)


def get_response_emoji(is_correct: bool, points: int = 0) -> str:
    """
    Get an appropriate emoji based on response.

    Args:
        is_correct: Whether the answer was correct
        points: Points earned (for correct answers)

    Returns:
        Emoji string
    """
    if is_correct:
        if points >= 150:
            return "🎉🔥🏆"
        elif points >= 100:
            return "🎉✨"
        else:
            return "✅"
    else:
        return "❌"


def format_streak_emoji(streak: int) -> str:
    """
    Format streak as emoji fire icons.

    Args:
        streak: Current streak count

    Returns:
        Emoji string
    """
    if streak == 0:
        return ""
    return "🔥" * min(streak, 5)


def get_badges(total_score: int, games_won: int, current_streak: int) -> list[str]:
    """
    Get badges based on player stats.

    Args:
        total_score: Player's total score
        games_won: Number of games won
        current_streak: Current streak

    Returns:
        List of badge strings
    """
    badges = []

    if total_score >= 1000:
        badges.append("🏆 Raja Tebak Kata")
    if current_streak >= 5:
        badges.append("🔥 On Fire!")
    if current_streak >= 10:
        badges.append("⚡ Legendary")
    if games_won >= 10:
        badges.append("🧠 Jenius")

    return badges
