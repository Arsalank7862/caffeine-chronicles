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

# ── MiniMax API ──────────────────────────────────────────────────────────────
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = "https://api.minimax.io/v1"
MINIMAX_MODEL = "MiniMax-M2.5"

# ── Content Settings ─────────────────────────────────────────────────────────
CHANNEL_NAME = "Caffeine Chronicles"

# Content categories and their rotation weights.
# The pipeline cycles through these in order, then repeats.
# Adjust the list to change how often each type appears.
CONTENT_ROTATION = [
    "fact",           # Day 1: classic coffee/caffeine fact
    "fact",           # Day 2: another fact
    "myth_buster",    # Day 3: myth vs. reality
    "fact",           # Day 4: fact
    "comparison",     # Day 5: this vs. that
    "fact",           # Day 6: fact
    "coffee_shop",    # Day 7: coffee shop recommendation
]

# ── Video Settings ───────────────────────────────────────────────────────────
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30
VIDEO_DURATION_SECONDS = 35  # total video length
TEXT_ANIMATE_IN_SECONDS = 2.0  # how long the text fade-in takes
BACKGROUND_MUSIC_FILE = ASSETS_DIR / "background_music.mp3"

# ── YouTube Settings ─────────────────────────────────────────────────────────
YOUTUBE_TAGS = [
    "coffee", "caffeine", "didyouknow", "facts", "shorts",
    "coffeefacts", "caffeinefacts", "coffeelovers", "coffeetok",
    "coffeetime", "coffeeaddict", "espresso", "barista",
    "morningcoffee", "coffeeshop", "latte", "coffeeholic",
    "funfacts", "dailyfacts", "themoreyouknow",
]
YOUTUBE_CATEGORY_ID = "22"  # People & Blogs
YOUTUBE_PRIVACY = "public"  # "public", "unlisted", or "private"
YOUTUBE_DESCRIPTION_TEMPLATE = (
    "{fact}\n\n"
    "Follow @CaffeineChronicles for your daily dose of coffee knowledge!\n\n"
    "#shorts #coffee #caffeine #didyouknow #facts #coffeelovers\n\n"
    "Music: Sol by Luke Bergs | https://soundcloud.com/bergscloud/\n"
    "Music promoted by https://www.chosic.com/free-music/all/\n"
    "Creative Commons CC BY-SA 3.0\n"
    "https://creativecommons.org/licenses/by-sa/3.0/"
)
