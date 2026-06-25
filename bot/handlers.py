"""
Telegram bot handlers using aiogram 3.x
Handles search, content selection, and video delivery with caching
"""
import logging
from urllib.parse import quote
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from services.rezka import RezkaService, RezkaServiceError, SearchResult
from cache.storage import CacheManager, CacheKey
from config import config

logger = logging.getLogger(__name__)

# Initialize services
rezka_service = RezkaService(
    mirror_url=config.rezka.mirror_url,
    proxy={'http': config.rezka.proxy_url, 'https': config.rezka.proxy_url} if config.rezka.proxy_url else None,
    timeout=config.rezka.timeout,
    email=config.rezka.email,
    password=config.rezka.password
)

cache_manager = CacheManager(
    backend=config.cache.backend,
    sqlite_path=config.cache.sqlite_path
)

# Router for all handlers
router = Router()


class SearchStates(StatesGroup):
    """FSM states for search flow"""
    waiting_for_query = State()
    viewing_results = State()
    selecting_content = State()


def create_search_results_keyboard(results: list[SearchResult]) -> InlineKeyboardMarkup:
    """Create inline keyboard with search results"""
    buttons = []
    for idx, result in enumerate(results[:10]):  # Limit to 10 results
        rating_text = f"⭐ {result.rating:.1f}" if result.rating else ""
        button_text = f"{idx + 1}. {result.title} {rating_text}"
        buttons.append([
            InlineKeyboardButton(
                text=button_text[:60],  # Telegram button text limit
                callback_data=f"select:{idx}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_translators_keyboard(translators: dict) -> InlineKeyboardMarkup:
    """Create inline keyboard with available translators"""
    buttons = []
    for tr_id, tr_info in list(translators.items())[:10]:  # Limit to 10
        premium = "👑 " if tr_info.get('premium') else ""
        button_text = f"{premium}{tr_info['name']}"
        buttons.append([
            InlineKeyboardButton(
                text=button_text[:60],
                callback_data=f"trans:{tr_id}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_seasons_keyboard(episodes_info: list) -> InlineKeyboardMarkup:
    """Create inline keyboard with available seasons"""
    buttons = []
    for season_obj in episodes_info[:20]:  # Limit to 20 seasons
        season_num = season_obj['season']
        season_text = season_obj['season_text']
        episode_count = len(season_obj['episodes'])
        buttons.append([
            InlineKeyboardButton(
                text=f"{season_text} ({episode_count} episodes)",
                callback_data=f"season:{season_num}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_episodes_keyboard(episodes: list, season: int) -> InlineKeyboardMarkup:
    """Create inline keyboard with available episodes"""
    buttons = []
    for ep in episodes[:30]:  # Limit to 30 episodes
        ep_num = ep['episode']
        ep_text = ep['episode_text']
        buttons.append([
            InlineKeyboardButton(
                text=f"{ep_text}",
                callback_data=f"episode:{season}:{ep_num}"
            )
        ])

    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_to_seasons")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_resolutions_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard with resolution options"""
    buttons = [
        [InlineKeyboardButton(text="1080p Ultra HD", callback_data="res:1080p")],
        [InlineKeyboardButton(text="720p HD", callback_data="res:720p")],
        [InlineKeyboardButton(text="480p", callback_data="res:480p")],
        [InlineKeyboardButton(text="360p", callback_data="res:360p")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command"""
    await message.answer(
        "🎬 Welcome to HDRezka Streaming Bot!\n\n"
        "Send me a movie or series name to search.\n"
        "Example: Inception\n\n"
        "Commands:\n"
        "/search - Search for content\n"
        "/help - Show help message"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command"""
    await message.answer(
        "🎬 HDRezka Streaming Bot Help\n\n"
        "How to use:\n"
        "1. Send a movie/series name (e.g., 'Breaking Bad')\n"
        "2. Select from search results\n"
        "3. Choose translation/dubbing\n"
        "4. For series: select season and episode\n"
        "5. Choose video quality\n"
        "6. Watch directly in Telegram!\n\n"
        "Features:\n"
        "• Direct streaming (no downloads)\n"
        "• Seeking/rewinding support\n"
        "• Multiple qualities (360p-1080p)\n"
        "• Smart caching for faster replays\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/search - Search for content\n"
        "/cache_clear - Clear your cache (admin only)"
    )


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    """Handle /search command"""
    await message.answer("🔍 What would you like to watch?\nSend me a movie or series name:")
    await state.set_state(SearchStates.waiting_for_query)


@router.message(Command("cache_clear"))
async def cmd_cache_clear(message: Message):
    """Handle /cache_clear command (admin only)"""
    if message.from_user.id not in config.bot.admin_ids:
        await message.answer("❌ This command is only available to administrators.")
        return

    await cache_manager.clear_all()
    await message.answer("✅ Cache cleared successfully!")


@router.message(SearchStates.waiting_for_query)
@router.message(F.text & ~F.text.startswith('/'))
async def handle_search_query(message: Message, state: FSMContext):
    """Handle search query from user"""
    query = message.text.strip()

    if not query:
        await message.answer("❌ Please send a valid search query.")
        return

    status_msg = await message.answer(f"🔍 Searching for '{query}'...")

    try:
        results = await rezka_service.search(query)

        if not results:
            await status_msg.edit_text(
                f"❌ No results found for '{query}'.\n"
                "Try different keywords or check spelling."
            )
            await state.clear()
            return

        # Store results in FSM context
        await state.update_data(
            search_results=results,
            current_query=query
        )
        await state.set_state(SearchStates.viewing_results)

        await status_msg.edit_text(
            f"📋 Found {len(results)} results for '{query}':\n"
            "Select a title to watch:",
            reply_markup=create_search_results_keyboard(results)
        )

    except RezkaServiceError as e:
        logger.error(f"Search error: {e}")
        await status_msg.edit_text(
            f"❌ Search failed: {str(e)}\n"
            "Try again or use a different mirror."
        )
        await state.clear()


@router.callback_query(F.data.startswith("select:"))
async def handle_content_selection(callback: CallbackQuery, state: FSMContext):
    """Handle content selection from search results"""
    await callback.answer()

    # Get selected index
    idx = int(callback.data.split(":")[1])

    # Get stored results
    data = await state.get_data()
    results = data.get("search_results", [])

    if idx >= len(results):
        await callback.message.edit_text("❌ Invalid selection.")
        await state.clear()
        return

    selected = results[idx]

    # Show loading
    await callback.message.edit_text(
        f"📡 Loading: {selected.title}..."
    )

    try:
        # Get content info
        content_info = await rezka_service.get_content_info(selected.url)

        # Store in context
        await state.update_data(
            selected_url=selected.url,
            content_info=content_info
        )

        # Show content info with translators
        info_text = (
            f"📺 {content_info.title}\n"
            f"{'⭐ ' + str(content_info.rating) if content_info.rating else ''}\n"
            f"📅 {content_info.year or 'N/A'}\n"
            f"🎭 {content_info.content_type.capitalize()}\n\n"
            f"{content_info.description[:200]}...\n\n"
            f"🌐 Select translation/dubbing:"
        )

        if not content_info.translators:
            await callback.message.edit_text(
                f"{info_text}\n\n❌ No translators available for this content."
            )
            await state.clear()
            return

        await callback.message.edit_text(
            info_text,
            reply_markup=create_translators_keyboard(content_info.translators)
        )

    except RezkaServiceError as e:
        logger.error(f"Content loading error: {e}")
        await callback.message.edit_text(
            f"❌ Failed to load content: {str(e)}"
        )
        await state.clear()


@router.callback_query(F.data.startswith("trans:"))
async def handle_translator_selection(callback: CallbackQuery, state: FSMContext):
    """Handle translator selection"""
    await callback.answer()

    translator_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    content_info = data.get("content_info")

    if not content_info:
        await callback.message.edit_text("❌ Session expired. Please search again.")
        await state.clear()
        return

    # Store translator selection
    await state.update_data(translator_id=translator_id)

    # Handle based on content type
    if content_info.content_type == "movie":
        # Show resolution selection for movies
        await callback.message.edit_text(
            f"🎬 {content_info.title}\n"
            f"🌐 {content_info.translators[translator_id]['name']}\n\n"
            "📺 Select video quality:",
            reply_markup=create_resolutions_keyboard()
        )
    else:
        # Show seasons for series
        await callback.message.edit_text(
            f"📺 Loading seasons for {content_info.title}..."
        )

        try:
            episodes_info = await rezka_service.get_episodes_info(data["selected_url"])
            await state.update_data(episodes_info=episodes_info)

            await callback.message.edit_text(
                f"📺 {content_info.title}\n"
                f"🌐 {content_info.translators[translator_id]['name']}\n\n"
                "📚 Select season:",
                reply_markup=create_seasons_keyboard(episodes_info)
            )
        except RezkaServiceError as e:
            await callback.message.edit_text(f"❌ Failed to load seasons: {str(e)}")
            await state.clear()


@router.callback_query(F.data.startswith("season:"))
async def handle_season_selection(callback: CallbackQuery, state: FSMContext):
    """Handle season selection"""
    await callback.answer()

    season_num = int(callback.data.split(":")[1])
    data = await state.get_data()
    episodes_info = data.get("episodes_info", [])

    # Find season
    season_obj = next((s for s in episodes_info if s['season'] == season_num), None)
    if not season_obj:
        await callback.message.edit_text("❌ Season not found.")
        return

    await state.update_data(selected_season=season_num)

    await callback.message.edit_text(
        f"📺 {data['content_info'].title}\n"
        f"Season {season_num}\n\n"
        "📺 Select episode:",
        reply_markup=create_episodes_keyboard(season_obj['episodes'], season_num)
    )


@router.callback_query(F.data.startswith("episode:"))
async def handle_episode_selection(callback: CallbackQuery, state: FSMContext):
    """Handle episode selection"""
    await callback.answer()

    _, season_str, episode_str = callback.data.split(":")
    season = int(season_str)
    episode = int(episode_str)

    await state.update_data(
        selected_season=season,
        selected_episode=episode
    )

    data = await state.get_data()

    await callback.message.edit_text(
        f"📺 {data['content_info'].title}\n"
        f"S{season:02d}E{episode:02d}\n\n"
        "📺 Select video quality:",
        reply_markup=create_resolutions_keyboard()
    )


@router.callback_query(F.data.startswith("res:"))
async def handle_resolution_selection(callback: CallbackQuery, state: FSMContext):
    """Handle resolution selection and send video"""
    await callback.answer()

    resolution = callback.data.split(":")[1]
    data = await state.get_data()

    content_info = data.get("content_info")
    selected_url = data.get("selected_url")
    translator_id = data.get("translator_id")

    if not all([content_info, selected_url, translator_id]):
        await callback.message.edit_text("❌ Session expired. Please search again.")
        await state.clear()
        return

    # Show loading
    await callback.message.edit_text(
        f"⏳ Preparing video...\n"
        f"Quality: {resolution}"
    )

    try:
        # Check cache first
        cache_key = CacheKey(
            content_url=selected_url,
            resolution=resolution,
            season=data.get("selected_season"),
            episode=data.get("selected_episode")
        )

        cached_file_id = await cache_manager.get_file_id(cache_key) if config.cache.enabled else None

        if cached_file_id:
            logger.info(f"Using cached file_id: {cached_file_id}")
            # Send from cache
            await callback.message.answer_video(
                video=cached_file_id,
                caption=f"📺 {content_info.title}\n🎬 Cached video",
                supports_streaming=True
            )
            await callback.message.delete()
            await state.clear()
            return

        # Extract stream URL
        if content_info.content_type == "movie":
            stream_data = await rezka_service.get_movie_stream(
                selected_url,
                translator_id=translator_id,
                resolution=resolution
            )
        else:
            stream_data = await rezka_service.get_series_stream(
                selected_url,
                season=data["selected_season"],
                episode=data["selected_episode"],
                translator_id=translator_id,
                resolution=resolution
            )

        # Check cache first
        cache_key = CacheKey(
            content_url=selected_url,
            resolution=resolution,
            season=data.get("selected_season"),
            episode=data.get("selected_episode")
        )

        cached_file_id = await cache_manager.get_file_id(cache_key) if config.cache.enabled else None

        if cached_file_id:
            logger.info(f"Using cached file_id: {cached_file_id}")
            # Send from cache
            await callback.message.answer_video(
                video=cached_file_id,
                caption=f"📺 {content_info.title}\n🎬 Cached video",
                supports_streaming=True
            )
            await callback.message.delete()
            await state.clear()
            return

        # Extract stream URL
        if content_info.content_type == "movie":
            stream_data = await rezka_service.get_movie_stream(
                selected_url,
                translator_id=translator_id,
                resolution=resolution
            )
        else:
            stream_data = await rezka_service.get_series_stream(
                selected_url,
                season=data["selected_season"],
                episode=data["selected_episode"],
                translator_id=translator_id,
                resolution=resolution
            )

        # Construct proxy URL (through Cloudflare)
        encoded_cdn_url = quote(stream_data.cdn_url, safe='')
        proxy_url = f"{config.server.public_url}/stream?url={encoded_cdn_url}"

        logger.info(f"Sending video via proxy: {proxy_url[:100]}...")

        # Send video through proxy
        caption_parts = [f"📺 {stream_data.title}"]
        if stream_data.season and stream_data.episode:
            caption_parts.append(f"S{stream_data.season:02d}E{stream_data.episode:02d}")
        caption_parts.append(f"🌐 {stream_data.translator_name}")
        caption_parts.append(f"📺 {stream_data.resolution}")

        try:
            sent_message = await callback.message.answer_video(
                video=proxy_url,
                caption=" • ".join(caption_parts),
                supports_streaming=True
            )

            # Cache the file_id if video was sent successfully
            if config.cache.enabled and sent_message.video:
                file_id = sent_message.video.file_id
                await cache_manager.cache_file_id(cache_key, file_id)
                logger.info(f"Cached file_id: {file_id}")

            await callback.message.delete()
            await state.clear()

        except Exception as e:
            logger.error(f"Failed to send video, falling back to link: {e}")
            # Fallback: send as link
            await callback.message.answer(
                f"{' • '.join(caption_parts)}\n\n"
                f"🔗 Прямая ссылка:\n{stream_data.cdn_url}\n\n"
                f"💡 Откройте в браузере",
                disable_web_page_preview=False
            )
            await callback.message.delete()
            await state.clear()

    except RezkaServiceError as e:
        logger.error(f"Stream extraction error: {e}")
        await callback.message.edit_text(
            f"❌ Failed to extract stream: {str(e)}"
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Video sending error: {e}", exc_info=True)
        await callback.message.edit_text(
            f"❌ Failed to send video: {str(e)}\n"
            "This may be due to:\n"
            "• Network issues\n"
            "• Telegram file size limits\n"
            "• Invalid proxy configuration"
        )
        await state.clear()


@router.callback_query(F.data == "cancel")
async def handle_cancel(callback: CallbackQuery, state: FSMContext):
    """Handle cancel button"""
    await callback.answer()
    await callback.message.edit_text("❌ Cancelled.")
    await state.clear()


@router.callback_query(F.data == "back")
async def handle_back(callback: CallbackQuery, state: FSMContext):
    """Handle back button"""
    await callback.answer("Use /search to start a new search")
    await callback.message.edit_text("Use /search to start over.")
    await state.clear()


@router.callback_query(F.data == "back_to_seasons")
async def handle_back_to_seasons(callback: CallbackQuery, state: FSMContext):
    """Handle back to seasons"""
    await callback.answer()
    data = await state.get_data()
    episodes_info = data.get("episodes_info", [])
    content_info = data.get("content_info")

    await callback.message.edit_text(
        f"📺 {content_info.title}\n\n"
        "📚 Select season:",
        reply_markup=create_seasons_keyboard(episodes_info)
    )
