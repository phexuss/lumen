"""
Async wrapper for HdRezkaApi library
Provides non-blocking interface for Telegram bot
"""
import sys
import asyncio
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from urllib.parse import urlparse

sys.path.insert(0, '/app/rezka_lib')

from rezka_lib.HdRezkaApi import HdRezkaApi, HdRezkaSearch
from rezka_lib.HdRezkaApi.types import TVSeries, Movie
from rezka_lib.HdRezkaApi.errors import HTTP, LoginRequiredError, CaptchaError, FetchFailed


@dataclass
class SearchResult:
    """Search result data structure"""
    title: str
    url: str
    rating: Optional[float]


@dataclass
class ContentInfo:
    """Content metadata"""
    title: str
    content_type: str  # "movie" or "series"
    year: Optional[int]
    rating: Optional[float]
    description: str
    translators: Dict[int, Dict[str, Any]]


@dataclass
class EpisodeInfo:
    """TV series episode information"""
    season: int
    episode: int
    season_text: str
    episode_text: str
    translations: List[Dict[str, Any]]


@dataclass
class StreamData:
    """Stream URL and metadata"""
    cdn_url: str
    resolution: str
    translator_id: int
    translator_name: str
    title: str
    content_type: str
    season: Optional[int] = None
    episode: Optional[int] = None


class RezkaServiceError(Exception):
    """Base exception for Rezka service errors"""
    pass


