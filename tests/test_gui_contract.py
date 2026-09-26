from media_studio.gui import UI_STYLES
from media_studio.pipeline import MediaPipeline
from media_studio.providers import THEMES


def test_customization_and_stage_contracts():
    assert {"midnight", "ember", "forest", "violet"} <= set(THEMES)
    assert MediaPipeline.STAGES == ("plan", "visuals", "voice", "avatar", "music", "render", "package")
    assert {"Obsidian Neon", "Violet Cinema", "Ember Studio", "Arctic Light"} <= set(UI_STYLES)
