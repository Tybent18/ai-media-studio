import os
import re
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


class RenderError(RuntimeError):
    pass


def _run(cmd, cancel, hook=None):
    if cancel.is_set():
        raise InterruptedError("Render cancelled")

    # Do not leave FFmpeg stderr attached to an unread PIPE while polling.
    # FFmpeg can fill the OS pipe buffer during a render and deadlock:
    # FFmpeg waits for Python to drain stderr while Python waits for FFmpeg
    # to exit. A temporary file keeps diagnostics without a bounded pipe.
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8", errors="replace") as err_file:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=err_file,
            text=True,
        )
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
                        process.wait()
                    raise InterruptedError("Render cancelled")
            if process.returncode:
                err_file.seek(0)
                err = err_file.read()
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


def _caption_font(size):
    """Load a usable bold caption font on Windows, macOS, or Linux."""
    windows = Path(os.environ.get("WINDIR", r"C:\\Windows")) / "Fonts"
    candidates = [
        windows / "arialbd.ttf",
        windows / "segoeuib.ttf",
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/Library/Fonts/Arial Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size), path
            except OSError:
                continue
    return ImageFont.load_default(), None


def _caption_image(frame, target, text):
    base = Image.open(frame).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font, _ = _caption_font(max(28, base.width // 32))
    wrapped = "\n".join(textwrap.wrap(text, 38 if base.width < base.height else 70))
    box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=8, align="center")
    tw, th = box[2] - box[0], box[3] - box[1]
    x, y = base.width // 2, int(base.height * 0.13)
    pad = max(18, base.width // 45)
    draw.rounded_rectangle(
        (x - tw // 2 - pad, y - pad, x + tw // 2 + pad, y + th + pad),
        radius=pad,
        fill=(0, 0, 0, 172),
        outline=(255, 255, 255, 70),
        width=2,
    )
    draw.multiline_text((x, y), wrapped, font=font, fill="white", anchor="ma", spacing=8, align="center")
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.alpha_composite(base, overlay).convert("RGB").save(target)
    return target


def _has_audio_stream(path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RenderError("FFprobe is required to validate rendered audio")
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "default=nw=1:nk=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def render_video(project, scenes, workspace, output, music, avatar, cancel, progress, hook=None, preview=None):
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
        if project.captions and not is_video:
            frame = _caption_image(frame, workspace / "captioned" / f"scene-{i:03d}.png", scene.text)
        if avatar and not is_video:
            _avatar(frame, avatar)
        segment = segdir / f"scene-{i:03d}.mp4"
        fade_out = max(0, scene.duration - 0.25)
        caption_text = re.sub(r"[':%]", "", scene.text).replace("\\", "").replace("\n", " ")[:180]
        caption = r"\n".join(textwrap.wrap(caption_text, 32 if project.format.value == "short" else 65))
        caption_filter = ""
        if project.captions and caption and is_video:
            _, font_path = _caption_font(max(34, w // 30))
            size = max(34, w // 30)
            caption_file = workspace / "captions" / f"scene-{i:03d}.txt"
            caption_file.parent.mkdir(parents=True, exist_ok=True)
            caption_file.write_text(caption_text, encoding="utf-8")
            font_option = f"fontfile='{font_path.as_posix()}':" if font_path else ""
            caption_filter = (
                f",drawtext={font_option}textfile='{caption_file}':fontcolor=white:fontsize={size}:"
                "x=(w-text_w)/2:y=h-text_h-h*0.075:box=1:boxcolor=black@0.62:boxborderw=18"
            )
        if is_video:
            visual_input = ["-stream_loop", "-1", "-i", str(frame)]
            visual_filter = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
        else:
            visual_input = ["-loop", "1", "-i", str(frame)]
            frames = max(1, int(scene.duration * project.fps))
            if scene.motion == "punch-in":
                zoom = "min(zoom+0.0018,1.14)"
                x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
            elif scene.motion == "pan-right":
                zoom = "1.08"
                x_expr, y_expr = f"(iw-iw/zoom)*on/{frames}", "ih/2-(ih/zoom/2)"
            elif scene.motion == "pan-left":
                zoom = "1.08"
                x_expr, y_expr = f"(iw-iw/zoom)*(1-on/{frames})", "ih/2-(ih/zoom/2)"
            elif scene.motion == "zoom-out":
                zoom = "max(1.08-0.0007*on,1.0)"
                x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
            else:
                zoom = "min(zoom+0.0007,1.08)"
                x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
            visual_filter = (
                f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
                f"zoompan=z='{zoom}':x='{x_expr}':y='{y_expr}':"
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
                "-af",
                f"volume={project.voice_volume}",
                "-shortest",
                str(segment),
            ],
            cancel,
            hook,
        )
        if not _has_audio_stream(segment):
            raise RenderError(f"Rendered scene {i + 1} has no audio stream: {segment}")
        segments.append(segment)
        if preview:
            preview(frame)
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
    if not _has_audio_stream(output):
        raise RenderError(
            "Final video has no audio stream. The render was stopped instead of reporting a silent video as complete."
        )
    progress("Video ready", 1)
    return output
