import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageTk

from .models import ProjectSpec, Scene, VideoFormat
from .pipeline import MediaPipeline, PipelineCancelled
from .providers import PROVIDER_CATALOG

UI_STYLES = {
    "Obsidian Neon": {
        "bg": "#050912",
        "panel": "#0d1728",
        "field": "#07101f",
        "accent": "#38bdf8",
        "text": "#f8fafc",
        "muted": "#8da2bd",
    },
    "Violet Cinema": {
        "bg": "#10091d",
        "panel": "#201238",
        "field": "#160d28",
        "accent": "#c084fc",
        "text": "#faf5ff",
        "muted": "#b9a4cc",
    },
    "Ember Studio": {
        "bg": "#180b0b",
        "panel": "#301515",
        "field": "#210d0d",
        "accent": "#fb923c",
        "text": "#fff7ed",
        "muted": "#d6a98d",
    },
    "Arctic Light": {
        "bg": "#dbeafe",
        "panel": "#eff6ff",
        "field": "#ffffff",
        "accent": "#2563eb",
        "text": "#10213b",
        "muted": "#526783",
    },
}


class StudioApp(tk.Tk):
    def __init__(self, demo=False):
        super().__init__()
        self.demo = demo
        self.title("AI Media Studio V5")
        self.geometry("1480x900")
        self.minsize(1120, 720)
        self.events, self.scenes = queue.Queue(), []
        self.pipeline = self.result = self.preview_process = self.preview_photo = None
        self.preview_playing = False
        self.style_var = tk.StringVar(value="Obsidian Neon")
        self._build()
        self.apply_style()
        self.after(70, self._poll)

    @property
    def palette(self):
        return UI_STYLES[self.style_var.get()]

    def section(self, parent, text):
        tk.Label(parent, text=text.upper(), font=("TkDefaultFont", 9, "bold"), anchor="w").pack(
            fill="x", padx=14, pady=(14, 5)
        )

    def _build(self):
        self.header = tk.Frame(self, height=64)
        self.header.pack(fill="x")
        tk.Label(self.header, text="AI MEDIA STUDIO", font=("TkDefaultFont", 20, "bold")).pack(
            side="left", padx=(20, 10), pady=15
        )
        tk.Label(self.header, text="V5  •  CREATE / PREVIEW / EDIT", font=("TkDefaultFont", 10, "bold")).pack(
            side="left"
        )
        ttk.Combobox(self.header, textvariable=self.style_var, values=list(UI_STYLES), state="readonly", width=18).pack(
            side="right", padx=20
        )
        self.style_var.trace_add("write", lambda *_: self.apply_style())
        self.main = ttk.Panedwindow(self, orient="horizontal")
        self.main.pack(fill="both", expand=True, padx=14, pady=(12, 8))
        self.settings_shell, self.editor_shell, self.monitor_shell = (
            tk.Frame(self, width=330),
            tk.Frame(self),
            tk.Frame(self, width=440),
        )
        self.main.add(self.settings_shell, weight=0)
        self.main.add(self.editor_shell, weight=1)
        self.main.add(self.monitor_shell, weight=1)
        self._build_settings()
        self._build_editor()
        self._build_monitor()
        self._build_footer()

    def _build_settings(self):
        canvas = tk.Canvas(self.settings_shell, highlightthickness=0, width=318)
        scroll = ttk.Scrollbar(self.settings_shell, orient="vertical", command=canvas.yview)
        self.settings = tk.Frame(canvas)
        self.settings.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.settings, anchor="nw", width=304)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.section(self.settings, "Project")
        self.title_var = tk.StringVar(value="The Future of Creative AI")
        tk.Entry(self.settings, textvariable=self.title_var, relief="flat").pack(fill="x", padx=14, ipady=7)
        self.section(self.settings, "Canvas")
        self.format_var = tk.StringVar(value="short")
        row = tk.Frame(self.settings)
        row.pack(fill="x", padx=14)
        ttk.Radiobutton(row, text="YouTube 16:9", variable=self.format_var, value="long").pack(side="left")
        ttk.Radiobutton(row, text="Reel 9:16", variable=self.format_var, value="short").pack(side="left", padx=10)
        friendly = {p.key: p.label for group in PROVIDER_CATALOG.values() for p in group}
        self.vars, self.provider_maps = {}, {}
        defaults = {
            "image": "Local images and video B-roll",
            "voice": "Piper neural narration",
            "avatar": "Local VTuber host",
            "music": "Procedural score",
        }
        for kind in ("image", "voice", "avatar", "music"):
            self.section(self.settings, kind)
            labels = [friendly[p.key] for p in PROVIDER_CATALOG[kind]]
            self.provider_maps[kind] = {friendly[p.key]: p.key for p in PROVIDER_CATALOG[kind]}
            self.vars[kind] = tk.StringVar(value=defaults[kind])
            ttk.Combobox(self.settings, textvariable=self.vars[kind], values=labels, state="readonly").pack(
                fill="x", padx=14
            )
        self.voice_var = tk.StringVar(value="en-US-GuyNeural")
        self.piper_model_var = tk.StringVar()
        self.media_dir_var, self.music_path_var = tk.StringVar(), tk.StringVar()
        self.music_title_var, self.music_artist_var, self.music_attribution_var = (
            tk.StringVar(),
            tk.StringVar(),
            tk.StringVar(),
        )
        self.voice_volume_var, self.music_volume_var = tk.DoubleVar(value=100), tk.DoubleVar(value=24)
        tk.Entry(self.settings, textvariable=self.voice_var, relief="flat").pack(
            fill="x", padx=14, pady=(6, 2), ipady=5
        )
        ttk.Button(self.settings, text="Choose Piper model", command=self.choose_piper_model).pack(
            fill="x", padx=14, pady=2
        )
        self.piper_label = tk.Label(self.settings, text="No offline voice selected", anchor="w")
        self.piper_label.pack(fill="x", padx=14)
        self._slider("Voice volume", self.voice_volume_var, 150)
        self._slider("Music volume", self.music_volume_var, 100)
        ttk.Button(self.settings, text="Choose media / B-roll", command=self.choose_media_dir).pack(
            fill="x", padx=14, pady=(8, 2)
        )
        self.media_label = tk.Label(self.settings, text="No media folder selected", anchor="w")
        self.media_label.pack(fill="x", padx=14)
        ttk.Button(self.settings, text="Choose owned music", command=self.choose_music).pack(
            fill="x", padx=14, pady=(8, 2)
        )
        ttk.Button(self.settings, text="Import YouTube Audio Library track", command=self.choose_youtube_audio).pack(
            fill="x", padx=14, pady=2
        )
        self.music_label = tk.Label(self.settings, text="Using original procedural score", anchor="w")
        self.music_label.pack(fill="x", padx=14, pady=(0, 10))

    def _slider(self, name, variable, maximum):
        row = tk.Frame(self.settings)
        row.pack(fill="x", padx=14, pady=(7, 0))
        tk.Label(row, text=name).pack(side="left")
        value = tk.Label(row, width=5, anchor="e")
        value.pack(side="right")
        ttk.Scale(self.settings, from_=0, to=maximum, variable=variable).pack(fill="x", padx=14)
        variable.trace_add("write", lambda *_: value.config(text=f"{variable.get():.0f}%"))
        value.config(text=f"{variable.get():.0f}%")

    def _build_editor(self):
        self.notebook = ttk.Notebook(self.editor_shell)
        self.notebook.pack(fill="both", expand=True)
        script_tab, scene_tab = tk.Frame(self.notebook), tk.Frame(self.notebook)
        self.notebook.add(script_tab, text="  Script  ")
        self.notebook.add(scene_tab, text="  Scene Editor  ")
        self.script = tk.Text(
            script_tab, relief="flat", wrap="word", padx=18, pady=18, font=("TkFixedFont", 11), undo=True
        )
        self.script.pack(fill="both", expand=True, padx=12, pady=12)
        self.script.insert(
            "1.0",
            "Hook: Open with a strong idea.\n"
            "Point: Build the scene with visible evidence.\n"
            "Outro: Close with a clear final thought.",
        )
        ttk.Button(script_tab, text="Build editable scenes →", command=self.build_scenes).pack(
            anchor="e", padx=12, pady=(0, 12)
        )
        body = tk.Frame(scene_tab)
        body.pack(fill="both", expand=True, padx=12, pady=12)
        self.scene_list = tk.Listbox(body, width=25, relief="flat", exportselection=False)
        self.scene_list.pack(side="left", fill="y")
        self.scene_list.bind("<<ListboxSelect>>", self.load_scene)
        form = tk.Frame(body)
        form.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.scene_kind_var, self.scene_duration_var, self.scene_media_var = (
            tk.StringVar(value="point"),
            tk.DoubleVar(value=3),
            tk.StringVar(),
        )
        ttk.Combobox(
            form,
            textvariable=self.scene_kind_var,
            values=["hook", "intro", "point", "section", "outro"],
            state="readonly",
        ).pack(fill="x")
        self.scene_text = tk.Text(form, height=9, relief="flat", wrap="word", padx=10, pady=10)
        self.scene_text.pack(fill="both", expand=True, pady=8)
        duration = tk.Frame(form)
        duration.pack(fill="x")
        tk.Label(duration, text="Duration").pack(side="left")
        ttk.Spinbox(duration, from_=1, to=30, increment=0.25, textvariable=self.scene_duration_var, width=8).pack(
            side="left", padx=8
        )
        tk.Entry(form, textvariable=self.scene_media_var, relief="flat").pack(fill="x", pady=6, ipady=5)
        buttons = tk.Frame(form)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Choose media", command=self.choose_scene_media).pack(side="left")
        ttk.Button(buttons, text="Apply changes", command=self.apply_scene).pack(side="left", padx=6)
        ttk.Button(buttons, text="+ Scene", command=self.add_scene).pack(side="right")
        ttk.Button(buttons, text="Delete", command=self.delete_scene).pack(side="right", padx=6)

    def _build_monitor(self):
        self.section(self.monitor_shell, "Production monitor")
        self.monitor = tk.Label(
            self.monitor_shell, text="Your render will appear here", anchor="center", compound="center"
        )
        self.monitor.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        controls = tk.Frame(self.monitor_shell)
        controls.pack(fill="x", padx=14)
        ttk.Button(controls, text="▶ Preview", command=self.toggle_preview).pack(side="left")
        ttk.Button(controls, text="Open with sound", command=self.open_video).pack(side="left", padx=6)
        self.preview_time = tk.Label(controls, text="00:00")
        self.preview_time.pack(side="right")
        self.section(self.monitor_shell, "Render status")
        self.status = tk.Label(self.monitor_shell, text="Ready", anchor="w")
        self.status.pack(fill="x", padx=14)
        self.progress = ttk.Progressbar(self.monitor_shell, maximum=100)
        self.progress.pack(fill="x", padx=14, pady=8)
        self.stages = tk.Listbox(self.monitor_shell, relief="flat", height=7)
        self.stages.pack(fill="x", padx=14)
        [self.stages.insert("end", f"○ {s.title()}") for s in MediaPipeline.STAGES]
        self.output = tk.Label(self.monitor_shell, text="No render yet", anchor="w", justify="left", wraplength=400)
        self.output.pack(fill="x", padx=14, pady=12)

    def _build_footer(self):
        footer = tk.Frame(self)
        footer.pack(fill="x", padx=14, pady=(0, 12))
        ttk.Button(footer, text="GENERATE VIDEO", style="Accent.TButton", command=self.generate).pack(side="left")
        ttk.Button(footer, text="Stop", command=self.stop).pack(side="left", padx=7)
        ttk.Button(footer, text="Save project", command=self.save_project).pack(side="right")

    def apply_style(self):
        if not hasattr(self, "main"):
            return
        p, style = self.palette, ttk.Style(self)
        style.theme_use("clam")
        style.configure("TButton", padding=8, background=p["field"], foreground=p["text"])
        style.configure(
            "Accent.TButton", background=p["accent"], foreground=p["bg"], font=("TkDefaultFont", 10, "bold")
        )
        style.configure("TCombobox", fieldbackground=p["field"], foreground=p["text"], arrowcolor=p["accent"])
        style.configure("TNotebook", background=p["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", padding=(12, 7), background=p["panel"], foreground=p["text"])
        style.map("TNotebook.Tab", background=[("selected", p["accent"])], foreground=[("selected", p["bg"])])
        self.configure(bg=p["bg"])

        def recolor(widget):
            for child in widget.winfo_children():
                if isinstance(child, (tk.Frame, tk.Canvas)):
                    child.configure(bg=p["panel"])
                elif isinstance(child, tk.Label):
                    child.configure(bg=p["panel"], fg=p["muted"])
                elif isinstance(child, (tk.Text, tk.Listbox, tk.Entry)):
                    child.configure(
                        bg=p["field"], fg=p["text"], insertbackground=p["accent"], selectbackground=p["accent"]
                    )
                recolor(child)

        recolor(self)
        self.header.configure(bg=p["panel"])
        self.monitor.configure(bg="#02040a", fg=p["muted"])

    def project(self):
        def provider(kind):
            return self.provider_maps[kind][self.vars[kind].get()]

        return ProjectSpec(
            title=self.title_var.get().strip() or "Untitled",
            script=self.script.get("1.0", "end").strip(),
            scenes=[Scene(**s.__dict__) for s in self.scenes],
            format=VideoFormat(self.format_var.get()),
            image_provider=provider("image"),
            voice_provider=provider("voice"),
            music_provider=provider("music"),
            avatar_provider=provider("avatar"),
            voice=self.voice_var.get().strip() or "en-US-GuyNeural",
            piper_model=Path(self.piper_model_var.get()) if self.piper_model_var.get() else None,
            media_dir=Path(self.media_dir_var.get()) if self.media_dir_var.get() else None,
            music_path=Path(self.music_path_var.get()) if self.music_path_var.get() else None,
            voice_volume=self.voice_volume_var.get() / 100,
            music_volume=self.music_volume_var.get() / 100,
            music_title=self.music_title_var.get(),
            music_artist=self.music_artist_var.get(),
            music_attribution=self.music_attribution_var.get(),
        )

    def build_scenes(self):
        self.scenes = MediaPipeline.parse_script(
            self.script.get("1.0", "end").strip(), VideoFormat(self.format_var.get())
        )
        self.refresh_scene_list()
        self.notebook.select(1)
        if self.scenes:
            self.scene_list.selection_set(0)
            self.load_scene()

    def refresh_scene_list(self):
        self.scene_list.delete(0, "end")
        for i, s in enumerate(self.scenes, 1):
            self.scene_list.insert("end", f"{i:02d}  {s.kind.upper()}  {s.text[:24]}")

    def selected_scene(self):
        selected = self.scene_list.curselection()
        return selected[0] if selected else None

    def load_scene(self, _event=None):
        i = self.selected_scene()
        if i is None:
            return
        s = self.scenes[i]
        self.scene_kind_var.set(s.kind)
        self.scene_duration_var.set(s.duration)
        self.scene_media_var.set(s.image_path or "")
        self.scene_text.delete("1.0", "end")
        self.scene_text.insert("1.0", s.text)
        if s.image_path and Path(s.image_path).is_file():
            self.show_frame(s.image_path)

    def apply_scene(self):
        i = self.selected_scene()
        if i is None:
            return
        s = self.scenes[i]
        s.kind = self.scene_kind_var.get()
        s.title = s.kind.upper()
        s.text = self.scene_text.get("1.0", "end").strip()
        s.duration = float(self.scene_duration_var.get())
        s.image_path = self.scene_media_var.get().strip() or None
        self.refresh_scene_list()
        self.scene_list.selection_set(i)

    def add_scene(self):
        self.scenes.append(Scene("New scene", "point", 3, title="POINT"))
        self.refresh_scene_list()
        self.scene_list.selection_set(len(self.scenes) - 1)
        self.load_scene()

    def delete_scene(self):
        i = self.selected_scene()
        if i is not None:
            self.scenes.pop(i)
            self.refresh_scene_list()

    def choose_scene_media(self):
        p = filedialog.askopenfilename(
            title="Choose scene media",
            filetypes=[("Media", "*.png *.jpg *.jpeg *.webp *.mp4 *.mov *.mkv *.webm"), ("All", "*.*")],
        )
        if p:
            self.scene_media_var.set(p)
            self.show_frame(p)

    def choose_media_dir(self):
        p = filedialog.askdirectory(title="Choose user-owned media/B-roll folder")
        if p:
            self.media_dir_var.set(p)
            self.vars["image"].set("Local images and video B-roll")
            self.media_label.config(text=Path(p).name)

    def choose_music(self):
        p = filedialog.askopenfilename(
            title="Choose user-owned music", filetypes=[("Audio", "*.wav *.mp3 *.m4a *.aac *.flac"), ("All", "*.*")]
        )
        if p:
            self.music_path_var.set(p)
            self.vars["music"].set("Local music file")
            self.music_label.config(text=Path(p).name)

    def choose_piper_model(self):
        p = filedialog.askopenfilename(
            title="Choose Piper voice model", filetypes=[("Piper ONNX", "*.onnx"), ("All", "*.*")]
        )
        if p:
            self.piper_model_var.set(p)
            self.vars["voice"].set("Piper neural narration")
            self.piper_label.config(text=Path(p).name)

    def choose_youtube_audio(self):
        self.choose_music()
        if not self.music_path_var.get():
            return
        self.vars["music"].set("YouTube Audio Library import")
        self.music_title_var.set(simpledialog.askstring("Track title", "Audio Library track title:") or "")
        self.music_artist_var.set(simpledialog.askstring("Artist", "Audio Library artist:") or "")
        self.music_attribution_var.set(
            simpledialog.askstring("Attribution", "Paste the exact Audio Library attribution text:") or ""
        )

    def generate(self):
        if self.pipeline:
            return
        if not self.scenes:
            self.build_scenes()
        self.stop_preview()
        self.pipeline = MediaPipeline(
            lambda m, p: self.events.put(("progress", m, p)), lambda path: self.events.put(("frame", str(path)))
        )
        threading.Thread(target=self.worker, args=(self.project(),), daemon=True).start()

    def worker(self, project):
        try:
            self.events.put(("done", self.pipeline.run(project)))
        except PipelineCancelled:
            self.events.put(("cancelled",))
        except (OSError, ValueError, RuntimeError) as exc:
            self.events.put(("error", str(exc)))

    def show_frame(self, path):
        try:
            if Path(path).suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
                temp = Path(path).with_suffix(".preview.jpg")
                subprocess.run(
                    ["ffmpeg", "-loglevel", "error", "-y", "-ss", ".2", "-i", str(path), "-frames:v", "1", str(temp)],
                    check=True,
                )
                path = temp
            image = Image.open(path).convert("RGB")
            image.thumbnail((620, 620), Image.Resampling.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(image)
            self.monitor.config(image=self.preview_photo, text="")
        except (OSError, subprocess.SubprocessError):
            pass

    def toggle_preview(self):
        if self.preview_playing:
            self.stop_preview()
        elif self.result:
            self.preview_playing = True
            threading.Thread(target=self._decode_preview, args=(self.result["video_path"],), daemon=True).start()

    def _decode_preview(self, path):
        width, height = (352, 626) if self.format_var.get() == "short" else (640, 360)
        self.preview_process = subprocess.Popen(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-i",
                path,
                "-vf",
                f"fps=12,scale={width}:{height}:force_original_aspect_ratio=decrease",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-",
            ],
            stdout=subprocess.PIPE,
        )
        size = width * height * 3
        frame = 0
        while self.preview_playing:
            data = self.preview_process.stdout.read(size)
            if len(data) != size:
                break
            self.events.put(("video-frame", data, width, height, frame / 12))
            frame += 1
        self.preview_playing = False

    def stop_preview(self):
        self.preview_playing = False
        if self.preview_process and self.preview_process.poll() is None:
            self.preview_process.terminate()
        self.preview_process = None

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
                elif kind == "frame":
                    self.show_frame(e[1])
                elif kind == "video-frame":
                    image = Image.frombytes("RGB", (e[2], e[3]), e[1])
                    self.preview_photo = ImageTk.PhotoImage(image)
                    self.monitor.config(image=self.preview_photo, text="")
                    seconds = int(e[4])
                    self.preview_time.config(text=f"{seconds // 60:02d}:{seconds % 60:02d}")
                elif kind == "done":
                    self.result = e[1]
                    self.output.config(text=self.result["video_path"])
                    self.status.config(text="Render complete — ready to preview")
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
        self.after(70, self._poll)

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

    def destroy(self):
        self.stop_preview()
        super().destroy()


def launch():
    StudioApp().mainloop()
