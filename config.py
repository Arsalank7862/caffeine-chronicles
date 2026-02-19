"""
Caffeine Chronicles — Configuration
"""
import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
ASSETS_DIR = PROJECT_ROOT / "assets"
OUTPUT_DIR = PROJECT_ROOT / "output"
STATE_FILE = PROJECT_ROOT / "state.json"

# ── Content Settings ─────────────────────────────────────────────────────────
CHANNEL_NAME = "Caffeine Chronicles"
COFFEE_SHOP_INTERVAL = 7  # every Nth episode is a coffee shop recommendation

# ── Video Settings ───────────────────────────────────────────────────────────
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30
VIDEO_DURATION_SECONDS = 35  # total video length
TEXT_ANIMATE_IN_SECONDS = 2.0  # how long the text fade-in takes
BACKGROUND_MUSIC_FILE = ASSETS_DIR / "background_music.mp3"

# ── YouTube Settings ─────────────────────────────────────────────────────────
YOUTUBE_TAGS = ["coffee", "caffeine", "didyouknow", "facts", "shorts",
                "coffeefacts", "caffeinefacts", "coffeelovers"]
YOUTUBE_CATEGORY_ID = "22"  # People & Blogs
YOUTUBE_PRIVACY = "public"  # "public", "unlisted", or "private"
YOUTUBE_DESCRIPTION_TEMPLATE = (
    "{fact}\n\n"
    "Follow @CaffeineChronicles for your daily dose of coffee knowledge!\n\n"
    "#shorts #coffee #caffeine #didyouknow #facts #coffeelovers"
)
