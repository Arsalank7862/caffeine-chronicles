"""
Caffeine Chronicles — Pipeline Orchestrator
Runs the full daily pipeline: generate → render → upload.
"""
import argparse
import sys
import traceback
from pathlib import Path

import content_generator
import video_renderer
import youtube_uploader


def run_pipeline(skip_upload: bool = False, dry_run: bool = False):
    """Execute the full pipeline."""
    print("=" * 60)
    print("  CAFFEINE CHRONICLES — Daily Pipeline")
    print("=" * 60)

    # ── Step 1: Generate content ─────────────────────────────────────────
    print("\n[1/3] Generating content...")
    try:
        episode_data = content_generator.run()
    except Exception as e:
        print(f"FATAL: Content generation failed: {e}")
        traceback.print_exc()
        sys.exit(1)

    if dry_run:
        print(f"\n[DRY RUN] Would render and upload Episode #{episode_data['episode']}")
        print(f"  Type: {episode_data['type']}")
        print(f"  Text: {episode_data['text']}")
        return

    # ── Step 2: Render video ─────────────────────────────────────────────
    print("\n[2/3] Rendering video...")
    try:
        video_path = video_renderer.run(episode_data)
    except Exception as e:
        print(f"FATAL: Video rendering failed: {e}")
        traceback.print_exc()
        sys.exit(2)

    # ── Step 3: Upload to YouTube ────────────────────────────────────────
    if skip_upload:
        print("\n[3/3] Upload skipped (--skip-upload flag).")
        print(f"  Video file: {video_path}")
    else:
        print("\n[3/3] Uploading to YouTube...")
        try:
            video_id = youtube_uploader.run(video_path, episode_data)
            print(f"  YouTube video ID: {video_id}")
        except Exception as e:
            print(f"FATAL: YouTube upload failed: {e}")
            traceback.print_exc()
            sys.exit(3)

    print("\n" + "=" * 60)
    print(f"  Pipeline complete! Episode #{episode_data['episode']}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Caffeine Chronicles pipeline")
    parser.add_argument(
        "--skip-upload", action="store_true",
        help="Generate content and render video but skip YouTube upload"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate content only (no render or upload)"
    )
    args = parser.parse_args()
    run_pipeline(skip_upload=args.skip_upload, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
