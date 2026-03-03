"""Reply keyboard menu for Telegram bot commands."""

from telegram import ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Build the main command keyboard shown to users."""
    return ReplyKeyboardMarkup(
        keyboard=[
            ["/tebak", "/hint"],
            ["/skip", "/skor"],
            ["/refresh", "/help"],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Pilih menu atau ketik jawaban...",
    )
