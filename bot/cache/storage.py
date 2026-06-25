"""
Cache storage interface for Telegram file_id caching
Supports both in-memory and SQLite backends
"""
import asyncio
import aiosqlite
from typing import Optional, Protocol
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CacheKey:
    """Cache key structure"""
    content_url: str
    resolution: str
    season: Optional[int] = None
    episode: Optional[int] = None

    def to_string(self) -> str:
        """Convert to string key"""
        if self.season is not None and self.episode is not None:
            return f"{self.content_url}:s{self.season}e{self.episode}:{self.resolution}"
        return f"{self.content_url}:{self.resolution}"


class CacheStorage(ABC):
    """Abstract cache storage interface"""

    @abstractmethod
    async def get(self, key: CacheKey) -> Optional[str]:
        """Get cached file_id"""
        pass

    @abstractmethod
    async def set(self, key: CacheKey, file_id: str) -> None:
        """Store file_id in cache"""
        pass

    @abstractmethod
    async def delete(self, key: CacheKey) -> None:
        """Delete cached entry"""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close cache backend"""
        pass


class MemoryCache(CacheStorage):
    """In-memory cache implementation"""

    def __init__(self):
        self._cache: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: CacheKey) -> Optional[str]:
        async with self._lock:
            return self._cache.get(key.to_string())

    async def set(self, key: CacheKey, file_id: str) -> None:
        async with self._lock:
            self._cache[key.to_string()] = file_id

    async def delete(self, key: CacheKey) -> None:
        async with self._lock:
            self._cache.pop(key.to_string(), None)

    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()

    async def close(self) -> None:
        """No cleanup needed for memory cache"""
        pass


class SQLiteCache(CacheStorage):
    """SQLite-backed cache implementation"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def _ensure_connection(self) -> aiosqlite.Connection:
        """Ensure database connection and table exists"""
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    key TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await self._db.commit()
        return self._db

    async def get(self, key: CacheKey) -> Optional[str]:
        async with self._lock:
            db = await self._ensure_connection()
            async with db.execute(
                "SELECT file_id FROM file_cache WHERE key = ?",
                (key.to_string(),)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def set(self, key: CacheKey, file_id: str) -> None:
        async with self._lock:
            db = await self._ensure_connection()
            await db.execute(
                "INSERT OR REPLACE INTO file_cache (key, file_id) VALUES (?, ?)",
                (key.to_string(), file_id)
            )
            await db.commit()

    async def delete(self, key: CacheKey) -> None:
        async with self._lock:
            db = await self._ensure_connection()
            await db.execute(
                "DELETE FROM file_cache WHERE key = ?",
                (key.to_string(),)
            )
            await db.commit()

    async def clear(self) -> None:
        async with self._lock:
            db = await self._ensure_connection()
            await db.execute("DELETE FROM file_cache")
            await db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None


class CacheManager:
    """Cache manager facade"""

    def __init__(self, backend: str = "memory", sqlite_path: str = "cache.db"):
        if backend == "sqlite":
            self._storage: CacheStorage = SQLiteCache(sqlite_path)
        else:
            self._storage: CacheStorage = MemoryCache()

    async def get_file_id(self, key: CacheKey) -> Optional[str]:
        """Get cached Telegram file_id"""
        return await self._storage.get(key)

    async def cache_file_id(self, key: CacheKey, file_id: str) -> None:
        """Cache Telegram file_id"""
        await self._storage.set(key, file_id)

    async def invalidate(self, key: CacheKey) -> None:
        """Invalidate cache entry"""
        await self._storage.delete(key)

    async def clear_all(self) -> None:
        """Clear entire cache"""
        await self._storage.clear()

    async def close(self) -> None:
        """Close cache backend"""
        await self._storage.close()
