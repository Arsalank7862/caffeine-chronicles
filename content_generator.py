"""
Caffeine Chronicles — Content Generator
Picks a daily coffee/caffeine fact (or coffee shop recommendation)
from a local bank, ensuring no repeats until the bank is exhausted.
"""
import json
import random
from pathlib import Path

from config import STATE_FILE, OUTPUT_DIR, COFFEE_SHOP_INTERVAL
from fact_bank import FACTS, COFFEE_SHOPS


def load_state() -> dict:
    """Load persistent state (episode counter, used indices)."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "episode": 0,
        "used_facts": [],       # indices into FACTS that have been used
        "used_shops": [],       # indices into COFFEE_SHOPS that have been used
    }


def save_state(state: dict) -> None:
    """Persist state to disk."""
    STATE_FILE.write_text(json.dumps(state, indent=2))


def pick_from_bank(bank: list[str], used_key: str, state: dict) -> str:
    """
    Pick a random unused item from the bank. If all items have been used,
    reset the used list and start over (shuffled fresh).
    """
    used = set(state.get(used_key, []))
    available = [i for i in range(len(bank)) if i not in used]

    if not available:
        # All items used — reset and start fresh cycle
        state[used_key] = []
        available = list(range(len(bank)))
        print(f"[ContentGen] Cycled through all items in bank, starting fresh.")

    choice = random.choice(available)
    state.setdefault(used_key, []).append(choice)
    return bank[choice]


def run() -> dict:
    """Main entry point. Returns the episode data dict."""
    state = load_state()
    state["episode"] += 1
    episode = state["episode"]

    is_coffee_shop = (episode % COFFEE_SHOP_INTERVAL == 0)
    content_type = "coffee_shop" if is_coffee_shop else "fact"

    if is_coffee_shop:
        text = pick_from_bank(COFFEE_SHOPS, "used_shops", state)
        header = "COFFEE SHOP SPOTLIGHT"
    else:
        text = pick_from_bank(FACTS, "used_facts", state)
        header = "DID YOU KNOW THAT..."

    episode_data = {
        "episode": episode,
        "type": content_type,
        "text": text,
        "header": header,
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
