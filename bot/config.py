"""
Configuration module for HDRezka Telegram Bot
Loads environment variables and provides application settings
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load .env file
load_dotenv()


@dataclass
class BotConfig:
    """Telegram Bot configuration"""
    token: str
    admin_ids: list[int]


@dataclass
class ServerConfig:
    """FastAPI server configuration"""
    host: str
    port: int
    public_url: str  # Public URL for proxy streaming (e.g., https://yourdomain.com)


@dataclass
class RezkaConfig:
    """HDRezka service configuration"""
    mirror_url: str
    timeout: int
    max_retries: int
    proxy_url: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


@dataclass
class CacheConfig:
    """Cache configuration"""
    enabled: bool
    backend: str  # "memory" or "sqlite"
    sqlite_path: str


class Config:
    """Main application configuration"""

    def __init__(self):
        self.bot = BotConfig(
            token=os.getenv("BOT_TOKEN", ""),
            admin_ids=self._parse_admin_ids()
        )

        self.server = ServerConfig(
            host=os.getenv("SERVER_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVER_PORT", "8080")),
            public_url=os.getenv("PUBLIC_URL", "http://localhost:8080")
        )

        self.rezka = RezkaConfig(
            mirror_url=os.getenv("REZKA_MIRROR", "https://hdrezka.ag"),
            timeout=int(os.getenv("REZKA_TIMEOUT", "30")),
            max_retries=int(os.getenv("REZKA_MAX_RETRIES", "3")),
            proxy_url=os.getenv("REZKA_PROXY_URL"),
            email=os.getenv("REZKA_EMAIL"),
            password=os.getenv("REZKA_PASSWORD")
        )

        self.cache = CacheConfig(
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            backend=os.getenv("CACHE_BACKEND", "memory"),
            sqlite_path=os.getenv("CACHE_SQLITE_PATH", "cache.db")
        )

    def _parse_admin_ids(self) -> list[int]:
        """Parse comma-separated admin IDs from environment"""
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if not admin_ids_str:
            return []
        return [int(id_.strip()) for id_ in admin_ids_str.split(",") if id_.strip()]

    def validate(self) -> None:
        """Validate required configuration"""
        if not self.bot.token:
            raise ValueError("BOT_TOKEN environment variable is required")
        if not self.server.public_url:
            raise ValueError("PUBLIC_URL environment variable is required")


# Global config instance
config = Config()
