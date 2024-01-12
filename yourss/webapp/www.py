from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from loguru import logger
from starlette.responses import HTMLResponse

import yourss

from ..config import YOURSS_USERS, current_config
from ..utils import parse_channel_names
from ..youtube import YoutubeWebClient
from .utils import get_youtube_client

TemplateResponse = Jinja2Templates(
    directory=Path(yourss.__file__).parent / "templates"
).TemplateResponse

router = APIRouter()


@router.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(
        router.url_path_for("view_channels", channels=current_config.DEFAULT_CHANNELS)
    )


@router.get("/watch", response_class=RedirectResponse)
async def watch(video: str = Query(alias="v", min_length=11, max_length=11)):
    return RedirectResponse(
        f"https://www.youtube-nocookie.com/embed/{video}?autoplay=1&control=2&rel=0"
    )


@router.get("/u/{user}", response_class=HTMLResponse)
async def get_user(
    request: Request,
    user: str,
    yt_client: Annotated[YoutubeWebClient, Depends(get_youtube_client)],
):
    if user not in YOURSS_USERS:
        raise HTTPException(status_code=404, detail="User not found")

    feeds = []
    for name in YOURSS_USERS[user]:
        try:
            feeds.append(await yt_client.get_rss_feed(name))
        except BaseException as error:
            logger.warning("Cannot get rss feed for {}: {}", name, error)

    if len(feeds) == 0:
        raise HTTPException(status_code=404, detail="No channels found")

    return TemplateResponse(
        "view.html",
        {
            "request": request,
            "title": f"/u/{user}",
            "feeds": feeds,
        },
    )


@router.get("/{channels}", response_class=HTMLResponse)
async def view_channels(
    request: Request,
    channels: str,
    yt_client: Annotated[YoutubeWebClient, Depends(get_youtube_client)],
):
    feeds = []
    for name in parse_channel_names(channels):
        try:
            feeds.append(await yt_client.get_rss_feed(name))
        except BaseException as error:
            logger.warning("Cannot get rss feed for {}: {}", name, error)

    if len(feeds) == 0:
        raise HTTPException(status_code=404, detail="No channels found")

    return TemplateResponse(
        "view.html",
        {
            "request": request,
            "title": ", ".join(sorted(map(lambda f: f.title, feeds))),
            "feeds": feeds,
        },
    )
