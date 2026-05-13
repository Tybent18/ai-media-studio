import hashlib


# -----------------------------
# EMOTION MAPPER
# -----------------------------
def _emotion(scene):
    text = scene.get("text", "").lower()
    scene_type = scene.get("type", "body")

    if scene_type == "hook":
        return "excited"

    if "warning" in text or "danger" in text:
        return "serious"

    if "sad" in text:
        return "sad"

    if scene_type == "outro":
        return "calm"

    return "neutral"


# -----------------------------
# GESTURE ENGINE
# -----------------------------
def _gesture(emotion):
    return {
        "excited": "hand_wave",
        "serious": "point",
        "sad": "low_head",
        "calm": "idle",
        "neutral": "idle"
    }.get(emotion, "idle")


# -----------------------------
# AVATAR RIG BUILDER
# -----------------------------
def build_avatar_rig(scene, audio_path):

    emotion = _emotion(scene)
    gesture = _gesture(emotion)

    return {
        "text": scene.get("text", ""),
        "audio": audio_path,

        # 🎭 performance layer
        "emotion": emotion,
        "gesture": gesture,

        "blink_rate": "normal",
        "head_movement": "subtle",
        "lip_sync": True
    }


# -----------------------------
# AVATAR CLIP GENERATOR (HOOK)
# -----------------------------
def generate_avatar_clip(rig, engine="heygen"):
    """
    Placeholder for real integration:
    - HeyGen
    - D-ID
    - Live2D / VTuber systems
    """

    h = hashlib.md5(rig["text"].encode()).hexdigest()[:10]

    path = f"assets/avatars/{h}.mp4"

    # placeholder output (replace with API later)
    with open(path, "w") as f:
        f.write("avatar_video_placeholder")

    return path