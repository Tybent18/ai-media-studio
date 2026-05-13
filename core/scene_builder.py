import math


# -----------------------------
# SMART TEXT TRIMMER
# -----------------------------
def _smart_trim(text, max_chars):
    sentences = text.split(". ")
    result = ""

    for s in sentences:
        candidate = (result + s + ". ").strip()

        if len(candidate) > max_chars:
            break

        result = candidate

    return result.strip()


# -----------------------------
# SCORING SYSTEM
# -----------------------------
def _rank_scene(section, scene_type):
    score = 0

    if scene_type == "hook":
        score += 120
    elif scene_type == "intro":
        score += 70
    elif scene_type == "outro":
        score += 40
    else:
        score += 20

    if "important" in section:
        score += 25
    if "main" in section:
        score += 15
    if "step" in section:
        score += 10

    return score


# -----------------------------
# VISUAL INTENT ENGINE
# -----------------------------
def _generate_visual_intent(scene_type, text):

    text_lower = text.lower()

    intent = {
        "motion": "static",
        "energy": "medium",
        "shot_count": 3,
        "style": "generic"
    }

    if scene_type == "hook":
        intent.update({
            "motion": "zoom_in",
            "energy": "high",
            "shot_count": 6,
            "style": "dramatic"
        })

    elif scene_type == "intro":
        intent.update({
            "motion": "zoom_out",
            "energy": "medium",
            "shot_count": 4,
            "style": "clean"
        })

    elif scene_type == "outro":
        intent.update({
            "motion": "static",
            "energy": "low",
            "shot_count": 2,
            "style": "minimal"
        })

    # keyword boosts
    if "fast" in text_lower or "quick" in text_lower:
        intent["shot_count"] += 2
        intent["motion"] = "zoom_in"

    if "step" in text_lower:
        intent["shot_count"] += 1

    if "danger" in text_lower or "warning" in text_lower:
        intent["style"] = "intense"
        intent["motion"] = "zoom_in"

    return intent


# -----------------------------
# 🧠 VISUAL PLAN GENERATOR (FIXED)
# -----------------------------
def _build_visual_plan(text, intent):
    """
    Clean version:
    - No fake placeholders
    - Leaves paths empty so fallback works correctly
    """

    visual = {
        "paths": [],  # ✅ leave empty → downstream fallback handles it
        "motion": intent["motion"],
        "style": intent["style"]
    }

    return visual


# -----------------------------
# MAIN SCENE BUILDER
# -----------------------------
def build_scenes(parsed_data, mode="long"):
    scenes = []

    if not isinstance(parsed_data, list):
        return scenes

    if mode == "short":
        max_chars = 200
        max_scenes = 6
    else:
        max_chars = 900
        max_scenes = 25

    for block in parsed_data:
        text = block.get("text", "").strip()
        section = block.get("section", "general").lower()

        if not text:
            continue

        # -----------------------------
        # Scene classification
        # -----------------------------
        if "hook" in section:
            scene_type = "hook"
        elif "intro" in section:
            scene_type = "intro"
        elif "outro" in section:
            scene_type = "outro"
        else:
            scene_type = "point"

        trimmed = _smart_trim(text, max_chars)

        # -----------------------------
        # VISUAL INTENT
        # -----------------------------
        visual_intent = _generate_visual_intent(scene_type, trimmed)

        # -----------------------------
        # VISUAL PLAN (FIXED)
        # -----------------------------
        visual_plan = _build_visual_plan(trimmed, visual_intent)

        scenes.append({
            "text": trimmed,
            "section": section,
            "type": scene_type,
            "score": _rank_scene(section, scene_type),

            # 🔥 Renderer input
            "visual": visual_plan,

            # future logic
            "visual_intent": visual_intent
        })

    # -----------------------------
    # ORDERING LOGIC
    # -----------------------------
    scenes.sort(key=lambda x: x["score"], reverse=True)

    hooks = [s for s in scenes if s["type"] == "hook"]
    intros = [s for s in scenes if s["type"] == "intro"]
    points = [s for s in scenes if s["type"] == "point"]
    outros = [s for s in scenes if s["type"] == "outro"]

    ordered = []

    if hooks:
        ordered.append(hooks[0])

    ordered.extend(intros)
    ordered.extend(points)
    ordered.extend(outros)

    return ordered[:max_scenes]