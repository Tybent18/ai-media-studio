import shutil
import subprocess
from pathlib import Path

from PIL import Image


class RenderError(RuntimeError):
    pass


def _run(cmd, cancel, hook=None):
    if cancel.is_set():
        raise InterruptedError("Render cancelled")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if hook:
        hook(process)
    try:
        while process.poll() is None:
            if cancel.wait(0.08):
                process.terminate()
                try:
                    process.wait(2)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise InterruptedError("Render cancelled")
        _, err = process.communicate()
        if process.returncode:
            raise RenderError(err.strip().splitlines()[-1] if err else "FFmpeg failed")
    finally:
        if hook:
            hook(None)


def _avatar(frame, avatar):
    base = Image.open(frame).convert("RGBA")
    host = Image.open(avatar).convert("RGBA")
    size = max(140, int(base.width * 0.22))
    host.thumbnail((size, size))
    base.alpha_composite(
        host, (base.width - host.width - int(base.width * 0.035), base.height - host.height - int(base.height * 0.025))
    )
    base.convert("RGB").save(frame)


def render_video(project, scenes, workspace, output, music, avatar, cancel, progress, hook=None):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RenderError("FFmpeg is required and must be available on PATH")
    segdir = workspace / "segments"
    segdir.mkdir(parents=True, exist_ok=True)
    segments = []
    w, h = project.format.size
    for i, scene in enumerate(scenes):
        frame = Path(scene.image_path)
        audio = Path(scene.audio_path)
        if avatar:
            _avatar(frame, avatar)
        segment = segdir / f"scene-{i:03d}.mp4"
        _run(
            [
                ffmpeg,
                "-y",
                "-loop",
                "1",
                "-i",
                str(frame),
                "-i",
                str(audio),
                "-t",
                str(scene.duration),
                "-vf",
                f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
                "-r",
                str(project.fps),
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-c:a",
                "aac",
                "-shortest",
                str(segment),
            ],
            cancel,
            hook,
        )
        segments.append(segment)
        progress(f"Rendered scene {i + 1}/{len(scenes)}", 0.55 + 0.3 * (i + 1) / len(scenes))
    listing = workspace / "segments.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in segments), encoding="utf-8")
    joined = workspace / "joined.mp4"
    _run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(joined)], cancel, hook)
    output.parent.mkdir(parents=True, exist_ok=True)
    if music:
        _run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(joined),
                "-stream_loop",
                "-1",
                "-i",
                str(music),
                "-filter_complex",
                "[1:a]volume=.13[m];[0:a][m]amix=inputs=2:duration=first[a]",
                "-map",
                "0:v",
                "-map",
                "[a]",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
                str(output),
            ],
            cancel,
            hook,
        )
    else:
        shutil.copy2(joined, output)
    progress("Video ready", 1)
    return output
