import unittest
from core.parser import ScriptParser


class TestScriptParser(unittest.TestCase):

    def setUp(self):
        self.parser = ScriptParser()

    # -----------------------------
    # BASIC PARSING
    # -----------------------------
    def test_basic_parsing(self):

        input_script = """
        Hook: Welcome to the future of AI.
        Intro: In this video we explore artificial intelligence.
        Point: AI is transforming industries.
        Outro: Thank you for watching!
        """

        result = self.parser.parse(input_script)

        self.assertEqual(result[0]["section"], "hook")
        self.assertEqual(result[1]["section"], "intro")
        self.assertEqual(result[2]["section"], "point")
        self.assertEqual(result[3]["section"], "outro")

    # -----------------------------
    # EMPTY SCRIPT
    # -----------------------------
    def test_empty_script(self):

        result = self.parser.parse("")
        self.assertEqual(result, [])

    # -----------------------------
    # INVALID LINES FILTERED
    # -----------------------------
    def test_invalid_lines_filtered(self):

        input_script = """
        Hook: Valid hook line.
        InvalidLine: Should be ignored.
        Outro: Valid outro.
        """

        result = self.parser.parse(input_script)

        sections = [r["section"] for r in result]

        self.assertIn("hook", sections)
        self.assertIn("outro", sections)
        self.assertNotIn("invalidline", sections)

    # -----------------------------
    # SCENE TYPE NORMALIZATION
    # -----------------------------
    def test_scene_detection(self):

        input_script = """
        Hook: Start strong.
        Intro: Build context.
        """

        result = self.parser.parse(input_script)

        self.assertEqual(result[0]["section"], "hook")
        self.assertEqual(result[1]["section"], "intro")

    # -----------------------------
    # SPECIAL CHARACTERS
    # -----------------------------
    def test_special_characters(self):

        input_script = """
        Hook: AI is insane! 🎉🔥
        Outro: Thanks 👍
        """

        result = self.parser.parse(input_script)

        self.assertTrue("🎉" in result[0]["text"])
        self.assertTrue("👍" in result[1]["text"])

    # -----------------------------
    # FALLBACK HANDLING
    # -----------------------------
    def test_untagged_lines_handling(self):

        input_script = """
        This should be ignored or normalized.
        Outro: Final line.
        """

        result = self.parser.parse(input_script)

        # only valid structured lines survive
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["section"], "outro")

    # -----------------------------
    # MULTI-LINE STRUCTURE
    # -----------------------------
    def test_multiline_structure(self):

        input_script = """
        Hook: Big idea incoming.
        Intro: AI is evolving rapidly.
        Outro: That’s it.
        """

        result = self.parser.parse(input_script)

        for item in result:
            self.assertIn("text", item)
            self.assertIn("section", item)

    # -----------------------------
    # ROBUST PIPELINE COMPATIBILITY
    # -----------------------------
    def test_pipeline_ready_format(self):

        input_script = """
        Hook: Testing pipeline compatibility.
        Point: Ensuring structure is valid.
        """

        result = self.parser.parse(input_script)

        for item in result:
            # critical schema contract for your system
            self.assertIn("text", item)
            self.assertIn("section", item)


if __name__ == "__main__":
    unittest.main()