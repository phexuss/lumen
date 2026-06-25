"""
FastAPI server with streaming proxy endpoint
Handles video streaming with proper headers to bypass hotlink protection
"""
import asyncio
import aiohttp
from urllib.parse import unquote, quote
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from config import config

logger = logging.getLogger(__name__)

# Setup Jinja2 templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan event handler"""
    logger.info(f"FastAPI server starting on {config.server.host}:{config.server.port}")
    yield
    logger.info("FastAPI server shutting down")


app = FastAPI(title="HDRezka Streaming Proxy", lifespan=lifespan)


# Spoofed headers to bypass hotlink protection
PROXY_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://rezka.ag/',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Origin': 'https://rezka.ag',
    'Sec-Fetch-Dest': 'video',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site'
}


async def stream_video(cdn_url: str, range_header: str = None) -> AsyncGenerator[bytes, None]:
    """
    Stream video from CDN with proper headers and proxy

    Args:
        cdn_url: Target CDN URL
        range_header: Optional Range header for seeking

    Yields:
        Video data chunks (64KB)
    """
    headers = PROXY_HEADERS.copy()
    if range_header:
        headers['Range'] = range_header

    timeout = aiohttp.ClientTimeout(total=None, connect=30)

    # Use proxy if configured
    proxy_url = config.rezka.proxy_url if config.rezka.proxy_url else None

    try:
        connector = None
        if proxy_url:
            from aiohttp_socks import ProxyConnector
            connector = ProxyConnector.from_url(proxy_url)

        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            async with session.get(cdn_url, headers=headers) as response:
                if response.status not in (200, 206):
                    logger.error(f"CDN returned status {response.status} for {cdn_url}")
                    raise HTTPException(
                        status_code=response.status,
                        detail=f"CDN error: {response.status}"
                    )

                # Stream in 64KB chunks
                chunk_size = 64 * 1024
                async for chunk in response.content.iter_chunked(chunk_size):
                    yield chunk

    except aiohttp.ClientError as e:
        logger.error(f"Failed to stream from CDN: {e}")
        raise HTTPException(status_code=502, detail=f"CDN connection failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during streaming: {e}")
        raise HTTPException(status_code=500, detail=f"Streaming error: {str(e)}")


@app.get("/stream")
@app.head("/stream")  # Add HEAD support for Telegram
async def proxy_stream(
    url: str = Query(..., description="Target CDN URL to proxy"),
    range: str = Query(None, description="Optional Range header for seeking")
):
    """
    Proxy video stream from CDN with spoofed headers

    This endpoint:
    1. Accepts a CDN URL as query parameter
    2. Fetches the video with proper Referer and User-Agent headers
    3. Streams the response back to Telegram with correct headers for seeking support

    Query params:
        url: The actual CDN video URL (URL-encoded)
        range: Optional Range header value (e.g., "bytes=0-1023")

    Returns:
        StreamingResponse with video/mp4 content
    """
    # Decode URL
    cdn_url = unquote(url)

    logger.info(f"Proxying stream: {cdn_url[:100]}...")
    if range:
        logger.info(f"Range request: {range}")

    # Return streaming response with proper headers
    # Add ngrok-skip-browser-warning to bypass ngrok warning page
    return StreamingResponse(
        stream_video(cdn_url, range),
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",
            "Content-Disposition": "inline",
            "ngrok-skip-browser-warning": "true"  # Skip ngrok warning page
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "hdrezka-proxy"}


@app.get("/watch", response_class=HTMLResponse)
async def watch_video(
    url: str = Query(..., description="CDN video URL"),
    title: str = Query("Video", description="Video title"),
    subtitle: str = Query("", description="Video subtitle (quality, translator, etc)")
):
    """
    Video player page with video.js

    Opens a full-screen HTML5 video player that streams through our proxy

    Query params:
        url: The CDN video URL (will be proxied)
        title: Video title to display
        subtitle: Additional info (quality, translator, season/episode)

    Returns:
        HTML page with video.js player
    """
    # Construct stream URL through our proxy
    encoded_cdn_url = quote(url, safe='')
    stream_url = f"{config.server.public_url}/stream?url={encoded_cdn_url}"

    return templates.TemplateResponse("player.html", {
        "request": {},  # Required by Jinja2Templates
        "title": title,
        "subtitle": subtitle,
        "stream_url": stream_url
    })

