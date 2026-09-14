from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class VideoFormat(str, Enum):
    LONG = "long"
    SHORT = "short"

    @property
    def size(self):
        return (1280, 720) if self is VideoFormat.LONG else (720, 1280)

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


@dataclass
class ProjectSpec:
    title: str
    script: str
    format: VideoFormat = VideoFormat.LONG
    image_provider: str = "local-card"
    voice_provider: str = "silent-preview"
    music_provider: str = "procedural"
    avatar_provider: str = "local-vtuber"
    theme: str = "midnight"
    fps: int = 24
    output_dir: Path = Path("output")
    scenes: list[Scene] = field(default_factory=list)

    def manifest(self):
        data = asdict(self)
        data["format"] = self.format.value
        data["output_dir"] = str(self.output_dir)
        return data
