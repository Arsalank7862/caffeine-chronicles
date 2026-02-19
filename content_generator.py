"""
Caffeine Chronicles — Content Generator
Uses MiniMax M2.5 API to generate fresh, unique content daily.
Rotates through content categories: facts, myth busters, comparisons,
and coffee shop recommendations.
"""
import json
import re
import random
from pathlib import Path
from openai import OpenAI

from config import (
    STATE_FILE, OUTPUT_DIR, CHANNEL_NAME,
    MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL,
    CONTENT_ROTATION,
)

# ── Headers / labels for each content type ───────────────────────────────────
CONTENT_CONFIG = {
    "fact": {
        "header": "DID YOU KNOW?",
        "title_prefix": "Coffee Fact",
    },
    "myth_buster": {
        "header": "MYTH vs. REALITY",
        "title_prefix": "Coffee Myth Busted",
    },
    "comparison": {
        "header": "THIS vs. THAT",
        "title_prefix": "Coffee Showdown",
    },
    "coffee_shop": {
        "header": "COFFEE SHOP SPOTLIGHT",
        "title_prefix": "Coffee Shop You Need to Visit",
    },
}

# ── Prompts per content type ─────────────────────────────────────────────────
PROMPTS = {
    "fact": """You are the content writer for "{channel}", a viral YouTube Shorts channel.

Generate a surprising, accurate, and unique coffee or caffeine FACT.
Make it genuinely mind-blowing — the kind of thing that makes people comment and share.
Keep it to 1-2 sentences max, suitable for a text card in a short video.

PREVIOUSLY USED (do NOT repeat or closely paraphrase):
{history}

Reply with ONLY the fact text, nothing else.""",

    "myth_buster": """You are the content writer for "{channel}", a viral YouTube Shorts channel.

Generate a coffee or caffeine MYTH BUSTER. State a common myth people believe,
then reveal the surprising truth. Format it as two parts:
"MYTH: [the myth]. TRUTH: [the reality]."
Keep the total to 2-3 sentences max.

PREVIOUSLY USED (do NOT repeat or closely paraphrase):
{history}

Reply with ONLY the myth buster text, nothing else.""",

    "comparison": """You are the content writer for "{channel}", a viral YouTube Shorts channel.

Generate an interesting coffee or caffeine COMPARISON (this vs. that).
Compare two related things and reveal a surprising difference or similarity.
Examples: espresso vs. drip coffee, Arabica vs. Robusta, cold brew vs. iced coffee.
Keep it to 2-3 sentences max.

PREVIOUSLY USED (do NOT repeat or closely paraphrase):
{history}

Reply with ONLY the comparison text, nothing else.""",

    "coffee_shop": """You are the content writer for "{channel}", a viral YouTube Shorts channel.

Recommend an interesting, unique COFFEE SHOP from anywhere in the world.
Include the shop name, city/country, and what makes it special or worth visiting.
Make it sound like a must-visit destination. Keep it to 1-2 sentences.

PREVIOUSLY USED (do NOT repeat or closely paraphrase):
{history}

Reply with ONLY the recommendation text, nothing else.""",
}


def load_state() -> dict:
    """Load persistent state (episode counter, history)."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"episode": 0, "history": []}


def save_state(state: dict) -> None:
    """Persist state to disk."""
    STATE_FILE.write_text(json.dumps(state, indent=2))


def generate_content(content_type: str, history: list[str]) -> str:
    """Call MiniMax API to generate fresh content."""
    key = MINIMAX_API_KEY
    # Debug: confirm key is being received (masked)
    if key:
        print(f"[DEBUG] API key loaded: {key[:8]}...{key[-4:]} (length={len(key)})")
    else:
        print("[DEBUG] WARNING: MINIMAX_API_KEY is empty!")
    client = OpenAI(
        api_key=key,
        base_url=MINIMAX_BASE_URL,
    )

    recent = history[-40:]
    history_block = "\n".join(f"- {h}" for h in recent) if recent else "(none yet)"

    prompt = PROMPTS[content_type].format(
        channel=CHANNEL_NAME,
        history=history_block,
    )

    response = client.chat.completions.create(
        model=MINIMAX_MODEL,
        max_tokens=250,
        temperature=0.9,
        messages=[
            {"role": "system", "content": (
                "You are a creative content writer for a coffee-themed YouTube Shorts channel. "
                "Your content should be accurate, surprising, and highly shareable. "
                "Never include hashtags, emojis, or meta-commentary. Just the content."
            )},
            {"role": "user", "content": prompt},
        ],
    )

    text = response.choices[0].message.content.strip()

    # Strip MiniMax's <think>...</think> reasoning tags if present
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # Remove any stray quotes wrapping the response
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()

    return text


def run() -> dict:
    """Main entry point. Returns the episode data dict."""
    state = load_state()
    state["episode"] += 1
    episode = state["episode"]

    # Determine content type from rotation
    rotation_index = (episode - 1) % len(CONTENT_ROTATION)
    content_type = CONTENT_ROTATION[rotation_index]

    # Generate content
    text = generate_content(content_type, state.get("history", []))
    state.setdefault("history", []).append(text)

    # Keep history from growing forever (last 200)
    if len(state["history"]) > 200:
        state["history"] = state["history"][-200:]

    config = CONTENT_CONFIG[content_type]

    episode_data = {
        "episode": episode,
        "type": content_type,
        "text": text,
        "header": config["header"],
        "title_prefix": config["title_prefix"],
    }

    # Save episode JSON
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    episode_file = OUTPUT_DIR / f"episode_{episode:04d}.json"
    episode_file.write_text(json.dumps(episode_data, indent=2))

    save_state(state)

    print(f"[ContentGen] Episode #{episode} ({content_type})")
    print(f"[ContentGen] Text: {text}")
    print(f"[ContentGen] Saved to: {episode_file}")

    return episode_data


if __name__ == "__main__":
    run()
