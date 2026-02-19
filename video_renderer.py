"""
Caffeine Chronicles — Video Renderer
Generates frames with Pillow + composites with FFmpeg.
Produces a 1080x1920 vertical short with:
  - Warm tan/brown background
  - White rounded card with episode number, header, and fact text
  - Dark brown "caffeine chronicles" pill banner at top
  - Golden sparkle particle effects
  - Text fade-in animation
  - Background music overlay
"""
import json
import math
import os
import random
import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import (
    VIDEO_WIDTH, VIDEO_HEIGHT, FPS, VIDEO_DURATION_SECONDS,
    TEXT_ANIMATE_IN_SECONDS, BACKGROUND_MUSIC_FILE, OUTPUT_DIR
)

# ── Colors ───────────────────────────────────────────────────────────────────
BG_COLOR = (210, 180, 140)          # warm tan
CARD_BG = (255, 255, 255)           # white card
CARD_SHADOW = (180, 155, 120, 80)   # subtle shadow
PILL_BG = (62, 39, 22)              # dark brown pill
PILL_TEXT = (255, 255, 255)          # white text on pill
HEADER_COLOR = (62, 39, 22)         # dark brown
EPISODE_COLOR = (160, 130, 100)     # muted tan
FACT_COLOR = (50, 40, 30)           # near-black
SPARKLE_COLOR_BASE = (255, 215, 0)  # gold

FRAMES_DIR = OUTPUT_DIR / "_frames"


# ── Font helpers ─────────────────────────────────────────────────────────────
def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font, falling back to default if custom fonts aren't available."""
    font_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for fp in font_candidates:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


# ── Sparkle particles ───────────────────────────────────────────────────────
class Sparkle:
    def __init__(self):
        self.x = random.randint(0, VIDEO_WIDTH)
        self.y = random.randint(0, VIDEO_HEIGHT)
        self.size = random.uniform(2, 6)
        self.phase = random.uniform(0, 2 * math.pi)
        self.speed = random.uniform(1.5, 4.0)
        self.drift_x = random.uniform(-0.3, 0.3)
        self.drift_y = random.uniform(-0.8, -0.2)
        brightness = random.randint(180, 255)
        self.color = (brightness, int(brightness * 0.85), 0)

    def get_opacity(self, frame: int) -> float:
        t = frame / FPS
        return max(0, min(1, 0.5 + 0.5 * math.sin(self.speed * t + self.phase)))

    def get_pos(self, frame: int) -> tuple[float, float]:
        t = frame / FPS
        x = (self.x + self.drift_x * t * 30) % VIDEO_WIDTH
        y = (self.y + self.drift_y * t * 30) % VIDEO_HEIGHT
        return x, y


def draw_sparkle(draw: ImageDraw.Draw, sparkle: Sparkle, frame: int):
    opacity = sparkle.get_opacity(frame)
    if opacity < 0.05:
        return
    x, y = sparkle.get_pos(frame)
    r = sparkle.size * (0.5 + 0.5 * opacity)
    color = tuple(int(c * opacity) for c in sparkle.color) + (int(255 * opacity),)

    # Draw a 4-pointed star
    points_main = [(x, y - r * 2), (x, y + r * 2)]
    points_cross = [(x - r * 2, y), (x + r * 2, y)]
    draw.line(points_main, fill=color, width=max(1, int(r * 0.5)))
    draw.line(points_cross, fill=color, width=max(1, int(r * 0.5)))
    # Center glow
    draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


# ── Rounded rectangle helper ────────────────────────────────────────────────
def draw_rounded_rect(draw, bbox, radius, fill, outline=None):
    x0, y0, x1, y1 = bbox
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline)


# ── Text wrapping helper ────────────────────────────────────────────────────
def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test = f"{current_line} {word}".strip()
        bbox = font.getbbox(test)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line = test
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


