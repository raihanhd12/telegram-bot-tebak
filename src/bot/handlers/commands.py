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
from src.app.repositories.player import PlayerRepository
from src.bot.dependencies import get_game_service, get_llm_service
from src.bot.keyboards import main_menu_keyboard
from src.bot.utils.helpers import (
    bind_topic,
    build_scope_chat_id,
    get_bound_topic,
    get_message_thread_id,
    is_user_admin,
    unbind_topic,
)
from src.bot.utils.timers import cancel_game_countdown, schedule_game_countdown
from src.database.session import SessionLocal

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


def _resolve_scope(update: Update) -> tuple[int, int | None, int] | None:
    """Resolve raw chat/topic and scoped chat ID."""
    if not update.effective_chat:
        return None
    chat_id = update.effective_chat.id
    thread_id = get_message_thread_id(update)
    scoped_chat_id = build_scope_chat_id(chat_id, thread_id)
    return chat_id, thread_id, scoped_chat_id


def _get_topic_lock_message(chat_id: int, thread_id: int | None) -> str | None:
    """Return rejection message when chat is locked to another topic."""
    bound_topic = get_bound_topic(chat_id)
    if bound_topic is None or bound_topic == thread_id:
        return None
    return (
        f"🔒 Bot ini sedang dikunci ke topic `{bound_topic}`.\n"
        "Jalankan /deinitiate di topic tersebut, atau /initiate di topic ini oleh admin."
    )


async def _is_bot_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    telegram_user_id: int,
    username: str | None,
) -> bool:
    """Check whether user is bot admin based on env allowlist or chat admin role."""
    if env.ADMIN_TELEGRAM_USERNAMES:
        return env.is_admin_username(username)
    return await is_user_admin(update, context, telegram_user_id)


def _resolve_target_player(update: Update, args: list[str], db) -> tuple[object | None, str | None]:
    """Resolve target player from reply message or command argument."""
    message = update.effective_message
    if not message:
        return None, "❌ Message tidak valid."

    if getattr(message, "reply_to_message", None) and message.reply_to_message.from_user:
        replied_user = message.reply_to_message.from_user
        if replied_user.is_bot:
            return None, "❌ Tidak bisa verifikasi akun bot."
        player = PlayerRepository.get_or_create_by_telegram_id(
            db=db,
            telegram_id=replied_user.id,
            username=replied_user.username,
            full_name=replied_user.full_name,
        )
        return player, None

    if not args:
        return (
            None,
            "❌ Tentukan target player.\nGunakan `/verify @username` atau reply pesan user lalu `/verify`.",
        )

    target = args[0].strip()
    if not target:
        return None, "❌ Target player kosong."

    if target.isdigit():
        telegram_id = int(target)
        player = PlayerRepository.get_by_telegram_id(db, telegram_id)
        if not player:
            player = PlayerRepository.create_player(db, telegram_id=telegram_id)
        return player, None

    player = PlayerRepository.get_by_username(db, target)
    if not player:
        return None, f"❌ Player dengan username `{target}` belum ditemukan di database."
    return player, None


