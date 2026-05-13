import json
import os


CHAR_PATH = "memory/character.json"


# -----------------------------
# DEFAULT CHARACTER
# -----------------------------
DEFAULT_CHARACTER = {
    "name": "AI Host",
    "voice": "en-US-AriaNeural",
    "tone": "confident",
    "style": "cinematic presenter",
    "emotion_bias": "neutral"
}


# -----------------------------
# LOAD CHARACTER
# -----------------------------
def load_character():

    if not os.path.exists(CHAR_PATH):
        os.makedirs("memory", exist_ok=True)

        with open(CHAR_PATH, "w") as f:
            json.dump(DEFAULT_CHARACTER, f, indent=2)

        return DEFAULT_CHARACTER

    with open(CHAR_PATH, "r") as f:
        return json.load(f)


# -----------------------------
# UPDATE CHARACTER (optional evolution)
# -----------------------------
def update_character(updates: dict):

    char = load_character()
    char.update(updates)

    with open(CHAR_PATH, "w") as f:
        json.dump(char, f, indent=2)

    return char