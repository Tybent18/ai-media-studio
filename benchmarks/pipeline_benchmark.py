import time
import tracemalloc
import statistics

from core.parser import ScriptParser
from story_intelligence import analyze_script
from scene_builder import build_scenes
from storyboard_builder import build_storyboard
from visual_engine import generate_all_scene_images
from tts import generate_voice
from video_time_controller import build_video_timeline


TEST_SCRIPTS = [
    "Hook: AI is changing everything. Intro: Let's explore this. Outro: Thanks.",
    "Hook: The future of automation. Intro: Systems are evolving. Point: AI replaces workflows. Outro: Done.",
    "Hook: Imagine infinite content creation. Intro: This is now possible. Outro: End."
]


def benchmark_pipeline():
    times = []
    memory_peaks = []

    for script in TEST_SCRIPTS:

        tracemalloc.start()
        start = time.time()

        parser = ScriptParser()
        parsed = parser.parse(script)

        story = analyze_script(script)
        scenes = build_scenes(parsed, story)
        storyboard = build_storyboard(parsed, story)

        # skip heavy image generation optionally
        scenes = generate_all_scene_images(scenes)

        tts_map = {}
        for i, scene in enumerate(scenes):
            try:
                tts_map[i] = generate_voice(scene, i)
            except:
                pass

        build_video_timeline(scenes, storyboard, tts_map, story)

        end = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        times.append(end - start)
        memory_peaks.append(peak / 1024 / 1024)

    print("\n=== PIPELINE BENCHMARK ===")
    print(f"Avg Time: {statistics.mean(times):.2f}s")
    print(f"Max Time: {max(times):.2f}s")
    print(f"Avg Memory: {statistics.mean(memory_peaks):.2f} MB")
    print(f"Peak Memory: {max(memory_peaks):.2f} MB")


if __name__ == "__main__":
    benchmark_pipeline()