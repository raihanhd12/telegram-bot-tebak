"""In-memory countdown helpers for active game rounds."""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timezone

from telegram.ext import Application

from src.app.repositories.game import GameRepository
from src.bot.dependencies import get_game_service

logger = logging.getLogger(__name__)

_COUNTDOWN_TASKS: dict[int, asyncio.Task] = {}


def get_remaining_seconds(expires_at: datetime | None) -> int:
    """Return remaining seconds until expiration (ceil, never negative)."""
    if expires_at is None:
        return 0
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)  # noqa: UP017
    remaining = (expires_at - datetime.now(timezone.utc)).total_seconds()  # noqa: UP017
    return max(0, math.ceil(remaining))


def cancel_game_countdown(scoped_chat_id: int) -> None:
    """Cancel countdown task for a chat scope if exists."""
    task = _COUNTDOWN_TASKS.pop(scoped_chat_id, None)
    if task and not task.done():
        task.cancel()


def schedule_game_countdown(
    application: Application,
    chat_id: int,
    thread_id: int | None,
    scoped_chat_id: int,
    game_id: int,
    expires_at: datetime | None,
) -> None:
    """Schedule countdown + auto-expire notification for an active game."""
    if expires_at is None:
        return

    cancel_game_countdown(scoped_chat_id)
    task = application.create_task(
        _run_countdown(
            application=application,
            chat_id=chat_id,
            thread_id=thread_id,
            scoped_chat_id=scoped_chat_id,
            game_id=game_id,
            expires_at=expires_at,
        )
    )
    _COUNTDOWN_TASKS[scoped_chat_id] = task


async def _run_countdown(
    application: Application,
    chat_id: int,
    thread_id: int | None,
    scoped_chat_id: int,
    game_id: int,
    expires_at: datetime,
) -> None:
    """Run countdown workflow and send time-up message."""
    try:
        remaining = get_remaining_seconds(expires_at)
        if remaining <= 0:
            await _expire_and_announce(application, chat_id, thread_id, scoped_chat_id, game_id)
            return

        if remaining > 3:
            await asyncio.sleep(remaining - 3)

        start_second = min(3, remaining)
        for second in range(start_second, 0, -1):
            if not await _is_same_active_game(scoped_chat_id, game_id):
                return
            await _send_message(application, chat_id, thread_id, f"⏳ {second}...")
            await asyncio.sleep(1)

        await _expire_and_announce(application, chat_id, thread_id, scoped_chat_id, game_id)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Countdown task failed for scoped chat %s", scoped_chat_id)
    finally:
        current_task = asyncio.current_task()
        if _COUNTDOWN_TASKS.get(scoped_chat_id) is current_task:
            _COUNTDOWN_TASKS.pop(scoped_chat_id, None)


async def _is_same_active_game(scoped_chat_id: int, game_id: int) -> bool:
    """Check if the same game is still active in this scope."""
    game_service = get_game_service()
    try:
        game = GameRepository.get_active_game_by_chat(game_service.db, scoped_chat_id)
        return bool(game and game.id == game_id)
    finally:
        game_service.db.close()


async def _expire_and_announce(
    application: Application,
    chat_id: int,
    thread_id: int | None,
    scoped_chat_id: int,
    game_id: int,
) -> None:
    """Expire active game and announce final timeout message."""
    game_service = get_game_service()
    try:
        game = GameRepository.get_active_game_by_chat(game_service.db, scoped_chat_id)
        if not game or game.id != game_id:
            return

        message = game_service.expire_game(game)
        if message:
            await _send_message(application, chat_id, thread_id, message)
    finally:
        game_service.db.close()


async def _send_message(
    application: Application,
    chat_id: int,
    thread_id: int | None,
    text: str,
) -> None:
    """Send message in thread when available."""
    kwargs = {"chat_id": chat_id, "text": text, "parse_mode": None}
    if thread_id is not None:
        kwargs["message_thread_id"] = thread_id
    await application.bot.send_message(**kwargs)
