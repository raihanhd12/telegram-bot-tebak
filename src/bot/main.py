"""
Telegram Bot "Tebak TTS" - Main Entry Point

A fun TTS-style guessing game for Telegram groups with LLM-generated questions.
"""

import logging
import os
import sys

from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import src.config.env as env
from src.bot.dependencies import get_game_service
from src.bot.handlers.commands import (
    deinitiate_command,
    help_command,
    hint_command,
    initiate_command,
    refresh_command,
    score_command,
    skip_command,
    start_command,
    tebak_command,
    unverify_command,
    verify_command,
)
from src.bot.utils.helpers import build_scope_chat_id, get_message_thread_id, is_topic_allowed
from src.bot.utils.timers import cancel_game_countdown, get_remaining_seconds

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, env.LOG_LEVEL),
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Post-initialization hook."""
    await application.bot.set_my_commands(
        commands=[
            BotCommand("start", "Mulai bot dan tampilkan menu"),
            BotCommand("help", "Lihat panduan bermain"),
            BotCommand("tebak", "Mulai game tebak TTS"),
            BotCommand("hint", "Buka petunjuk jawaban"),
            BotCommand("skip", "Lewati soal yang sedang aktif"),
            BotCommand("skor", "Lihat leaderboard"),
            BotCommand("refresh", "Generate soal TTS baru (admin)"),
            BotCommand("initiate", "Kunci bot di topic ini (admin)"),
            BotCommand("deinitiate", "Lepas kunci topic (admin)"),
            BotCommand("verify", "Verifikasi pemain (admin)"),
            BotCommand("unverify", "Cabut verifikasi pemain (admin)"),
        ]
    )
    logger.info(f"Bot started successfully! @{application.bot.username}")
    logger.info(f"Environment: {env.ENVIRONMENT}")


async def error_handler(_update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)


# Message handler for text answers
async def handle_message(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages - check if it's an answer to an active game."""
    if not update.effective_message or not update.effective_message.text:
        return

    if not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    thread_id = get_message_thread_id(update)
    scoped_chat_id = build_scope_chat_id(chat_id, thread_id)

    if not is_topic_allowed(chat_id, thread_id):
        return

    user = update.effective_user
    if not user:
        return

    # Get game service
    game_service = get_game_service()
    try:
        # Check if there's an active game
        active_game = game_service.get_active_game(scoped_chat_id)

        if not active_game:
            # No active game, ignore the message
            return

        # Get the user's answer
        user_answer = update.effective_message.text.strip()

        # Check if it's a command (skip commands)
        if user_answer.startswith("/"):
            return

        # Submit the answer
        is_correct, message, points = game_service.submit_answer(
            chat_id=scoped_chat_id,
            telegram_id=user.id,
            username=user.username,
            full_name=user.full_name,
            answer=user_answer,
        )
        response_text = message or "❌ Terjadi kesalahan saat memproses jawaban."

        active_after = game_service.get_active_game(scoped_chat_id)
        if is_correct:
            cancel_game_countdown(scoped_chat_id)
        elif active_after and active_after.expires_at:
            remaining_seconds = get_remaining_seconds(active_after.expires_at)
            response_text = f"{response_text}\n⏱️ Sisa waktu: {remaining_seconds} detik."
        elif not active_after:
            cancel_game_countdown(scoped_chat_id)

        # Send the response
        await update.effective_message.reply_text(
            response_text,
            parse_mode=None,
        )
    except Exception:
        logger.exception("Failed to process incoming message")
    finally:
        # Close the DB session
        game_service.db.close()


def main() -> None:
    """Start the bot."""
    # Check for bot token
    if not env.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set! Please set it in .env or environment variables.")
        sys.exit(1)

    # Build the application
    application = Application.builder().token(env.BOT_TOKEN).post_init(post_init).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("tebak", tebak_command))
    application.add_handler(CommandHandler("skip", skip_command))
    application.add_handler(CommandHandler("skor", score_command))
    application.add_handler(CommandHandler("hint", hint_command))
    application.add_handler(CommandHandler("refresh", refresh_command))
    application.add_handler(CommandHandler("initiate", initiate_command))
    application.add_handler(CommandHandler("deinitiate", deinitiate_command))
    application.add_handler(CommandHandler("verify", verify_command))
    application.add_handler(CommandHandler("unverify", unverify_command))

    # Register message handler for answers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
