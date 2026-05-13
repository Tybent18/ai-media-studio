import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from system_check import run_system_check

from story_intelligence import analyze_script
from scene_builder import build_scenes
from storyboard_builder import build_storyboard
from visual_engine import generate_all_scene_images
from tts import generate_voice

# avatar system
from avatar_engine import build_avatar_rig

# timeline systems
from video_time_controller import build_video_timeline
from master_timeline_engine import build_master_timeline

# metadata
from youtube_pipeline import (
    generate_title,
    generate_description
)

# renderer
from renderer import assemble_video

from config import MODE_DEFAULT


# -----------------------------
# OUTPUT ROUTING
# -----------------------------
def get_output_dir(mode):
    return f"output/{mode}"


# -----------------------------
# CORE PIPELINE
# -----------------------------
def run_pipeline(topic, mode=MODE_DEFAULT):

    print("\n🎬 STARTING AI VIDEO PIPELINE\n")

    # -----------------------------
    # SYSTEM CHECK
    # -----------------------------
    if not run_system_check():

        print("❌ System not ready")
        return None

    # -----------------------------
    # SCRIPT
    # -----------------------------
    script = (
        f"Imagine a future where "
        f"{topic} is fully automated "
        f"and intelligent."
    )

    print(f"🧠 Topic: {topic}")

    # -----------------------------
    # STORY ANALYSIS
    # -----------------------------
    print("\n📖 Building story intelligence...")

    story = analyze_script(script)

    # -----------------------------
    # SCENE BUILDING
    # -----------------------------
    print("\n🎞️ Building scenes...")

    scenes = build_scenes(
        [{"text": script, "section": "hook"}],
        mode
    )

    print(f"✅ Scenes created: {len(scenes)}")

    # -----------------------------
    # STORYBOARD
    # -----------------------------
    print("\n🧩 Building storyboard...")

    storyboard = build_storyboard(
        scenes,
        story,
        mode
    )

    # -----------------------------
    # VISUAL GENERATION
    # -----------------------------
    print("\n🖼️ Generating visuals...")

    scenes = generate_all_scene_images(scenes)

    # -----------------------------
    # AUDIO GENERATION
    # -----------------------------
    print("\n🎤 Generating voice audio...")

    valid_scenes = []

    for i, scene in enumerate(scenes):

        try:

            audio = generate_voice(
                scene,
                i,
                mode
            )

            if not audio:
                raise Exception("No audio path returned")

            if not os.path.exists(audio):
                raise Exception(
                    f"Audio file missing: {audio}"
                )

            # attach audio
            scene["audio"] = audio

            # -----------------------------
            # AVATAR RIG ONLY
            # -----------------------------
            # IMPORTANT:
            # DO NOT generate fake mp4 files
            # until real avatar rendering exists
            # -----------------------------
            rig = build_avatar_rig(scene, audio)

            scene["avatar_rig"] = rig

            # -----------------------------
            # DEBUG
            # -----------------------------
            print(f"\n✅ Scene {i} ready")
            print(f"AUDIO: {scene.get('audio')}")
            print(f"VISUAL: {scene.get('visual')}")

            valid_scenes.append(scene)

        except Exception as e:

            print(f"\n❌ Scene {i} failed")
            print(e)

    # -----------------------------
    # SAFETY CHECK
    # -----------------------------
    if not valid_scenes:

        print("\n❌ No valid scenes generated")
        return None

    scenes = valid_scenes

    # -----------------------------
    # TIMELINE SYSTEMS
    # -----------------------------
    # kept for metadata / future editing
    # -----------------------------
    print("\n⏱️ Building timelines...")

    timeline = build_video_timeline(
        scenes,
        storyboard,
        story
    )

    master = build_master_timeline(
        scenes,
        storyboard,
        story
    )

    # -----------------------------
    # OUTPUT DIR
    # -----------------------------
    output_dir = get_output_dir(mode)

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    # -----------------------------
    # FINAL RENDER
    # -----------------------------
    print("\n🎬 Rendering final video...")

    output_path = assemble_video(
        scenes,
        mode
    )

    if not output_path:

        print("\n❌ Render failed")
        return None

    # -----------------------------
    # METADATA
    # -----------------------------
    print("\n🧠 Generating metadata...")

    title = generate_title(
        topic,
        script
    )

    desc = generate_description(topic)

    # -----------------------------
    # COMPLETE
    # -----------------------------
    print("\n🔥 PIPELINE COMPLETE")
    print(f"🎬 OUTPUT: {output_path}")
    print(f"📝 TITLE: {title}")

    return {
        "video_path": output_path,
        "title": title,
        "description": desc,
        "timeline": master
    }


# -----------------------------
# CLI ENTRY
# -----------------------------
if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--topic",
        required=True
    )

    parser.add_argument(
        "--mode",
        default=MODE_DEFAULT
    )

    args = parser.parse_args()

    run_pipeline(
        args.topic,
        args.mode
    )