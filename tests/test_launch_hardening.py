import threading
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from media_studio import renderer
from media_studio.pipeline import MediaPipeline


def test_avatar_compositing_does_not_modify_imported_image(tmp_path, monkeypatch):
    original = tmp_path / "original.png"
    avatar = tmp_path / "avatar.png"
    Image.new("RGB", (240, 160), (30, 40, 50)).save(original)
    Image.new("RGBA", (80, 80), (200, 10, 10, 255)).save(avatar)
    before = original.read_bytes()
    captured = []

    def fake_run(cmd, cancel, hook=None):
        captured.append(cmd)

    monkeypatch.setattr(renderer, "_run", fake_run)
    monkeypatch.setattr(renderer, "_has_audio_stream", lambda path: True)
    monkeypatch.setattr(renderer.shutil, "copy2", lambda src, dst: __import__("shutil").copyfile(src, dst))
    scene = SimpleNamespace(image_path=str(original), audio_path=str(original), composition_path=None,
                            duration=2.5, text="Example", motion="zoom-in")
    project = SimpleNamespace(format=SimpleNamespace(size=(240, 160), value="long"), captions=False,
                              fps=30, voice_volume=1.0, music_volume=0.2)
    monkeypatch.setattr(renderer.shutil, "which", lambda name: name)
    renderer.render_video(project, [scene], tmp_path / "work", tmp_path / "out.mp4", None,
                          avatar, threading.Event(), lambda *args: None)
    assert original.read_bytes() == before
    assert any("avatar-composited" in str(item) for cmd in captured for item in cmd)


def test_project_scenes_are_not_mutated_when_render_fails(tmp_path, monkeypatch):
    from media_studio.models import ProjectSpec, Scene

    project = ProjectSpec(title="Safety", script="Point: Hello", scenes=[Scene("Hello", "point", 2.5)],
                          output_dir=str(tmp_path))
    before = [scene.__dict__.copy() for scene in project.scenes]

    def fail(*args, **kwargs):
        raise RuntimeError("render failure")

    monkeypatch.setattr("media_studio.pipeline.LocalMediaProvider.generate", fail)
    try:
        MediaPipeline().run(project)
    except RuntimeError:
        pass
    assert [scene.__dict__ for scene in project.scenes] == before
