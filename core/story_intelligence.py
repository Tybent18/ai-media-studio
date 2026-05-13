import re


# -----------------------------
# STORY INTELLIGENCE ENGINE v3
# -----------------------------
def analyze_script(text):

    t = text.lower()

    signals = {
        "has_hook": False,
        "has_question": "?" in text,
        "energy": "medium",
        "topic": "general",
        "structure": "linear",
        "emotional_tone": "neutral",

        # 🔥 NEW DIRECTOR SIGNALS
        "pacing": "medium",
        "visual_style": "generic",
        "motion_bias": "balanced",
        "scene_density": "medium"
    }

    # -----------------------------
    # HOOK DETECTION
    # -----------------------------
    hook_patterns = [
        "imagine",
        "what if",
        "you won't believe",
        "here's the truth",
        "nobody tells you",
        "this is why"
    ]

    signals["has_hook"] = any(p in t for p in hook_patterns)

    # -----------------------------
    # ENERGY MODEL
    # -----------------------------
    word_count = len(text.split())

    if word_count < 300:
        signals["energy"] = "high"
        signals["pacing"] = "fast"
        signals["scene_density"] = "high"

    elif word_count < 1200:
        signals["energy"] = "medium"
        signals["pacing"] = "medium"

    else:
        signals["energy"] = "low"
        signals["pacing"] = "slow"
        signals["scene_density"] = "low"

    # -----------------------------
    # TOPIC CLASSIFIER
    # -----------------------------
    if any(w in t for w in ["ai", "model", "algorithm", "data"]):
        signals["topic"] = "technology"
        signals["visual_style"] = "futuristic"

    elif any(w in t for w in ["money", "business", "startup", "profit"]):
        signals["topic"] = "finance"
        signals["visual_style"] = "clean"

    elif any(w in t for w in ["fitness", "body", "health"]):
        signals["topic"] = "health"
        signals["visual_style"] = "energetic"

    # -----------------------------
    # STRUCTURE
    # -----------------------------
    if signals["has_hook"] and signals["has_question"]:
        signals["structure"] = "viral"
        signals["motion_bias"] = "dynamic"

    elif signals["has_hook"]:
        signals["structure"] = "engaging"

    # -----------------------------
    # EMOTION MODEL
    # -----------------------------
    if any(w in t for w in ["shock", "crazy", "insane", "exposed"]):
        signals["emotional_tone"] = "high_energy"
        signals["motion_bias"] = "aggressive"

    elif any(w in t for w in ["sad", "problem", "issue", "danger"]):
        signals["emotional_tone"] = "serious"
        signals["visual_style"] = "dark"

    return signals