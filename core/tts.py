import edge_tts
import asyncio
import os
import hashlib
import time

from moviepy.editor import AudioFileClip

VOICE = "en-US-AriaNeural"


# -----------------------------
# TEXT SAFETY
# -----------------------------
def _safe_text(text, max_chars=1200):

    text = text.strip()

    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0]

    return text


# -----------------------------
# STYLE ENGINE
# -----------------------------
def get_voice_style(scene, story_signals=None):

    scene_type = scene.get("type", "body")
    text = scene.get("text", "")

    style = {
        "rate": "+0%",
        "pitch": "+0Hz"
    }

    if isinstance(story_signals, dict):

        if story_signals.get("energy") == "high":
            style["pitch"] = "+6Hz"

        elif story_signals.get("energy") == "low":
            style["pitch"] = "-6Hz"

        if story_signals.get("pacing") == "fast":
            style["rate"] = "+18%"

        elif story_signals.get("pacing") == "slow":
            style["rate"] = "-10%"

    if scene_type == "hook":
        style.update({
            "rate": "+20%",
            "pitch": "+8Hz"
        })

    elif scene_type == "intro":
        style.update({
            "rate": "+8%",
            "pitch": "+2Hz"
        })

    elif scene_type == "outro":
        style.update({
            "rate": "-8%",
            "pitch": "-6Hz"
        })

    t = text.lower()

    if "fast" in t or "quick" in t:
        style["rate"] = "+22%"

    if "important" in t or "warning" in t:
        style["pitch"] = "+10Hz"

    return style


# -----------------------------
# HASH CACHE
# -----------------------------
def _hash_text(text, style):

    return hashlib.md5(
        (text + str(style)).encode()
    ).hexdigest()


# -----------------------------
# ASYNC GENERATION
# -----------------------------
async def _generate_tts_async(text, path, style):

    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=style["rate"],
        pitch=style["pitch"]
    )

    await communicate.save(path)


# -----------------------------
# SAFE ASYNC RUNNER
# -----------------------------
def _run_async(coro):

    try:
        return asyncio.run(coro)

    except RuntimeError:

        loop = asyncio.get_event_loop()

        return loop.run_until_complete(coro)


# -----------------------------
# FILE WAIT
# -----------------------------
def _wait_for_file(path, timeout=10):

    start = time.time()

    while time.time() - start < timeout:

        if os.path.exists(path):

            if os.path.getsize(path) > 5000:
                return True

        time.sleep(0.1)

    return False


# -----------------------------
# AUDIO VALIDATION
# -----------------------------
def _validate_audio(path):

    try:

        audio = AudioFileClip(path)

        duration = audio.duration

        audio.close()

        if duration is None:
            return False

        if duration <= 0.2:
            return False

        return True

    except Exception as e:

        print(f"[TTS] Validation failed: {e}")
        return False


# -----------------------------
# PUBLIC API
# -----------------------------
def generate_voice(scene, index, story_signals=None):

    os.makedirs("assets/audio", exist_ok=True)

    if not isinstance(story_signals, dict):
        story_signals = None

    text = scene.get("text", "")

    if not text:
        raise ValueError(
            f"TTS error: empty text in scene {index}"
        )

    text = _safe_text(text)

    style = get_voice_style(
        scene,
        story_signals
    )

    cache_key = _hash_text(text, style)

    # IMPORTANT:
    # edge_tts outputs MP3
    path = f"assets/audio/{cache_key}.mp3"

    # -----------------------------
    # CACHE
    # -----------------------------
    if os.path.exists(path):

        if _validate_audio(path):

            print(f"[TTS] Using cached: {path}")
            return path

    print(f"[TTS] Generating scene {index}...")

    # -----------------------------
    # GENERATE
    # -----------------------------
    for attempt in range(3):

        try:

            _run_async(
                _generate_tts_async(
                    text,
                    path,
                    style
                )
            )

            if _wait_for_file(path):

                if _validate_audio(path):

                    print(f"[TTS] Success: {path}")
                    return path

            print(f"⚠️ Retry {attempt+1}/3")

        except Exception as e:

            print(f"⚠️ TTS attempt failed: {e}")

    raise RuntimeError(
        f"TTS failed for scene {index}"
    )