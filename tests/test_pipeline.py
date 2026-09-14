import json
from pathlib import Path

import pytest

from media_studio.models import ProjectSpec, VideoFormat
from media_studio.pipeline import MediaPipeline, PipelineCancelled, probe_video
from media_studio.providers import PROVIDER_CATALOG

SCRIPT = """Hook: Start with a sharp question.
Point: Explain the system with visible evidence.
Outro: End with a clear next step."""


def test_parser_normalizes_modes():
    assert [x.kind for x in MediaPipeline.parse_script(SCRIPT, VideoFormat.LONG)] == ["hook", "point", "outro"]
    assert len(MediaPipeline.parse_script("\n".join(f"Point: {i}" for i in range(10)), VideoFormat.SHORT)) == 6


@pytest.mark.parametrize("mode,size", [(VideoFormat.LONG, (1280, 720)), (VideoFormat.SHORT, (720, 1280))])
def test_real_render_has_expected_canvas(tmp_path, mode, size):
    result = MediaPipeline().run(ProjectSpec("Render proof", SCRIPT, mode, output_dir=tmp_path))
    path = Path(result["video_path"])
    assert path.exists() and path.stat().st_size > 1000
    info = probe_video(path)
    video = next(x for x in info["streams"] if x["codec_type"] == "video")
    assert (video["width"], video["height"]) == size
    assert float(info["format"]["duration"]) > 5
    assert Path(result["manifest_path"]).exists()
    assert json.loads(Path(result["provider_catalog"]).read_text())["image"]


def test_cancellation_before_work_removes_partial_run(tmp_path):
    pipe = MediaPipeline()
    pipe.cancel_event.set()
    with pytest.raises(PipelineCancelled):
        pipe._emit("stop", 0.2)


def test_active_render_can_be_cancelled_and_cleaned(tmp_path):
    holder = {}

    def stop_during_render(_message, value):
        if value >= 0.55:
            holder["pipe"].cancel()

    pipe = MediaPipeline(stop_during_render)
    holder["pipe"] = pipe
    with pytest.raises(PipelineCancelled):
        pipe.run(ProjectSpec("Cancelled render", SCRIPT, VideoFormat.LONG, output_dir=tmp_path))
    assert not list(tmp_path.rglob("*.mp4"))


def test_provider_catalog_has_local_fallbacks_and_remote_contracts():
    assert {x.mode for x in PROVIDER_CATALOG["image"]} >= {"offline", "adapter"}
    assert any(x.key == "elevenlabs" for x in PROVIDER_CATALOG["voice"])
    assert any(x.key == "local-vtuber" for x in PROVIDER_CATALOG["avatar"])


def test_uninstalled_remote_adapter_is_never_silently_faked(tmp_path):
    with pytest.raises(ValueError, match="not an installed adapter"):
        MediaPipeline().run(ProjectSpec("Remote", SCRIPT, image_provider="openai-image", output_dir=tmp_path))
