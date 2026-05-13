def build_storyboard(parsed_blocks, story_signals, mode="long"):
    """
    Converts parsed script into a cinematic storyboard
    (director-level structure, not slideshow timing)
    """

    storyboard = []

    topic = story_signals.get("topic", "general")
    energy = story_signals.get("energy", "medium")
    pacing = story_signals.get("pacing", "medium")
    visual_style = story_signals.get("visual_style", "neutral")

    for i, block in enumerate(parsed_blocks):

        text = block.get("text", "")
        section = block.get("section", "general")

        # -----------------------------
        # SCENE TYPE CLASSIFICATION
        # -----------------------------
        if "hook" in section or i == 0:
            scene_type = "hook"
        elif "intro" in section:
            scene_type = "intro"
        elif "outro" in section or i == len(parsed_blocks) - 1:
            scene_type = "outro"
        else:
            scene_type = "body"

        # -----------------------------
        # 🧠 DURATION SYSTEM (ENERGY-AWARE)
        # -----------------------------
        word_count = len(text.split())

        if mode == "short":
            base = 3.0
            max_dur = 6.0
        else:
            base = 5.5
            max_dur = 12.0

        duration = base + (word_count * 0.025)

        # pacing influence from story intelligence
        if pacing == "fast":
            duration *= 0.85
        elif pacing == "slow":
            duration *= 1.25

        # clamp
        duration = min(duration, max_dur)

        # -----------------------------
        # 🧠 VISUAL STRATEGY (REPLACES visual_hint)
        # -----------------------------
        visual_strategy = {
            "topic": topic,
            "style": visual_style,
            "scene_type": scene_type,
            "energy": energy,

            # NEW DIRECTOR SIGNALS
            "shot_density": "medium",
            "motion_profile": "balanced"
        }

        # hook = aggressive pacing
        if scene_type == "hook":
            visual_strategy["shot_density"] = "high"
            visual_strategy["motion_profile"] = "dynamic"

        # body adjusts by topic
        if topic == "technology":
            visual_strategy["style"] = "futuristic"
        elif topic == "finance":
            visual_strategy["style"] = "clean"
        elif topic == "health":
            visual_strategy["style"] = "energetic"

        # energy overrides
        if energy == "high":
            visual_strategy["motion_profile"] = "aggressive"
        elif energy == "low":
            visual_strategy["motion_profile"] = "calm"

        # -----------------------------
        # CUT LOGIC (IMPORTANT FOR RENDERER)
        # -----------------------------
        if duration < 4:
            transition = "cut"
        else:
            transition = "smooth"

        # -----------------------------
        # FINAL STORYBOARD NODE
        # -----------------------------
        storyboard.append({
            "text": text,
            "type": scene_type,
            "duration": round(duration, 2),

            # 🔥 THIS IS THE KEY UPGRADE
            "visual_strategy": visual_strategy,

            # renderer hook
            "transition": transition,

            # future compatibility
            "metadata": {
                "word_count": word_count,
                "index": i
            }
        })

    return storyboard