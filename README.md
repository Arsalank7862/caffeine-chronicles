# Caffeine Chronicles — Automated YouTube Shorts Pipeline

Generates and uploads a daily YouTube Short with coffee/caffeine facts, fully automated via GitHub Actions.

## Architecture

```
pipeline.py  (orchestrator)
  ├── content_generator.py   → local fact bank → episode JSON
  ├── video_renderer.py      → Pillow frames + FFmpeg → MP4
  └── youtube_uploader.py    → YouTube Data API v3 → upload
```

## Quick Start

### 1. Clone and install

```bash
git clone <your-repo-url> && cd caffeine-chronicles
pip install -r requirements.txt
```

You also need **FFmpeg** installed:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`
- Windows: download from https://ffmpeg.org

### 2. Set up YouTube credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. Enable **YouTube Data API v3** under APIs & Services → Library
4. Go to APIs & Services → Credentials → Create Credentials → **OAuth 2.0 Client ID**
5. Application type: **Desktop app**
6. Download the JSON file and save it as `client_secrets.json` in this directory
7. Run the auth setup script:

```bash
python auth_setup.py
```

This opens a browser for you to authorize your YouTube account. After authorization, it prints three values you'll need for GitHub Actions secrets.

### 3. Add background music (optional)

Place an MP3 file at `assets/background_music.mp3`. If absent, the video will render with silence.

### 4. Test locally

```bash
# Full pipeline (generate + render + upload)
python pipeline.py

# Generate + render only (no upload)
python pipeline.py --skip-upload

# Content generation only (no render)
python pipeline.py --dry-run
```

### 5. Deploy to GitHub Actions

Push this repo to GitHub, then add these **repository secrets** (Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `YOUTUBE_CLIENT_ID` | From `auth_setup.py` output |
| `YOUTUBE_CLIENT_SECRET` | From `auth_setup.py` output |
| `YOUTUBE_REFRESH_TOKEN` | From `auth_setup.py` output |

The workflow runs daily at **6:00 PM UTC**. You can also trigger it manually from the Actions tab.

## Project Structure

```
caffeine-chronicles/
├── .github/workflows/
│   └── daily-short.yml       # GitHub Actions workflow
├── assets/
│   └── background_music.mp3  # (you provide this)
├── output/                   # generated videos + episode JSONs
├── auth_setup.py             # one-time YouTube OAuth setup
├── config.py                 # all settings in one place
├── content_generator.py      # picks facts from local bank
├── fact_bank.py              # 370 facts + 55 coffee shop recs
├── pipeline.py               # main orchestrator
├── requirements.txt          # Python dependencies
├── state.json                # episode counter + used indices (auto-generated)
├── video_renderer.py         # frame generation + FFmpeg
└── youtube_uploader.py       # YouTube Data API upload
```

## Content Bank

Instead of calling an API, the pipeline draws from a local bank of 370 coffee/caffeine facts and 55 coffee shop recommendations in `fact_bank.py`. Facts are picked randomly without repeats — once all facts are used, the cycle resets. At 6 facts + 1 shop rec per week, the bank covers about a full year before recycling.

To add your own facts, just append strings to the `FACTS` or `COFFEE_SHOPS` lists in `fact_bank.py`.

## Configuration

Edit `config.py` to customize:
- `COFFEE_SHOP_INTERVAL` — how often to feature a coffee shop (default: every 7th episode)
- `VIDEO_DURATION_SECONDS` — video length (default: 35s)
- `YOUTUBE_PRIVACY` — "public", "unlisted", or "private"
- `YOUTUBE_TAGS` — hashtags for discovery
- Colors, fonts, and layout constants in `video_renderer.py`

## Important Notes

- **YouTube API quotas**: The YouTube Data API has a daily quota of 10,000 units. A video upload costs ~1,600 units, so a single daily upload is well within limits.
- **State persistence**: `state.json` tracks the episode counter and which facts have been used. The GitHub Actions workflow auto-commits this file after each run.
- **Refresh token expiry**: Google OAuth refresh tokens for apps in "testing" mode expire after 7 days. To avoid this, publish your OAuth consent screen (even as internal) or re-run `auth_setup.py` when needed.
- **No external APIs needed for content**: The fact bank is self-contained. The only API credential you need is for YouTube uploads.
