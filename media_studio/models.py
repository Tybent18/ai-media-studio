from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class VideoFormat(str, Enum):
    LONG = "long"
    SHORT = "short"

    @property
    def size(self):
        return (1920, 1080) if self is VideoFormat.LONG else (1080, 1920)

    @property
    def aspect_ratio(self):
        return "16:9" if self is VideoFormat.LONG else "9:16"


@dataclass
class Scene:
    text: str
    kind: str = "point"
    duration: float = 3.0
    image_path: str | None = None
    audio_path: str | None = None
    title: str = ""
    motion: str = "zoom-in"


@dataclass
class ProjectSpec:
    title: str
    script: str
    format: VideoFormat = VideoFormat.LONG
    image_provider: str = "local-card"
    voice_provider: str = "edge-tts"
    music_provider: str = "procedural"
    avatar_provider: str = "local-vtuber"
    theme: str = "midnight"
    fps: int = 30
    voice: str = "en-US-GuyNeural"
    voice_rate: str = "+0%"
    piper_model: Path | None = None
    captions: bool = True
    media_dir: Path | None = None
    music_path: Path | None = None
    voice_volume: float = 1.0
    music_volume: float = 0.12
    music_title: str = ""
    music_artist: str = ""
    music_source: str = "YouTube Audio Library"
    music_license: str = "YouTube Audio Library License"
    music_attribution: str = ""
    music_credit_card: bool = True
    output_dir: Path = Path("output")
    scenes: list[Scene] = field(default_factory=list)

    def manifest(self):
        data = asdict(self)
        data["format"] = self.format.value
        data["output_dir"] = str(self.output_dir)
        data["media_dir"] = str(self.media_dir) if self.media_dir else None
        data["music_path"] = str(self.music_path) if self.music_path else None
        data["piper_model"] = str(self.piper_model) if self.piper_model else None
        return data
