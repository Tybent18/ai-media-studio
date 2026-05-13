from beat_editor import generate_cut_points


# -----------------------------
# MASTER SYNCHRONIZER
# -----------------------------
def build_master_timeline(scenes, storyboard, story_signals):

    timeline = []
    current_time = 0.0

    for i, scene in enumerate(scenes):

        text = scene.get("text", "")
        audio = scene.get("audio")
        visual = scene.get("visual", {})
        avatar = scene.get("avatar")

        duration = scene.get("duration", 5.0)

        # -----------------------------
        # CUT INTELLIGENCE (BEAT + STORY)
        # -----------------------------
        cut_points = []

        if audio:
            try:
                cut_points = generate_cut_points(audio)
            except:
                cut_points = []

        # -----------------------------
        # FINAL TIMING NODE
        # -----------------------------
        node = {
            "index": i,
            "start": round(current_time, 2),
            "end": round(current_time + duration, 2),

            "duration": duration,
            "text": text,

            "visual": visual,
            "audio": audio,
            "avatar": avatar,

            "cut_points": cut_points
        }

        timeline.append(node)

        current_time += duration

    return {
        "total_duration": current_time,
        "timeline": timeline
    }