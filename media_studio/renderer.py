import re
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
            raise RenderError("\n".join(err.strip().splitlines()[-12:]) if err else "FFmpeg failed")
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
        is_video = frame.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}
        if avatar and not is_video:
            _avatar(frame, avatar)
        segment = segdir / f"scene-{i:03d}.mp4"
        fade_out = max(0, scene.duration - 0.25)
        caption = re.sub(r"[':%]", "", scene.text).replace("\\", "").replace("\n", " ")[:180]
        caption_filter = ""
        if project.captions and caption:
            font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            size = max(34, w // 30)
            caption_filter = (
                f",drawtext=fontfile={font}:text='{caption}':fontcolor=white:fontsize={size}:"
                "x=(w-text_w)/2:y=h-text_h-h*0.075:box=1:boxcolor=black@0.62:boxborderw=18"
            )
        if is_video:
            visual_input = ["-stream_loop", "-1", "-i", str(frame)]
            visual_filter = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
        else:
            visual_input = ["-loop", "1", "-i", str(frame)]
            frames = max(1, int(scene.duration * project.fps))
            zoom = "min(zoom+0.0007,1.08)" if scene.motion != "zoom-out" else "max(1.08-0.0007*on,1.0)"
            visual_filter = (
                f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
                f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={frames}:s={w}x{h}:fps={project.fps}"
            )
        visual_filter += f",fade=t=in:st=0:d=0.22,fade=t=out:st={fade_out}:d=0.25{caption_filter},format=yuv420p"
        _run(
            [
                ffmpeg,
                "-y",
                *visual_input,
                "-i",
                str(audio),
                "-t",
                str(scene.duration),
                "-vf",
                visual_filter,
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
                f"[1:a]volume={project.music_volume}[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,"
                "loudnorm=I=-16:TP=-1.5:LRA=11[a]",
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
