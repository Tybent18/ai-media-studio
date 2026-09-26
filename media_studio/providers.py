import asyncio
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import textwrap
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .models import ProjectSpec, Scene


@dataclass(frozen=True)
class ProviderSpec:
    key: str
    label: str
    mode: str
    env_var: str | None
    notes: str
    reference: str


PROVIDER_CATALOG = {
    "image": [
        ProviderSpec(
            "local-card", "Local storyboard cards", "offline", None, "Deterministic test/demo fallback.", "built-in"
        ),
        ProviderSpec(
            "local-media",
            "Local images and video B-roll",
            "offline",
            None,
            "User-owned media folder or per-scene media tags.",
            "built-in",
        ),
        ProviderSpec(
            "openai-image",
            "OpenAI Image API",
            "free-network",
            "OPENAI_API_KEY",
            "Generation and editing contract.",
            "https://platform.openai.com/docs/guides/image-generation",
        ),
        ProviderSpec(
            "imagen",
            "Google Imagen",
            "adapter",
            "GOOGLE_CLOUD_PROJECT",
            "Vertex AI image contract.",
            "https://cloud.google.com/vertex-ai/generative-ai/docs/image/overview",
        ),
        ProviderSpec(
            "stability",
            "Stability AI",
            "adapter",
            "STABILITY_API_KEY",
            "Stable Image contract.",
            "https://platform.stability.ai/docs",
        ),
    ],
    "voice": [
        ProviderSpec(
            "silent-preview",
            "Timed preview track",
            "offline",
            None,
            "Keeps local renders independent of cloud TTS.",
            "built-in",
        ),
        ProviderSpec(
            "edge-tts",
            "Microsoft Edge TTS",
            "adapter",
            None,
            "Network narration adapter.",
            "https://github.com/rany2/edge-tts",
        ),
        ProviderSpec(
            "flite",
            "Offline Flite narration",
            "offline",
            None,
            "Fully offline narration through FFmpeg's libflite filter.",
            "https://ffmpeg.org/ffmpeg-filters.html#flite",
        ),
        ProviderSpec(
            "piper",
            "Piper neural narration",
            "offline",
            None,
            "Natural offline narration using a user-installed Piper voice model.",
            "https://github.com/rhasspy/piper",
        ),
        ProviderSpec(
            "elevenlabs",
            "ElevenLabs",
            "adapter",
            "ELEVENLABS_API_KEY",
            "TTS and consent-gated cloning contract.",
            "https://elevenlabs.io/docs/eleven-api/quickstart",
        ),
    ],
    "music": [
        ProviderSpec(
            "procedural", "Procedural score", "offline", None, "Original deterministic ambient score.", "built-in"
        ),
        ProviderSpec(
            "local-file",
            "Local music file",
            "offline",
            None,
            "User-owned WAV, MP3, M4A, AAC, or FLAC soundtrack.",
            "built-in",
        ),
        ProviderSpec(
            "youtube-audio-library",
            "YouTube Audio Library import",
            "import",
            None,
            "Imported Audio Library download with preserved attribution metadata.",
            "https://support.google.com/youtube/answer/3376882",
        ),
        ProviderSpec(
            "suno-export",
            "Suno export",
            "import",
            None,
            "User-authorized audio import; no unofficial API.",
            "https://suno.com",
        ),
        ProviderSpec(
            "udio-export",
            "Udio export",
            "import",
            None,
            "User-authorized audio import; no unofficial API.",
            "https://udio.com",
        ),
    ],
    "avatar": [
        ProviderSpec("local-vtuber", "Local VTuber host", "offline", None, "Illustrated host overlay.", "built-in"),
        ProviderSpec(
            "live2d", "Live2D model", "import", None, "Planned local model adapter.", "https://www.live2d.com/en/"
        ),
        ProviderSpec(
            "heygen",
            "HeyGen avatar",
            "adapter",
            "HEYGEN_API_KEY",
            "Remote avatar-video contract.",
            "https://docs.heygen.com/",
        ),
    ],
}
THEMES = {
    "midnight": ((8, 15, 30), (24, 36, 58), (56, 189, 248)),
    "ember": ((28, 12, 17), (61, 24, 32), (251, 146, 60)),
    "forest": ((5, 24, 21), (12, 55, 46), (52, 211, 153)),
    "violet": ((21, 13, 36), (49, 30, 82), (167, 139, 250)),
}


