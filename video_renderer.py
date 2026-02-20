"""
Caffeine Chronicles — Video Renderer
Generates frames with Pillow + composites with FFmpeg.
Produces a 1080x1920 vertical short with:
  - Warm tan/brown background with scattered coffee bean graphics
  - White rounded card with header and fact text
  - Dark brown "caffeine chronicles" pill banner at top
  - Golden sparkle particle effects
  - 3 scenes that fade in/out with different facts
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
    FADE_DURATION_SECONDS, SCENE_DURATION_SECONDS,
    BACKGROUND_MUSIC_FILE, OUTPUT_DIR, FACTS_PER_VIDEO
)

# ── Colors ───────────────────────────────────────────────────────────────────
BG_COLOR = (210, 180, 140)
CARD_BG = (255, 255, 255)
CARD_SHADOW = (180, 155, 120, 80)
PILL_BG = (62, 39, 22)
PILL_TEXT = (255, 255, 255)
HEADER_COLOR = (62, 39, 22)
EPISODE_COLOR = (160, 130, 100)
FACT_COLOR = (50, 40, 30)
SPARKLE_COLOR_BASE = (255, 215, 0)
BEAN_COLOR = (101, 67, 33)
BEAN_COLOR_LIGHT = (139, 90, 43)

FRAMES_DIR = OUTPUT_DIR / "_frames"


# ── Font helpers ─────────────────────────────────────────────────────────────
def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
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


# ── Coffee bean drawing ──────────────────────────────────────────────────────
class CoffeeBean:
    def __init__(self):
        self.x = random.randint(-20, VIDEO_WIDTH + 20)
        self.y = random.randint(-20, VIDEO_HEIGHT + 20)
        self.size = random.uniform(18, 40)
        self.angle = random.uniform(0, 360)
        self.shade = random.choice([BEAN_COLOR, BEAN_COLOR_LIGHT])
        self.opacity = random.randint(25, 55)

    def draw(self, draw: ImageDraw.Draw, img: Image.Image):
        """Draw a simple coffee bean shape (oval with a center line)."""
        bean_img = Image.new("RGBA", (int(self.size * 2.5), int(self.size * 2.5)), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bean_img)

        cx = bean_img.width // 2
        cy = bean_img.height // 2
        rx = int(self.size * 0.9)
        ry = int(self.size * 0.55)

        # Bean body (oval)
        bd.ellipse(
            [cx - rx, cy - ry, cx + rx, cy + ry],
            fill=self.shade + (self.opacity,)
        )
        # Center line
        bd.line(
            [(cx - rx + 4, cy), (cx + rx - 4, cy)],
            fill=(40, 25, 10, self.opacity),
            width=max(1, int(self.size * 0.06))
        )

        # Rotate
        rotated = bean_img.rotate(self.angle, expand=True, resample=Image.BICUBIC)
        paste_x = int(self.x - rotated.width // 2)
        paste_y = int(self.y - rotated.height // 2)
        img.paste(rotated, (paste_x, paste_y), rotated)


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
    draw.line([(x, y - r * 2), (x, y + r * 2)], fill=color, width=max(1, int(r * 0.5)))
    draw.line([(x - r * 2, y), (x + r * 2, y)], fill=color, width=max(1, int(r * 0.5)))
    draw.ellipse([x - r, y - r, x + r, y + r], fill=color)


# ── Rounded rectangle helper ────────────────────────────────────────────────
def draw_rounded_rect(draw, bbox, radius, fill, outline=None):
    draw.rounded_rectangle(bbox, radius=radius, fill=fill, outline=outline)


# ── Text wrapping helper ────────────────────────────────────────────────────
def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
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


# ── Scene timing ─────────────────────────────────────────────────────────────
def get_scene_info(frame_num: int) -> tuple[int, float, float]:
    """
    Returns (scene_index, card_opacity, text_opacity) for the given frame.
    Each scene: fade_in -> hold -> fade_out.
    """
    t = frame_num / FPS
    scene_idx = min(int(t / SCENE_DURATION_SECONDS), FACTS_PER_VIDEO - 1)
    scene_start = scene_idx * SCENE_DURATION_SECONDS
    scene_t = t - scene_start

    fade = FADE_DURATION_SECONDS
    hold = SCENE_DURATION_SECONDS - 2 * fade

    if scene_t < fade:
        progress = scene_t / fade
        ease = 1 - (1 - progress) ** 3
        return scene_idx, ease, ease
    elif scene_t < fade + hold:
        return scene_idx, 1.0, 1.0
    else:
        progress = (scene_t - fade - hold) / fade
        ease = 1 - progress ** 3
        return scene_idx, ease, ease


# ── Frame renderer ───────────────────────────────────────────────────────────
def render_frame(
    frame_num: int,
    total_frames: int,
    episode_data: dict,
    sparkles: list[Sparkle],
    beans: list[CoffeeBean],
    bg_cache: Image.Image | None = None,
) -> tuple[Image.Image, Image.Image]:
    """Render a single frame. Returns (frame_image, bg_cache)."""

    scene_idx, card_opacity, text_opacity = get_scene_info(frame_num)
    texts = episode_data.get("texts", [episode_data.get("text", "")])
    current_text = texts[scene_idx] if scene_idx < len(texts) else texts[-1]
    header = episode_data.get("header", "DID YOU KNOW?")

    # ── Static background (cached) ───────────────────────────────────────
    if bg_cache is None:
        bg_cache = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), BG_COLOR + (255,))
        for bean in beans:
            bean.draw(ImageDraw.Draw(bg_cache), bg_cache)

    img = bg_cache.copy()

    # ── Sparkles ─────────────────────────────────────────────────────────
    sparkle_layer = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    sparkle_draw = ImageDraw.Draw(sparkle_layer)
    for s in sparkles:
        draw_sparkle(sparkle_draw, s, frame_num)
    img = Image.alpha_composite(img, sparkle_layer)

    # ── "caffeine chronicles" pill banner (always visible) ───────────────
    pill_font = get_font(36, bold=True)
    pill_text = "caffeine chronicles"
    pill_bbox = pill_font.getbbox(pill_text)
    pill_tw = pill_bbox[2] - pill_bbox[0]
    pill_th = pill_bbox[3] - pill_bbox[1]
    pill_pad_x, pill_pad_y = 50, 18
    pill_w = pill_tw + pill_pad_x * 2
    pill_h = pill_th + pill_pad_y * 2
    pill_x = (VIDEO_WIDTH - pill_w) // 2
    pill_y = 140

    pill_layer = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    pill_draw = ImageDraw.Draw(pill_layer)
    draw_rounded_rect(pill_draw, [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
                       radius=pill_h // 2, fill=PILL_BG + (255,))
    pill_draw.text(
        (pill_x + pill_pad_x, pill_y + pill_pad_y - 2),
        pill_text, font=pill_font, fill=PILL_TEXT + (255,)
    )
    img = Image.alpha_composite(img, pill_layer)

    # ── White card (fades with scene) ────────────────────────────────────
    card_margin = 80
    card_w = VIDEO_WIDTH - card_margin * 2
    card_h = 900
    card_x = card_margin
    card_y = (VIDEO_HEIGHT - card_h) // 2 + 40
    card_radius = 40
    c_alpha = int(255 * card_opacity)

    # Shadow
    shadow_layer = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_layer)
    draw_rounded_rect(shadow_draw,
                       [card_x + 6, card_y + 10, card_x + card_w + 6, card_y + card_h + 10],
                       radius=card_radius, fill=CARD_SHADOW[:3] + (int(CARD_SHADOW[3] * card_opacity),))
    img = Image.alpha_composite(img, shadow_layer)

    # Card background
    card_layer = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_layer)
    draw_rounded_rect(card_draw,
                       [card_x, card_y, card_x + card_w, card_y + card_h],
                       radius=card_radius, fill=CARD_BG + (c_alpha,))
    img = Image.alpha_composite(img, card_layer)

    # ── Card content ─────────────────────────────────────────────────────
    t_alpha = int(255 * text_opacity)
    text_layer = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)

    inner_w = card_w - 120
    current_y = card_y + 60

    # Scene counter dots
    dot_r = 8
    dot_gap = 30
    total_dot_w = FACTS_PER_VIDEO * dot_r * 2 + (FACTS_PER_VIDEO - 1) * dot_gap
    dot_start_x = card_x + (card_w - total_dot_w) // 2
    for i in range(FACTS_PER_VIDEO):
        dx = dot_start_x + i * (dot_r * 2 + dot_gap)
        if i == scene_idx:
            dot_color = HEADER_COLOR + (t_alpha,)
        else:
            dot_color = EPISODE_COLOR + (t_alpha // 2,)
        text_draw.ellipse([dx, current_y, dx + dot_r * 2, current_y + dot_r * 2], fill=dot_color)
    current_y += 50

    # Thin divider
    div_margin = 100
    text_draw.line(
        [(card_x + div_margin, current_y), (card_x + card_w - div_margin, current_y)],
        fill=EPISODE_COLOR + (t_alpha // 2,), width=2
    )
    current_y += 40

    # Header
    header_font = get_font(44, bold=True)
    header_bbox = header_font.getbbox(header)
    header_tw = header_bbox[2] - header_bbox[0]
    text_draw.text(
        (card_x + (card_w - header_tw) // 2, current_y),
        header, font=header_font, fill=HEADER_COLOR + (t_alpha,)
    )
    current_y += 90

    # Fact text (wrapped)
    fact_font = get_font(38, bold=False)
    lines = wrap_text(current_text, fact_font, inner_w)
    line_height = 54
    total_text_h = len(lines) * line_height
    remaining_h = card_h - (current_y - card_y) - 80
    text_start_y = current_y + max(0, (remaining_h - total_text_h) // 2)

    for i, line in enumerate(lines):
        line_bbox = fact_font.getbbox(line)
        line_tw = line_bbox[2] - line_bbox[0]
        lx = card_x + (card_w - line_tw) // 2
        ly = text_start_y + i * line_height
        text_draw.text((lx, ly), line, font=fact_font, fill=FACT_COLOR + (t_alpha,))

    img = Image.alpha_composite(img, text_layer)

    # ── Bottom watermark ─────────────────────────────────────────────────
    wm_font = get_font(24, bold=False)
    wm_text = "@CaffeineChronicles"
    wm_bbox = wm_font.getbbox(wm_text)
    wm_tw = wm_bbox[2] - wm_bbox[0]
    final_draw = ImageDraw.Draw(img)
    final_draw.text(
        ((VIDEO_WIDTH - wm_tw) // 2, VIDEO_HEIGHT - 100),
        wm_text, font=wm_font, fill=EPISODE_COLOR + (180,)
    )

    return img.convert("RGB"), bg_cache


# ── Main render pipeline ────────────────────────────────────────────────────
def render_video(episode_data: dict) -> Path:
    episode = episode_data["episode"]
    total_frames = FPS * VIDEO_DURATION_SECONDS

    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True)

    random.seed(episode)
    sparkles = [Sparkle() for _ in range(60)]
    beans = [CoffeeBean() for _ in range(35)]

    print(f"[VideoRenderer] Rendering {total_frames} frames at {FPS}fps...")
    print(f"[VideoRenderer] {FACTS_PER_VIDEO} scenes, {SCENE_DURATION_SECONDS}s each")

    bg_cache = None
    for f in range(total_frames):
        img, bg_cache = render_frame(f, total_frames, episode_data, sparkles, beans, bg_cache)
        img.save(FRAMES_DIR / f"frame_{f:05d}.png")
        if f % (FPS * 5) == 0:
            print(f"  ... frame {f}/{total_frames}")

    output_file = OUTPUT_DIR / f"episode_{episode:04d}.mp4"

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES_DIR / "frame_%05d.png"),
    ]

    if BACKGROUND_MUSIC_FILE.exists():
        ffmpeg_cmd += ["-i", str(BACKGROUND_MUSIC_FILE), "-shortest"]
        audio_opts = ["-c:a", "aac", "-b:a", "128k"]
    else:
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

    shutil.rmtree(FRAMES_DIR)
    print(f"[VideoRenderer] Output: {output_file}")
    return output_file


def run(episode_data: dict) -> Path:
    return render_video(episode_data)


if __name__ == "__main__":
    sample = {
        "episode": 1,
        "type": "fact",
        "texts": [
            "Coffee is the second most traded commodity on Earth, right behind crude oil.",
            "The first webcam was invented at Cambridge to monitor a coffee pot so researchers wouldn't walk to an empty machine.",
            "Beethoven was so obsessive about his coffee that he counted exactly 60 beans per cup, every single time.",
        ],
        "text": "Coffee is the second most traded commodity on Earth.",
        "header": "DID YOU KNOW?",
    }
    render_video(sample)
