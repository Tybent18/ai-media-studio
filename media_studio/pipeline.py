import json
import re
import shutil
import subprocess
import threading
import uuid
from pathlib import Path

from .models import ProjectSpec, Scene, VideoFormat
from .layered import AssetLibrary, render_frame as render_layered_frame, write_plan
from .providers import (
    InfographicProvider,
    LocalAvatarProvider,
    LocalMediaProvider,
    export_catalog,
    write_edge_narration,
    write_flite_narration,
    write_music,
    write_piper_narration,
    write_silence,
)
from .renderer import render_video


class PipelineCancelled(RuntimeError):
    pass


class MediaPipeline:
    STAGES = ("plan", "visuals", "voice", "avatar", "music", "render", "package")

    def __init__(self, progress=None, preview=None):
        self.progress = progress or (lambda m, p: None)
        self.preview = preview or (lambda path: None)
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
        asset = re.compile(r"\s*\[media=(.+?)\]\s*$", re.I)
        scenes = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            match = tagged.match(line)
            kind, body = (match.group(1).lower(), match.group(2).strip()) if match else ("point", line)
            media = asset.search(body)
            image_path = media.group(1).strip() if media else None
            body = asset.sub("", body).strip()
            duration = max(2.4, min(8, len(body.split()) / 2.6))
            duration = max(2, min(5, duration)) if mode is VideoFormat.SHORT else duration
            scenes.append(Scene(body, kind, round(duration, 2), image_path=image_path, title=kind.upper()))
        return scenes[: 6 if mode is VideoFormat.SHORT else 30]

    def run(self, project: ProjectSpec):
        self.cancel_event.clear()
        supported = {
            "image_provider": {"local-card", "local-media", "infographic"},
            "voice_provider": {"silent-preview", "edge-tts", "flite", "piper"},
            "music_provider": {"none", "procedural", "local-file", "youtube-audio-library"},
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
        # Resolve the run workspace once. V6 scene plans survive multiple
        # rendering stages, so relative output/work paths can otherwise be
        # interpreted from a different current directory later in the run.
        root = (Path(project.output_dir) / project.format.value / run_id).resolve()
        work = root / "work"
        work.mkdir(parents=True, exist_ok=True)
        try:
            self._emit("Planning scenes", 0.05)
            scenes = project.scenes or self.parse_script(project.script, project.format)
            if not scenes:
                raise ValueError("Add at least one line of script")
            if project.music_provider == "youtube-audio-library" and project.music_credit_card:
                label = " — ".join(x for x in (project.music_title, project.music_artist) if x)
                scenes.append(
                    Scene(
                        f"Music: {label or 'YouTube Audio Library track'}\nSource: {project.music_source}",
                        "music-credit",
                        3.0,
                        title="MUSIC CREDIT",
                    )
                )
            for i, s in enumerate(scenes):
                if project.image_provider == "infographic":
                    assets = AssetLibrary()
                    plan = write_plan(s, i, project, work / "plans" / f"scene-{i:03d}.json", assets)
                    s.composition_path = str(plan)
                    s.image_path = str(render_layered_frame(plan, work / "frames" / f"scene-{i:03d}.png", project))
                    s.motion = "layered"
                else:
                    s.image_path = str(LocalMediaProvider().generate(s, project, i, work / "frames" / f"scene-{i:03d}.png"))
                self.preview(s.image_path)
                self._emit(f"Visual {i + 1}/{len(scenes)}", 0.1 + 0.18 * (i + 1) / len(scenes))
            for i, s in enumerate(scenes):
                if s.kind == "music-credit":
                    s.audio_path = str(write_silence(work / "voice" / f"scene-{i:03d}.wav", s.duration))
                elif project.voice_provider == "edge-tts":
                    audio, duration = write_edge_narration(
                        work / "voice" / f"scene-{i:03d}.mp3", s.text, project.voice, project.voice_rate
                    )
                    s.audio_path = str(audio)
                    s.duration = round(max(2.0, duration + 0.35), 2)
                elif project.voice_provider == "flite":
                    audio, duration = write_flite_narration(
                        work / "voice" / f"scene-{i:03d}.wav",
                        s.text,
                        project.voice if project.voice in {"awb", "kal", "kal16", "rms", "slt"} else "slt",
                    )
                    s.audio_path = str(audio)
                    s.duration = round(max(2.0, duration + 0.35), 2)
                elif project.voice_provider == "piper":
                    audio, duration = write_piper_narration(
                        work / "voice" / f"scene-{i:03d}.wav", s.text, project.piper_model
                    )
                    s.audio_path = str(audio)
                    s.duration = round(max(2.0, duration + 0.35), 2)
                else:
                    s.audio_path = str(write_silence(work / "voice" / f"scene-{i:03d}.wav", s.duration))
                self._emit(f"Voice track {i + 1}/{len(scenes)}", 0.3 + 0.12 * (i + 1) / len(scenes))
            avatar = (
                LocalAvatarProvider().generate(project, work / "avatar.png")
                if project.avatar_provider != "none"
                else None
            )
            self._emit("Avatar prepared", 0.46)
            total = sum(s.duration for s in scenes)
            if project.music_provider == "procedural":
                music = write_music(work / "music.wav", total, project.title)
            elif project.music_provider in {"local-file", "youtube-audio-library"}:
                if not project.music_path or not Path(project.music_path).is_file():
                    raise ValueError("Choose an existing music file when using local-file music")
                music = Path(project.music_path)
            else:
                music = None
            self._emit("Music prepared", 0.52)
            slug = re.sub(r"[^a-z0-9]+", "-", project.title.lower()).strip("-") or "video"
            output = render_video(
                project,
                scenes,
                work,
                root / f"{slug}.mp4",
                music,
                avatar,
                self.cancel_event,
                self._emit,
                self._hook,
                self.preview,
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
            description_path = None
            if project.music_provider == "youtube-audio-library":
                credit = project.music_attribution.strip() or "\n".join(
                    x
                    for x in (
                        f"Music: {project.music_title}" if project.music_title else "",
                        f"Artist: {project.music_artist}" if project.music_artist else "",
                        f"Source: {project.music_source}" if project.music_source else "",
                        f"License: {project.music_license}" if project.music_license else "",
                    )
                    if x
                )
                description_path = root / "video-description.txt"
                description_path.write_text("MUSIC CREDIT\n" + credit + "\n", encoding="utf-8")
            export_catalog(root / "provider-catalog.json")
            shutil.rmtree(work, ignore_errors=True)
            return {
                "video_path": str(output),
                "manifest_path": str(root / "project.json"),
                "provider_catalog": str(root / "provider-catalog.json"),
                "description_path": str(description_path) if description_path else None,
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
