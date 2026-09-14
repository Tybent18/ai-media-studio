import argparse
import json

from media_studio.gui import launch
from media_studio.models import ProjectSpec, VideoFormat
from media_studio.pipeline import MediaPipeline


def main():
    p = argparse.ArgumentParser(description="AI Media Studio V4")
    p.add_argument("--gui", action="store_true")
    p.add_argument("--topic")
    p.add_argument("--script")
    p.add_argument("--mode", choices=["long", "short"], default="long")
    p.add_argument("--theme", choices=["midnight", "ember", "forest", "violet"], default="midnight")
    a = p.parse_args()
    if a.gui or not a.topic:
        launch()
        return 0
    script = (
        a.script
        or f"Hook: Imagine {a.topic}.\n"
        "Point: This preview was rendered locally by AI Media Studio.\n"
        "Outro: Review the result and continue editing."
    )
    result = MediaPipeline(lambda m, v: print(f"[{v:>6.1%}] {m}")).run(
        ProjectSpec(title=a.topic, script=script, format=VideoFormat(a.mode), theme=a.theme)
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
