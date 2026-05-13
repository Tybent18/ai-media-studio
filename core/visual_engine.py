import os
import random
import textwrap
import uuid
import requests


# -----------------------------
# B-ROLL KNOWLEDGE BASE
# -----------------------------
BROLL_MAP = {
    "technology": [
        "futuristic ai interface",
        "data center servers",
        "neural network visualization"
    ],
    "finance": [
        "stock market chart",
        "business skyline",
        "trading screens"
    ],
    "storytelling": [
        "cinematic sunset",
        "person walking alone",
        "dramatic portrait"
    ],
    "general": [
        "abstract background",
        "minimal studio backdrop"
    ]
}


# -----------------------------
# LOCAL B-ROLL ASSETS
# -----------------------------
BROLL_ASSETS = {
    "technology": [
        "assets/broll/ai_1.jpg",
        "assets/broll/ai_2.jpg"
    ],
    "finance": [
        "assets/broll/money_1.jpg",
        "assets/broll/money_2.jpg"
    ],
    "storytelling": [
        "assets/broll/story_1.jpg",
        "assets/broll/story_2.jpg"
    ],
    "general": [
        "assets/broll/general_1.jpg"
    ]
}


# -----------------------------
# TEXT WRAPPER
# -----------------------------
def _wrap(text, width):
    return "\n".join(textwrap.wrap(text, width))


# -----------------------------
# PROMPT GENERATOR (AI IMAGES)
# -----------------------------
def build_image_prompt(scene):
    text = scene.get("text", "")
    intent = scene.get("visual_intent", {})
    style = intent.get("style", "cinematic")

    prompt = f"{text}, {style}, cinematic lighting, highly detailed, 4k"

    if style == "futuristic":
        prompt += ", sci-fi, neon glow, advanced tech"

    elif style == "dark":
        prompt += ", moody lighting, shadows, intense"

    elif style == "clean":
        prompt += ", minimal, professional, soft light"

    return prompt


# -----------------------------
# IMAGE GENERATOR (API) — SAFE VERSION
# -----------------------------
def generate_image(prompt, output_dir="images"):
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{uuid.uuid4()}.png"
    path = os.path.join(output_dir, filename)

    API_KEY = "YOUR_API_KEY"  # optional — can leave as-is for demo

    try:
        response = requests.post(
            "https://api.stability.ai/v2beta/stable-image/generate/core",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Accept": "image/*"  # ✅ FIXED
            },
            files={"none": ''},
            data={"prompt": prompt}
        )

        if response.status_code == 200:
            with open(path, "wb") as f:
                f.write(response.content)
            return path
        else:
            print("❌ Image API error:", response.text)

    except Exception as e:
        print("❌ Image generation failed:", e)

    return None


# -----------------------------
# B-ROLL SELECTOR
# -----------------------------
def _select_broll(topic, text):
    candidates = BROLL_MAP.get(topic, BROLL_MAP["general"])
    text_lower = text.lower()

    if "ai" in text_lower:
        return "futuristic ai interface"

    if "money" in text_lower:
        return "stock market chart"

    return random.choice(candidates)


# -----------------------------
# B-ROLL RESOLVER
# -----------------------------
def _resolve_broll_asset(topic):
    assets = BROLL_ASSETS.get(topic, BROLL_ASSETS["general"])
    valid = [a for a in assets if os.path.exists(a)]

    if not valid:
        return "assets/default.jpg"

    return random.choice(valid)


# -----------------------------
# GENERATE SCENE IMAGES (DEMO MODE SAFE)
# -----------------------------
def generate_scene_images(scene):
    visual = scene.get("visual", {})
    intent = scene.get("visual_intent", {})

    shot_count = intent.get("shot_count", 3)

    paths = []

    # 🔥 DEMO MODE: disable API, force fallback
    # (comment this out later when you fix API key)
    visual["paths"] = []
    scene["visual"] = visual
    return scene


# -----------------------------
# BATCH GENERATION
# -----------------------------
def generate_all_scene_images(scenes):
    updated = []

    for i, scene in enumerate(scenes):
        print(f"🎨 Generating visuals for scene {i}")

        try:
            scene = generate_scene_images(scene)
        except Exception as e:
            print(f"❌ Scene {i} failed: {e}")

        updated.append(scene)

    return updated


# -----------------------------
# MAIN VISUAL RESOLVER (RENDERER INPUT)
# -----------------------------
def get_visual(scene, index, mode="long", story_signals=None):

    text = scene.get("text", "")
    intent = scene.get("visual_intent", {})
    visual_plan = scene.get("visual", {})

    topic = "general"
    visual_style = intent.get("style", "neutral")

    if story_signals:
        topic = story_signals.get("topic", topic)
        visual_style = story_signals.get("visual_style", visual_style)

    image_paths = visual_plan.get("paths", [])

    valid_generated = [
        p for p in image_paths
        if isinstance(p, str) and os.path.exists(p)
    ]

    # -----------------------------
    # FALLBACK (THIS WILL NOW ALWAYS WORK)
    # -----------------------------
    if not valid_generated:
        fallback = _resolve_broll_asset(topic)
        image_paths = [fallback]
        print(f"⚠️ Scene {index}: using B-roll fallback")

    else:
        image_paths = valid_generated

    # -----------------------------
    # TEXT OVERLAY
    # -----------------------------
    if mode == "short":
        wrapped = _wrap(text[:200], 30)
    else:
        wrapped = _wrap(text[:400], 50)

    motion = intent.get("motion", "static")

    return {
        "paths": image_paths,
        "motion": motion,
        "style": visual_style,
        "overlay_text": True,
        "text": wrapped,
        "broll_query": _select_broll(topic, text),
        "effects": [],
        "transition": "cut"
    }