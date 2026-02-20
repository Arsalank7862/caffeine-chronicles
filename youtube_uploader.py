"""
Caffeine Chronicles — YouTube Uploader
Uploads rendered video as a YouTube Short using YouTube Data API v3.

Authentication uses OAuth 2.0 with a refresh token for headless/CI environments.
See README for how to obtain credentials.
"""
import json
import os
import time
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import (
    YOUTUBE_TAGS, YOUTUBE_CATEGORY_ID, YOUTUBE_PRIVACY,
    YOUTUBE_DESCRIPTION_TEMPLATE, CHANNEL_NAME, PROJECT_ROOT
)

TOKEN_FILE = PROJECT_ROOT / "youtube_token.json"

# These can come from env vars (for CI) or a local client_secrets.json
CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_URI = "https://oauth2.googleapis.com/token"

# Retry settings for resumable uploads
MAX_RETRIES = 5
RETRY_BACKOFF = 2  # exponential backoff base (seconds)


def get_authenticated_service():
    """Build an authenticated YouTube API service."""
    creds = None

    # Try loading from token file first (local dev)
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Try env-var refresh token (CI/CD)
    if creds is None and REFRESH_TOKEN:
        creds = Credentials(
            token=None,
            refresh_token=REFRESH_TOKEN,
            token_uri=TOKEN_URI,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            scopes=SCOPES,
        )

    if creds is None:
        raise RuntimeError(
            "No YouTube credentials found. Set YOUTUBE_CLIENT_ID, "
            "YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN env vars, "
            "or run auth_setup.py to create youtube_token.json."
        )

    # Refresh if expired
    if creds.expired or not creds.token:
        creds.refresh(Request())
        # Save refreshed token locally
        TOKEN_FILE.write_text(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(video_path: Path, episode_data: dict) -> str:
    """
    Upload a video to YouTube as a Short.
    Returns the video ID on success.
    """
    youtube = get_authenticated_service()

    episode = episode_data["episode"]
    texts = episode_data.get("texts", [episode_data.get("text", "")])
    fact_text = texts[0] if texts else ""
    content_type = episode_data.get("type", "fact")

    # Build title from content type
    title_prefix = episode_data.get("title_prefix", "Coffee Fact")
    # Grab a short snippet of the first fact for a unique title
    # Strip any leftover tags or weird characters
    clean_text = fact_text.replace("<", "").replace(">", "")
    snippet = clean_text.split(".")[0].split(",")[0].strip()
    if len(snippet) > 55:
        snippet = snippet[:52] + "..."
    # Fallback if snippet is empty or too short
    if len(snippet) < 5:
        snippet = "You Won't Believe This"
    title = f"{title_prefix}: {snippet} #shorts"

    # YouTube Shorts titles must be ≤100 chars and not empty
    title = title[:100].strip()
    if not title:
        title = "Caffeine Chronicles #shorts"

    # Build description with all facts listed
    all_facts = "\n".join(f"☕ {t}" for t in texts if t)
    description = YOUTUBE_DESCRIPTION_TEMPLATE.format(fact=all_facts)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": YOUTUBE_TAGS,
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 8,  # 8 MB chunks
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    # Resumable upload with retry
    video_id = None
    retries = 0
    response = None

    print(f"[YouTubeUploader] Uploading: {title}")
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"  ... {pct}% uploaded")
        except Exception as e:
            retries += 1
            if retries > MAX_RETRIES:
                raise RuntimeError(f"Upload failed after {MAX_RETRIES} retries: {e}")
            wait = RETRY_BACKOFF ** retries
            print(f"  [retry {retries}/{MAX_RETRIES}] Error: {e}. Waiting {wait}s...")
            time.sleep(wait)

    video_id = response["id"]
    video_url = f"https://youtube.com/shorts/{video_id}"
    print(f"[YouTubeUploader] Success! {video_url}")

    return video_id


def run(video_path: Path, episode_data: dict) -> str:
    """Public entry point."""
    return upload_video(video_path, episode_data)


if __name__ == "__main__":
    # Manual test
    import sys
    if len(sys.argv) < 3:
        print("Usage: python youtube_uploader.py <video.mp4> <episode.json>")
        sys.exit(1)
    vp = Path(sys.argv[1])
    ep = json.loads(Path(sys.argv[2]).read_text())
    upload_video(vp, ep)
