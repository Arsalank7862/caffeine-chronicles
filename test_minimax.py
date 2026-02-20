"""Quick test to verify MiniMax API key works."""
from openai import OpenAI

API_KEY = input("Paste your MiniMax API key: ").strip()

client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.minimax.io/v1",
)

try:
    response = client.chat.completions.create(
        model="MiniMax-M2.5",
        max_tokens=50,
        messages=[{"role": "user", "content": "Say hello in one sentence."}],
    )
    print(f"\nSUCCESS! Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"\nFAILED: {e}")
