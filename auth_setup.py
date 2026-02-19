"""
Caffeine Chronicles — YouTube OAuth Setup (run once locally)

This script performs the one-time OAuth 2.0 flow to obtain a refresh token
for headless YouTube uploads. Run this on your local machine with a browser,
then copy the resulting refresh token to your GitHub Actions secrets.

Prerequisites:
  1. Create a project in Google Cloud Console
  2. Enable the YouTube Data API v3
  3. Create OAuth 2.0 credentials (Desktop app)
  4. Download the client_secrets.json file to this directory

Usage:
  python auth_setup.py
"""
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS_FILE = Path(__file__).parent / "client_secrets.json"
TOKEN_FILE = Path(__file__).parent / "youtube_token.json"


def main():
    if not CLIENT_SECRETS_FILE.exists():
        print("ERROR: client_secrets.json not found.")
        print("Download it from Google Cloud Console → APIs → Credentials")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRETS_FILE), scopes=SCOPES
    )
    credentials = flow.run_local_server(port=8080, prompt="consent")

    # Save full token
    TOKEN_FILE.write_text(credentials.to_json())
    print(f"\nToken saved to: {TOKEN_FILE}")

    # Extract values for CI/CD
    token_data = json.loads(credentials.to_json())
    print("\n" + "=" * 60)
    print("Add these to your GitHub Actions secrets:")
    print("=" * 60)
    print(f"YOUTUBE_CLIENT_ID = {token_data.get('client_id', 'N/A')}")
    print(f"YOUTUBE_CLIENT_SECRET = {token_data.get('client_secret', 'N/A')}")
    print(f"YOUTUBE_REFRESH_TOKEN = {token_data.get('refresh_token', 'N/A')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