async def start_command(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - welcome message."""
    if not update.effective_message:
        return
    scope = _resolve_scope(update)
    if not scope:
        return
    chat_id, thread_id, _scoped_chat_id = scope

    topic_lock_message = _get_topic_lock_message(chat_id, thread_id)
    if topic_lock_message:
        await update.effective_message.reply_text(topic_lock_message, parse_mode=ParseMode.MARKDOWN)
        return

    message = (
        "🎮 *Selamat Datang di Tebak TTS!*\n\n"
        "Main tebak-tebakan ala TTS Cak Lontong bareng di grup Telegram. 🔥\n\n"
        "*Perintah Utama:*\n"
        "• `/tebak` - Mulai game baru\n"
        "• `/skip` - Lewati soal sekarang\n"
        "• `/hint` - Dapatkan hint\n"
        "• `/skor` - Lihat leaderboard\n"
        "• `/refresh` - Generate soal baru (Admin)\n\n"
        "• `/initiate` - Kunci bot ke topic ini (Admin)\n"
        "• `/deinitiate` - Lepas kunci topic (Admin)\n\n"
        "• `/verify` - Verifikasi pemain (Admin)\n"
        "• `/unverify` - Cabut verifikasi pemain (Admin)\n\n"
        "*Cara Main:*\n"
        "1. Ketik /tebak untuk mulai\n"
        "2. Baca pertanyaan jebakan\n"
        "3. Tebak jawaban nyeleneh ala TTS\n"
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
    scope = _resolve_scope(update)
    if not scope:
        return
    chat_id, thread_id, _scoped_chat_id = scope

    topic_lock_message = _get_topic_lock_message(chat_id, thread_id)
    if topic_lock_message:
        await update.effective_message.reply_text(topic_lock_message, parse_mode=ParseMode.MARKDOWN)
        return

    message = (
        "📖 *Panduan Bermain Tebak TTS*\n\n"
        "*Commands:*\n"
        "• `/tebak` - Mulai game baru\n"
        "• `/skip` - Lewati soal sekarang\n"
        "• `/hint` - Buka huruf jawaban (kurangi poin)\n"
        "• `/skor` - Leaderboard Top 5 pemain\n"
        "• `/refresh` - Generate soal baru (Admin)\n\n"
        "• `/initiate` - Kunci bot ke topic ini (Admin)\n"
        "• `/deinitiate` - Lepas kunci topic (Admin)\n\n"
        "• `/verify` - Verifikasi pemain (Admin)\n"
        "• `/unverify` - Cabut verifikasi pemain (Admin)\n\n"
        "*Fitur:*\n"
        "• ⏱️ Game timeout 60 detik\n"
        "• 💡 Max 3 hints per game\n"
        "• 🔥 Streak system\n"
        "• 🏆 Leaderboard per server\n"
        "• 🤖 Soal TTS generate dari AI\n\n"
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

    scope = _resolve_scope(update)
    if not scope:
        return
    chat_id, thread_id, scoped_chat_id = scope

    topic_lock_message = _get_topic_lock_message(chat_id, thread_id)
    if topic_lock_message:
        await update.effective_message.reply_text(topic_lock_message, parse_mode=ParseMode.MARKDOWN)
        return

    game_service = get_game_service()
    try:
        game, message = game_service.start_game(
            chat_id=scoped_chat_id,
            starter_telegram_id=user.id,
            starter_username=user.username,
            starter_full_name=user.full_name,
            category=None,
        )
        response_text = message or "❌ Gagal memulai game. Silakan coba lagi."

        await update.effective_message.reply_text(
            response_text,
            parse_mode=None,
        )
        if game and game.expires_at:
            schedule_game_countdown(
                application=context.application,
                chat_id=chat_id,
                thread_id=thread_id,
                scoped_chat_id=scoped_chat_id,
                game_id=game.id,
                expires_at=game.expires_at,
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

    scope = _resolve_scope(update)
    if not scope:
        return
    chat_id, thread_id, scoped_chat_id = scope

    topic_lock_message = _get_topic_lock_message(chat_id, thread_id)
    if topic_lock_message:
        await update.effective_message.reply_text(topic_lock_message, parse_mode=ParseMode.MARKDOWN)
        return

    # Check if user is admin (for now, allow everyone to skip)
    is_admin = await _is_bot_admin(update, context, user.id, user.username)

    game_service = get_game_service()
    try:
        success, message = game_service.skip_game(
            chat_id=scoped_chat_id,
            user_telegram_id=user.id,
            username=user.username,
            full_name=user.full_name,
            is_admin=is_admin,
        )

        await update.effective_message.reply_text(
            message,
            parse_mode=None,
        )
        if success:
            cancel_game_countdown(scoped_chat_id)
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

    scope = _resolve_scope(update)
    if not scope:
        return
    chat_id, thread_id, scoped_chat_id = scope

    topic_lock_message = _get_topic_lock_message(chat_id, thread_id)
    if topic_lock_message:
        await update.effective_message.reply_text(topic_lock_message, parse_mode=ParseMode.MARKDOWN)
        return

    game_service = get_game_service()
    try:
        leaderboard = game_service.get_leaderboard(chat_id=scoped_chat_id, limit=5)

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
    user = update.effective_user
    if not user:
        return

    scope = _resolve_scope(update)
    if not scope:
        return
    chat_id, thread_id, scoped_chat_id = scope

    topic_lock_message = _get_topic_lock_message(chat_id, thread_id)
    if topic_lock_message:
        await update.effective_message.reply_text(topic_lock_message, parse_mode=ParseMode.MARKDOWN)
        return

    game_service = get_game_service()
    try:
        success, message = game_service.use_hint(
            chat_id=scoped_chat_id,
            telegram_id=user.id,
            username=user.username,
            full_name=user.full_name,
        )

        await update.effective_message.reply_text(
            message,
            parse_mode=None,
        )
    except Exception:
        logger.exception("Failed to use hint")
        await update.effective_message.reply_text(
            "❌ Gagal mengambil hint karena terjadi error internal.",
            parse_mode=ParseMode.MARKDOWN,
        )
    finally:
        game_service.db.close()


async def initiate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lock the bot to current topic (admin only)."""
    if not update.effective_message or not update.effective_chat:
        return

    user = update.effective_user
    if not user:
        return

    chat_id = update.effective_chat.id
    thread_id = get_message_thread_id(update)

    if not thread_id:
        await update.effective_message.reply_text(
            "❌ `/initiate` hanya bisa dipakai di dalam topic forum.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    is_admin = await _is_bot_admin(update, context, user.id, user.username)
    if not is_admin:
        await update.effective_message.reply_text(
            "❌ Hanya admin yang bisa lock topic.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    previous_topic = get_bound_topic(chat_id)
    bind_topic(chat_id, thread_id)

    if previous_topic == thread_id:
        message = f"✅ Bot sudah aktif di topic ini (`{thread_id}`)."
    elif previous_topic is None:
        message = f"✅ Bot dikunci ke topic ini (`{thread_id}`)."
    else:
        message = (
            f"✅ Topic lock dipindah dari `{previous_topic}` ke `{thread_id}`.\n"
            "Sekarang bot hanya merespon di topic ini."
        )

    await update.effective_message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


async def deinitiate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove topic lock (admin only)."""
    if not update.effective_message or not update.effective_chat:
        return

    user = update.effective_user
    if not user:
        return

    is_admin = await _is_bot_admin(update, context, user.id, user.username)
    if not is_admin:
        await update.effective_message.reply_text(
            "❌ Hanya admin yang bisa melepas topic lock.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    chat_id = update.effective_chat.id
    was_unbound = unbind_topic(chat_id)

    if was_unbound:
        await update.effective_message.reply_text(
            "✅ Topic lock dilepas. Bot sekarang bisa dipakai di semua topic.",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.effective_message.reply_text(
            "ℹ️ Chat ini belum punya topic lock.",
            parse_mode=ParseMode.MARKDOWN,
        )


async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verify a player so they can play."""
    if not update.effective_message:
        return

    user = update.effective_user
    if not user:
        return

    is_admin = await _is_bot_admin(update, context, user.id, user.username)
    if not is_admin:
        await update.effective_message.reply_text(
            "❌ Hanya admin bot yang bisa verifikasi pemain.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    db = SessionLocal()
    try:
        player, error = _resolve_target_player(update, context.args, db)
        if error:
            await update.effective_message.reply_text(error, parse_mode=ParseMode.MARKDOWN)
            return
        if not player:
            await update.effective_message.reply_text(
                "❌ Target player tidak ditemukan.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        PlayerRepository.set_verified(db, player, True)
        username_display = f"@{player.username}" if player.username else "(tanpa username)"
        await update.effective_message.reply_text(
            (
                "✅ Player berhasil diverifikasi.\n"
                f"ID: `{player.telegram_id}`\n"
                f"Username: `{username_display}`"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    finally:
        db.close()


async def unverify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unverify a player so they cannot play."""
    if not update.effective_message:
        return

    user = update.effective_user
    if not user:
        return

    is_admin = await _is_bot_admin(update, context, user.id, user.username)
    if not is_admin:
        await update.effective_message.reply_text(
            "❌ Hanya admin bot yang bisa mencabut verifikasi pemain.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    db = SessionLocal()
    try:
        player, error = _resolve_target_player(update, context.args, db)
        if error:
            await update.effective_message.reply_text(error, parse_mode=ParseMode.MARKDOWN)
            return
        if not player:
            await update.effective_message.reply_text(
                "❌ Target player tidak ditemukan.",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        PlayerRepository.set_verified(db, player, False)
        username_display = f"@{player.username}" if player.username else "(tanpa username)"
        await update.effective_message.reply_text(
            (
                "✅ Verifikasi player dicabut.\n"
                f"ID: `{player.telegram_id}`\n"
                f"Username: `{username_display}`"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    finally:
        db.close()


async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /refresh command - generate new questions (Admin only)."""
    if not update.effective_message or not update.effective_chat:
        return

    scope = _resolve_scope(update)
    if not scope:
        return
    chat_id, thread_id, scoped_chat_id = scope

    topic_lock_message = _get_topic_lock_message(chat_id, thread_id)
    if topic_lock_message:
        await update.effective_message.reply_text(topic_lock_message, parse_mode=ParseMode.MARKDOWN)
        return

    user = update.effective_user
    if not user:
        return

    # Check if user is admin
    is_admin = await _is_bot_admin(update, context, user.id, user.username)

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

    refresh_lock = _get_refresh_lock(scoped_chat_id)
    if refresh_lock.locked():
        await update.effective_message.reply_text(
            "⏳ Refresh masih berjalan. Tunggu proses saat ini selesai.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    cooldown_remaining = _get_refresh_cooldown_remaining(scoped_chat_id)
    if cooldown_remaining > 0:
        await update.effective_message.reply_text(
            f"⏱️ /refresh sedang cooldown. Coba lagi dalam {cooldown_remaining} detik.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    async with refresh_lock:
        # Re-check inside lock to avoid race when many commands arrive together.
        cooldown_remaining = _get_refresh_cooldown_remaining(scoped_chat_id)
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
        refresh_success = False
        try:
            success, count, message = await llm_service.refresh_questions(count=env.LLM_REFRESH_COUNT)
            refresh_success = success
            response_text = message or "❌ Gagal generate soal."
        except Exception:
            logger.exception("Failed to refresh questions")
            response_text = "❌ Gagal generate soal karena koneksi LLM/DB bermasalah."
        finally:
            llm_service.db.close()
            if refresh_success:
                _refresh_last_run_at[scoped_chat_id] = time.monotonic()

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
