import os


# =========================================================
# 🎬 CORE PIPELINE SETTINGS
# =========================================================

PROJECT_NAME = "AI_VIDEO_ENGINE"

MODE_DEFAULT = "long"   # long | short

FPS = 24

VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"


# =========================================================
# 📁 DIRECTORY STRUCTURE
# =========================================================

BASE_DIR = os.getcwd()

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")
BROLL_DIR = os.path.join(ASSETS_DIR, "broll")
AVATAR_DIR = os.path.join(ASSETS_DIR, "avatars")

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MEMORY_DIR = os.path.join(BASE_DIR, "memory")

IMAGE_DIR = os.path.join(BASE_DIR, "images")


# =========================================================
# 🎙️ TTS SETTINGS
# =========================================================

TTS_VOICE = "en-US-AriaNeural"

TTS_MAX_CHARS = 1200

TTS_RATE_DEFAULT = "+0%"

TTS_PITCH_DEFAULT = "+0Hz"


# =========================================================
# 🧠 STORY ENGINE SETTINGS
# =========================================================

MAX_SCENES_LONG = 25
MAX_SCENES_SHORT = 6

MAX_CHARS_LONG = 900
MAX_CHARS_SHORT = 200


# =========================================================
# 🎥 VISUAL ENGINE SETTINGS
# =========================================================

DEFAULT_MOTION = "static"

MOTION_INTENSITY_MAP = {
    "high": "zoom_in",
    "medium": "static",
    "low": "zoom_out"
}


# =========================================================
# 🧪 SYSTEM FLAGS
# =========================================================

AUTO_HEAL = True
STRICT_MODE = True   # fail fast if pipeline breaks

ENABLE_AVATAR = True
ENABLE_MUSIC_SYNC = True


# =========================================================
# 📊 QUALITY SETTINGS
# =========================================================

TARGET_BITRATE = "8000k"

ENABLE_DEBUG_TIMELINE = False