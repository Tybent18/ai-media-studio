import random


# -----------------------------
# TITLE GENERATOR
# -----------------------------
def generate_title(topic, hook_text):

    templates = [
        f"This Will Change How You Think About {topic}",
        f"The Truth About {topic} Nobody Talks About",
        f"Why Everyone Is Wrong About {topic}",
        f"{topic} Explained in 5 Minutes"
    ]

    return random.choice(templates)


# -----------------------------
# DESCRIPTION BUILDER
# -----------------------------
def generate_description(topic):

    return f"""
In this video, we explore {topic} in a cinematic AI-generated breakdown.

🔹 AI visuals
🔹 Voice narration
🔹 Automated storytelling system

Generated using an AI video pipeline.
"""


# -----------------------------
# THUMBNAIL PROMPT
# -----------------------------
def generate_thumbnail_prompt(topic):

    return f"""
cinematic youtube thumbnail about {topic},
dramatic lighting, bold text space,
high contrast, ultra detailed, eye catching
"""