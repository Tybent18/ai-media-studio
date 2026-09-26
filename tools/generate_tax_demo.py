"""Generate the neutral V5 README proof video and its animated preview."""

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from media_studio.models import ProjectSpec, Scene, VideoFormat
from media_studio.pipeline import MediaPipeline

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo" / "v5"
MEDIA = DEMO / "tax-media"
VOICE = ROOT / "voices" / "en_US-lessac-medium.onnx"

SCENES = [
    ("TAXES IN UNDER A MINUTE", "Taxes in under a minute. Here is the basic journey from your paycheck to filing day.", "$"),
    ("1  GROSS INCOME", "Gross income is what you earn before taxes and other deductions are taken out.", "+"),
    (
        "2  TAXABLE INCOME",
        "Eligible adjustments and deductions can reduce the amount of income that is taxed.",
        "−",
    ),
    (
        "3  TAX BRACKETS",
        "Tax brackets are layered. A higher rate generally applies only to income inside that bracket, not every dollar.",
        "%",
    ),
    (
        "4  CREDITS & WITHHOLDING",
        "Credits reduce your tax bill directly. Withholding is tax you have already paid during the year.",
        "✓",
    ),
    (
        "5  FILE & COMPARE",
        "At filing, compare the tax owed with what you paid. Overpaid may mean a refund. Underpaid means a balance due.",
        "=",
    ),
    (
        "THE SIMPLE FLOW",
        "Income, minus eligible deductions, creates taxable income. Calculate tax, subtract credits and payments, then file. Rules vary, so use official guidance for your situation.",
        "→",
    ),
]


def font(size, bold=False):
    suffix = "-Bold" if bold else ""
    return ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/DejaVuSans{suffix}.ttf", size)


def make_card(index, title, symbol):
    width, height = 1080, 1920
    image = Image.new("RGB", (width, height), "#07111f")
    draw = ImageDraw.Draw(image)
    colors = ["#38bdf8", "#22c55e", "#f59e0b", "#a78bfa", "#fb7185", "#2dd4bf", "#60a5fa"]
    accent = colors[index % len(colors)]
    draw.rounded_rectangle((74, 120, 1006, 1800), 52, fill="#0f1d31", outline=accent, width=8)
    draw.rounded_rectangle((130, 235, 950, 1055), 54, fill="#07111f", outline="#263b55", width=4)
    draw.ellipse((260, 345, 820, 905), fill="#122942", outline=accent, width=16)
    draw.text((540, 625), symbol, anchor="mm", font=font(270, True), fill=accent)
    draw.text((540, 1185), title, anchor="mm", font=font(66, True), fill="#f8fafc")
    draw.rounded_rectangle((210, 1300, 870, 1310), 5, fill=accent)
    draw.text((540, 1435), "AI MEDIA STUDIO V5", anchor="mm", font=font(32, True), fill="#8da2bd")
    draw.text((540, 1500), "NEURAL VOICE  •  CAPTIONS  •  MUSIC", anchor="mm", font=font(25), fill="#64748b")
    target = MEDIA / f"{index:02d}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    return target


def main():
    if not VOICE.is_file():
        raise SystemExit(
            "Download en_US-lessac-medium with: "
            "python -m piper.download_voices --download-dir voices en_US-lessac-medium"
        )
    scenes = [
        Scene(text, "hook" if index == 0 else "outro" if index == len(SCENES) - 1 else "point",
              image_path=str(make_card(index, title, symbol)), title=title)
        for index, (title, text, symbol) in enumerate(SCENES)
    ]
    project = ProjectSpec(
        title="Taxes in Under a Minute",
        script="",
        scenes=scenes,
        format=VideoFormat.SHORT,
        image_provider="local-media",
        voice_provider="piper",
        piper_model=VOICE,
        avatar_provider="none",
        music_provider="procedural",
        voice_volume=1.0,
        music_volume=0.24,
        output_dir=DEMO / "render",
    )
    result = MediaPipeline(lambda message, value: print(f"{value:>6.1%} {message}")).run(project)
    full_output = Path(result["video_path"])
    output = DEMO / "taxes-in-under-a-minute.mp4"
    subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-y", "-i", str(full_output),
            "-vf", "scale=270:480:flags=lanczos", "-c:v", "libx264", "-preset", "slow",
            "-crf", "35", "-maxrate", "80k", "-bufsize", "160k", "-c:a", "aac",
            "-b:a", "40k", "-movflags", "+faststart", str(output),
        ],
        check=True,
    )
    subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-y", "-i", str(full_output), "-t", "8",
            "-vf", "fps=4,scale=180:-1:flags=lanczos,split[s0][s1];"
            "[s0]palettegen=max_colors=64[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5",
            str(DEMO / "taxes-in-under-a-minute.gif"),
        ],
        check=True,
    )
    print(output)


if __name__ == "__main__":
    main()