def _font(size, bold=False):
    for p in [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation2/LiberationSans{'-Bold' if bold else '-Regular'}.ttf",
    ]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


class LocalCardProvider:
    def generate(self, scene: Scene, project: ProjectSpec, index: int, target: Path):
        w, h = project.format.size
        bg, panel, accent = THEMES.get(project.theme, THEMES["midnight"])
        im = Image.new("RGB", (w, h), bg)
        d = ImageDraw.Draw(im)
        seed = int(hashlib.sha256(f"{project.title}:{index}".encode()).hexdigest()[:8], 16)
        for n in range(8):
            x = (seed * (n + 7) + n * 193) % w
            y = (seed // (n + 3) + n * 149) % h
            r = max(55, min(w, h) // (5 + n % 3))
            shade = tuple(min(255, c + 12 + n * 2) for c in panel)
            d.ellipse((x - r, y - r, x + r, y + r), fill=shade)
        m = int(w * 0.07)
        box = (m, int(h * 0.15), w - m, int(h * 0.82))
        d.rounded_rectangle(box, radius=28, fill=panel, outline=accent, width=max(3, w // 300))
        d.rectangle((m, int(h * 0.15), m + int(w * 0.012), int(h * 0.82)), fill=accent)
        d.text(
            (m + 38, int(h * 0.2)), scene.title or scene.kind.upper(), font=_font(max(28, w // 25), True), fill=accent
        )
        chars = 34 if project.format.value == "short" else 58
        lines = textwrap.wrap(scene.text, chars)[:8]
        size = max(24, w // 34)
        d.multiline_text(
            (m + 38, int(h * 0.32)), "\n".join(lines), font=_font(size), fill=(241, 245, 249), spacing=int(size * 0.45)
        )
        d.text(
            (m, h - m),
            f"AI MEDIA STUDIO  •  {project.format.aspect_ratio}  •  SCENE {index + 1:02d}",
            font=_font(max(16, w // 58), True),
            fill=(148, 163, 184),
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        im.save(target)
        return target


class LocalMediaProvider:
    """Resolve user-owned images or video clips without paid services."""

    EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".mkv", ".webm")

    def generate(self, scene: Scene, project: ProjectSpec, index: int, target: Path):
        if scene.image_path and Path(scene.image_path).is_file():
            return Path(scene.image_path)
        if project.media_dir and Path(project.media_dir).is_dir():
            files = sorted(p for p in Path(project.media_dir).iterdir() if p.suffix.lower() in self.EXTENSIONS)
            if files:
                return files[index % len(files)]
        return LocalCardProvider().generate(scene, project, index, target)


def probe_duration(path: Path) -> float:
    import subprocess

    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def write_edge_narration(path: Path, text: str, voice: str, rate: str = "+0%"):
    """Generate free narration through Edge TTS and return its measured duration."""
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError("Edge narration requires: pip install edge-tts") from exc
    path.parent.mkdir(parents=True, exist_ok=True)

    async def synthesize():
        await edge_tts.Communicate(text=text, voice=voice, rate=rate).save(str(path))

    try:
        asyncio.run(synthesize())
    except Exception as exc:
        raise RuntimeError(f"Edge narration failed: {exc}") from exc
    return path, probe_duration(path)


def write_flite_narration(path: Path, text: str, voice: str = "slt"):
    """Generate narration completely offline when FFmpeg includes libflite."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("Offline narration requires FFmpeg on PATH")
    clean = text.replace("'", "").replace(":", " - ")
    path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            ffmpeg,
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"flite=text='{clean}':voice={voice}",
            "-ar",
            "44100",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError("This FFmpeg build does not provide working Flite narration")
    return path, probe_duration(path)


def write_piper_narration(path: Path, text: str, model: Path):
    """Generate natural neural narration locally with a Piper ONNX voice model."""
    executable = shutil.which("piper")
    command = [executable] if executable else [os.sys.executable, "-m", "piper"]
    if not model or not Path(model).is_file():
        raise RuntimeError("Choose a downloaded Piper .onnx voice model")
    path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [*command, "--model", str(model), "--output_file", str(path), "--sentence-silence", "0.12"],
        input=text,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"Piper narration failed: {result.stderr.strip()}")
    return path, probe_duration(path)


class LocalAvatarProvider:
    def generate(self, project, target):
        _, panel, accent = THEMES.get(project.theme, THEMES["midnight"])
        im = Image.new("RGBA", (360, 360), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.ellipse((65, 50, 295, 280), fill=(238, 205, 180, 255), outline=accent + (255,), width=8)
        d.polygon([(82, 120), (110, 35), (180, 75), (250, 35), (285, 125)], fill=panel + (255,))
        d.ellipse((118, 145, 148, 175), fill=(15, 23, 42, 255))
        d.ellipse((212, 145, 242, 175), fill=(15, 23, 42, 255))
        d.arc((130, 145, 230, 235), 25, 155, fill=(120, 53, 80, 255), width=7)
        d.rounded_rectangle((70, 260, 290, 355), 35, fill=panel + (255,), outline=accent + (255,), width=8)
        d.text((180, 309), "HOST", anchor="mm", font=_font(28, True), fill="white")
        target.parent.mkdir(parents=True, exist_ok=True)
        im.save(target)
        return target


def write_silence(path, duration, rate=44100):
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(duration * rate)
    chunk_frames = rate
    silence_chunk = struct.pack("<h", 0) * chunk_frames
    with wave.open(str(path), "w") as out:
        out.setparams((1, 2, rate, frames, "NONE", "not compressed"))
        remaining = frames
        while remaining:
            count = min(chunk_frames, remaining)
            out.writeframesraw(silence_chunk[: count * 2])
            remaining -= count
    return path


def write_music(path, duration, seed_text, rate=44100):
    """Write a clearly audible, original synth score without copyrighted samples."""
    path.parent.mkdir(parents=True, exist_ok=True)
    seed = int(hashlib.sha256(seed_text.encode()).hexdigest()[:8], 16)
    root = [110, 130.81, 146.83, 164.81][seed % 4]
    notes = [root, root * 1.25, root * 1.5, root * 2]
    with wave.open(str(path), "w") as out:
        total = int(duration * rate)
        out.setparams((1, 2, rate, total, "NONE", "not compressed"))
        for start in range(0, total, rate):
            buf = []
            for i in range(min(rate, total - start)):
                t = (start + i) / rate
                beat = t % 2
                f = notes[int(t / 2) % 4]
                env = min(1, beat / 0.10) * min(1, (2 - beat) / 0.28)
                pad = 0.58 * math.sin(2 * math.pi * (f / 2) * t)
                lead = env * (
                    0.72 * math.sin(2 * math.pi * f * t)
                    + 0.22 * math.sin(4 * math.pi * f * t)
                )
                pulse_phase = t % 0.5
                pulse_env = math.exp(-pulse_phase * 13)
                pulse = 0.34 * pulse_env * math.sin(2 * math.pi * (root / 2) * t)
                value = int(7200 * (pad + lead + pulse))
                value = max(-32767, min(32767, value))
                buf.append(struct.pack("<h", value))
            out.writeframesraw(b"".join(buf))
    return path


def export_catalog(path):
    path.write_text(
        json.dumps({k: [asdict(x) for x in v] for k, v in PROVIDER_CATALOG.items()}, indent=2), encoding="utf-8"
    )
    return path
