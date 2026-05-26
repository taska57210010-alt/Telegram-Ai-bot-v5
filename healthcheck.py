"""
Production health check script.
Validates all critical services.
"""

import asyncio
import sys

async def check_health():
    """Check health of all services."""
    try:
        # Import here to avoid circular dependencies
        from config import config
        from database import Database
        from cache import cache
        from aiogram import Bot
        
        print("🔍 Checking health...")
        
        # Check database
        print("  ├─ Database...", end=" ")
        db = Database()
        await db.initialize()
        # Try a simple query
        await db.get_user_balance(1)
        await db.close()
        print("✅")
        
        # Check Redis
        print("  ├─ Redis...", end=" ")
        await cache.initialize()
        await cache.set("health_check", "ok", ttl=10)
        result = await cache.get("health_check")
        await cache.close()
        if result != "ok":
            raise Exception("Redis read/write failed")
        print("✅")
        
        # Check Telegram API
        print("  ├─ Telegram API...", end=" ")
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        await bot.get_me()
        await bot.session.close()
        print("✅")
        
        print("\n✅ All health checks passed!")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_health())
