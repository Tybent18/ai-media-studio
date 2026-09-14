# V4 baseline and verification record

## Environment

- Python 3.12.14
- FFmpeg 6.1.1
- Clean repository checkout
- Test date: 2026-09-14

## Before V4

The documented V3 installation did not produce a video in the evaluation environment.

1. `pytest -q` stopped during collection because package imports were inconsistent.
2. `python main.py --topic "A one minute test render" --mode short` stopped because `requests` was imported but absent from `requirements.txt`.
3. After installing that missing dependency manually, startup stopped again because the renderer imported the removed `moviepy.editor` interface while the unconstrained dependency installed MoviePy 2.x.

Measured baseline:

| Measure | V3 result |
| --- | --- |
| Tests executed | 0 |
| Test collection | Failed |
| Documented render completed | No |
| MP4 produced | No |

## After V4

V4 uses typed project contracts and direct FFmpeg execution. Its local providers generate deterministic storyboard cards, timed audio, an illustrated host overlay, and an original procedural score.

| Measure | V4 result |
| --- | --- |
| Tests executed | 8 |
| Tests passed | 8 |
| Long-form canvas | 1280×720 verified by FFprobe |
| Short-form canvas | 720×1280 verified by FFprobe |
| Audio stream | Present |
| Video stream | Present |
| Active cancellation | Tested with partial-output cleanup |
| Provider substitution | Uninstalled adapters fail explicitly instead of being silently faked |

The tests generate real MP4 files. They do not evaluate aesthetic quality, cloud-provider quality, upload behavior, or user analytics.

## Reproduce

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python main.py --topic "Render proof" --mode short --theme violet
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height -of json output/short/*/*.mp4
```
