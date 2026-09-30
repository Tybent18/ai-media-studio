"""Network-backed generative visual providers for V6."""

import base64
import hashlib
import os
from pathlib import Path

import requests
from PIL import Image


class GeneratedVisualError(RuntimeError):
    pass


def _scene_prompt(scene, project, index):
    aspect = "vertical 9:16" if project.format.value == "short" else "widescreen 16:9"
    return f"""Create one polished {aspect} frame for a professional animated educational explainer.
Series identity: Lazy Math. Scene {index + 1}.
Narration meaning: {scene.text}

ART DIRECTION:
- premium modern vector/editorial illustration with dimensional lighting and clean shapes
- energetic educational YouTube motion-infographic aesthetic; original visual identity, not a copy of any channel
- expressive recurring young adult presenter, navy/blue outfit, warm friendly face
- visually explain the concept with physical objects, diagrams, classroom/lab props, arrows, groups, number blocks, or environmental storytelling
- strong foreground/midground/background separation so camera movement feels dimensional
- bold composition, high contrast, polished studio quality, immediately readable on a phone
- vary camera angle and staging from neighboring scenes
- leave useful negative space for programmatic captions/equations
- NO logos, watermarks, paragraphs, subtitles, or decorative gibberish text
- do not rely on written words to explain the concept
The image is a production asset that will receive precise text and math overlays later."""
    

class OpenAIStoryboardProvider:
    """Generate and cache high-quality scene artwork through OpenAI's image API."""

    endpoint = "https://api.openai.com/v1/images/generations"

    def __init__(self, cache=Path("assets/v6/generated/storyboards")):
        self.cache=Path(cache).resolve()
        self.cache.mkdir(parents=True,exist_ok=True)

    def generate(self, scene, project, index, target=None):
        key=hashlib.sha256(
            f"{project.title}|{project.format.value}|{scene.text}|{index}|v6-storyboard-2".encode()
        ).hexdigest()[:20]
        cached=self.cache/f"{key}.png"
        if cached.is_file():
            return cached

        api_key=os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise GeneratedVisualError(
                "AI Storyboard requires OPENAI_API_KEY. Set it in your environment, then restart AI Media Studio."
            )
        model=os.environ.get("AI_MEDIA_IMAGE_MODEL","gpt-image-2")
        # Current Images API supports portrait image generation; normalize to the project canvas afterward.
        size="1024x1536" if project.format.value=="short" else "1536x1024"
        response=requests.post(
            self.endpoint,
            headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
            json={
                "model":model,
                "prompt":_scene_prompt(scene,project,index),
                "size":size,
                "quality":"high",
                "output_format":"png",
            },
            timeout=240,
        )
        if not response.ok:
            detail=response.text[:800]
            raise GeneratedVisualError(f"Image generation failed ({response.status_code}): {detail}")
        data=response.json()
        item=data["data"][0]
        if item.get("b64_json"):
            raw=base64.b64decode(item["b64_json"])
        elif item.get("url"):
            download=requests.get(item["url"],timeout=120)
            download.raise_for_status(); raw=download.content
        else:
            raise GeneratedVisualError("Image API returned no image payload")
        cached.write_bytes(raw)
        # Normalize exact dimensions for the video renderer.
        w,h=project.format.size
        im=Image.open(cached).convert("RGB")
        scale=max(w/im.width,h/im.height)
        im=im.resize((int(im.width*scale),int(im.height*scale)),Image.Resampling.LANCZOS)
        left=(im.width-w)//2; top=(im.height-h)//2
        im.crop((left,top,left+w,top+h)).save(cached)
        return cached
