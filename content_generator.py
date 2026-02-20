"""
Caffeine Chronicles — Content Generator
Uses MiniMax M2.5 API to generate fresh, unique content daily.
Generates 3 pieces of content per video, rotating through categories.
"""
import json
import re
import random
from pathlib import Path
from openai import OpenAI

from config import (
    STATE_FILE, OUTPUT_DIR, CHANNEL_NAME,
    MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL,
    CONTENT_ROTATION, FACTS_PER_VIDEO,
)

# ── Headers / labels for each content type ───────────────────────────────────
CONTENT_CONFIG = {
    "fact": {
        "header": "DID YOU KNOW?",
        "title_prefix": "Coffee Facts",
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

Generate {count} surprising, accurate, and unique coffee or caffeine FACTS.
Make each one genuinely mind-blowing — the kind of thing that makes people comment and share.
Each fact should be 1-2 sentences max, suitable for a text card in a short video.
The facts should be on DIFFERENT topics from each other.

PREVIOUSLY USED (do NOT repeat or closely paraphrase):
{history}

Reply with ONLY the facts, one per line, numbered like:
1. [fact]
2. [fact]
3. [fact]""",

    "myth_buster": """You are the content writer for "{channel}", a viral YouTube Shorts channel.

Generate {count} coffee or caffeine MYTH BUSTERS. For each, state a common myth,
then reveal the surprising truth. Format each as:
"MYTH: [the myth]. TRUTH: [the reality]."
Each should be 2-3 sentences max.

PREVIOUSLY USED (do NOT repeat or closely paraphrase):
{history}

Reply with ONLY the myth busters, one per line, numbered like:
1. [myth buster]
2. [myth buster]
3. [myth buster]""",

    "comparison": """You are the content writer for "{channel}", a viral YouTube Shorts channel.

Generate {count} interesting coffee or caffeine COMPARISONS (this vs. that).
Compare two related things and reveal a surprising difference or similarity.
Each should be 2-3 sentences max and cover DIFFERENT comparisons.

PREVIOUSLY USED (do NOT repeat or closely paraphrase):
{history}

Reply with ONLY the comparisons, one per line, numbered like:
1. [comparison]
2. [comparison]
3. [comparison]""",

    "coffee_shop": """You are the content writer for "{channel}", a viral YouTube Shorts channel.

Recommend {count} interesting, unique COFFEE SHOPS from different parts of the world.
Include each shop's name, city/country, and what makes it special.
Each recommendation should be 1-2 sentences.

PREVIOUSLY USED (do NOT repeat or closely paraphrase):
{history}

Reply with ONLY the recommendations, one per line, numbered like:
1. [shop]
2. [shop]
3. [shop]""",
}

FALLBACK_FACTS = [
    "Coffee is the world's most popular psychoactive substance, consumed by over 2 billion people daily.",
    "A single coffee tree produces only about 1 pound of roasted coffee per year.",
    "Caffeine takes just 10 minutes to start affecting your brain after your first sip.",
]


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"episode": 0, "history": []}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def parse_numbered_list(text: str, expected_count: int) -> list[str]:
    """Parse a numbered list response into individual items."""
    lines = text.strip().split("\n")
    items = []
    for line in lines:
        # Strip numbering like "1. ", "2) ", "1: ", etc.
        cleaned = re.sub(r"^\s*\d+[\.\)\:\-]\s*", "", line).strip()
        if cleaned and len(cleaned) > 15:
            items.append(cleaned)
    return items[:expected_count]


def generate_content(content_type: str, count: int, history: list[str]) -> list[str]:
    """Call MiniMax API to generate fresh content. Returns a list of items."""
    key = MINIMAX_API_KEY
    if not key:
        print("[ContentGen] WARNING: MINIMAX_API_KEY is empty! Using fallback facts.")
        return FALLBACK_FACTS[:count]

    client = OpenAI(api_key=key, base_url=MINIMAX_BASE_URL)

    recent = history[-40:]
    history_block = "\n".join(f"- {h}" for h in recent) if recent else "(none yet)"

    prompt = PROMPTS[content_type].format(
        channel=CHANNEL_NAME,
        history=history_block,
        count=count,
    )

    response = client.chat.completions.create(
        model=MINIMAX_MODEL,
        max_tokens=2048,
        temperature=0.9,
        messages=[
            {"role": "system", "content": (
                "You are a creative content writer for a coffee-themed YouTube Shorts channel. "
                "Your content should be accurate, surprising, and highly shareable. "
                "Never include hashtags, emojis, or meta-commentary. "
                "Reply with ONLY the numbered list, nothing else."
            )},
            {"role": "user", "content": prompt},
        ],
        extra_body={"reasoning_split": True},
    )

    text = (response.choices[0].message.content or "").strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # If empty, try extracting from reasoning
    if not text:
        reasoning = getattr(response.choices[0].message, "reasoning_details", None)
        if reasoning and isinstance(reasoning, list):
            raw = reasoning[0].get("text", "") if isinstance(reasoning[0], dict) else str(reasoning[0])
            quoted = re.findall(r'"([^"]{20,})"', raw)
            if quoted:
                text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(quoted[:count]))

    items = parse_numbered_list(text, count)

    # Pad with fallbacks if we didn't get enough
    while len(items) < count:
        idx = len(items)
        if idx < len(FALLBACK_FACTS):
            items.append(FALLBACK_FACTS[idx])
        else:
            items.append("Coffee beans are actually seeds from a bright red fruit called a coffee cherry.")
        print(f"[ContentGen] WARNING: Used fallback for item {idx + 1}")

    return items


def run() -> dict:
    """Main entry point. Returns the episode data dict."""
    state = load_state()
    state["episode"] += 1
    episode = state["episode"]

    # Determine content type from rotation
    rotation_index = (episode - 1) % len(CONTENT_ROTATION)
    content_type = CONTENT_ROTATION[rotation_index]

    # Generate multiple items
    texts = generate_content(content_type, FACTS_PER_VIDEO, state.get("history", []))
    state.setdefault("history", []).extend(texts)

    # Keep history from growing forever
    if len(state["history"]) > 200:
        state["history"] = state["history"][-200:]

    config = CONTENT_CONFIG[content_type]

    episode_data = {
        "episode": episode,
        "type": content_type,
        "texts": texts,              # list of 3 items
        "text": texts[0],            # first one for title/description
        "header": config["header"],
        "title_prefix": config["title_prefix"],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    episode_file = OUTPUT_DIR / f"episode_{episode:04d}.json"
    episode_file.write_text(json.dumps(episode_data, indent=2))

    save_state(state)

    print(f"[ContentGen] Episode #{episode} ({content_type})")
    for i, t in enumerate(texts):
        print(f"[ContentGen]   Fact {i+1}: {t}")
    print(f"[ContentGen] Saved to: {episode_file}")

    return episode_data


if __name__ == "__main__":
    run()
