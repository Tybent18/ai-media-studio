"""Create deterministic README demos without API keys or a display server."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "v4"
OUT.mkdir(parents=True, exist_ok=True)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def font(n, b=False):
    return ImageFont.truetype(BOLD if b else FONT, n)


def frame(format_name, progress, stage, accent=(56, 189, 248)):
    im = Image.new("RGB", (1200, 720), (8, 15, 30))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1200, 72), fill=(15, 27, 48))
    d.text((28, 18), "AI MEDIA STUDIO", font=font(28, True), fill="white")
    d.text((330, 27), "V4 • LOCAL-FIRST PRODUCTION", font=font(15, True), fill=accent)
    d.rounded_rectangle((22, 95, 315, 690), 20, fill=(15, 27, 48))
    d.rounded_rectangle((335, 95, 860, 690), 20, fill=(15, 27, 48))
    d.rounded_rectangle((880, 95, 1178, 690), 20, fill=(15, 27, 48))
    d.text((45, 125), "PROJECT", font=font(14, True), fill=accent)
    d.text((45, 160), "Creative AI Explained", font=font(20), fill="white")
    d.text((45, 220), "FORMAT", font=font(14, True), fill=accent)
    d.text((45, 255), format_name, font=font(22, True), fill="white")
    for i, t in enumerate(["Image  local-card", "Voice  timed-preview", "Avatar local-vtuber", "Music  procedural"]):
        d.text((45, 330 + i * 55), t, font=font(16), fill=(203, 213, 225))
    d.text((360, 125), "SCRIPT / SCENE EDITOR", font=font(14, True), fill=accent)
    script = [
        "Hook: What if one studio coordinated",
        "every part of your video?",
        "",
        "Point: Every stage stays editable.",
        "",
        "Outro: Render, review, publish.",
    ]
    d.multiline_text((365, 175), "\n".join(script), font=font(19), fill=(226, 232, 240), spacing=12)
    d.text((905, 125), "PRODUCTION STATUS", font=font(14, True), fill=accent)
    d.text((905, 170), stage, font=font(19, True), fill="white")
    d.rounded_rectangle((905, 215, 1150, 238), 10, fill=(30, 41, 59))
    d.rounded_rectangle((905, 215, 905 + int(245 * progress), 238), 10, fill=accent)
    stages = ["Plan", "Visuals", "Voice", "Avatar", "Music", "Render", "Package"]
    active = min(6, int(progress * 7))
    for i, s in enumerate(stages):
        d.text(
            (905, 285 + i * 46),
            ("● " if i <= active else "○ ") + s,
            font=font(17),
            fill=accent if i <= active else (100, 116, 139),
        )
    return im


def save(name, fmt):
    stages = [
        ("Planning scenes", 0.08),
        ("Generating visuals", 0.22),
        ("Preparing voice", 0.38),
        ("Rigging VTuber host", 0.48),
        ("Composing music", 0.56),
        ("Rendering video", 0.72),
        ("Video ready", 1.0),
    ]
    frames = []
    for stage, p in stages:
        frames.extend([frame(fmt, p, stage)] * 3)
    frames[0].save(OUT / name, save_all=True, append_images=frames[1:], duration=220, loop=0, optimize=True)


save("long-production.gif", "Long • 16:9")
save("short-production.gif", "Short • 9:16")
print(OUT)
