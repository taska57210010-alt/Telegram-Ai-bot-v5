"""
Middleware layer for aiogram 3.x.
Handles logging, throttling, and user registration.
"""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery

from database import Database
from rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """Log all incoming updates for debugging and analytics."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Log update and pass to handler."""
        update: Update = data.get("event_update")
        
        if update:
            user_id = None
            update_type = "unknown"
            
            if update.message:
                user_id = update.message.from_user.id
                update_type = "message"
            elif update.callback_query:
                user_id = update.callback_query.from_user.id
                update_type = "callback"
            elif update.pre_checkout_query:
                user_id = update.pre_checkout_query.from_user.id
                update_type = "pre_checkout"
            
            logger.debug(
                f"Update received: type={update_type}, user_id={user_id}, "
                f"update_id={update.update_id}"
            )
        
        return await handler(event, data)


class ThrottlingMiddleware(BaseMiddleware):
    """Global throttling middleware to prevent spam."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Check global rate limit before processing."""
        # Check global rate limit
        if not await rate_limiter.check_global_limit():
            logger.warning("Global rate limit exceeded")
            
            # Try to notify user if it's a message or callback
            if isinstance(event, Message):
                try:
                    await event.answer("⏱️ System is busy. Please try again in a moment.")
                except Exception:
                    pass
            elif isinstance(event, CallbackQuery):
                try:
                    await event.answer("⏱️ System is busy. Please try again.", show_alert=True)
                except Exception:
                    pass
            
            return None
        
        return await handler(event, data)


class UserRegistrationMiddleware(BaseMiddleware):
    """Automatically register new users on first interaction."""

    def __init__(self, db: Database):
        """Initialize with database instance."""
        super().__init__()
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Ensure user exists in database (with caching to reduce DB load)."""
        user = None
        
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user
        
        if user:
            # Check cache first to avoid hitting DB on every update
            from cache import cache
            exists_key = f"user_exists:{user.id}"
            
            if not await cache.get(exists_key):
                try:
                    # This will create user if not exists
                    await self.db.get_or_create_user(
                        user.id,
                        user.username or f"user_{user.id}"
                    )
                    # Cache for 1 hour - user definitely exists now
                    await cache.set(exists_key, True, ttl=3600)
                except Exception as e:
                    logger.warning(f"Failed to register user {user.id}: {e}")
        
        return await handler(event, data)
