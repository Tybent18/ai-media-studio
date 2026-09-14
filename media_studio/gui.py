import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .models import ProjectSpec, VideoFormat
from .pipeline import MediaPipeline, PipelineCancelled
from .providers import PROVIDER_CATALOG, THEMES


class StudioApp(tk.Tk):
    def __init__(self, demo=False):
        super().__init__()
        self.demo = demo
        self.title("AI Media Studio V4")
        self.geometry("1240x800")
        self.minsize(980, 680)
        self.configure(bg="#080f1e")
        self.events = queue.Queue()
        self.pipeline = None
        self.result = None
        self._build()
        self.after(80, self._poll)

    def label(self, parent, text):
        tk.Label(parent, text=text, bg="#0f1b30", fg="#7dd3fc", font=("TkDefaultFont", 9, "bold")).pack(
            anchor="w", padx=16, pady=(15, 6)
        )

    def _build(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", padding=9)
        style.configure(
            "Accent.TButton", background="#38bdf8", foreground="#07111f", font=("TkDefaultFont", 10, "bold")
        )
        style.configure("TCombobox", fieldbackground="#15233a", foreground="#e2e8f0")
        header = tk.Frame(self, bg="#0f1b30", height=70)
        header.pack(fill="x")
        tk.Label(header, text="AI MEDIA STUDIO", font=("TkDefaultFont", 20, "bold"), fg="#f8fafc", bg="#0f1b30").pack(
            side="left", padx=22, pady=16
        )
        tk.Label(
            header, text="V4  •  LOCAL-FIRST PRODUCTION", fg="#38bdf8", bg="#0f1b30", font=("TkDefaultFont", 10, "bold")
        ).pack(side="left")
        body = tk.Frame(self, bg="#080f1e")
        body.pack(fill="both", expand=True, padx=18, pady=16)
        left = tk.Frame(body, bg="#0f1b30", width=340)
        left.pack(side="left", fill="y", padx=(0, 14))
        left.pack_propagate(False)
        center = tk.Frame(body, bg="#0f1b30")
        center.pack(side="left", fill="both", expand=True)
        right = tk.Frame(body, bg="#0f1b30", width=290)
        right.pack(side="left", fill="y", padx=(14, 0))
        right.pack_propagate(False)
        self.label(left, "PROJECT")
        self.title_var = tk.StringVar(value="The Future of Creative AI")
        tk.Entry(
            left, textvariable=self.title_var, bg="#091426", fg="#f8fafc", insertbackground="#38bdf8", relief="flat"
        ).pack(fill="x", padx=16, ipady=8)
        self.label(left, "FORMAT")
        self.format_var = tk.StringVar(value="long")
        row = tk.Frame(left, bg="#0f1b30")
        row.pack(fill="x", padx=16)
        ttk.Radiobutton(row, text="Long 16:9", variable=self.format_var, value="long").pack(side="left")
        ttk.Radiobutton(row, text="Short 9:16", variable=self.format_var, value="short").pack(side="left", padx=10)
        self.vars = {}
        for kind in ("image", "voice", "avatar", "music"):
            self.label(left, kind.upper())
            vals = [p.key for p in PROVIDER_CATALOG[kind]]
            self.vars[kind] = tk.StringVar(value=vals[0])
            ttk.Combobox(left, textvariable=self.vars[kind], values=vals, state="readonly").pack(fill="x", padx=16)
        self.label(left, "THEME")
        self.theme_var = tk.StringVar(value="midnight")
        theme_picker = ttk.Combobox(left, textvariable=self.theme_var, values=list(THEMES), state="readonly")
        theme_picker.pack(fill="x", padx=16)
        theme_picker.bind("<<ComboboxSelected>>", self.apply_theme)
        self.label(center, "SCRIPT / SCENE EDITOR")
        self.script = tk.Text(
            center,
            bg="#091426",
            fg="#e2e8f0",
            insertbackground="#38bdf8",
            relief="flat",
            font=("TkFixedFont", 11),
            wrap="word",
            padx=15,
            pady=15,
        )
        self.script.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.script.insert(
            "1.0",
            "Hook: What if one studio coordinated every part of a video?\n"
            "Intro: AI Media Studio turns a script into an editable production plan.\n"
            "Point: Visuals, voice, avatar, music, and rendering remain independent providers.\n"
            "Point: Long videos use sixteen by nine while shorts use a vertical canvas.\n"
            "Outro: Build locally, review every stage, and publish only when it is ready.",
        )
        bar = tk.Frame(center, bg="#0f1b30")
        bar.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Button(bar, text="Generate", style="Accent.TButton", command=self.generate).pack(side="left")
        ttk.Button(bar, text="Stop", command=self.stop).pack(side="left", padx=8)
        ttk.Button(bar, text="Open video", command=self.open_video).pack(side="left")
        ttk.Button(bar, text="Save project", command=self.save_project).pack(side="right")
        self.label(right, "PRODUCTION STATUS")
        self.status = tk.Label(
            right, text="Ready", bg="#0f1b30", fg="#f8fafc", anchor="w", justify="left", wraplength=250
        )
        self.status.pack(fill="x", padx=16)
        self.progress = ttk.Progressbar(right, maximum=100)
        self.progress.pack(fill="x", padx=16, pady=12)
        self.stages = tk.Listbox(
            right, bg="#091426", fg="#94a3b8", selectbackground="#1d4ed8", relief="flat", height=13
        )
        self.stages.pack(fill="x", padx=16)
        [self.stages.insert("end", f"○ {s.title()}") for s in MediaPipeline.STAGES]
        self.label(right, "OUTPUT")
        self.output = tk.Label(
            right, text="No render yet", bg="#0f1b30", fg="#38bdf8", anchor="w", justify="left", wraplength=250
        )
        self.output.pack(fill="x", padx=16)

    def project(self):
        return ProjectSpec(
            title=self.title_var.get().strip() or "Untitled",
            script=self.script.get("1.0", "end").strip(),
            format=VideoFormat(self.format_var.get()),
            image_provider=self.vars["image"].get(),
            voice_provider=self.vars["voice"].get(),
            music_provider=self.vars["music"].get(),
            avatar_provider=self.vars["avatar"].get(),
            theme=self.theme_var.get(),
        )

    def apply_theme(self, _event=None):
        bg, panel, accent = THEMES[self.theme_var.get()]

        def to_hex(color):
            return "#" + "".join(f"{value:02x}" for value in color)

        background, surface, highlight = map(to_hex, (bg, panel, accent))
        self.configure(bg=background)
        ttk.Style(self).configure("Accent.TButton", background=highlight)

        def recolor(widget):
            for child in widget.winfo_children():
                if isinstance(child, tk.Frame):
                    child.configure(bg=surface)
                elif isinstance(child, tk.Label):
                    child.configure(bg=surface)
                elif isinstance(child, (tk.Text, tk.Listbox)):
                    child.configure(bg=background)
                recolor(child)

        recolor(self)

    def generate(self):
        if self.pipeline:
            return
        self.pipeline = MediaPipeline(lambda m, p: self.events.put(("progress", m, p)))
        threading.Thread(target=self.worker, args=(self.project(),), daemon=True).start()

    def worker(self, p):
        try:
            self.events.put(("done", self.pipeline.run(p)))
        except PipelineCancelled:
            self.events.put(("cancelled",))
        except (OSError, ValueError, RuntimeError) as exc:
            self.events.put(("error", str(exc)))

    def stop(self):
        if self.pipeline:
            self.pipeline.cancel()
            self.status.config(text="Stopping safely…")

    def _poll(self):
        try:
            while True:
                e = self.events.get_nowait()
                kind = e[0]
                if kind == "progress":
                    self.status.config(text=e[1])
                    self.progress["value"] = e[2] * 100
                    i = min(6, int(e[2] * 7))
                    self.stages.selection_clear(0, "end")
                    self.stages.selection_set(i)
                elif kind == "done":
                    self.result = e[1]
                    self.output.config(text=self.result["video_path"])
                    self.status.config(text="Render complete")
                    self.progress["value"] = 100
                    self.pipeline = None
                elif kind == "cancelled":
                    self.status.config(text="Cancelled; partial run removed")
                    self.pipeline = None
                elif kind == "error":
                    messagebox.showerror("Render failed", e[1])
                    self.status.config(text="Render failed")
                    self.pipeline = None
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def open_video(self):
        if not self.result:
            return
        p = self.result["video_path"]
        try:
            subprocess.Popen(
                ["open", p]
                if sys.platform == "darwin"
                else ["cmd", "/c", "start", "", p]
                if os.name == "nt"
                else ["xdg-open", p]
            )
        except OSError:
            messagebox.showinfo("Video ready", p)

    def save_project(self):
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("AI Media Studio project", "*.json")])
        if p:
            Path(p).write_text(json.dumps(self.project().manifest(), indent=2), encoding="utf-8")


def launch():
    StudioApp().mainloop()
