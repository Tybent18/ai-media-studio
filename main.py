import argparse
import json

from media_studio.gui import launch
from media_studio.models import ProjectSpec, VideoFormat
from media_studio.pipeline import MediaPipeline


def main():
    p = argparse.ArgumentParser(description="AI Media Studio V5")
    p.add_argument("--gui", action="store_true")
    p.add_argument("--topic")
    p.add_argument("--script")
    p.add_argument("--mode", choices=["long", "short"], default="long")
    p.add_argument("--theme", choices=["midnight", "ember", "forest", "violet"], default="midnight")
    p.add_argument("--voice", default="en-US-GuyNeural", help="Edge TTS voice name")
    p.add_argument("--voice-rate", default="+0%")
    p.add_argument("--voice-volume", type=float, default=1.0, help="Narration gain, where 1.0 is 100 percent")
    p.add_argument("--piper-model", help="Path to a downloaded Piper .onnx voice model")
    p.add_argument("--silent", action="store_true", help="Use a silent preview instead of narration")
    p.add_argument("--media-dir", help="Folder of user-owned images/video B-roll")
    p.add_argument("--infographic", action="store_true", help="Use the animated educational infographic visual mode")
    p.add_argument("--music", help="User-owned music file (otherwise an original procedural score is used)")
    p.add_argument("--youtube-audio", help="MP3 downloaded by the user from YouTube Audio Library")
    p.add_argument("--music-title", default="")
    p.add_argument("--music-artist", default="")
    p.add_argument("--music-attribution", default="", help="Exact attribution text copied from Audio Library")
    p.add_argument("--music-source", default="YouTube Audio Library")
    p.add_argument("--music-volume", type=float, default=0.24, help="Music gain, where 0.24 is 24 percent")
    p.add_argument("--no-captions", action="store_true")
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
        ProjectSpec(
            title=a.topic,
            script=script,
            format=VideoFormat(a.mode),
            theme=a.theme,
            voice_provider="silent-preview" if a.silent else "piper" if a.piper_model else "edge-tts",
            voice=a.voice,
            voice_rate=a.voice_rate,
            piper_model=a.piper_model,
            voice_volume=max(0, a.voice_volume),
            image_provider="infographic" if a.infographic else "local-media" if a.media_dir else "local-card",
            media_dir=a.media_dir,
            music_provider="youtube-audio-library" if a.youtube_audio else "local-file" if a.music else "procedural",
            music_path=a.youtube_audio or a.music,
            music_title=a.music_title,
            music_artist=a.music_artist,
            music_attribution=a.music_attribution,
            music_source=a.music_source,
            music_volume=max(0, a.music_volume),
            captions=not a.no_captions,
        )
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
