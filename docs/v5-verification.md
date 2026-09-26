# V5 verification record

## Verified production behavior

| Capability | V5 target |
| --- | --- |
| YouTube canvas | 1920×1080 |
| Reel/Short canvas | 1080×1920 |
| Frame rate | 30 fps |
| Video/audio | H.264 video and AAC audio |
| Offline neural voice | Piper ONNX model |
| Network neural voice | Microsoft Edge TTS |
| Music | Original procedural score or user-authorized import |
| Audio control | Independent narration and music gain |
| Editing | Script plus structured scene editor |
| Monitoring | Live render frames plus finished-MP4 visual preview |
| Cancellation | Active FFmpeg termination and partial-output cleanup |

Run the verification suite with:

```bash
pip install -e ".[dev,voice]"
pytest -q
python main.py --gui
```

The automated suite validates real MP4 generation, both full-HD canvases, provider contracts, manifests, music
attribution packaging, audio-level serialization, themes, styles, and cancellation. Neural-voice quality and interface
aesthetics still require human review.
