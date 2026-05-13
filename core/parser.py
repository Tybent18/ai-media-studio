import re


# -----------------------------
# Utility: text chunking
# -----------------------------
def _chunk_text(text, max_words):
    words = text.split()

    if len(words) <= max_words:
        return [text]

    return [
        " ".join(words[i:i + max_words])
        for i in range(0, len(words), max_words)
    ]


# -----------------------------
# Cleanup
# -----------------------------
def _clean_text(text):
    text = re.sub(r"\s+", " ", text)
    text = text.replace("—", "-")
    return text.strip()


# -----------------------------
# Parser → Scene IR Builder
# -----------------------------
def parse_script(file_path, mode="long"):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    text = text.replace("\r\n", "\n").strip()
    lines = text.split("\n")

    blocks = []
    buffer = []
    current_section = "general"

    max_words = 35 if mode == "short" else 120

    def flush_buffer():
        nonlocal buffer, current_section, blocks

        if not buffer:
            return

        full_text = _clean_text(" ".join(buffer))
        chunks = _chunk_text(full_text, max_words)

        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue

            section_lower = current_section.lower()

            # -----------------------------
            # 🔥 DIRECT SCENE FORMAT (NEW)
            # -----------------------------
            scene_type = "point"

            if "hook" in section_lower:
                scene_type = "hook"
            elif "intro" in section_lower:
                scene_type = "intro"
            elif "outro" in section_lower:
                scene_type = "outro"

            blocks.append({
                "text": chunk,
                "section": section_lower,
                "type": scene_type,

                # pipeline-safe placeholders
                "audio": None,
                "visual": None,

                "meta": {
                    "word_count": len(chunk.split()),
                    "mode": mode
                }
            })

        buffer = []

    for line in lines:
        line = line.strip()

        section_match = re.match(r"(section\s*\d+[:\-]?\s*)(.*)", line, re.IGNORECASE)
        bracket_match = re.match(r"\[(.*?)\]", line)

        if section_match:
            flush_buffer()
            current_section = section_match.group(2) or "section"
            continue

        elif bracket_match:
            flush_buffer()
            current_section = bracket_match.group(1).lower()
            continue

        elif line == "":
            flush_buffer()

        else:
            buffer.append(line)

    flush_buffer()

    return blocks