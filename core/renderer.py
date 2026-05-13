import os
import random

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeAudioClip,
    concatenate_videoclips,
    vfx
)

from PIL import Image

# Pillow compatibility fix
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS


# -----------------------------
# MOTION ENGINE
# -----------------------------
def apply_motion(clip, motion_type):

    try:

        if motion_type == "zoom_in":
            return clip.fx(vfx.resize, lambda t: 1 + 0.03 * t)

        elif motion_type == "zoom_out":
            return clip.fx(vfx.resize, lambda t: 1.1 - 0.03 * t)

        elif motion_type == "pan_left":
            return clip.set_position(
                lambda t: (-20 * t, "center")
            )

        elif motion_type == "pan_right":
            return clip.set_position(
                lambda t: (20 * t, "center")
            )

        return clip

    except Exception as e:

        print(f"⚠️ Motion failed: {e}")
        return clip


# -----------------------------
# BUILD SCENE CLIP
# -----------------------------
def build_clip(scene):

    audio_path = scene.get("audio")

    if not audio_path:
        raise Exception("Scene missing audio")

    if not os.path.exists(audio_path):
        raise Exception(f"Missing audio: {audio_path}")

    audio = AudioFileClip(audio_path)

    print(f"[DEBUG] Audio loaded: {audio_path}")
    print(f"[DEBUG] Audio duration: {audio.duration}")

    if audio.duration is None or audio.duration <= 0.2:
        raise Exception("Invalid audio duration")

    visual = scene.get("visual", {})

    image_paths = visual.get(
        "paths",
        [visual.get("path")]
    )

    image_paths = [
        p for p in image_paths
        if p and os.path.exists(p)
    ]

    # fallback
    if not image_paths:

        print("⚠️ Using fallback image")

        fallback = "assets/broll/general_1.jpg"

        if not os.path.exists(fallback):
            raise Exception("Fallback image missing")

        image_paths = [fallback]

    duration_per_image = (
        audio.duration / len(image_paths)
    )

    subclips = []

    for img in image_paths:

        clip = (
            ImageClip(img)
            .set_duration(duration_per_image)
            .resize(height=1280)
        )

        motion = random.choice([
            "zoom_in",
            "zoom_out",
            "pan_left",
            "pan_right",
            "static"
        ])

        clip = apply_motion(clip, motion)

        subclips.append(clip)

    clip = concatenate_videoclips(
        subclips,
        method="compose"
    )

    clip = clip.set_duration(audio.duration)

    # attach native audio
    clip = clip.set_audio(audio)

    print(f"[DEBUG] Clip audio: {clip.audio}")

    return clip


# -----------------------------
# MUSIC OVERLAY
# -----------------------------
def add_music(video, music_path):

    if not music_path:
        return video

    if not os.path.exists(music_path):
        return video

    try:

        music = (
            AudioFileClip(music_path)
            .volumex(0.15)
            .set_duration(video.duration)
        )

        if video.audio:

            final_audio = CompositeAudioClip([
                video.audio,
                music
            ])

        else:
            final_audio = music

        return video.set_audio(final_audio)

    except Exception as e:

        print(f"⚠️ Music failed: {e}")
        return video


# -----------------------------
# MAIN ASSEMBLER
# -----------------------------
def assemble_video(
    scenes,
    mode="long",
    music_path=None
):

    output_dir = f"output/{mode}"

    os.makedirs(output_dir, exist_ok=True)

    clips = []

    # -----------------------------
    # BUILD CLIPS
    # -----------------------------
    for i, scene in enumerate(scenes):

        try:

            clip = build_clip(scene)

            clips.append(clip)

            print(f"✅ Scene {i} complete")

        except Exception as e:

            print(f"❌ Scene {i} failed: {e}")

    if not clips:
        raise Exception("No clips generated")

    final = None

    try:

        # MoviePy preserves audio automatically
        final = concatenate_videoclips(
            clips,
            method="compose"
        )

        print(f"[DEBUG] Final audio: {final.audio}")

        if music_path:
            final = add_music(final, music_path)

        output_path = os.path.join(
            output_dir,
            "final_video.mp4"
        )

        print("[DEBUG] Exporting final video...")

        final.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            audio=True,
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            threads=4,
            preset="medium"
        )

        print(f"✅ Final video: {output_path}")

        return output_path

    finally:

        for clip in clips:

            try:
                clip.close()
            except:
                pass

        try:
            if final:
                final.close()
        except:
            pass