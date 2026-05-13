import math


# -----------------------------
# TIMING NORMALIZER
# -----------------------------
def _clamp(value, min_v, max_v):
    return max(min_v, min(value, max_v))


# -----------------------------
# SPEECH-DURATION ESTIMATOR (FALLBACK SAFETY)
# -----------------------------
def estimate_speech_duration(text, wpm=155):
    """
    Rough fallback if TTS duration is unknown.
    """
    words = len(text.split())
    return (words / wpm) * 60


# -----------------------------
# SCENE TIMING ANALYZER
# -----------------------------
def analyze_scene_timing(scene, tts_duration=None, storyboard=None, story_signals=None):

    text = scene.get("text", "")
    scene_type = scene.get("type", "body")

    # -----------------------------
    # BASE DURATION
    # -----------------------------
    if tts_duration:
        duration = tts_duration
    else:
        duration = estimate_speech_duration(text)

    # -----------------------------
    # STORY-LEVEL INFLUENCE
    # -----------------------------
    if story_signals:
        pacing = story_signals.get("pacing", "medium")

        if pacing == "fast":
            duration *= 0.92
        elif pacing == "slow":
            duration *= 1.15

    # -----------------------------
    # SCENE TYPE ADJUSTMENTS
    # -----------------------------
    if scene_type == "hook":
        duration *= 0.9

    elif scene_type == "intro":
        duration *= 1.05

    elif scene_type == "outro":
        duration *= 1.2

    # -----------------------------
    # TEXT SIGNAL ADJUSTMENTS
    # -----------------------------
    t = text.lower()

    if "important" in t or "warning" in t:
        duration *= 1.1

    if "quick" in t or "fast" in t:
        duration *= 0.9

    # -----------------------------
    # CLAMPING (SAFETY)
    # -----------------------------
    if storyboard:
        if isinstance(storyboard, dict):
            mode = storyboard.get("mode", "long")
        else:
            mode = "long"

        if mode == "short":
            duration = _clamp(duration, 2.5, 6.5)
        else:
            duration = _clamp(duration, 4.0, 12.0)
    else:
        duration = _clamp(duration, 3.0, 12.0)

    return round(duration, 2)


# -----------------------------
# GLOBAL TIMELINE BUILDER
# -----------------------------
def build_video_timeline(scenes, storyboard, tts_map, story_signals=None):

    timeline = []
    current_time = 0.0

    for i, scene in enumerate(scenes):

        text = scene.get("text", "")

        # -----------------------------
        # GET TTS DURATION
        # -----------------------------
        audio_path = tts_map.get(i)
        tts_duration = None

        if audio_path:
            try:
                from moviepy.editor import AudioFileClip
                tts_duration = AudioFileClip(audio_path).duration
            except:
                tts_duration = None

        # -----------------------------
        # COMPUTE FINAL SCENE DURATION
        # -----------------------------
        duration = analyze_scene_timing(
            scene,
            tts_duration=tts_duration,
            storyboard=storyboard,
            story_signals=story_signals
        )

        # -----------------------------
        # KEYFRAME INFO (FOR RENDERER)
        # -----------------------------
        entry = {
            "scene_index": i,
            "start_time": round(current_time, 2),
            "end_time": round(current_time + duration, 2),
            "duration": duration,

            "text": text,
            "type": scene.get("type", "body"),

            "visual": scene.get("visual", {}),
            "motion": scene.get("visual_intent", {}).get("motion", "static"),

            "audio": audio_path
        }

        timeline.append(entry)
        current_time += duration

    return {
        "total_duration": round(current_time, 2),
        "timeline": timeline
    }


# -----------------------------
# TIMING VALIDATION (DEBUG TOOL)
# -----------------------------
def validate_timeline(timeline_data):

    timeline = timeline_data["timeline"]
    errors = []

    for i in range(1, len(timeline)):
        prev = timeline[i - 1]
        curr = timeline[i]

        if curr["start_time"] < prev["end_time"]:
            errors.append(f"Overlap at scene {i}")

    if not errors:
        print("✅ Timeline validated successfully")
    else:
        print("❌ Timeline issues detected:")
        for e in errors:
            print(" -", e)

    return len(errors) == 0


from beat_editor import generate_cut_points


def attach_beats_to_timeline(timeline, audio_map):

    for i, scene in enumerate(timeline["timeline"]):

        audio = scene.get("audio")

        if audio:
            scene["cut_points"] = generate_cut_points(audio)
        else:
            scene["cut_points"] = []

    return timeline