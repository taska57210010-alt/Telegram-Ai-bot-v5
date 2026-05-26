"""
Admin command handlers for bot management.
Provides admin panel functionality for user management and analytics.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from config import config
from database import Database
from monitoring import monitoring

logger = logging.getLogger(__name__)

# Admin router
admin_router = Router()


class AdminState(StatesGroup):
    """Admin FSM states."""
    waiting_for_ban_user_id = State()
    waiting_for_unban_user_id = State()
    waiting_for_broadcast_message = State()


# ============ ADMIN COMMAND HANDLERS ============

@admin_router.message(Command("admin"))
async def handle_admin_panel(message: Message, db: Database) -> None:
    """Show admin panel."""
    user_id = message.from_user.id
    
    if not config.is_admin(user_id):
        await message.answer("❌ Access denied. Admin only.")
        return
    
    admin_text = (
        "<b>🔧 Admin Panel</b>\n\n"
        "<b>Available Commands:</b>\n"
        "/stats - View bot statistics\n"
        "/ban - Ban a user\n"
        "/unban - Unban a user\n"
        "/broadcast - Send message to all users\n"
        "/maintenance - Toggle maintenance mode\n"
        "/admin - Show this panel\n"
    )
    
    await message.answer(admin_text)
    logger.info(f"Admin panel accessed by {user_id}")


@admin_router.message(Command("stats"))
async def handle_admin_stats(message: Message, db: Database) -> None:
    """Show bot statistics."""
    user_id = message.from_user.id
    
    if not config.is_admin(user_id):
        await message.answer("❌ Access denied. Admin only.")
        return
    
    try:
        # Get statistics from database
        async with db.async_session() as session:
            from sqlalchemy import select, func
            from database import User, Payment, QuestionLog
            
            # Total users
            total_users_result = await session.execute(
                select(func.count(User.user_id))
            )
            total_users = total_users_result.scalar() or 0
            
            # Active users (asked question in last 24h)
            yesterday = datetime.utcnow() - timedelta(days=1)
            active_users_result = await session.execute(
                select(func.count(func.distinct(QuestionLog.user_id)))
                .where(QuestionLog.created_at >= yesterday)
            )
            active_users = active_users_result.scalar() or 0
            
            # Total questions asked
            total_questions_result = await session.execute(
                select(func.count(QuestionLog.log_id))
            )
            total_questions = total_questions_result.scalar() or 0
            
            # Total payments
            total_payments_result = await session.execute(
                select(func.count(Payment.payment_id))
                .where(Payment.payment_status == "completed")
            )
            total_payments = total_payments_result.scalar() or 0
            
            # Total revenue (stars)
            total_revenue_result = await session.execute(
                select(func.sum(Payment.amount_stars))
                .where(Payment.payment_status == "completed")
            )
            total_revenue = total_revenue_result.scalar() or 0
            
            # Questions today
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            questions_today_result = await session.execute(
                select(func.count(QuestionLog.log_id))
                .where(QuestionLog.created_at >= today)
            )
            questions_today = questions_today_result.scalar() or 0
        
        stats_text = (
            "<b>📊 Bot Statistics</b>\n\n"
            f"<b>Users:</b>\n"
            f"├ Total: <code>{total_users}</code>\n"
            f"└ Active (24h): <code>{active_users}</code>\n\n"
            f"<b>Questions:</b>\n"
            f"├ Total: <code>{total_questions}</code>\n"
            f"└ Today: <code>{questions_today}</code>\n\n"
            f"<b>Revenue:</b>\n"
            f"├ Payments: <code>{total_payments}</code>\n"
            f"└ Stars: <code>{total_revenue}</code>\n\n"
            f"<b>System:</b>\n"
            f"├ Maintenance: <code>{'ON' if config.MAINTENANCE_MODE else 'OFF'}</code>\n"
            f"└ Payments: <code>{'Enabled' if config.PAYMENTS_ENABLED else 'Disabled'}</code>"
        )
        
        await message.answer(stats_text)
        logger.info(f"Stats viewed by admin {user_id}")
        
    except Exception as e:
        logger.exception(f"Failed to get stats: {e}")
        monitoring.capture_exception(e, {"admin_id": user_id})
        await message.answer("❌ Failed to retrieve statistics.")


@admin_router.message(Command("ban"))
async def handle_ban_user(message: Message, state: FSMContext) -> None:
    """Ban a user."""
    user_id = message.from_user.id
    
    if not config.is_admin(user_id):
        await message.answer("❌ Access denied. Admin only.")
        return
    
    await state.set_state(AdminState.waiting_for_ban_user_id)
    await message.answer(
        "<b>🚫 Ban User</b>\n\n"
        "Send the user ID to ban.\n"
        "Use /cancel to abort."
    )


@admin_router.message(AdminState.waiting_for_ban_user_id)
async def process_ban_user(message: Message, state: FSMContext, db: Database) -> None:
    """Process user ban."""
    admin_id = message.from_user.id
    
    try:
        target_user_id = int(message.text.strip())
        
        # Don't allow banning admins
        if config.is_admin(target_user_id):
            await message.answer("❌ Cannot ban an admin user.")
            await state.clear()
            return
        
        # Ban user in database
        async with db.async_session() as session:
            from sqlalchemy import update
            from database import User
            
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(is_banned=True, updated_at=datetime.utcnow())
            )
            await session.commit()
        
        # Invalidate ban cache for immediate enforcement
        from cache import cache
        ban_key = f"user_banned:{target_user_id}"
        await cache.set(ban_key, True, ttl=300)
        
        await message.answer(f"✅ User <code>{target_user_id}</code> has been banned.")
        logger.info(f"User {target_user_id} banned by admin {admin_id}")
        
    except ValueError:
        await message.answer("❌ Invalid user ID. Please send a numeric ID.")
        return
    except Exception as e:
        logger.exception(f"Failed to ban user: {e}")
        await message.answer("❌ Failed to ban user.")
    finally:
        await state.clear()


@admin_router.message(Command("unban"))
async def handle_unban_user(message: Message, state: FSMContext) -> None:
    """Unban a user."""
    user_id = message.from_user.id
    
    if not config.is_admin(user_id):
        await message.answer("❌ Access denied. Admin only.")
        return
    
    await state.set_state(AdminState.waiting_for_unban_user_id)
    await message.answer(
        "<b>✅ Unban User</b>\n\n"
        "Send the user ID to unban.\n"
        "Use /cancel to abort."
    )


@admin_router.message(AdminState.waiting_for_unban_user_id)
async def process_unban_user(message: Message, state: FSMContext, db: Database) -> None:
    """Process user unban."""
    admin_id = message.from_user.id
    
    try:
        target_user_id = int(message.text.strip())
        
        # Unban user in database
        async with db.async_session() as session:
            from sqlalchemy import update
            from database import User
            
            await session.execute(
                update(User)
                .where(User.user_id == target_user_id)
                .values(is_banned=False, updated_at=datetime.utcnow())
            )
            await session.commit()
        
        # Invalidate ban cache for immediate enforcement
        from cache import cache
        ban_key = f"user_banned:{target_user_id}"
        await cache.set(ban_key, False, ttl=300)
        
        await message.answer(f"✅ User <code>{target_user_id}</code> has been unbanned.")
        logger.info(f"User {target_user_id} unbanned by admin {admin_id}")
        
    except ValueError:
        await message.answer("❌ Invalid user ID. Please send a numeric ID.")
        return
    except Exception as e:
        logger.exception(f"Failed to unban user: {e}")
        await message.answer("❌ Failed to unban user.")
    finally:
        await state.clear()


@admin_router.message(Command("broadcast"))
async def handle_broadcast(message: Message, state: FSMContext) -> None:
    """Broadcast message to all users."""
    user_id = message.from_user.id
    
    if not config.is_admin(user_id):
        await message.answer("❌ Access denied. Admin only.")
        return
    
    await state.set_state(AdminState.waiting_for_broadcast_message)
    await message.answer(
        "<b>📢 Broadcast Message</b>\n\n"
        "Send the message to broadcast to all users.\n"
        "Use /cancel to abort.\n\n"
        "⚠️ <i>This will send to ALL users!</i>"
    )


@admin_router.message(AdminState.waiting_for_broadcast_message)
async def process_broadcast(message: Message, state: FSMContext, db: Database) -> None:
    """Process broadcast message."""
    admin_id = message.from_user.id
    broadcast_text = message.text
    
    if not broadcast_text:
        await message.answer("❌ Message cannot be empty.")
        return
    
    try:
        # Get all user IDs
        async with db.async_session() as session:
            from sqlalchemy import select
            from database import User
            
            result = await session.execute(
                select(User.user_id).where(User.is_banned == False)
            )
            user_ids = [row[0] for row in result.fetchall()]
        
        await message.answer(
            f"📤 Broadcasting to <code>{len(user_ids)}</code> users...\n"
            f"This may take a while."
        )
        
        # Import bot from message
        bot = message.bot
        
        # Telegram rate limit: 30 messages/second
        # Use semaphore to stay under limit
        from aiogram.exceptions import TelegramRetryAfter
        
        semaphore = asyncio.Semaphore(25)  # Stay under 30/s limit
        
        async def send_one(user_id: int) -> bool:
            """Send message to one user with rate limiting."""
            async with semaphore:
                try:
                    await bot.send_message(user_id, broadcast_text, parse_mode="HTML")
                    return True
                except TelegramRetryAfter as e:
                    # Telegram asked us to wait - respect it
                    logger.warning(f"Rate limited, waiting {e.retry_after}s")
                    await asyncio.sleep(e.retry_after)
                    try:
                        await bot.send_message(user_id, broadcast_text, parse_mode="HTML")
                        return True
                    except Exception:
                        return False
                except Exception as e:
                    logger.warning(f"Broadcast failed for {user_id}: {e}")
                    return False
        
        # Send to all users concurrently (but rate-limited)
        results = await asyncio.gather(*[send_one(uid) for uid in user_ids])
        success_count = sum(results)
        fail_count = len(results) - success_count
        
        await message.answer(
            f"✅ <b>Broadcast Complete</b>\n\n"
            f"✅ Sent: <code>{success_count}</code>\n"
            f"❌ Failed: <code>{fail_count}</code>"
        )
        
        logger.info(
            f"Broadcast by admin {admin_id}: {success_count} sent, {fail_count} failed"
        )
        
    except Exception as e:
        logger.exception(f"Broadcast failed: {e}")
        monitoring.capture_exception(e, {"admin_id": admin_id})
        await message.answer("❌ Broadcast failed.")
    finally:
        await state.clear()


@admin_router.message(Command("maintenance"))
async def handle_maintenance_toggle(message: Message) -> None:
    """Toggle maintenance mode."""
    user_id = message.from_user.id
    
    if not config.is_admin(user_id):
        await message.answer("❌ Access denied. Admin only.")
        return
    
    # Note: This only shows current state. To actually toggle, you'd need to
    # modify the config or use a database flag
    current_state = "ON" if config.MAINTENANCE_MODE else "OFF"
    
    await message.answer(
        f"<b>🔧 Maintenance Mode</b>\n\n"
        f"Current state: <code>{current_state}</code>\n\n"
        f"<i>To toggle, update MAINTENANCE_MODE in .env and restart the bot.</i>"
    )
    
    logger.info(f"Maintenance mode checked by admin {user_id}")
