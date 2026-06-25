"""
Main entry point for HDRezka Telegram Bot
Runs aiogram bot and FastAPI server on the same asyncio event loop
"""
import asyncio
import logging
import sys

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from handlers import router, cache_manager
from server import app as fastapi_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class UvicornServer(uvicorn.Server):
    """Custom Uvicorn server that can be run in asyncio task"""

    async def serve_in_task(self):
        """Run server as asyncio task"""
        await self.serve()


async def start_bot(bot: Bot, dispatcher: Dispatcher):
    """Start aiogram bot"""
    logger.info("Starting Telegram bot...")

    # Register handlers
    dispatcher.include_router(router)

    # Start polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


async def stop_bot(bot: Bot, dispatcher: Dispatcher):
    """Stop aiogram bot"""
    logger.info("Stopping Telegram bot...")
    await dispatcher.stop_polling()
    await bot.session.close()
    await cache_manager.close()


async def main():
    """Main application entry point"""

    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please set required environment variables:")
        logger.error("  - BOT_TOKEN: Your Telegram bot token")
        logger.error("  - PUBLIC_URL: Public URL for streaming proxy")
        sys.exit(1)

    logger.info("="*60)
    logger.info("HDRezka Telegram Bot Starting")
    logger.info("="*60)
    logger.info(f"Bot: @{config.bot.token[:10]}...")
    logger.info(f"FastAPI: {config.server.host}:{config.server.port}")
    logger.info(f"Public URL: {config.server.public_url}")
    logger.info(f"Rezka Mirror: {config.rezka.mirror_url}")
    logger.info(f"Cache: {config.cache.backend} ({'enabled' if config.cache.enabled else 'disabled'})")
    logger.info("="*60)

    # Initialize bot and dispatcher
    bot = Bot(token=config.bot.token)
    dispatcher = Dispatcher(storage=MemoryStorage())

    # Configure Uvicorn server
    uvicorn_config = uvicorn.Config(
        app=fastapi_app,
        host=config.server.host,
        port=config.server.port,
        log_level="info",
        access_log=False
    )
    server = UvicornServer(config=uvicorn_config)

    # Create tasks for both bot and server
    server_task = None
    bot_task = None

    try:
        # For Python 3.11+: use TaskGroup
        if sys.version_info >= (3, 11):
            async with asyncio.TaskGroup() as tg:
                # Start FastAPI server
                tg.create_task(server.serve_in_task())

                # Give server a moment to start
                await asyncio.sleep(1)

                # Start Telegram bot
                tg.create_task(start_bot(bot, dispatcher))

            logger.info("All services started successfully")
        else:
            # Fallback for Python 3.10 and earlier
            server_task = asyncio.create_task(server.serve_in_task())
            await asyncio.sleep(1)
            bot_task = asyncio.create_task(start_bot(bot, dispatcher))

            # Wait for both tasks
            await asyncio.gather(server_task, bot_task)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal (Ctrl+C)")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("Shutting down...")

        # Cancel tasks if they exist
        if server_task and not server_task.done():
            server_task.cancel()
        if bot_task and not bot_task.done():
            bot_task.cancel()

        await stop_bot(bot, dispatcher)
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
