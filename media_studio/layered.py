"""Layered V6 educational scene planning and asset rendering."""

import json
import math
import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .providers import THEMES, _font


def _equation(text):
    # Accept both digits and the small number vocabulary used by educational scripts.
    words = {"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,
             "ten":10,"eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15}
    low=text.lower()
    m=re.search(r"\b(\d+)\s*(?:\+|plus)\s*(\d+)\b",low)
    if m:
        return int(m.group(1)),int(m.group(2))
    m=re.search(r"\b("+"|".join(words)+r")\s+plus\s+("+"|".join(words)+r")\b",low)
    return (words[m.group(1)],words[m.group(2)]) if m else None


class AssetLibrary:
    """Persistent, reusable transparent assets. Generated once, then cached."""

    def __init__(self, root=Path("assets/v6")):
        self.root=Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)

    def _save(self,name,build,size=(420,420)):
        p=self.root/f"{name}.png"
        if p.is_file():
            return p
        im=Image.new("RGBA",size,(0,0,0,0)); d=ImageDraw.Draw(im)
        build(d,size[0],size[1])
        im.save(p)
        return p

    def host(self,pose="neutral"):
        def build(d,w,h):
            accent=(56,189,248); skin=(238,205,180); hair=(30,41,59)
            d.ellipse((85,35,335,285),fill=skin,outline=accent,width=8)
            d.polygon([(95,120),(125,15),(190,65),(260,15),(325,125)],fill=hair)
            d.ellipse((140,140,170,172),fill=(15,23,42)); d.ellipse((245,140,275,172),fill=(15,23,42))
            if pose=="shocked": d.ellipse((175,205,245,260),fill=(120,53,80))
            else: d.arc((155,180,265,255),10,170,fill=(120,53,80),width=8)
            d.rounded_rectangle((80,275,340,415),45,fill=(20,82,145),outline=accent,width=8)
            if pose=="point":
                d.line((95,315,15,210),fill=skin,width=34); d.ellipse((0,185,35,220),fill=skin)
            elif pose=="thinking":
                d.line((315,315,370,225),fill=skin,width=30); d.ellipse((350,195,390,235),fill=skin)
        return self._save(f"host-{pose}",build)

    def sign(self,label,color):
        safe=re.sub(r"[^a-z0-9]+","-",label.lower()).strip("-")
        def build(d,w,h):
            d.rounded_rectangle((12,90,w-12,h-90),36,fill=color+(235,),outline=(255,255,255,210),width=7)
            f=_font(52,True); d.text((w//2,h//2),label,anchor="mm",font=f,fill="white")
        return self._save(f"sign-{safe}",build,(480,260))


def plan_scene(scene,index,project,assets):
    w,h=project.format.size
    text=scene.text; low=text.lower(); eq=_equation(text)
    layers=[
        {"type":"background","name":"board","z":0,"anim":"static"},
        {"type":"text","name":"brand","text":"LAZY MATH","x":.07,"y":.07,"z":3,"anim":"slide-down","size":.045},
    ]
    dangerous="danger" in low or ("ten" in low and ("higher" in low or "above" in low))
    safe="safe" in low and not dangerous
    pose="shocked" if dangerous else "thinking" if "?" in text or scene.kind=="hook" else "point"
    layers.append({"type":"image","name":"host","path":str(assets.host(pose)),"x":.67,"y":.60,"w":.30,"z":8,"anim":"slide-left"})
    if eq:
        a,b=eq; total=a+b
        layers += [
            {"type":"text","name":"lhs-a","text":str(a),"x":.13,"y":.27,"z":5,"anim":"pop","size":.13},
            {"type":"text","name":"plus","text":"+","x":.35,"y":.27,"z":5,"anim":"pop-delay","size":.11},
            {"type":"text","name":"lhs-b","text":str(b),"x":.52,"y":.27,"z":5,"anim":"pop-delay2","size":.13},
        ]
        if any(x in low for x in ("equals","makes","thirteen","seven","cross")):
            color=(239,68,68) if total>=10 else (34,197,94)
            layers += [
                {"type":"text","name":"answer","text":str(total),"x":.29,"y":.47,"z":6,"anim":"slam","size":.18,"color":color},
                {"type":"image","name":"result-sign","path":str(assets.sign("DANGEROUS" if total>=10 else "SAFE",color)),
                 "x":.20,"y":.68,"w":.42,"z":7,"anim":"slam-delay"},
            ]
    elif ("zero" in low and "nine" in low) or ("0" in low and "9" in low):
        layers.append({"type":"numberline","name":"safe-line","start":0,"end":9,"x":.08,"y":.42,"w":.78,"z":4,"anim":"wipe","color":(34,197,94)})
        layers.append({"type":"image","name":"safe-sign","path":str(assets.sign("SAFE",(34,197,94))),"x":.20,"y":.62,"w":.42,"z":6,"anim":"pop"})
    elif ("ten" in low or "10" in low) and ("higher" in low or "above" in low or dangerous):
        layers.append({"type":"numberline","name":"danger-line","start":10,"end":15,"x":.08,"y":.42,"w":.78,"z":4,"anim":"wipe","color":(239,68,68)})
        layers.append({"type":"image","name":"danger-sign","path":str(assets.sign("DANGEROUS",(239,68,68))),"x":.18,"y":.62,"w":.46,"z":6,"anim":"slam"})
    else:
        layers.append({"type":"text","name":"headline","text":"PREDICT FIRST" if scene.kind=="hook" else scene.title,
                       "x":.08,"y":.28,"z":5,"anim":"slam","size":.075})
    return {"version":1,"scene":index,"duration":scene.duration,"layers":layers}


def write_plan(scene,index,project,target,assets=None):
    assets=assets or AssetLibrary()
    target=Path(target).resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(plan_scene(scene,index,project,assets),indent=2),encoding="utf-8")
    return target


def render_frame(plan_path,target,project):
    """Render a representative frame for GUI preview/fallback. Video renderer animates the same layers."""
    plan_path=Path(plan_path).resolve()
    target=Path(target).resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    plan=json.loads(plan_path.read_text(encoding="utf-8"))
    w,h=project.format.size; bg,panel,accent=THEMES.get(project.theme,THEMES["midnight"])
    im=Image.new("RGBA",(w,h),bg+(255,)); d=ImageDraw.Draw(im)
    d.rounded_rectangle((int(w*.035),int(h*.035),int(w*.965),int(h*.965)),radius=max(30,w//28),fill=panel+(255,),outline=accent+(255,),width=max(4,w//220))
    for L in sorted(plan["layers"],key=lambda x:x["z"]):
        if L["type"]=="background": continue
        if L["type"]=="image":
            a=Image.open(L["path"]).convert("RGBA"); tw=int(w*L["w"]); a.thumbnail((tw,int(h*.5)))
            im.alpha_composite(a,(int(w*L["x"]),int(h*L["y"])))
        elif L["type"]=="text":
            size=max(26,int(w*L["size"])); color=tuple(L.get("color",(241,245,249)))
            d.text((int(w*L["x"]),int(h*L["y"])),L["text"],font=_font(size,True),fill=color)
        elif L["type"]=="numberline":
            x=int(w*L["x"]); y=int(h*L["y"]); ww=int(w*L["w"]); color=tuple(L["color"])
            d.line((x,y,x+ww,y),fill=color,width=max(8,w//100))
            count=L["end"]-L["start"]
            for n in range(count+1):
                xx=x+int(ww*n/max(1,count)); d.ellipse((xx-10,y-10,xx+10,y+10),fill=color)
                d.text((xx,y+28),str(L["start"]+n),anchor="ma",font=_font(max(18,w//50),True),fill="white")
    im.convert("RGB").save(target); return target


def render_animation(plan_path, target, project, duration, fps=30):
    """Render independently animated composition layers to a silent MP4.

    Pillow performs the per-frame compositing so every object has its own
    entrance timing and motion. FFmpeg then encodes the resulting frame stream.
    """
    import subprocess
    plan_path=Path(plan_path).resolve()
    target=Path(target).resolve()
    plan=json.loads(plan_path.read_text(encoding="utf-8"))
    w,h=project.format.size; bg,panel,accent=THEMES.get(project.theme,THEMES["midnight"])
    frames=max(1,int(duration*fps))
    target.parent.mkdir(parents=True,exist_ok=True)
    cmd=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{w}x{h}","-r",str(fps),"-i","-",
         "-an","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",str(target)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for fi in range(frames):
            t=fi/fps
            im=Image.new("RGBA",(w,h),bg+(255,)); d=ImageDraw.Draw(im)
            d.rounded_rectangle((int(w*.035),int(h*.035),int(w*.965),int(h*.965)),radius=max(30,w//28),
                                fill=panel+(255,),outline=accent+(255,),width=max(4,w//220))
            for order,L in enumerate(sorted(plan["layers"],key=lambda x:x["z"])):
                if L["type"]=="background": continue
                delay=min(duration*.48, order*.12)
                q=max(0.0,min(1.0,(t-delay)/.38))
                # cubic ease-out
                e=1-(1-q)**3
                if q<=0: continue
                x=float(L.get("x",0)); y=float(L.get("y",0)); anim=L.get("anim","static")
                scale=1.0
                if anim in {"pop","pop-delay","pop-delay2"}: scale=.55+.45*e
                elif anim in {"slam","slam-delay"}: scale=1.35-.35*e; y-=.08*(1-e)
                elif anim=="slide-left": x+=.24*(1-e)
                elif anim=="slide-down": y-=.12*(1-e)
                if L["type"]=="image":
                    a=Image.open(L["path"]).convert("RGBA")
                    tw=max(1,int(w*L["w"]*scale)); a.thumbnail((tw,int(h*.55*scale)))
                    if scale<1:
                        a=a.resize((max(1,int(a.width*scale)),max(1,int(a.height*scale))),Image.Resampling.LANCZOS)
                    im.alpha_composite(a,(int(w*x),int(h*y)))
                elif L["type"]=="text":
                    size=max(26,int(w*L["size"]*scale)); color=tuple(L.get("color",(241,245,249)))
                    d.text((int(w*x),int(h*y)),L["text"],font=_font(size,True),fill=color)
                elif L["type"]=="numberline":
                    xx=int(w*x); yy=int(h*y); full=int(w*L["w"]); ww=int(full*e); color=tuple(L["color"])
                    d.line((xx,yy,xx+ww,yy),fill=color,width=max(8,w//100))
                    count=L["end"]-L["start"]
                    for n in range(count+1):
                        nx=xx+int(full*n/max(1,count))
                        if nx<=xx+ww:
                            d.ellipse((nx-10,yy-10,nx+10,yy+10),fill=color)
                            d.text((nx,yy+28),str(L["start"]+n),anchor="ma",font=_font(max(18,w//50),True),fill="white")
            proc.stdin.write(im.convert("RGB").tobytes())
    finally:
        if proc.stdin: proc.stdin.close()
        rc=proc.wait()
    if rc: raise RuntimeError("Layered animation encoder failed")
    return target
