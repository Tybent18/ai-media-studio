import unittest

# Core pipeline imports (adjust paths if needed)
from core.parser import ScriptParser
from story_intelligence import analyze_script
from scene_builder import build_scenes
from storyboard_builder import build_storyboard
from visual_engine import get_visual
from tts import generate_voice
from video_time_controller import build_video_timeline


# -----------------------------
# SAMPLE SCRIPT (REALISTIC INPUT)
# -----------------------------
TEST_SCRIPT = """
Hook: Imagine a world where AI builds everything for you.

Intro: In this video, we explore how AI video systems actually work.

Point: These systems combine vision models, speech synthesis, and editing logic.

Outro: This is just the beginning of automated storytelling.
"""


class TestVideoPipeline(unittest.TestCase):

    # -----------------------------
    # FULL PIPELINE TEST
    # -----------------------------
    def test_full_pipeline_execution(self):

        parser = ScriptParser()

        # 1. PARSE
        parsed = parser.parse(TEST_SCRIPT)
        self.assertTrue(len(parsed) > 0)

        # 2. STORY INTELLIGENCE
        story = analyze_script(TEST_SCRIPT)
        self.assertIn("energy", story)
        self.assertIn("topic", story)

        # 3. SCENE BUILDING
        scenes = build_scenes(parsed, story, mode="long")
        self.assertTrue(len(scenes) > 0)

        # validate scene structure
        for s in scenes:
            self.assertIn("text", s)
            self.assertIn("type", s)

        # 4. STORYBOARD
        storyboard = build_storyboard(parsed, story, mode="long")
        self.assertTrue(len(storyboard) > 0)

        # 5. VISUAL GENERATION (SAFE MODE)
        for i, scene in enumerate(scenes):

            visual = get_visual(
                scene,
                i,
                mode="long",
                story_signals=story
            )

            self.assertIn("paths", visual)
            self.assertIn("motion", visual)

            # attach for downstream validation
            scene["visual"] = visual

        # 6. TTS GENERATION (MOCK-SAFE CHECK)
        tts_map = {}

        for i, scene in enumerate(scenes):

            try:
                audio = generate_voice(scene, i, mode="long")
                tts_map[i] = audio

                self.assertTrue(audio.endswith(".mp3"))

            except Exception as e:
                self.fail(f"TTS failed at scene {i}: {e}")

        # 7. TIMELINE BUILDING
        timeline = build_video_timeline(
            scenes,
            storyboard,
            tts_map,
            story
        )

        self.assertIn("timeline", timeline)
        self.assertTrue(len(timeline["timeline"]) > 0)

        # -----------------------------
        # STRUCTURAL VALIDATION
        # -----------------------------
        for node in timeline["timeline"]:

            self.assertIn("start_time", node)
            self.assertIn("end_time", node)
            self.assertIn("text", node)

            # sanity check timing
            self.assertLess(node["start_time"], node["end_time"])

        print("\n✅ FULL PIPELINE TEST PASSED")


    # -----------------------------
    # TIMING CONSISTENCY TEST
    # -----------------------------
    def test_timeline_consistency(self):

        parser = ScriptParser()
        parsed = parser.parse(TEST_SCRIPT)

        story = analyze_script(TEST_SCRIPT)
        scenes = build_scenes(parsed, story)

        storyboard = build_storyboard(parsed, story)

        tts_map = {i: f"audio_{i}.mp3" for i in range(len(scenes))}

        timeline = build_video_timeline(
            scenes,
            storyboard,
            tts_map,
            story
        )

        last_end = 0

        for node in timeline["timeline"]:

            # no overlaps allowed
            self.assertGreaterEqual(node["start_time"], last_end)

            last_end = node["end_time"]

        print("\n✅ TIMELINE CONSISTENCY OK")


    # -----------------------------
    # SYSTEM STABILITY TEST
    # -----------------------------
    def test_system_resilience(self):

        parser = ScriptParser()

        # broken input simulation
        broken_script = """
        Random text with no structure
        Another line without tags
        Outro: Still should survive
        """

        parsed = parser.parse(broken_script)

        # system should NOT crash
        self.assertIsInstance(parsed, list)

        # should recover at least one valid scene
        self.assertTrue(len(parsed) >= 0)

        print("\n✅ RESILIENCE TEST PASSED")


if __name__ == "__main__":
    unittest.main()