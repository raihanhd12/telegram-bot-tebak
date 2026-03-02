"""
Telegram Bot Command Handlers

All command handlers for the Tebak Kata bot.
"""

import asyncio
import logging
import time

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ContextTypes

import src.config.env as env
from src.bot.dependencies import get_game_service, get_llm_service
from src.bot.keyboards import main_menu_keyboard
from src.bot.utils.helpers import is_user_admin

logger = logging.getLogger(__name__)

_refresh_locks: dict[int, asyncio.Lock] = {}
_refresh_last_run_at: dict[int, float] = {}


def _get_refresh_lock(chat_id: int) -> asyncio.Lock:
    lock = _refresh_locks.get(chat_id)
    if lock is None:
        lock = asyncio.Lock()
        _refresh_locks[chat_id] = lock
    return lock


def _get_refresh_cooldown_remaining(chat_id: int) -> int:
    cooldown_seconds = max(0, int(env.LLM_REFRESH_COOLDOWN_SECONDS))
    if cooldown_seconds == 0:
        return 0

    last_run_at = _refresh_last_run_at.get(chat_id)
    if last_run_at is None:
        return 0

    elapsed = int(time.monotonic() - last_run_at)
    return max(0, cooldown_seconds - elapsed)


async def start_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - welcome message."""
    if not update.effective_message:
        return

    message = (
        "🎮 *Selamat Datang di Tebak Kata!*\n\n"
        "Bot tebak kata seru untuk grup Telegram! 🔥\n\n"
        "*Perintah Utama:*\n"
        "• `/tebak` - Mulai game baru\n"
        "• `/tebak lucu` - Mulai kategori Lucu\n"
        "• `/tebak mindblowing` - Mulai kategori Mind Blowing\n"
        "• `/skip` - Lewati soal sekarang\n"
        "• `/hint` - Dapatkan hint\n"
        "• `/skor` - Lihat leaderboard\n"
        "• `/refresh` - Generate soal baru (Admin)\n\n"
        "*Cara Main:*\n"
        "1. Ketik /tebak untuk mulai\n"
        "2. Tebak kata yang diacak\n"
        "3. Ketik jawaban langsung di chat\n"
        "4. Raih poin dan jadilah juara! 🏆\n\n"
        "Pastikan bot ditambahkan sebagai admin di grup!"
    )

    await update.effective_message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(),
    )


async def help_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not update.effective_message:
        return

    message = (
        "📖 *Panduan Bermain Tebak Kata*\n\n"
        "*Commands:*\n"
        "• `/tebak` - Mulai game baru\n"
        "• `/tebak lucu` - Kategori Lucu 😂\n"
        "• `/tebak mindblowing` - Kategori Mind Blowing 🤯\n"
        "• `/skip` - Lewati soal sekarang\n"
        "• `/hint` - Dapatkan hint (kurangi 50% poin)\n"
        "• `/skor` - Leaderboard Top 5\n"
        "• `/refresh` - Generate soal baru (Admin)\n\n"
        "*Fitur:*\n"
        "• ⏱️ Game timeout 60 detik\n"
        "• 💡 Max 3 hints per game\n"
        "• 🔥 Streak system\n"
        "• 🏆 Leaderboard per server\n\n"
        # "*Tips Admin:*\n"
        # "• Matikan Privacy Mode di @BotFather\n"
        # "• Jadikan bot sebagai admin grup"
    )

    await update.effective_message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(),
    )


async def tebak_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tebak command - start a new game."""
    if not update.effective_message or not update.effective_chat:
        return

    user = update.effective_user
    if not user:
        return

    # Get category from arguments
    category = None
    if context.args and len(context.args) > 0:
        category = context.args[0]

    game_service = get_game_service()
    try:
        game, message = game_service.start_game(
            chat_id=update.effective_chat.id,
            starter_telegram_id=user.id,
            starter_username=user.username,
            starter_full_name=user.full_name,
            category=category,
        )
        response_text = message or "❌ Gagal memulai game. Silakan coba lagi."

        await update.effective_message.reply_text(
            response_text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("Failed to start game")
        await update.effective_message.reply_text(
            (
                "❌ Gagal memulai game karena koneksi database bermasalah. "
                "Cek `DATABASE_URL` dan status DB."
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    finally:
        game_service.db.close()


async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /skip command - skip current game."""
    if not update.effective_message or not update.effective_chat:
        return

    user = update.effective_user
    if not user:
        return

    chat_id = update.effective_chat.id

    # Check if user is admin (for now, allow everyone to skip)
    is_admin = await is_user_admin(update, context, user.id)

    game_service = get_game_service()
    try:
        success, message = game_service.skip_game(
            chat_id=chat_id,
            user_telegram_id=user.id,
            is_admin=is_admin,
        )

        await update.effective_message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("Failed to skip game")
        await update.effective_message.reply_text(
            "❌ Gagal skip game karena terjadi error internal.",
            parse_mode=ParseMode.MARKDOWN,
        )
    finally:
        game_service.db.close()


async def score_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /skor command - show leaderboard."""
    if not update.effective_message or not update.effective_chat:
        return

    game_service = get_game_service()
    try:
        leaderboard = game_service.get_leaderboard(chat_id=update.effective_chat.id, limit=5)

        await update.effective_message.reply_text(
            leaderboard,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("Failed to get leaderboard")
        await update.effective_message.reply_text(
            "❌ Gagal mengambil leaderboard. Coba lagi sebentar.",
            parse_mode=ParseMode.MARKDOWN,
        )
    finally:
        game_service.db.close()


async def hint_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /hint command - get a hint."""
    if not update.effective_message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id

    game_service = get_game_service()
    try:
        success, message = game_service.use_hint(chat_id=chat_id)

        await update.effective_message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception:
        logger.exception("Failed to use hint")
        await update.effective_message.reply_text(
            "❌ Gagal mengambil hint karena terjadi error internal.",
            parse_mode=ParseMode.MARKDOWN,
        )
    finally:
        game_service.db.close()


async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /refresh command - generate new questions (Admin only)."""
    if not update.effective_message or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user
    if not user:
        return

    # Check if user is admin
    is_admin = await is_user_admin(update, context, user.id)

    if not is_admin:
        await update.effective_message.reply_text(
            "❌ Maaf, command ini hanya untuk admin grup.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Check if LLM is configured
    if (
        not env.LLM_URL
        or not env.LLM_HEADER_API_KEY
        or not env.LLM_MODEL_API_KEY
        or not env.LLM_AGENT_ID
    ):
        await update.effective_message.reply_text(
            "❌ LLM belum dikonfigurasi. Silakan hubungi owner bot.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    refresh_lock = _get_refresh_lock(chat_id)
    if refresh_lock.locked():
        await update.effective_message.reply_text(
            "⏳ Refresh masih berjalan. Tunggu proses saat ini selesai.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    cooldown_remaining = _get_refresh_cooldown_remaining(chat_id)
    if cooldown_remaining > 0:
        await update.effective_message.reply_text(
            f"⏱️ /refresh sedang cooldown. Coba lagi dalam {cooldown_remaining} detik.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    async with refresh_lock:
        # Re-check inside lock to avoid race when many commands arrive together.
        cooldown_remaining = _get_refresh_cooldown_remaining(chat_id)
        if cooldown_remaining > 0:
            await update.effective_message.reply_text(
                f"⏱️ /refresh sedang cooldown. Coba lagi dalam {cooldown_remaining} detik.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        # Send "generating" message
        status_message = await update.effective_message.reply_text(
            "🔄 Sedang generate soal baru... Mohon tunggu.",
        )

        llm_service = get_llm_service()
        try:
            success, count, message = await llm_service.refresh_questions(count=env.LLM_REFRESH_COUNT)
            response_text = message or "❌ Gagal generate soal."
        except Exception:
            logger.exception("Failed to refresh questions")
            response_text = "❌ Gagal generate soal karena koneksi LLM/DB bermasalah."
        finally:
            llm_service.db.close()
            _refresh_last_run_at[chat_id] = time.monotonic()

        # Update the status message
        try:
            await status_message.edit_text(
                response_text,
                parse_mode=None,
            )
        except BadRequest:
            logger.exception("Failed to edit refresh status message")
            # Fallback: kirim pesan baru plain-text agar user tetap dapat hasil.
            await update.effective_message.reply_text(response_text, parse_mode=None)