# ── Frame renderer ───────────────────────────────────────────────────────────
def render_frame(
    frame_num: int,
    total_frames: int,
    episode_data: dict,
    sparkles: list[Sparkle],
) -> Image.Image:
    """Render a single frame and return as PIL Image."""
    img = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    t = frame_num / FPS  # time in seconds
    anim_progress = min(1.0, t / TEXT_ANIMATE_IN_SECONDS)  # 0→1 ease
    ease = 1 - (1 - anim_progress) ** 3  # cubic ease-out

    # ── Sparkles (behind card) ───────────────────────────────────────────
    sparkle_layer = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    sparkle_draw = ImageDraw.Draw(sparkle_layer)
    for s in sparkles:
        draw_sparkle(sparkle_draw, s, frame_num)
    img = Image.alpha_composite(img, sparkle_layer)
    draw = ImageDraw.Draw(img)

    # ── "caffeine chronicles" pill banner ────────────────────────────────
    pill_font = get_font(36, bold=True)
    pill_text = "caffeine chronicles"
    pill_bbox = pill_font.getbbox(pill_text)
    pill_tw = pill_bbox[2] - pill_bbox[0]
    pill_th = pill_bbox[3] - pill_bbox[1]
    pill_pad_x, pill_pad_y = 50, 18
    pill_w = pill_tw + pill_pad_x * 2
    pill_h = pill_th + pill_pad_y * 2
    pill_x = (VIDEO_WIDTH - pill_w) // 2
    pill_y_target = 140
    pill_y = int(pill_y_target - 30 + 30 * ease)
    pill_alpha = int(255 * ease)

    pill_layer = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    pill_draw = ImageDraw.Draw(pill_layer)
    draw_rounded_rect(pill_draw, [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
                       radius=pill_h // 2, fill=PILL_BG + (pill_alpha,))
    pill_draw.text(
        (pill_x + pill_pad_x, pill_y + pill_pad_y - 2),
        pill_text, font=pill_font,
        fill=PILL_TEXT[:3] + (pill_alpha,)
    )
    img = Image.alpha_composite(img, pill_layer)
    draw = ImageDraw.Draw(img)

    # ── White card ───────────────────────────────────────────────────────
    card_margin = 80
    card_w = VIDEO_WIDTH - card_margin * 2
    card_h = 900
    card_x = card_margin
    card_y = (VIDEO_HEIGHT - card_h) // 2 + 40
    card_radius = 40

    # Shadow
    shadow_layer = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    draw_rounded_rect(shadow_draw,
                       [card_x + 6, card_y + 10, card_x + card_w + 6, card_y + card_h + 10],
                       radius=card_radius, fill=CARD_SHADOW)
    img = Image.alpha_composite(img, shadow_layer)
    draw = ImageDraw.Draw(img)

    # Card background
    card_alpha = int(255 * ease)
    card_layer = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_layer)
    draw_rounded_rect(card_draw,
                       [card_x, card_y, card_x + card_w, card_y + card_h],
                       radius=card_radius, fill=CARD_BG + (card_alpha,))
    img = Image.alpha_composite(img, card_layer)
    draw = ImageDraw.Draw(img)

    # ── Card content ─────────────────────────────────────────────────────
    text_alpha = int(255 * ease)
    text_layer = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)

    inner_x = card_x + 60
    inner_w = card_w - 120
    current_y = card_y + 60

    # Thin decorative line above header
    div_margin = 100
    text_draw.line(
        [(card_x + div_margin, current_y), (card_x + card_w - div_margin, current_y)],
        fill=EPISODE_COLOR + (text_alpha // 2,), width=2
    )
    current_y += 40

    # Header ("DID YOU KNOW THAT..." or "COFFEE SHOP SPOTLIGHT")
    header_font = get_font(44, bold=True)
    header_text = episode_data.get("header", "DID YOU KNOW THAT...")
    header_bbox = header_font.getbbox(header_text)
    header_tw = header_bbox[2] - header_bbox[0]
    text_draw.text(
        (card_x + (card_w - header_tw) // 2, current_y),
        header_text, font=header_font,
        fill=HEADER_COLOR + (text_alpha,)
    )
    current_y += 90

    # Fact text (wrapped)
    fact_font = get_font(40, bold=False)
    lines = wrap_text(episode_data["text"], fact_font, inner_w)
    line_height = 56
    total_text_h = len(lines) * line_height
    text_start_y = current_y + (card_h - (current_y - card_y) - 80 - total_text_h) // 2
    text_start_y = max(current_y, text_start_y)

    for i, line in enumerate(lines):
        line_bbox = fact_font.getbbox(line)
        line_tw = line_bbox[2] - line_bbox[0]
        lx = card_x + (card_w - line_tw) // 2
        ly = text_start_y + i * line_height
        # Per-line staggered fade
        line_delay = i * 0.08
        line_progress = max(0, min(1, (t - line_delay) / TEXT_ANIMATE_IN_SECONDS))
        line_ease = 1 - (1 - line_progress) ** 3
        line_alpha = int(255 * line_ease)
        y_offset = int(15 * (1 - line_ease))
        text_draw.text(
            (lx, ly + y_offset), line, font=fact_font,
            fill=FACT_COLOR + (line_alpha,)
        )

    img = Image.alpha_composite(img, text_layer)

    # ── Small bottom watermark ───────────────────────────────────────────
    wm_font = get_font(24, bold=False)
    wm_text = "@CaffeineChronicles"
    wm_bbox = wm_font.getbbox(wm_text)
    wm_tw = wm_bbox[2] - wm_bbox[0]
    final_draw = ImageDraw.Draw(img)
    final_draw.text(
        ((VIDEO_WIDTH - wm_tw) // 2, VIDEO_HEIGHT - 100),
        wm_text, font=wm_font, fill=EPISODE_COLOR + (180,)
    )

    return img.convert("RGB")


# ── Main render pipeline ────────────────────────────────────────────────────
def render_video(episode_data: dict) -> Path:
    """Render all frames and compose into final MP4."""
    episode = episode_data["episode"]
    total_frames = FPS * VIDEO_DURATION_SECONDS

    # Prepare frames directory
    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True)

    # Seed sparkles
    random.seed(episode)  # deterministic per episode
    sparkles = [Sparkle() for _ in range(60)]

    print(f"[VideoRenderer] Rendering {total_frames} frames at {FPS}fps...")
    for f in range(total_frames):
        img = render_frame(f, total_frames, episode_data, sparkles)
        img.save(FRAMES_DIR / f"frame_{f:05d}.png")
        if f % (FPS * 5) == 0:
            print(f"  ... frame {f}/{total_frames}")

    # ── FFmpeg compose ───────────────────────────────────────────────────
    output_file = OUTPUT_DIR / f"episode_{episode:04d}.mp4"

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES_DIR / "frame_%05d.png"),
    ]

    # Add background music if available
    if BACKGROUND_MUSIC_FILE.exists():
        ffmpeg_cmd += ["-i", str(BACKGROUND_MUSIC_FILE), "-shortest"]
        audio_opts = ["-c:a", "aac", "-b:a", "128k"]
    else:
        # Generate a silent audio track so the video has an audio stream
        ffmpeg_cmd += [
            "-f", "lavfi", "-i",
            f"anullsrc=r=44100:cl=stereo:d={VIDEO_DURATION_SECONDS}",
        ]
        audio_opts = ["-c:a", "aac", "-b:a", "128k"]
        print("[VideoRenderer] No background_music.mp3 found — using silence.")

    ffmpeg_cmd += [
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "20",
        *audio_opts,
        "-movflags", "+faststart",
        str(output_file),
    ]

    print("[VideoRenderer] Running FFmpeg...")
    subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

    # Cleanup frames
    shutil.rmtree(FRAMES_DIR)

    print(f"[VideoRenderer] Output: {output_file}")
    return output_file


def run(episode_data: dict) -> Path:
    """Public entry point."""
    return render_video(episode_data)


if __name__ == "__main__":
    # For testing: render with sample data
    sample = {
        "episode": 1,
        "type": "fact",
        "text": "Coffee is the second most traded commodity on Earth, right behind crude oil.",
        "header": "DID YOU KNOW THAT..."
    }
    render_video(sample)