class RezkaService:
    """Async service for HDRezka operations"""

    def __init__(self, mirror_url: str, proxy: Optional[Dict] = None, timeout: int = 30, email: Optional[str] = None, password: Optional[str] = None):
        self.mirror_url = mirror_url
        self.proxy = proxy or {}
        self.timeout = timeout
        self.email = email
        self.password = password
        self.cookies = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        # Login if credentials provided
        if self.email and self.password:
            self._login()

    def _login(self):
        """Login to HDRezka and store cookies"""
        try:
            from rezka_lib.HdRezkaApi import HdRezkaApi
            api = HdRezkaApi(self.mirror_url, headers=self.headers, proxy=self.proxy)
            if api.login(email=self.email, password=self.password):
                self.cookies = api.cookies
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"HDRezka login failed: {e}")

    async def search(self, query: str) -> List[SearchResult]:
        """
        Search for content by title

        Args:
            query: Search query string

        Returns:
            List of search results

        Raises:
            RezkaServiceError: If search fails
        """
        def _search():
            search_engine = HdRezkaSearch(
                self.mirror_url,
                proxy=self.proxy,
                headers=self.headers,
                cookies=self.cookies
            )
            return search_engine(query)

        try:
            results = await asyncio.to_thread(_search)
            return [
                SearchResult(
                    title=r['title'],
                    url=r['url'],
                    rating=r.get('rating')
                )
                for r in results
            ]
        except Exception as e:
            raise RezkaServiceError(f"Search failed: {e}") from e

    async def get_content_info(self, url: str) -> ContentInfo:
        """
        Load content metadata

        Args:
            url: Content URL

        Returns:
            ContentInfo object

        Raises:
            RezkaServiceError: If loading fails
        """
        def _load():
            rezka = HdRezkaApi(url, proxy=self.proxy, headers=self.headers, cookies=self.cookies)
            if not rezka.ok:
                raise rezka.exception
            return rezka

        try:
            rezka = await asyncio.to_thread(_load)

            # Safe property access with fallbacks
            try:
                title = rezka.name
            except Exception:
                title = "Unknown Title"

            try:
                content_type = "movie" if rezka.type == Movie else "series"
            except Exception:
                content_type = "unknown"

            try:
                year = rezka.releaseYear
            except Exception:
                year = None

            try:
                rating = float(rezka.rating) if rezka.rating else None
            except Exception:
                rating = None

            try:
                description = rezka.description[:500]
            except Exception:
                description = ""

            try:
                translators = rezka.translators
            except Exception:
                translators = {}

            return ContentInfo(
                title=title,
                content_type=content_type,
                year=year,
                rating=rating,
                description=description,
                translators=translators
            )
        except Exception as e:
            raise RezkaServiceError(f"Failed to load content: {e}") from e

    async def get_episodes_info(self, url: str) -> List[Dict[str, Any]]:
        """
        Get TV series episodes structure

        Args:
            url: Content URL

        Returns:
            List of seasons with episodes

        Raises:
            RezkaServiceError: If loading fails
        """
        def _load():
            rezka = HdRezkaApi(url, proxy=self.proxy, headers=self.headers, cookies=self.cookies)
            if not rezka.ok:
                raise rezka.exception
            return rezka.episodesInfo

        try:
            return await asyncio.to_thread(_load)
        except Exception as e:
            raise RezkaServiceError(f"Failed to load episodes: {e}") from e

    async def get_movie_stream(
        self,
        url: str,
        translator_id: Optional[int] = None,
        resolution: str = "720p"
    ) -> StreamData:
        """
        Extract movie stream URL

        Args:
            url: Content URL
            translator_id: Optional translator ID
            resolution: Preferred resolution

        Returns:
            StreamData object

        Raises:
            RezkaServiceError: If extraction fails
        """
        def _extract():
            rezka = HdRezkaApi(url, proxy=self.proxy, headers=self.headers, cookies=self.cookies)
            if not rezka.ok:
                raise rezka.exception

            stream = rezka.getStream(translation=translator_id)

            # Get title safely
            try:
                title = rezka.name
            except Exception:
                title = "Unknown Movie"

            # Find best available resolution
            selected_resolution = resolution  # Use parameter value
            if selected_resolution in stream.videos:
                urls = stream.videos[selected_resolution]
            else:
                # Fallback to highest available
                available = list(stream.videos.keys())
                selected_resolution = available[-1] if available else "720p"
                urls = stream.videos.get(selected_resolution, [])

            if not urls:
                raise RezkaServiceError("No stream URLs found")

            translator_name = rezka.translators.get(
                stream.translator_id, {}
            ).get('name', 'Unknown')

            return StreamData(
                cdn_url=urls[0],  # Use first CDN mirror
                resolution=selected_resolution,
                translator_id=stream.translator_id,
                translator_name=translator_name,
                title=title,
                content_type="movie"
            )

        try:
            return await asyncio.to_thread(_extract)
        except Exception as e:
            raise RezkaServiceError(f"Failed to extract stream: {e}") from e

    async def get_series_stream(
        self,
        url: str,
        season: int,
        episode: int,
        translator_id: Optional[int] = None,
        resolution: str = "720p"
    ) -> StreamData:
        """
        Extract TV series episode stream URL

        Args:
            url: Content URL
            season: Season number
            episode: Episode number
            translator_id: Optional translator ID
            resolution: Preferred resolution

        Returns:
            StreamData object

        Raises:
            RezkaServiceError: If extraction fails
        """
        def _extract():
            rezka = HdRezkaApi(url, proxy=self.proxy, headers=self.headers, cookies=self.cookies)
            if not rezka.ok:
                raise rezka.exception

            stream = rezka.getStream(
                season=str(season),
                episode=str(episode),
                translation=translator_id
            )

            # Get title safely
            try:
                title = rezka.name
            except Exception:
                title = "Unknown Series"

            # Find best available resolution
            selected_resolution = resolution  # Use parameter value
            if selected_resolution in stream.videos:
                urls = stream.videos[selected_resolution]
            else:
                # Fallback to highest available
                available = list(stream.videos.keys())
                selected_resolution = available[-1] if available else "720p"
                urls = stream.videos.get(selected_resolution, [])

            if not urls:
                raise RezkaServiceError("No stream URLs found")

            translator_name = rezka.translators.get(
                stream.translator_id, {}
            ).get('name', 'Unknown')

            return StreamData(
                cdn_url=urls[0],
                resolution=selected_resolution,
                translator_id=stream.translator_id,
                translator_name=translator_name,
                title=title,
                content_type="series",
                season=season,
                episode=episode
            )

        try:
            return await asyncio.to_thread(_extract)
        except Exception as e:
            raise RezkaServiceError(f"Failed to extract stream: {e}") from e
