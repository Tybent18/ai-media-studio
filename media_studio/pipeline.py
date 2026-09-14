import json
import re
import shutil
import subprocess
import threading
import uuid
from pathlib import Path

from .models import ProjectSpec, Scene, VideoFormat
from .providers import LocalAvatarProvider, LocalCardProvider, export_catalog, write_music, write_silence
from .renderer import render_video


class PipelineCancelled(RuntimeError):
    pass


class MediaPipeline:
    STAGES = ("plan", "visuals", "voice", "avatar", "music", "render", "package")

    def __init__(self, progress=None):
        self.progress = progress or (lambda m, p: None)
        self.cancel_event = threading.Event()
        self._process = None

    def cancel(self):
        self.cancel_event.set()
        if self._process and self._process.poll() is None:
            self._process.terminate()

    def _hook(self, p):
        self._process = p

    def _emit(self, m, p):
        if self.cancel_event.is_set():
            raise PipelineCancelled("Generation cancelled")
        self.progress(m, p)

    @staticmethod
    def parse_script(text, mode):
        tagged = re.compile(r"^(hook|intro|point|section|outro)\s*:\s*(.+)$", re.I)
        scenes = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            match = tagged.match(line)
            kind, body = (match.group(1).lower(), match.group(2).strip()) if match else ("point", line)
            duration = max(2.4, min(8, len(body.split()) / 2.6))
            duration = max(2, min(5, duration)) if mode is VideoFormat.SHORT else duration
            scenes.append(Scene(body, kind, round(duration, 2), title=kind.upper()))
        return scenes[: 6 if mode is VideoFormat.SHORT else 30]

    def run(self, project: ProjectSpec):
        self.cancel_event.clear()
        supported = {
            "image_provider": {"local-card"},
            "voice_provider": {"silent-preview"},
            "music_provider": {"none", "procedural"},
            "avatar_provider": {"local-vtuber", "none"},
        }
        for field, choices in supported.items():
            selected = getattr(project, field)
            if selected not in choices:
                raise ValueError(
                    f"{selected!r} is a cataloged provider contract, not an installed adapter. "
                    f"Choose one of: {', '.join(sorted(choices))}."
                )
        run_id = uuid.uuid4().hex[:10]
        root = Path(project.output_dir) / project.format.value / run_id
        work = root / "work"
        work.mkdir(parents=True, exist_ok=True)
        try:
            self._emit("Planning scenes", 0.05)
            scenes = project.scenes or self.parse_script(project.script, project.format)
            if not scenes:
                raise ValueError("Add at least one line of script")
            for i, s in enumerate(scenes):
                s.image_path = str(LocalCardProvider().generate(s, project, i, work / "frames" / f"scene-{i:03d}.png"))
                self._emit(f"Visual {i + 1}/{len(scenes)}", 0.1 + 0.18 * (i + 1) / len(scenes))
            for i, s in enumerate(scenes):
                s.audio_path = str(write_silence(work / "voice" / f"scene-{i:03d}.wav", s.duration))
                self._emit(f"Voice track {i + 1}/{len(scenes)}", 0.3 + 0.12 * (i + 1) / len(scenes))
            avatar = (
                LocalAvatarProvider().generate(project, work / "avatar.png")
                if project.avatar_provider != "none"
                else None
            )
            self._emit("Avatar prepared", 0.46)
            total = sum(s.duration for s in scenes)
            music = (
                write_music(work / "music.wav", total, project.title)
                if project.music_provider == "procedural"
                else None
            )
            self._emit("Music prepared", 0.52)
            slug = re.sub(r"[^a-z0-9]+", "-", project.title.lower()).strip("-") or "video"
            output = render_video(
                project, scenes, work, root / f"{slug}.mp4", music, avatar, self.cancel_event, self._emit, self._hook
            )
            manifest = project.manifest()
            manifest.update(
                {
                    "run_id": run_id,
                    "duration": round(total, 2),
                    "video": str(output),
                    "scenes": [s.__dict__ for s in scenes],
                }
            )
            (root / "project.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            export_catalog(root / "provider-catalog.json")
            shutil.rmtree(work, ignore_errors=True)
            return {
                "video_path": str(output),
                "manifest_path": str(root / "project.json"),
                "provider_catalog": str(root / "provider-catalog.json"),
                "duration": round(total, 2),
                "format": project.format.value,
            }
        except InterruptedError as exc:
            shutil.rmtree(root, ignore_errors=True)
            raise PipelineCancelled(str(exc)) from exc


def probe_video(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)
