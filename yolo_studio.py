#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO Studio v1.2.0 - Alat persiapan deteksi objek berbasis YOLO
Akuisisi (video/webcam) → Anotasi → Split → Export → Colab Training → Evaluasi
"""

import os
import sys
import csv
import json
import random
import shutil
import zipfile
import threading
import webbrowser
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

try:
    import cv2
    HAS_CV = True
except ImportError:
    HAS_CV = False

try:
    from PIL import Image, ImageTk, ImageDraw, ImageEnhance
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import numpy as np
    HAS_NP = True
except ImportError:
    HAS_NP = False


APP_TITLE = "YOLO Studio"
APP_VERSION = "1.2.0"
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")

# ============================================================
#  TEMA UI
# ============================================================
THEMES = {
    "midnight": {
        "name": "Midnight", "bg": "#0b0e1c", "panel": "#161b30", "panel2": "#232a47",
        "border": "#3a4370", "fg": "#f0f3ff", "fg_muted": "#b8c0dc", "accent": "#7d9bff",
        "success": "#5ee88f", "warning": "#fcd34d", "danger": "#ff8a8a",
        "entry_bg": "#1c2340", "entry_fg": "#f0f3ff", "text_bg": "#11162b",
        "text_fg": "#dde3fa", "select_bg": "#40508e", "canvas_bg": "#0b0e1c",
        "tree_bg": "#161b30", "tree_sel": "#40508e",
    },
    "nord": {
        "name": "Nord", "bg": "#2e3440", "panel": "#3b4252", "panel2": "#4a5468",
        "border": "#607089", "fg": "#f4f6fb", "fg_muted": "#c8d1e0", "accent": "#8fbcbb",
        "success": "#b1d196", "warning": "#f0d68b", "danger": "#e08a92",
        "entry_bg": "#434c5e", "entry_fg": "#f4f6fb", "text_bg": "#2e3440",
        "text_fg": "#e0e6f0", "select_bg": "#5e81ac", "canvas_bg": "#272c36",
        "tree_bg": "#3b4252", "tree_sel": "#5e81ac",
    },
    "dracula": {
        "name": "Dracula", "bg": "#191a21", "panel": "#21222c", "panel2": "#2d2f3d",
        "border": "#5a5f7a", "fg": "#f8f8f2", "fg_muted": "#c5c9dc", "accent": "#bd93f9",
        "success": "#6ef29b", "warning": "#f5fb9e", "danger": "#ff7878",
        "entry_bg": "#2d2f3d", "entry_fg": "#f8f8f2", "text_bg": "#1e1f29",
        "text_fg": "#f0f0ea", "select_bg": "#6272a4", "canvas_bg": "#16171d",
        "tree_bg": "#21222c", "tree_sel": "#6272a4",
    },
    "light": {
        "name": "Light", "bg": "#dfe3ea", "panel": "#eceff5", "panel2": "#d8dde6",
        "border": "#b7bfcd", "fg": "#141821", "fg_muted": "#4a5364", "accent": "#2f63c9",
        "success": "#0e7440", "warning": "#9a6100", "danger": "#b62222",
        "entry_bg": "#f6f8fb", "entry_fg": "#141821", "text_bg": "#eceff5",
        "text_fg": "#141821", "select_bg": "#a9c2ec", "canvas_bg": "#eceff5",
        "tree_bg": "#f6f8fb", "tree_sel": "#a9c2ec",
    },
}

THEME = {}

def tc(key: str, fallback: str = "#888888") -> str:
    return THEME.get(key, fallback)

_COLOR_REMAP = {
    "#555": "fg_muted", "#666": "fg_muted", "#444": "fg_muted", "#888": "fg_muted", "#999": "fg_muted", "#aaa": "fg_muted",
    "#a00": "danger", "#080": "success", "#c80": "warning", "#e67e22": "warning",
    "#f5f5f5": "text_bg", "#fafafa": "text_bg", "#eee": "panel2", "#dddddd": "border", "#ccc": "panel2",
    "#ff8a8a": "danger", "#e08a92": "danger", "#ff7878": "danger", "#b62222": "danger",
    "#5ee88f": "success", "#b1d196": "success", "#6ef29b": "success", "#0e7440": "success",
    "#fcd34d": "warning", "#f0d68b": "warning", "#f5fb9e": "warning", "#9a6100": "warning",
    "#b8c0dc": "fg_muted", "#c8d1e0": "fg_muted", "#c5c9dc": "fg_muted", "#4a5364": "fg_muted",
    "#7d9bff": "accent", "#8fbcbb": "accent", "#bd93f9": "accent", "#2f63c9": "accent",
    "#f0f3ff": "fg", "#f4f6fb": "fg", "#f8f8f2": "fg", "#141821": "fg",
    "#161b30": "panel", "#3b4252": "panel", "#21222c": "panel", "#eceff5": "panel",
    "#1c2340": "entry_bg", "#434c5e": "entry_bg", "#2d2f3d": "entry_bg", "#f6f8fb": "entry_bg",
    "#11162b": "text_bg", "#2e3440": "text_bg", "#1e1f29": "text_bg",
}

def remap_hardcoded_colors(widget):
    for child in widget.winfo_children():
        try:
            cls = child.winfo_class()
            if cls in ("TLabel", "TCheckbutton", "TRadiobutton", "TButton"):
                try:
                    fg = str(child.cget("foreground")).lower()
                    if fg in _COLOR_REMAP: child.configure(foreground=THEME[_COLOR_REMAP[fg]])
                except: pass
            elif cls == "Label":
                try:
                    fg = str(child.cget("fg")).lower()
                    if fg in _COLOR_REMAP: child.configure(fg=THEME[_COLOR_REMAP[fg]])
                except: pass
                try:
                    bg = str(child.cget("bg")).lower()
                    if bg in _COLOR_REMAP: child.configure(bg=THEME[_COLOR_REMAP[bg]])
                except: pass
            elif cls == "Treeview":
                try:
                    child.tag_configure("done", foreground=THEME["success"])
                    child.tag_configure("empty", foreground=THEME["warning"])
                    child.tag_configure("todo", foreground=THEME["fg_muted"])
                except: pass
        except: pass
        remap_hardcoded_colors(child)

def restyle_tk_widgets(widget):
    for child in widget.winfo_children():
        try:
            cls = child.winfo_class()
            if cls == "Text":
                child.configure(background=THEME["text_bg"], foreground=THEME["text_fg"],
                                insertbackground=THEME["text_fg"], selectbackground=THEME["select_bg"], selectforeground="#ffffff")
            elif cls == "Listbox":
                child.configure(background=THEME["text_bg"], foreground=THEME["text_fg"],
                                selectbackground=THEME["select_bg"], selectforeground="#ffffff")
            elif cls == "Canvas":
                cur = str(child.cget("background")).lower()
                if cur not in ("#1e1e1e", "#0a0d1a", "#000000", "#111111"):
                    child.configure(background=THEME["canvas_bg"])
        except: pass
        restyle_tk_widgets(child)

def apply_theme(root, name: str):
    global THEME
    if name not in THEMES: name = "midnight"
    THEME.clear()
    THEME.update(THEMES[name])
    THEME["name"] = name

    style = ttk.Style(root)
    try: style.theme_use("clam")
    except: pass

    root.configure(bg=THEME["bg"])
    style.configure(".", background=THEME["panel"], foreground=THEME["fg"], fieldbackground=THEME["entry_bg"], bordercolor=THEME["border"], focuscolor=THEME["accent"], troughcolor=THEME["panel2"])
    style.configure("TFrame", background=THEME["panel"])
    style.configure("TLabel", background=THEME["panel"], foreground=THEME["fg"])
    style.configure("TLabelframe", background=THEME["panel"], bordercolor=THEME["border"], relief="solid")
    style.configure("TLabelframe.Label", background=THEME["panel"], foreground=THEME["accent"], font=("Segoe UI", 10, "bold"))
    style.configure("TButton", background=THEME["panel2"], foreground=THEME["fg"], bordercolor=THEME["border"], focuscolor=THEME["accent"], padding=(8, 4), relief="flat")
    style.map("TButton", background=[("active", THEME["accent"]), ("pressed", THEME["accent"])], foreground=[("active", "#ffffff"), ("pressed", "#ffffff")])
    style.configure("TEntry", fieldbackground=THEME["entry_bg"], foreground=THEME["entry_fg"], bordercolor=THEME["border"], insertcolor=THEME["entry_fg"], lightcolor=THEME["border"], darkcolor=THEME["border"])
    style.map("TEntry", fieldbackground=[("readonly", THEME["panel2"])], foreground=[("readonly", THEME["fg_muted"])])
    style.configure("TCombobox", fieldbackground=THEME["entry_bg"], foreground=THEME["entry_fg"], background=THEME["panel2"], bordercolor=THEME["border"], arrowcolor=THEME["fg"], selectbackground=THEME["entry_bg"], selectforeground=THEME["entry_fg"])
    style.map("TCombobox", fieldbackground=[("readonly", THEME["entry_bg"])], foreground=[("readonly", THEME["entry_fg"])])
    
    root.option_add("*TCombobox*Listbox.background", THEME["entry_bg"])
    root.option_add("*TCombobox*Listbox.foreground", THEME["entry_fg"])
    root.option_add("*TCombobox*Listbox.selectBackground", THEME["accent"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    style.configure("TSpinbox", fieldbackground=THEME["entry_bg"], foreground=THEME["entry_fg"], background=THEME["panel2"], bordercolor=THEME["border"], arrowcolor=THEME["fg"])
    style.configure("TNotebook", background=THEME["bg"], bordercolor=THEME["border"], tabmargins=(2, 4, 2, 0))
    style.configure("TNotebook.Tab", background=THEME["panel"], foreground=THEME["fg_muted"], padding=(14, 6), bordercolor=THEME["border"])
    style.map("TNotebook.Tab", background=[("selected", THEME["accent"]), ("active", THEME["panel2"])], foreground=[("selected", "#ffffff"), ("active", THEME["fg"])])
    style.configure("TProgressbar", background=THEME["accent"], troughcolor=THEME["panel2"], bordercolor=THEME["border"], lightcolor=THEME["accent"], darkcolor=THEME["accent"])
    style.configure("Treeview", background=THEME["tree_bg"], foreground=THEME["fg"], fieldbackground=THEME["tree_bg"], bordercolor=THEME["border"], rowheight=22)
    style.map("Treeview", background=[("selected", THEME["tree_sel"])], foreground=[("selected", "#ffffff")])
    style.configure("Treeview.Heading", background=THEME["panel2"], foreground=THEME["fg"], bordercolor=THEME["border"], relief="flat")
    style.map("Treeview.Heading", background=[("active", THEME["accent"])])
    style.configure("TCheckbutton", background=THEME["panel"], foreground=THEME["fg"])
    style.configure("TRadiobutton", background=THEME["panel"], foreground=THEME["fg"])
    style.configure("TScale", background=THEME["panel"], troughcolor=THEME["panel2"], bordercolor=THEME["border"])
    style.configure("TSeparator", background=THEME["border"])
    style.configure("TScrollbar", background=THEME["panel2"], troughcolor=THEME["bg"], bordercolor=THEME["border"], arrowcolor=THEME["fg"])

    restyle_tk_widgets(root)
    remap_hardcoded_colors(root)
    try: root.tk.call("tk", "scaling", 1.2)
    except: pass

def load_theme_pref() -> str:
    p = Path.home() / ".yolo_studio_config.json"
    if p.exists():
        try: return json.loads(p.read_text(encoding="utf-8")).get("theme", "midnight")
        except: pass
    return "midnight"

def save_theme_pref(name: str):
    p = Path.home() / ".yolo_studio_config.json"
    try: cfg = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except: cfg = {}
    cfg["theme"] = name
    try: p.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except: pass

CLASS_PALETTE = [
    "#e6194B", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4", "#f032e6", "#bfef45",
    "#fabed4", "#469990", "#dcbeff", "#9A6324", "#800000", "#aaffc3", "#808000", "#ffd8b1",
    "#000075", "#a9a9a9", "#ffe119", "#fffac8",
]

def class_color(idx: int) -> str:
    if 0 <= idx < len(CLASS_PALETTE): return CLASS_PALETTE[idx]
    import colorsys
    hue = ((idx - len(CLASS_PALETTE)) * 0.61803398875) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.65, 0.95)
    return "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))

def draw_label_tag(draw, x, y, text, color):
    try:
        bbox = draw.textbbox((0, 0), text)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except: w, h = len(text) * 6, 12
    pad = 3
    draw.rectangle([x, y, x + w + pad*2, y + h + pad*2], fill=color)
    r = int(color[1:3], 16); g = int(color[3:5], 16); b = int(color[5:7], 16)
    lum = (0.299*r + 0.587*g + 0.114*b) / 255
    fg = "#000" if lum > 0.55 else "#fff"
    draw.text((x + pad, y + pad), text, fill=fg)

YOLO_VERSIONS = {
    "YOLOv8": {"install": "pip install -q ultralytics", "import": "from ultralytics import YOLO", "models": ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"], "api": "ultralytics"},
    "YOLO11": {"install": "pip install -q ultralytics", "import": "from ultralytics import YOLO", "models": ["yolo11n.pt", "yolo11s.pt", "yolo11m.pt", "yolo11l.pt", "yolo11x.pt"], "api": "ultralytics"},
    "YOLOv9": {"install": "pip install -q ultralytics", "import": "from ultralytics import YOLO", "models": ["yolov9t.pt", "yolov9s.pt", "yolov9m.pt", "yolov9c.pt", "yolov9e.pt"], "api": "ultralytics"},
    "YOLOv10": {"install": "pip install -q ultralytics", "import": "from ultralytics import YOLO", "models": ["yolov10n.pt", "yolov10s.pt", "yolov10m.pt", "yolov10b.pt", "yolov10l.pt"], "api": "ultralytics"},
    "YOLOv5": {"install": "!git clone -q https://github.com/ultralytics/yolov5\n%cd yolov5\n!pip install -q -r requirements.txt", "import": "import torch", "models": ["yolov5s.pt", "yolov5m.pt", "yolov5l.pt", "yolov5x.pt"], "api": "yolov5"},
    "YOLO26": {"install": "pip install -q ultralytics", "import": "from ultralytics import YOLO", "models": ["yolo26n.pt", "yolo26s.pt", "yolo26m.pt", "yolo26l.pt", "yolo26x.pt"], "api": "ultralytics"},
    "YOLOv12": {"install": "pip install -q ultralytics", "import": "from ultralytics import YOLO", "models": ["yolo12n.pt", "yolo12s.pt", "yolo12m.pt", "yolo12l.pt", "yolo12x.pt"], "api": "ultralytics"},
    "YOLOv13": {"install": "pip install -q ultralytics", "import": "from ultralytics import YOLO", "models": ["yolov13n.pt", "yolov13s.pt", "yolov13l.pt", "yolov13x.pt"], "api": "ultralytics"},
}

PROJECT_DIRS = [
    "01_raw/frames", "01_raw/labels",
    "02_split/images/train", "02_split/images/val", "02_split/images/test",
    "02_split/labels/train", "02_split/labels/val", "02_split/labels/test",
    "04_export", "05_models", "06_runs", "notebooks", "configs",
]

def safe_name(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)

def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# ============================================================
#  Project State
# ============================================================
class Project:
    DEFAULTS = {
        "name": "", "root": "", "description": "", "author": "",
        "yolo_version": "YOLOv8", "base_model": "yolov8n.pt",
        "classes": [],
        "split": {"train": 70, "val": 20, "test": 10, "seed": 42},
        "training": {"epochs": 100, "imgsz": 640, "batch": 16, "patience": 20, "optimizer": "auto"},
        "annotation": {"last_idx": 0, "last_filename": ""},
        "created_at": "",
    }

    def __init__(self):
        self.data = json.loads(json.dumps(self.DEFAULTS))

    @property
    def root(self):
        return Path(self.data["root"]) if self.data["root"] else None

    def save(self):
        if self.root:
            (self.root / "project.json").write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def load(self, root: Path) -> bool:
        p = root / "project.json"
        if not p.exists(): return False
        self.data = json.loads(p.read_text(encoding="utf-8"))
        for k, v in self.DEFAULTS.items(): self.data.setdefault(k, v)
        
        # ✨ FIX BUG CLONE
        self.data["root"] = str(root.resolve())
        self.save() 
        return True

    def create(self, root: Path, name: str):
        root.mkdir(parents=True, exist_ok=True)
        for d in PROJECT_DIRS: (root / d).mkdir(parents=True, exist_ok=True)
        self.data["root"] = str(root)
        self.data["name"] = name
        self.data["created_at"] = datetime.now().isoformat(timespec="seconds")
        self.save()

# ============================================================
#  Tab 1: Proyek
# ============================================================
class ProjectTab(ttk.Frame):
    def __init__(self, master, project: Project, app):
        super().__init__(master, padding=16)
        self.project = project
        self.app = app
        self._build()

    def _build(self):
        ttk.Label(self, text="1. Setup Proyek", font=("Segoe UI", 15, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(self, text="Nama proyek:").grid(row=1, column=0, sticky="w", pady=4)
        self.e_name = ttk.Entry(self, width=50)
        self.e_name.grid(row=1, column=1, sticky="we", pady=4)

        ttk.Label(self, text="Nama pengguna:").grid(row=2, column=0, sticky="w", pady=4)
        self.e_author = ttk.Entry(self, width=50)
        self.e_author.grid(row=2, column=1, sticky="we", pady=4)

        ttk.Label(self, text="Lokasi folder proyek:").grid(row=3, column=0, sticky="w", pady=4)
        self.e_root = ttk.Entry(self, width=50)
        self.e_root.grid(row=3, column=1, sticky="we", pady=4)
        ttk.Button(self, text="Browse...", command=self.pick_root).grid(row=3, column=2, padx=4)

        ttk.Label(self, text="Deskripsi singkat:").grid(row=4, column=0, sticky="nw", pady=4)
        self.t_desc = tk.Text(self, height=3, width=60)
        self.t_desc.grid(row=4, column=1, columnspan=2, sticky="we", pady=4)

        ttk.Label(self, text="Versi YOLO:").grid(row=5, column=0, sticky="w", pady=(12, 4))
        self.cb_yolo = ttk.Combobox(self, values=list(YOLO_VERSIONS.keys()), state="readonly", width=20)
        self.cb_yolo.current(0)
        self.cb_yolo.grid(row=5, column=1, sticky="w", pady=(12, 4))
        self.cb_yolo.bind("<<ComboboxSelected>>", self._update_models)

        ttk.Label(self, text="Model dasar:").grid(row=6, column=0, sticky="w", pady=4)
        self.cb_model = ttk.Combobox(self, state="readonly", width=20)
        self.cb_model.grid(row=6, column=1, sticky="w", pady=4)
        self._update_models()

        ttk.Label(self, text="Kelas objek (1 per baris):", font=("Segoe UI", 10, "bold")).grid(row=7, column=0, sticky="nw", pady=(16, 4))
        self.t_classes = tk.Text(self, height=6, width=50, font=("Consolas", 10))
        self.t_classes.grid(row=7, column=1, columnspan=2, sticky="we", pady=(16, 4))

        btn = ttk.Frame(self)
        btn.grid(row=8, column=0, columnspan=3, sticky="w", pady=16)
        ttk.Button(btn, text="➕ Buat Proyek Baru", command=self.create_project).pack(side="left", padx=4)
        ttk.Button(btn, text="📂 Muat Proyek", command=self.load_project).pack(side="left", padx=4)
        ttk.Button(btn, text="💾 Simpan Konfigurasi", command=self.save_config).pack(side="left", padx=4)

        self.dash = tk.Text(self, height=9, width=95, state="disabled", relief="sunken", font=("Consolas", 9))
        self.dash.grid(row=9, column=0, columnspan=3, sticky="we", pady=8)
        self.columnconfigure(1, weight=1)

    def _update_models(self, *_):
        v = self.cb_yolo.get()
        self.cb_model["values"] = YOLO_VERSIONS[v]["models"]
        self.cb_model.current(0)

    def pick_root(self):
        d = filedialog.askdirectory(title="Pilih folder untuk proyek")
        if d:
            self.e_root.delete(0, "end"); self.e_root.insert(0, d)

    def create_project(self):
        name = self.e_name.get().strip()
        root = self.e_root.get().strip()
        if not name or not root:
            messagebox.showwarning("Lengkapi", "Nama dan lokasi folder wajib diisi.")
            return
        root_p = Path(root) / safe_name(name)
        try:
            self.project.create(root_p, name)
            self._apply_form()
            messagebox.showinfo("Sukses", f"Proyek dibuat di:\n{root_p}")
            self.app.refresh_all()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_project(self):
        d = filedialog.askdirectory(title="Pilih folder proyek (berisi project.json)")
        if not d: return
        if self.project.load(Path(d)):
            self._fill_form()
            self.app.refresh_all()
            messagebox.showinfo("Sukses", "Proyek berhasil dimuat.")
        else:
            messagebox.showwarning("Tidak ditemukan", "project.json tidak ada di folder itu.")

    def save_config(self):
        if not self.project.root:
            messagebox.showwarning("Belum ada proyek", "Buat atau muat proyek dulu.")
            return
        self._apply_form()
        self.app.refresh_all()
        messagebox.showinfo("Sukses", "Konfigurasi tersimpan.")

    def _apply_form(self):
        self.project.data["name"] = self.e_name.get().strip() or self.project.data["name"]
        self.project.data["author"] = self.e_author.get().strip()
        self.project.data["description"] = self.t_desc.get("1.0", "end").strip()
        self.project.data["yolo_version"] = self.cb_yolo.get()
        self.project.data["base_model"] = self.cb_model.get()
        raw = self.t_classes.get("1.0", "end").strip()
        self.project.data["classes"] = [c.strip() for c in raw.splitlines() if c.strip()]
        self.project.save()

    def _fill_form(self):
        d = self.project.data
        self.e_name.delete(0, "end"); self.e_name.insert(0, d["name"])
        self.e_author.delete(0, "end"); self.e_author.insert(0, d.get("author", ""))
        self.e_root.delete(0, "end")
        if d["root"]: self.e_root.insert(0, str(Path(d["root"]).parent))
        self.t_desc.delete("1.0", "end"); self.t_desc.insert("1.0", d.get("description", ""))
        if d["yolo_version"] in YOLO_VERSIONS:
            self.cb_yolo.set(d["yolo_version"]); self._update_models()
            if d["base_model"] in YOLO_VERSIONS[d["yolo_version"]]["models"]:
                self.cb_model.set(d["base_model"])
        self.t_classes.delete("1.0", "end")
        self.t_classes.insert("1.0", "\n".join(d.get("classes", [])))
        self.refresh_dashboard()

    def refresh_dashboard(self):
        self.dash.configure(state="normal")
        self.dash.delete("1.0", "end")
        if not self.project.root:
            self.dash.insert("end", "Belum ada proyek aktif.\n")
            self.dash.configure(state="disabled")
            return
        d = self.project.data
        frames_dir = self.project.root / "01_raw" / "frames"
        labels_dir = self.project.root / "01_raw" / "labels"
        
        n_frames = sum(1 for p in frames_dir.glob("*") if p.suffix.lower() in IMAGE_EXTS) if frames_dir.exists() else 0
        n_aug = sum(1 for p in frames_dir.glob("*_aug_*") if p.suffix.lower() in IMAGE_EXTS) if frames_dir.exists() else 0
        n_ann = sum(1 for p in frames_dir.glob("*") if p.suffix.lower() in IMAGE_EXTS
                    and (labels_dir / (p.stem + ".txt")).exists()
                    and (labels_dir / (p.stem + ".txt")).stat().st_size > 0) if frames_dir.exists() else 0

        self.dash.insert("end", f"📁 Proyek     : {d['name']}\n")
        self.dash.insert("end", f"🤖 YOLO        : {d['yolo_version']}  ({d['base_model']})\n")
        self.dash.insert("end", f"🏷  Kelas       : {len(d.get('classes', []))} → {', '.join(d['classes']) or '-'}\n")
        self.dash.insert("end", f"🖼  Gambar      : {n_frames} (Termasuk {n_aug} hasil augmentasi)\n")
        self.dash.insert("end", f"✏  Anotasi     : {n_ann}/{n_frames} ({(n_ann/n_frames*100 if n_frames else 0):.1f}%)\n")
        
        split_root = self.project.root / "02_split" / "images"
        line = "🔀 Split       : "
        for sp in ("train", "val", "test"):
            n = len(list((split_root / sp).glob("*"))) if (split_root / sp).exists() else 0
            line += f"{sp}={n}  "
        self.dash.insert("end", line + "\n")
        
        models = list((self.project.root / "05_models").glob("*.pt"))
        self.dash.insert("end", f"🎯 Model       : {len(models)} file .pt tersedia\n")
        
        preds = list((self.project.root / "06_runs" / "predictions").glob("*.mp4"))
        self.dash.insert("end", f"🎬 Video Prediksi: {len(preds)} file tersimpan\n")
        self.dash.configure(state="disabled")

# ============================================================
#  Tab 2: Akuisisi
# ============================================================
class AcquireTab(ttk.Frame):
    def __init__(self, master, project: Project, app):
        super().__init__(master, padding=16)
        self.project = project
        self.app = app
        self._build()

    def _build(self):
        ttk.Label(self, text="2. Akuisisi Data (Video / Webcam)", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 4))
        ttk.Label(self, text="Ambil gambar objek dari sekitar Anda.", foreground=tc("fg_muted")).pack(anchor="w", pady=(0, 12))

        lf_v = ttk.LabelFrame(self, text="A. Ekstrak Frame dari Video", padding=10)
        lf_v.pack(fill="x", pady=6)

        ttk.Label(lf_v, text="File video:").grid(row=0, column=0, sticky="w", pady=4)
        self.e_video = ttk.Entry(lf_v, width=55)
        self.e_video.grid(row=0, column=1, sticky="we", pady=4)
        ttk.Button(lf_v, text="Browse...", command=self.pick_video).grid(row=0, column=2, padx=4)

        ttk.Label(lf_v, text="Ambil 1 frame setiap:").grid(row=1, column=0, sticky="w", pady=4)
        self.v_fps = tk.IntVar(value=15)
        ttk.Spinbox(lf_v, from_=1, to=120, textvariable=self.v_fps, width=8).grid(row=1, column=1, sticky="w", pady=4)
        ttk.Label(lf_v, text="frame").grid(row=1, column=1, sticky="w", padx=(80, 0))
        ttk.Button(lf_v, text="▶ Ekstrak Frame", command=self.extract_frames).grid(row=2, column=1, sticky="w", pady=10)
        lf_v.columnconfigure(1, weight=1)

        lf_w = ttk.LabelFrame(self, text="B. Capture dari Webcam", padding=10)
        lf_w.pack(fill="x", pady=6)

        ttk.Label(lf_w, text="Kamera index:").grid(row=0, column=0, sticky="w", pady=4)
        self.v_cam = tk.IntVar(value=0)
        ttk.Spinbox(lf_w, from_=0, to=5, textvariable=self.v_cam, width=8).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Label(lf_w, text="(0=laptop, 1+=eksternal)", foreground=tc("fg_muted")).grid(row=0, column=2, sticky="w", padx=8)

        ttk.Label(lf_w, text="Nama sesi:").grid(row=1, column=0, sticky="w", pady=4)
        self.e_session = ttk.Entry(lf_w, width=25)
        self.e_session.insert(0, "sesi1")
        self.e_session.grid(row=1, column=1, sticky="w", pady=4)

        hint = ("Kontrol kamera:  SPASI = simpan  •  A = auto (tiap 10 frame)  •  Q/ESC = keluar")
        ttk.Label(lf_w, text=hint, foreground=tc("fg_muted")).grid(row=2, column=0, columnspan=3, sticky="w", pady=(6, 4))

        ttk.Button(lf_w, text="🎥 Buka Kamera", command=self.capture_webcam).grid(row=3, column=1, sticky="w", pady=8)
        lf_w.columnconfigure(1, weight=1)

        ttk.Label(self, text="Log:").pack(anchor="w", pady=(12, 2))
        self.info = tk.Text(self, height=10, width=100, state="disabled", relief="sunken", font=("Consolas", 9))
        self.info.pack(fill="x")

    def _log(self, m):
        self.info.configure(state="normal")
        self.info.insert("end", m + "\n"); self.info.see("end")
        self.info.configure(state="disabled")

    def _check(self):
        if not self.project.root:
            messagebox.showwarning("Belum ada proyek", "Buat proyek dulu di tab 1.")
            return False
        if not HAS_CV:
            messagebox.showerror("OpenCV tidak ada", "pip install opencv-python")
            return False
        return True

    def pick_video(self):
        f = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv *.webm"), ("All", "*.*")])
        if f: self.e_video.delete(0, "end"); self.e_video.insert(0, f)

    def extract_frames(self):
        if not self._check(): return
        vpath = self.e_video.get().strip()
        if not vpath or not Path(vpath).exists():
            messagebox.showwarning("Kosong", "Pilih file video dulu.")
            return
        interval = max(1, self.v_fps.get())
        out = self.project.root / "01_raw" / "frames"
        out.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(vpath)
        if not cap.isOpened():
            messagebox.showerror("Gagal", "Tidak bisa buka video.")
            return
        base = Path(vpath).stem; idx = 0; saved = 0
        while True:
            ret, frame = cap.read()
            if not ret: break
            if idx % interval == 0:
                cv2.imwrite(str(out / f"{base}_{idx:06d}.jpg"), frame)
                saved += 1
            idx += 1
        cap.release()
        self._log(f"✓ {saved} frame disimpan dari {base}")
        self.app.refresh_all()
        messagebox.showinfo("Sukses", f"{saved} frame tersimpan.")

    def capture_webcam(self):
        if not self._check(): return
        cam_idx = self.v_cam.get()
        session = safe_name(self.e_session.get().strip() or "sesi1")
        out = self.project.root / "01_raw" / "frames"
        out.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(cam_idx)
        if not cap.isOpened():
            messagebox.showerror("Gagal", f"Tidak bisa buka kamera {cam_idx}.")
            return
        self._log(f"Kamera {cam_idx} aktif. SPASI/A/Q.")
        saved = 0; auto = False; counter = 0
        win = f"Capture - {session}"
        while True:
            ret, frame = cap.read()
            if not ret: break
            counter += 1
            disp = frame.copy()
            cv2.putText(disp, f"Saved: {saved}  {'AUTO' if auto else 'MANUAL'}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0) if not auto else (0, 200, 255), 2)
            cv2.imshow(win, disp)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27): break
            if key == ord(' '):
                cv2.imwrite(str(out / f"{session}_{now_tag()}_{saved:04d}.jpg"), frame); saved += 1
                self._log(f"  ✓ Tersimpan")
            elif key == ord('a'):
                auto = not auto
                self._log(f"  Auto: {'ON' if auto else 'OFF'}")
            if auto and counter % 10 == 0:
                cv2.imwrite(str(out / f"{session}_{now_tag()}_{saved:04d}.jpg"), frame); saved += 1
        cap.release(); cv2.destroyAllWindows()
        self._log(f"✓ {saved} frame dari sesi '{session}'")
        self.app.refresh_all()
        messagebox.showinfo("Sukses", f"{saved} frame tersimpan.")

# ============================================================
#  Preprocessing Studio (Fitur Baru v1.2.0)
# ============================================================
class PreprocessingWindow(tk.Toplevel):
    def __init__(self, master, project: Project, on_close=None):
        super().__init__(master)
        self.project = project
        self.on_close = on_close
        
        frames_dir = project.root / "01_raw" / "frames"
        self.items = sorted([p for p in frames_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS]) if frames_dir.exists() else []
        self.labels_dir = project.root / "01_raw" / "labels"
        
        if not self.items:
            messagebox.showwarning("Kosong", "Belum ada gambar di 01_raw/frames.")
            self.destroy()
            return

        self.idx = 0
        self.title("Preprocessing Studio — Preview & Augmentasi")
        self.geometry("1100x700")
        self.minsize(900, 600)
        
        self.pil_asli = None
        self.pil_hasil = None
        self.cv_asli = None
        
        self._build()
        self.load_image()

    def _build(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        
        ttk.Button(top, text="◀ Prev", command=lambda: self.load_image(self.idx-1)).pack(side="left")
        ttk.Button(top, text="Next ▶", command=lambda: self.load_image(self.idx+1)).pack(side="left", padx=5)
        
        self.lbl_info = ttk.Label(top, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_info.pack(side="left", padx=20)

        mid = ttk.Frame(self, padding=5)
        mid.pack(fill="both", expand=True)
        
        self.canvas_asli = tk.Canvas(mid, bg="#1e1e1e", highlightthickness=1, highlightbackground="#444")
        self.canvas_asli.pack(side="left", fill="both", expand=True, padx=(0, 5))
        ttk.Label(self.canvas_asli, text="Gambar Asli", background="#1e1e1e", foreground="#aaa").place(x=10, y=10)
        
        self.canvas_hasil = tk.Canvas(mid, bg="#1e1e1e", highlightthickness=1, highlightbackground="#444")
        self.canvas_hasil.pack(side="right", fill="both", expand=True, padx=(5, 0))
        ttk.Label(self.canvas_hasil, text="Preview Hasil", background="#1e1e1e", foreground=tc("success")).place(x=10, y=10)

        bot = ttk.Frame(self, padding=10)
        bot.pack(fill="x")
        
        ctrl = ttk.Frame(bot)
        ctrl.pack(side="left")
        
        ttk.Label(ctrl, text="Metode:").grid(row=0, column=0, sticky="w")
        self.cb_method = ttk.Combobox(ctrl, state="readonly", width=22, values=[
            "CLAHE (Retakan/Detail)", "Sharpen (Tajamkan)", "Contrast (Ubah Kontras)",
            "Saturation (Ubah Warna)", "Brightness (Ubah Cahaya)", "Grayscale (Hitam Putih)"
        ])
        self.cb_method.current(0)
        self.cb_method.grid(row=0, column=1, padx=5)
        self.cb_method.bind("<<ComboboxSelected>>", lambda e: self.update_preview())
        
        ttk.Label(ctrl, text="Intensitas:").grid(row=0, column=2, padx=(10, 0))
        self.v_slider = tk.DoubleVar(value=1.0)
        self.slider = ttk.Scale(ctrl, from_=0.1, to=3.0, variable=self.v_slider, command=lambda e: self.update_preview())
        self.slider.grid(row=0, column=3, padx=5)
        
        act = ttk.Frame(bot)
        act.pack(side="right")
        
        ttk.Button(act, text="Skip ⏭", command=lambda: self.load_image(self.idx+1)).pack(side="left", padx=5)
        
        # ✨ TOMBOL BATCH PROCESS (PROSES SEMUA)
        self.btn_batch = ttk.Button(act, text="📦 Batch Proses Semua Asli", command=self.batch_process)
        self.btn_batch.pack(side="left", padx=5)

        ttk.Button(act, text="➕ Simpan Duplikat", command=lambda: self.save(duplicate=True)).pack(side="left", padx=5)
        ttk.Button(act, text="💾 Timpa Asli", command=lambda: self.save(duplicate=False)).pack(side="left", padx=5)

    def load_image(self, idx=None):
        if idx is not None:
            if idx < 0 or idx >= len(self.items): return
            self.idx = idx
            
        p = self.items[self.idx]
        self.pil_asli = Image.open(p).convert("RGB")
        
        if HAS_CV and HAS_NP:
            self.cv_asli = cv2.cvtColor(np.array(self.pil_asli), cv2.COLOR_RGB2BGR)
        
        self.lbl_info.config(text=f"[{self.idx+1}/{len(self.items)}] {p.name}")
        
        self.update_preview()
        self._draw_canvas(self.canvas_asli, self.pil_asli)

    def _apply_method(self, img_cv, method, val):
        """Fungsi terpusat untuk menerapkan filter OpenCV."""
        import cv2
        import numpy as np
        img = img_cv.copy()
        
        if method == "CLAHE (Retakan/Detail)":
            clip = max(1.0, val * 2.0)
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8,8))
            cl = clahe.apply(l)
            img = cv2.cvtColor(cv2.merge((cl,a,b)), cv2.COLOR_LAB2BGR)
            
        elif method == "Sharpen (Tajamkan)":
            amount = val
            kernel = np.array([[0, -1, 0], [-1, 1 + 4*amount, -1], [0, -1, 0]])
            img = cv2.filter2D(img, -1, kernel)
            
        elif method == "Contrast (Ubah Kontras)":
            img = cv2.convertScaleAbs(img, alpha=val, beta=0)
            
        elif method == "Saturation (Ubah Warna)":
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype("float32")
            hsv[:,:,1] = hsv[:,:,1] * val
            hsv[:,:,1] = np.clip(hsv[:,:,1], 0, 255)
            img = cv2.cvtColor(hsv.astype("uint8"), cv2.COLOR_HSV2BGR)
            
        elif method == "Brightness (Ubah Cahaya)":
            beta = int((val - 1.0) * 100)
            img = cv2.convertScaleAbs(img, alpha=1.0, beta=beta)
            
        elif method == "Grayscale (Hitam Putih)":
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            
        return img

    def update_preview(self):
        if self.cv_asli is None: return
        method = self.cb_method.get()
        val = self.v_slider.get()
        
        try:
            img_result = self._apply_method(self.cv_asli, method, val)
            self.pil_hasil = Image.fromarray(cv2.cvtColor(img_result, cv2.COLOR_BGR2RGB))
            self._draw_canvas(self.canvas_hasil, self.pil_hasil)
        except: pass

    def _draw_canvas(self, canvas, pil_img):
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        if cw < 20 or ch < 20:
            self.after(100, lambda: self._draw_canvas(canvas, pil_img))
            return
        W, H = pil_img.size
        s = min(cw/W, ch/H)
        nw, nh = max(1, int(W*s)), max(1, int(H*s))
        
        tk_img = ImageTk.PhotoImage(pil_img.resize((nw, nh)))
        canvas.delete("all")
        canvas.create_image(cw//2, ch//2, anchor="center", image=tk_img)
        canvas._img = tk_img

    def _get_method_tag(self):
        """Mengambil nama metode saja untuk dijadikan nama file.
        Contoh: 'CLAHE (Retakan/Detail)' -> 'clahe'
        """
        raw = self.cb_method.get()
        # Ambil kata pertama, jadikan huruf kecil
        tag = raw.split(" (")[0].lower().replace(" ", "")
        return tag
    
    def save(self, duplicate=True):
        if self.pil_hasil is None: return
        p = self.items[self.idx]
        
        if duplicate:
            method_tag = self._get_method_tag()
            # Format: nama_aug_metode_tanggal.jpg
            new_p = p.parent / f"{p.stem}_aug_{method_tag}_{now_tag()}.jpg"
            self.pil_hasil.save(new_p)
            
            lbl = self.labels_dir / (p.stem + ".txt")
            if lbl.exists():
                shutil.copy2(lbl, self.labels_dir / (new_p.stem + ".txt"))
            
            messagebox.showinfo("Sukses", f"Disimpan: {new_p.name}")
        else:
            self.pil_hasil.save(p)
            messagebox.showinfo("Sukses", "Gambar asli ditimpa.")
        
        self.load_image(self.idx)

    # ✨ FITUR BARU: BATCH PROCESS
    def batch_process(self):
        method = self.cb_method.get()
        val = self.v_slider.get()
        
        # Hanya ambil gambar asli (yang tidak mengandung _aug_)
        originals = [p for p in self.items if "_aug_" not in p.stem]
        
        if not originals:
            messagebox.showinfo("Info", "Tidak ada gambar asli (tanpa _aug_) untuk diproses.")
            return
            
        confirm = messagebox.askyesno(
            "Batch Processing", 
            f"Proses {len(originals)} gambar asli dengan {method}?\n\n"
            "Hasil akan disimpan sebagai gambar baru (berakhiran _aug_).\n"
            "Label YOLO (.txt) akan otomatis diduplikasi."
        )
        if not confirm: return
        
        self.btn_batch.config(state="disabled", text="Memproses...")
        
        def worker():
            count = 0
            total = len(originals)
            
            for p in originals:
                try:
                    # Load gambar
                    pil_img = Image.open(p).convert("RGB")
                    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                    
                    # Proses
                    res_cv = self._apply_method(cv_img, method, val)
                    res_pil = Image.fromarray(cv2.cvtColor(res_cv, cv2.COLOR_BGR2RGB))
                    
                    # Simpan
                    method_tag = self._get_method_tag()
                    new_p = p.parent / f"{p.stem}_aug_{method_tag}_{now_tag()}.jpg"
                    res_pil.save(new_p)
                    
                    # Copy Label
                    lbl = self.labels_dir / (p.stem + ".txt")
                    if lbl.exists():
                        shutil.copy2(lbl, self.labels_dir / (new_p.stem + ".txt"))
                    
                    count += 1
                    self.after(0, lambda c=count, t=total: self.lbl_info.config(text=f"Memproses {c}/{t}..."))
                except Exception as e:
                    print(f"Error pada {p.name}: {e}")
                    
            self.after(0, lambda: self._on_batch_done(count))
            
        threading.Thread(target=worker, daemon=True).start()

    def _on_batch_done(self, count):
        self.btn_batch.config(state="normal", text="📦 Batch Proses Semua Asli")
        messagebox.showinfo("Selesai", f"Berhasil membuat {count} gambar variasi baru.")
        
        # Refresh list gambar
        frames_dir = self.project.root / "01_raw" / "frames"
        self.items = sorted([p for p in frames_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS])
        self.load_image(0)
        if self.on_close: self.on_close()
# ============================================================
#  Tab 3: Anotator
# ============================================================
class AnnotatorWindow(tk.Toplevel):
    def __init__(self, master, project: Project, on_close=None):
        super().__init__(master)
        self.project = project
        self.classes = project.data["classes"]
        self.on_close = on_close

        if not self.classes:
            messagebox.showwarning("Kelas kosong", "Isi kelas di tab 1 dulu.")
            self.destroy(); return

        self.title("Anotator — YOLO Studio")
        self.geometry("1280x860")
        self.minsize(1000, 680)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        frames_dir = project.root / "01_raw" / "frames"
        self.items = []
        if frames_dir.exists():
            for p in sorted(frames_dir.iterdir()):
                if p.suffix.lower() in IMAGE_EXTS: self.items.append(p)
        if not self.items:
            messagebox.showwarning("Kosong", "Belum ada gambar di 01_raw/frames.")
            self.destroy(); return

        self.labels_dir = project.root / "01_raw" / "labels"
        self.labels_dir.mkdir(parents=True, exist_ok=True)

        self.idx = self._restore_position()
        self.boxes = []
        self.suggested_boxes = []
        self.start_pt = None
        self.rect_id = None
        self.pil_img = None
        self.tk_img = None
        self.scale = 1.0
        self.offset = (0, 0)

        self.yolo_model = None
        self.suggest_model_name = "yolov8n.pt"
        self.suggest_conf = 0.35
        self._suggesting = False

        # --- Variabel untuk Fitur Magnet Mode ---
        self.magnet_mode = False
        self.magnet_candidates = []  # List of dicts {cls, x1, y1, x2, y2, conf}
        self.hovered_candidate_idx = -1

        self._build()
        self.load(self.idx)
        self._refresh_progress()

    def _restore_position(self) -> int:
        ann = self.project.data.get("annotation", {})
        name = ann.get("last_filename", "")
        if name:
            for i, p in enumerate(self.items):
                if p.name == name: return i
        return min(ann.get("last_idx", 0), len(self.items) - 1)

    def _save_position(self):
        self.project.data["annotation"] = {"last_idx": self.idx, "last_filename": self.items[self.idx].name}
        self.project.save()

    def _build(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        ttk.Button(top, text="◀ Prev (B)", command=lambda: self.load(self.idx-1)).pack(side="left")
        ttk.Button(top, text="Next (Space) ▶", command=self.save_next).pack(side="left", padx=4)
        
        ttk.Label(top, text="  Kelas:").pack(side="left", padx=(12, 4))
        self.cb_cls = ttk.Combobox(top, values=self.classes, state="readonly", width=18)
        self.cb_cls.current(0)
        self.cb_cls.pack(side="left")
        self.cb_cls.bind("<<ComboboxSelected>>", lambda e: self._update_active_label())
        
        ttk.Button(top, text="↶ Undo (D)", command=self.undo).pack(side="left", padx=(8, 2))
        ttk.Button(top, text="🗑 Clear (C)", command=self.clear).pack(side="left", padx=2)
        ttk.Button(top, text="💾 Simpan", command=self.save_labels).pack(side="left", padx=8)
        
        # Tombol Auto-Suggest Biasa
        ttk.Button(top, text="🤖 Auto-Suggest", command=self.auto_suggest).pack(side="left", padx=8)
        
        # --- Tombol Magnet Mode & Auto-Trim ---
        ttk.Button(top, text="🧲 Magnet Mode (G)", command=self.toggle_magnet).pack(side="left", padx=2)
        ttk.Button(top, text="🗑 Hapus Gambar", command=self.delete_current_image).pack(side="left", padx=2)

        ttk.Label(top, text=" ✂️ Auto-Trim:").pack(side="left", padx=(8, 2))
        self.cb_trim = ttk.Combobox(top, state="readonly", width=20, values=[
            "GrabCut (Detail/Umum)", "Contour (Kontras Tinggi)", "Adaptive Thr. (Gelap/Terang)"
        ])
        self.cb_trim.current(0)
        self.cb_trim.pack(side="left")
        ttk.Button(top, text="Terapkan (T)", command=self.auto_trim_box).pack(side="left", padx=2)

        self.lbl_active_cls = tk.Label(top, text="", font=("Segoe UI", 10, "bold"), fg="#000", bg="#ccc", padx=8, pady=2)
        self.lbl_active_cls.pack(side="right", padx=8)

        sbar = ttk.Frame(self, padding=(6, 0))
        sbar.pack(fill="x")
        self.lbl_suggest = ttk.Label(sbar, text="Auto-suggest idle.", font=("Consolas", 9), foreground=tc("fg_muted"))
        self.lbl_suggest.pack(side="left")
        ttk.Label(sbar, text="  [Enter] terima usulan  •  [Esc] tolak  •  [klik kanan] terima 1 kotak", font=("Consolas", 8), foreground=tc("fg_muted")).pack(side="left", padx=8)

        self.status = ttk.Label(self, text="", padding=4, font=("Consolas", 9))
        self.status.pack(fill="x")

        hint = ("[1-9] kelas  •  [Space] lanjut  •  [B] prev  •  [N] next  •  [D] undo  •  [C] clear  •  "
                "[Ctrl+S] simpan  •  [Ctrl+A] auto-suggest  •  [G] Magnet Mode  •  [T] auto-trim")
        ttk.Label(self, text=hint, foreground=tc("fg_muted"), font=("Consolas", 8)).pack(fill="x", padx=6)

        self.canvas = tk.Canvas(self, bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_mouse_move) # Fitur Hover Magnet
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<Key>", self._on_key)
        self.canvas.focus_set()

        legend_outer = ttk.Frame(self, padding=(6, 2))
        legend_outer.pack(fill="x")
        ttk.Label(legend_outer, text="Kelas:", font=("Segoe UI", 8, "bold")).pack(side="left", padx=(0, 6))
        for i, cname in enumerate(self.classes):
            color = class_color(i)
            swatch = tk.Label(legend_outer, text=f" {i+1}. {cname} ", bg=color, fg="#000", font=("Consolas", 8, "bold"), padx=4, pady=1)
            swatch.pack(side="left", padx=2)

        bottom = ttk.Frame(self, padding=6)
        bottom.pack(fill="x")
        self.prog = ttk.Progressbar(bottom, mode="determinate")
        self.prog.pack(fill="x", side="left", expand=True, padx=(0, 8))
        self.lbl_prog = ttk.Label(bottom, text="", font=("Consolas", 9))
        self.lbl_prog.pack(side="left")

        self.bind("<Left>", lambda e: self.load(self.idx-1))
        self.bind("<Right>", lambda e: self.load(self.idx+1))
        self._update_active_label()

    def _update_active_label(self):
        i = self.cb_cls.current()
        if 0 <= i < len(self.classes):
            c = class_color(i)
            r = int(c[1:3], 16); g = int(c[3:5], 16); b = int(c[5:7], 16)
            lum = (0.299*r + 0.587*g + 0.114*b) / 255
            fg = "#000" if lum > 0.55 else "#fff"
            self.lbl_active_cls.config(text=f"● Aktif: [{i+1}] {self.classes[i]}", bg=c, fg=fg)

    def _on_key(self, event):
        key = event.keysym
        ctrl = bool(event.state & 0x4)
        lower = key.lower()

        if ctrl:
            if lower == "a": self.auto_suggest(); return "break"
            if lower == "s": self.save_labels(); return "break"
            return None

        if key == "Return":
            if self.suggested_boxes: self.accept_all_suggestions()
            else: self.save_next()
            return "break"
        if key == "Escape":
            if self.suggested_boxes: self.reject_all_suggestions()
            elif self.magnet_mode: self.toggle_magnet(False)
            return "break"
        if key == "space": self.save_next(); return "break"
        if key == "Delete": self.undo(); return "break"

        if len(key) == 1 and key in "1234567890":
            i = int(key) - 1
            if 0 <= i < len(self.classes):
                self.cb_cls.current(i)
                self._update_active_label()
            return "break"

        if lower == "b": self.load(self.idx - 1); return "break"
        if lower == "n": self.load(self.idx + 1); return "break"
        if lower == "d": self.undo(); return "break"
        if lower == "c": self.clear(); return "break"
        if lower == "p": self.open_preprocessing(); return "break"
        if lower == "t": self.auto_trim_box(); return "break"
        if lower == "g": self.toggle_magnet(); return "break"
        return None

    def _refresh_progress(self):
        total = len(self.items)
        done = sum(1 for p in self.items if (self.labels_dir / (p.stem + ".txt")).exists() and (self.labels_dir / (p.stem + ".txt")).stat().st_size > 0)
        pct = (done / total * 100) if total else 0
        self.prog["maximum"] = total
        self.prog["value"] = done
        self.lbl_prog.config(text=f"Anotasi: {done}/{total} ({pct:.1f}%)")

    def load(self, i):
        if i < 0 or i >= len(self.items): return
        if self.pil_img is not None and i != self.idx: self.save_labels(silent=True)
        self.idx = i
        p = self.items[i]
        self.pil_img = Image.open(p).convert("RGB")
        self.boxes = []
        self.suggested_boxes = []
        self.magnet_candidates = []
        self.hovered_candidate_idx = -1
        
        lbl = self.labels_dir / (p.stem + ".txt")
        if lbl.exists():
            W, H = self.pil_img.size
            for line in lbl.read_text().splitlines():
                parts = line.split()
                if len(parts) != 5: continue
                try:
                    c = int(parts[0]); xc, yc, w, h = map(float, parts[1:])
                except: continue
                self.boxes.append({"cls": c, "x1": (xc - w/2)*W, "y1": (yc - h/2)*H, "x2": (xc + w/2)*W, "y2": (yc + h/2)*H})
        
        self.lbl_suggest.config(text="Auto-suggest idle.", foreground=tc("fg_muted"))
        self.redraw()
        self._save_position()
        self._refresh_progress()
        self.canvas.focus_set()

    def redraw(self):
        if self.pil_img is None: return
        
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        # Tunggu sampai kanvas benar-benar punya ukuran
        if cw < 20 or ch < 20:
            self.after(100, self.redraw)
            return
            
        W, H = self.pil_img.size
        s = min(cw/W, ch/H)
        self.scale = s
        
        # ✨ KUNCI PERBAIKAN: Paksa ukuran minimal 1 piksel
        nw = max(1, int(W*s))
        nh = max(1, int(H*s))
        
        self.offset = ((cw-nw)//2, (ch-nh)//2)
        disp = self.pil_img.resize((nw, nh))
        draw = ImageDraw.Draw(disp)

        # Gambar Kandidat Magnet (Biru / Kuning)
        if self.magnet_mode:
            for idx, b in enumerate(self.magnet_candidates):
                x1, y1 = b["x1"]*s, b["y1"]*s; x2, y2 = b["x2"]*s, b["y2"]*s
                if idx == self.hovered_candidate_idx:
                    color = "#ffd400" # Kuning
                    width = 3
                else:
                    color = "#42d4f4" # Cyan
                    width = 1
                self._draw_dashed_rect(draw, (x1, y1, x2, y2), color, width=width)
                name = b.get("src", "obj")
                draw_label_tag(draw, x1, max(0, y1-16), f"{name} {b['conf']:.2f}", color)

        # Gambar Kotak Usulan Auto-Suggest
        for b in self.suggested_boxes:
            x1, y1 = b["x1"]*s, b["y1"]*s; x2, y2 = b["x2"]*s, b["y2"]*s
            self._draw_dashed_rect(draw, (x1, y1, x2, y2), "#ff9800", width=2)
            name = self.classes[b["cls"]] if 0 <= b["cls"] < len(self.classes) else str(b["cls"])
            draw_label_tag(draw, x1, y2 + 2, f"usul: {name} {b['conf']:.2f}", "#ff9800")

        # Gambar Kotak Final
        for b in self.boxes:
            x1, y1 = b["x1"]*s, b["y1"]*s; x2, y2 = b["x2"]*s, b["y2"]*s
            color = class_color(b["cls"])
            draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
            name = self.classes[b["cls"]] if 0 <= b["cls"] < len(self.classes) else str(b["cls"])
            ty = y1 - 16
            if ty < 0: ty = y1 + 2
            draw_label_tag(draw, x1, ty, name, color)

        self.tk_img = ImageTk.PhotoImage(disp)
        self.canvas.delete("all")
        self.canvas.create_image(self.offset[0], self.offset[1], anchor="nw", image=self.tk_img)
        
        p = self.items[self.idx]
        has_lbl = (self.labels_dir / (p.stem + ".txt")).exists()
        mark = "✓" if has_lbl and (self.labels_dir / (p.stem + ".txt")).stat().st_size > 0 else "○"
        extra = f"  •  {len(self.suggested_boxes)} usulan" if self.suggested_boxes else ""
        self.status.config(text=f"{mark} [{self.idx+1}/{len(self.items)}] {p.name}  |  {len(self.boxes)} objek{extra}  |  Kelas aktif: {self.classes[self.cb_cls.current()] if self.classes else '-'}")

    @staticmethod
    def _draw_dashed_rect(draw, xy, color, dash=6, gap=4, width=2):
        x1, y1, x2, y2 = xy
        x = x1
        while x < x2:
            xe = min(x + dash, x2)
            draw.line([(x, y1), (xe, y1)], fill=color, width=width)
            draw.line([(x, y2), (xe, y2)], fill=color, width=width)
            x += dash + gap
        y = y1
        while y < y2:
            ye = min(y + dash, y2)
            draw.line([(x1, y), (x1, ye)], fill=color, width=width)
            draw.line([(x2, y), (x2, ye)], fill=color, width=width)
            y += dash + gap

    # --- FITUR MAGNET MODE ---
    def toggle_magnet(self, force_state=None):
        if force_state is not None:
            self.magnet_mode = force_state
        else:
            self.magnet_mode = not self.magnet_mode

        if self.magnet_mode:
            self.lbl_suggest.config(text="🧲 Magnet Mode ON. Jalankan AI...", foreground=tc("warning"))
            self.canvas.config(cursor="crosshair")
            threading.Thread(target=self._run_magnet_ai, daemon=True).start()
        else:
            self.magnet_candidates = []
            self.hovered_candidate_idx = -1
            self.lbl_suggest.config(text="Magnet Mode OFF.", foreground=tc("fg_muted"))
            self.canvas.config(cursor="")
            self.redraw()

    def _run_magnet_ai(self):
        try:
            if self.yolo_model is None:
                from ultralytics import YOLO
                self.yolo_model = YOLO(self.suggest_model_name)
            
            # Deteksi semua objek tanpa filter kelas
            results = self.yolo_model(self.pil_img, conf=0.25, verbose=False)
            candidates = []
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    coco_name = r.names[cls_id]
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    candidates.append({
                        "cls": -1, # Belum ditentukan
                        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        "conf": float(box.conf[0]), "src": coco_name
                    })
            
            self.after(0, lambda: self._on_magnet_ready(candidates))
        except ImportError:
            self.after(0, lambda: self._on_suggest_error("ultralytics belum terinstall"))
            self.after(0, lambda: self.toggle_magnet(False))
        except Exception as e:
            self.after(0, lambda: self._on_suggest_error(str(e)))
            self.after(0, lambda: self.toggle_magnet(False))

    def _on_magnet_ready(self, candidates):
        self.magnet_candidates = candidates
        if not candidates:
            self.lbl_suggest.config(text="0 objek terdeteksi.", foreground=tc("danger"))
            self.toggle_magnet(False)
        else:
            self.lbl_suggest.config(text=f"✓ {len(candidates)} objek terdeteksi. Arahkan mouse & Klik untuk memilih.", foreground=tc("success"))
            self.redraw()

    def on_mouse_move(self, event):
        if not self.magnet_mode or not self.magnet_candidates: return
        
        x, y = self._to_img(event.x, event.y)
        new_hover = -1
        
        # Cari kandidat mana yang sedang di-hover (prioritaskan yang luasnya paling kecil)
        for i in sorted(range(len(self.magnet_candidates)), key=lambda k: (self.magnet_candidates[k]["x2"]-self.magnet_candidates[k]["x1"]) * (self.magnet_candidates[k]["y2"]-self.magnet_candidates[k]["y1"])):
            b = self.magnet_candidates[i]
            if b["x1"] <= x <= b["x2"] and b["y1"] <= y <= b["y2"]:
                new_hover = i
                break
                
        if new_hover != self.hovered_candidate_idx:
            self.hovered_candidate_idx = new_hover
            self.redraw()

    # --- AUTO SUGGEST BIASA ---
    def auto_suggest(self):
        if self._suggesting: return
        self._suggesting = True
        self.lbl_suggest.config(text="⏳ Mendeteksi objek dengan model COCO...", foreground=tc("warning"))
        threading.Thread(target=self._do_suggest, daemon=True).start()

    def _do_suggest(self):
        try:
            if self.yolo_model is None:
                from ultralytics import YOLO
                self.yolo_model = YOLO(self.suggest_model_name)
            results = self.yolo_model(self.pil_img, conf=self.suggest_conf, verbose=False)
            suggestions = []
            cls_lower = [c.lower() for c in self.classes]
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    coco_name = r.names[cls_id]
                    if coco_name.lower() in cls_lower:
                        pc = cls_lower.index(coco_name.lower())
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        suggestions.append({"cls": pc, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "conf": float(box.conf[0]), "src": coco_name})
            self.after(0, lambda: self._on_suggest_done(suggestions))
        except ImportError:
            self.after(0, lambda: self._on_suggest_error("ultralytics belum terinstall. Jalankan: pip install ultralytics"))
        except Exception as e:
            self.after(0, lambda: self._on_suggest_error(str(e)))

    def _on_suggest_done(self, suggestions):
        self._suggesting = False
        self.suggested_boxes = suggestions
        if not suggestions:
            self.lbl_suggest.config(text="0 usulan. Model COCO tidak menemukan objek yang cocok.", foreground=tc("danger"))
        else:
            self.lbl_suggest.config(text=f"✓ {len(suggestions)} usulan. Enter=terima semua, Esc=tolak, klik kanan=terima 1.", foreground=tc("warning"))
        self.redraw()

    def _on_suggest_error(self, msg):
        self._suggesting = False
        self.lbl_suggest.config(text=f"✗ {msg}", foreground=tc("danger"))

    def accept_all_suggestions(self):
        if not self.suggested_boxes: return
        for b in self.suggested_boxes:
            self.boxes.append({"cls": b["cls"], "x1": b["x1"], "y1": b["y1"], "x2": b["x2"], "y2": b["y2"]})
        n = len(self.suggested_boxes)
        self.suggested_boxes = []
        self.redraw()
        self.save_labels(silent=True)
        self._refresh_progress()
        self.lbl_suggest.config(text=f"✓ {n} usulan diterima.", foreground=tc("success"))

    def reject_all_suggestions(self):
        n = len(self.suggested_boxes)
        self.suggested_boxes = []
        self.redraw()
        self.lbl_suggest.config(text=f"✗ {n} usulan ditolak.", foreground=tc("fg_muted"))

    def on_right_click(self, e):
        if not self.suggested_boxes: return
        x, y = self._to_img(e.x, e.y)
        for i in sorted(range(len(self.suggested_boxes)), key=lambda k: (self.suggested_boxes[k]["x2"]-self.suggested_boxes[k]["x1"]) * (self.suggested_boxes[k]["y2"]-self.suggested_boxes[k]["y1"])):
            b = self.suggested_boxes[i]
            if b["x1"] <= x <= b["x2"] and b["y1"] <= y <= b["y2"]:
                self.boxes.append({"cls": b["cls"], "x1": b["x1"], "y1": b["y1"], "x2": b["x2"], "y2": b["y2"]})
                self.suggested_boxes.pop(i)
                self.redraw()
                self.save_labels(silent=True)
                self._refresh_progress()
                self.lbl_suggest.config(text=f"Sisa {len(self.suggested_boxes)} usulan.", foreground=tc("warning"))
                return

    def _to_img(self, cx, cy):
        return (cx - self.offset[0]) / self.scale, (cy - self.offset[1]) / self.scale

    def on_press(self, e):
        self.canvas.focus_set()
        self.start_pt = (e.x, e.y)

    def on_drag(self, e):
        if not self.start_pt: return
        if self.magnet_mode: return # Jika magnet mode, jangan gambar kotak manual
        if self.rect_id: self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(self.start_pt[0], self.start_pt[1], e.x, e.y, outline="#ffd400", width=2)

    def on_release(self, e):
        if not self.start_pt: return
        
        # LOGIKA KLIK MAGNET MODE
        if self.magnet_mode and self.hovered_candidate_idx != -1:
            b = self.magnet_candidates[self.hovered_candidate_idx]
            # Masukkan ke kotak final dengan kelas yang sedang aktif saat ini
            self.boxes.append({
                "cls": self.cb_cls.current(), 
                "x1": b["x1"], "y1": b["y1"], "x2": b["x2"], "y2": b["y2"]
            })
            # Hapus dari kandidat agar tidak dobel
            self.magnet_candidates.pop(self.hovered_candidate_idx)
            self.hovered_candidate_idx = -1
            self.redraw()
            self.save_labels(silent=True)
            self._refresh_progress()
            self.lbl_suggest.config(text="✓ Objek dikotaki via Magnet Mode.", foreground=tc("success"))
            self.start_pt = None
            return

        # LOGIKA GAMBAR MANUAL BIASA
        if self.magnet_mode: 
            self.start_pt = None
            return

        x1, y1 = self._to_img(*self.start_pt)
        x2, y2 = self._to_img(e.x, e.y)
        self.start_pt = None
        if self.rect_id: self.canvas.delete(self.rect_id); self.rect_id = None
        W, H = self.pil_img.size
        x1 = max(0, min(W, x1)); x2 = max(0, min(W, x2))
        y1 = max(0, min(H, y1)); y2 = max(0, min(H, y2))
        if abs(x2-x1) < 5 or abs(y2-y1) < 5: return
        self.boxes.append({"cls": self.cb_cls.current(), "x1": min(x1, x2), "y1": min(y1, y2), "x2": max(x1, x2), "y2": max(y1, y2)})
        self.redraw()
        self.save_labels(silent=True)
        self._refresh_progress()

    def undo(self):
        if self.boxes:
            self.boxes.pop()
            self.redraw()
            self.save_labels(silent=True)
            self._refresh_progress()
        elif self.suggested_boxes:
            self.suggested_boxes.pop()
            self.redraw()

    def clear(self):
        if (self.boxes or self.suggested_boxes) and messagebox.askyesno("Konfirmasi", "Hapus semua kotak (final & usulan)?"):
            self.boxes = []
            self.suggested_boxes = []
            self.redraw()
            self.save_labels(silent=True)
            self._refresh_progress()

    def save_labels(self, silent=False):
        if not self.items: return
        p = self.items[self.idx]
        W, H = self.pil_img.size
        lbl = self.labels_dir / (p.stem + ".txt")
        if not self.boxes:
            lbl.write_text("", encoding="utf-8")
        else:
            lines = []
            for b in self.boxes:
                xc = ((b["x1"]+b["x2"])/2) / W
                yc = ((b["y1"]+b["y2"])/2) / H
                w  = (b["x2"]-b["x1"]) / W
                h  = (b["y2"]-b["y1"]) / H
                lines.append(f"{b['cls']} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")
            lbl.write_text("\n".join(lines), encoding="utf-8")
        self._save_position()
        if not silent: messagebox.showinfo("Tersimpan", f"Label disimpan: {lbl.name} ({len(self.boxes)} objek)")

    def save_next(self):
        self.save_labels(silent=True)
        if self.idx < len(self.items) - 1: self.load(self.idx + 1)
        else: messagebox.showinfo("Selesai", "Semua gambar sudah dikunjungi.")

    def _on_close(self):
        self.save_labels(silent=True)
        self._save_position()
        if self.on_close: self.on_close()
        self.destroy()

    # --- FITUR BARU v1.2.0 ---
    def open_preprocessing(self):
        if not self.items: return
        self.save_labels(silent=True)
        # Panggil dengan parameter yang baru
        win = PreprocessingWindow(self, self.project)
        self.wait_window(win)
        # Reload karena mungkin ada file augmentasi baru
        self.load(self.idx)

    def delete_current_image(self):
        if not self.items: return
        p = self.items[self.idx]
        if not messagebox.askyesno("Hapus", f"Hapus permanen {p.name} beserta labelnya?"): return
        p.unlink(missing_ok=True)
        lbl = self.labels_dir / (p.stem + ".txt")
        lbl.unlink(missing_ok=True)
        self.items.pop(self.idx)
        if not self.items:
            messagebox.showinfo("Selesai", "Semua gambar telah dihapus.")
            self._on_close()
            return
        if self.idx >= len(self.items): self.idx = len(self.items) - 1
        self.load(self.idx)

    def auto_trim_box(self):
        if not self.boxes:
            messagebox.showwarning("Kosong", "Gambar kotak kasar dulu, lalu klik Auto-Trim.")
            return
        try:
            import numpy as np
            import cv2
        except ImportError:
            messagebox.showerror("Error", "Fitur ini butuh numpy dan opencv-python.")
            return

        b = self.boxes[-1]
        img_cv = cv2.cvtColor(np.array(self.pil_img), cv2.COLOR_RGB2BGR)
        h_img, w_img = img_cv.shape[:2]
        pad = 10
        x1 = max(0, int(b["x1"]) - pad); y1 = max(0, int(b["y1"]) - pad)
        x2 = min(w_img, int(b["x2"]) + pad); y2 = min(h_img, int(b["y2"]) + pad)
        roi = img_cv[y1:y2, x1:x2]
        if roi.size == 0: return

        metode = self.cb_trim.get()
        new_x1, new_y1, new_x2, new_y2 = b["x1"], b["y1"], b["x2"], b["y2"]

        try:
            if metode == "GrabCut (Detail/Umum)":
                mask = np.zeros(roi.shape[:2], np.uint8)
                bgdModel = np.zeros((1,65), np.float64)
                fgdModel = np.zeros((1,65), np.float64)
                rect = (2, 2, roi.shape[1]-4, roi.shape[0]-4)
                cv2.grabCut(roi, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
                mask2 = np.where((mask==2)|(mask==0), 0, 1).astype('uint8')
                y_coords, x_coords = np.where(mask2 == 1)
                if len(x_coords) > 0 and len(y_coords) > 0:
                    new_x1 = x1 + x_coords.min(); new_x2 = x1 + x_coords.max()
                    new_y1 = y1 + y_coords.min(); new_y2 = y1 + y_coords.max()

            elif metode == "Contour (Kontras Tinggi)":
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                blur = cv2.GaussianBlur(gray, (5,5), 0)
                edges = cv2.Canny(blur, 50, 150)
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    c = max(contours, key=cv2.contourArea)
                    bx, by, bw, bh = cv2.boundingRect(c)
                    new_x1 = x1 + bx; new_y1 = y1 + by
                    new_x2 = x1 + bx + bw; new_y2 = y1 + by + bh

            elif metode == "Adaptive Thr. (Gelap/Terang)":
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    c = max(contours, key=cv2.contourArea)
                    bx, by, bw, bh = cv2.boundingRect(c)
                    new_x1 = x1 + bx; new_y1 = y1 + by
                    new_x2 = x1 + bx + bw; new_y2 = y1 + by + bh

            b["x1"], b["y1"] = new_x1, new_y1
            b["x2"], b["y2"] = new_x2, new_y2
            
            self.redraw()
            self.save_labels(silent=True)
            self.lbl_suggest.config(text=f"✓ Kotak diperketat dengan {metode.split(' ')[0]}.", foreground=tc("success"))
        except Exception as e:
            messagebox.showerror("Auto-Trim Gagal", f"Error: {e}")

# ============================================================
#  Tab 3 UI: Anotasi
# ============================================================
class AnnotTab(ttk.Frame):
    def __init__(self, master, project: Project, app):
        super().__init__(master, padding=16)
        self.project = project
        self.app = app
        self._preview_ref = None
        self._build()

    def _build(self):
        ttk.Label(self, text="3. Anotasi Bounding Box", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 4))
        ttk.Label(self, text="Auto-save & resume otomatis. Shortcut angka untuk pilih kelas.", foreground=tc("fg_muted")).pack(anchor="w", pady=(0, 8))

        box = ttk.LabelFrame(self, text="Progress Timeline", padding=8)
        box.pack(fill="x", pady=4)
        self.prog = ttk.Progressbar(box, mode="determinate")
        self.prog.pack(fill="x")
        self.lbl_prog = ttk.Label(box, text="", font=("Segoe UI", 10))
        self.lbl_prog.pack(anchor="w", pady=(4, 0))
        self.lbl_resume = ttk.Label(box, text="", foreground=tc("fg_muted"))
        self.lbl_resume.pack(anchor="w")

        fbar = ttk.Frame(self); fbar.pack(fill="x", pady=(8, 4))
        ttk.Label(fbar, text="Filter:").pack(side="left", padx=(0, 4))
        self.cb_filter = ttk.Combobox(fbar, state="readonly", width=22, values=["Semua", "Sudah dianotasi", "Belum dianotasi", "Kosong (0 objek)", "Multi-objek (>=2)"])
        self.cb_filter.current(0)
        self.cb_filter.pack(side="left")
        self.cb_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Button(fbar, text="🖊 Buka Anotator", command=self.open_annot).pack(side="right", padx=4)
        ttk.Button(fbar, text="🔄 Refresh", command=self.refresh).pack(side="right", padx=4)
        ttk.Button(fbar, text="⏭ Lanjut dari terakhir", command=self.open_annot).pack(side="right", padx=4)
        ttk.Button(fbar, text="🛠 Preprocessing Studio", command=self.open_preprocessing).pack(side="right", padx=4)
        


        mid = ttk.Frame(self); mid.pack(fill="both", expand=True, pady=4)

        tv_frame = ttk.Frame(mid); tv_frame.pack(side="left", fill="both", expand=True)
        cols = ("status", "name", "objek")
        self.tree = ttk.Treeview(tv_frame, columns=cols, show="headings", height=12)
        self.tree.heading("status", text="✓"); self.tree.heading("name", text="File"); self.tree.heading("objek", text="Obj")
        self.tree.column("status", width=36, anchor="center"); self.tree.column("name", width=380, anchor="w"); self.tree.column("objek", width=48, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tv_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.tag_configure("done", foreground=tc("success"))
        self.tree.tag_configure("empty", foreground=tc("warning"))
        self.tree.tag_configure("todo", foreground=tc("fg_muted"))
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        pv = ttk.LabelFrame(mid, text="Preview", padding=6, width=280)
        pv.pack(side="right", fill="y", padx=(8, 0))
        pv.pack_propagate(False)
        self.lbl_preview = ttk.Label(pv, text="Pilih file untuk\nmelihat preview", anchor="center", justify="center")
        self.lbl_preview.pack(fill="both", expand=True)
        self.lbl_preview_info = ttk.Label(pv, text="", foreground=tc("fg_muted"), font=("Consolas", 8), justify="left")
        self.lbl_preview_info.pack(fill="x", pady=(4, 0))

        dist = ttk.LabelFrame(self, text="Distribusi Kelas (jumlah objek)", padding=6)
        dist.pack(fill="x", pady=(4, 6))
        self.cv_dist = tk.Canvas(dist, height=80, highlightthickness=0)
        self.cv_dist.pack(fill="x")
        self.lbl_dist_info = ttk.Label(dist, text="", foreground=tc("fg_muted"), font=("Consolas", 8))
        self.lbl_dist_info.pack(anchor="w", pady=(2, 0))

    def refresh(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        if not self.project.root:
            self.lbl_prog.config(text="Belum ada proyek."); self.lbl_resume.config(text=""); self.cv_dist.delete("all")
            return
        frames_dir = self.project.root / "01_raw" / "frames"
        labels_dir = self.project.root / "01_raw" / "labels"
        if not frames_dir.exists():
            self.lbl_prog.config(text="Belum ada gambar."); return

        imgs = sorted([p for p in frames_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS])
        total = len(imgs); done = 0; f = self.cb_filter.get()

        for p in imgs:
            lbl = labels_dir / (p.stem + ".txt")
            exists = lbl.exists(); n_obj = 0
            if exists and lbl.stat().st_size > 0:
                n_obj = len([l for l in lbl.read_text().splitlines() if l.strip()])
            is_done = exists and n_obj > 0
            if is_done: done += 1
            if f == "Sudah dianotasi" and not is_done: continue
            if f == "Belum dianotasi" and is_done: continue
            if f == "Kosong (0 objek)" and not (exists and n_obj == 0): continue
            if f == "Multi-objek (>=2)" and not (is_done and n_obj >= 2): continue

            if is_done: tag, mark = ("done",), "✓"
            elif exists: tag, mark = ("empty",), "○"
            else: tag, mark = ("todo",), "·"
            self.tree.insert("", "end", values=(mark, p.name, n_obj if exists else ""), tags=tag)

        pct = (done / total * 100) if total else 0
        self.prog["maximum"] = max(total, 1)
        self.prog["value"] = done
        self.lbl_prog.config(text=f"Total: {done}/{total} gambar dianotasi ({pct:.1f}%)")

        ann = self.project.data.get("annotation", {})
        if ann.get("last_filename"):
            self.lbl_resume.config(text=f"Posisi terakhir: {ann['last_filename']} (gambar ke-{ann.get('last_idx', 0)+1})")
        else: self.lbl_resume.config(text="Belum ada riwayat.")
        self._draw_class_distribution()

    def _draw_class_distribution(self):
        c = self.cv_dist; c.delete("all")
        if not self.project.root: return
        classes = self.project.data.get("classes", [])
        if not classes:
            c.create_text(10, 20, text="Belum ada kelas terdefinisi.", anchor="w", fill=tc("fg_muted"), font=("Consolas", 9))
            self.lbl_dist_info.config(text=""); return

        labels_dir = self.project.root / "01_raw" / "labels"
        counts = [0] * len(classes); total_obj = 0; img_with_obj = 0
        if labels_dir.exists():
            for lf in labels_dir.glob("*.txt"):
                if not lf.stat().st_size: continue
                has = False
                for line in lf.read_text().splitlines():
                    if not line.strip(): continue
                    parts = line.split()
                    try: ci = int(parts[0])
                    except: continue
                    if 0 <= ci < len(counts):
                        counts[ci] += 1; total_obj += 1; has = True
                if has: img_with_obj += 1

        max_c = max(counts) if counts else 0
        if max_c == 0: max_c = 1

        c.update_idletasks(); W = c.winfo_width() or 700
        row_h = 22; pad_left = 140; bar_max_w = max(60, W - pad_left - 60)

        for i, name in enumerate(classes):
            y = 6 + i * row_h
            color = class_color(i)
            c.create_rectangle(8, y + 4, 20, y + 16, fill=color, outline="")
            c.create_text(24, y + 10, text=f"{i+1}. {name}", anchor="w", font=("Consolas", 9), fill=tc("text_fg"))
            w = int(bar_max_w * counts[i] / max_c)
            bar_color = color if counts[i] > 0 else tc("border")
            c.create_rectangle(pad_left, y + 4, pad_left + max(1, w), y + 16, fill=bar_color, outline="")
            c.create_text(pad_left + w + 4, y + 10, text=str(counts[i]), anchor="w", font=("Consolas", 9), fill=tc("text_fg"))

        c.config(height=6 + max(1, len(classes)) * row_h + 8)
        warn = ""
        if counts and max(counts) > 0 and min(counts) == 0: warn = "  ⚠  Ada kelas tanpa objek sama sekali."
        elif counts and max(counts) >= 5 * max(1, min(counts)): warn = "  ⚠  Distribusi tidak seimbang (imbalance)."
        self.lbl_dist_info.config(text=f"Total objek: {total_obj}  •  Gambar berisi objek: {img_with_obj}  •  Kelas: {len(classes)}{warn}")

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        item = self.tree.item(sel[0])
        fname = item["values"][1]
        p = self.project.root / "01_raw" / "frames" / fname
        if not p.exists(): return
        try:
            img = Image.open(p).convert("RGB")
            lbl = self.project.root / "01_raw" / "labels" / (p.stem + ".txt")
            if lbl.exists() and lbl.stat().st_size > 0:
                draw = ImageDraw.Draw(img); W, H = img.size
                for line in lbl.read_text().splitlines():
                    parts = line.split()
                    if len(parts) < 5: continue
                    try: ci = int(parts[0]); xc, yc, w, h = map(float, parts[1:])
                    except: continue
                    x1 = (xc - w/2)*W; y1 = (yc - h/2)*H; x2 = (xc + w/2)*W; y2 = (yc + h/2)*H
                    color = class_color(ci)
                    draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
                    cn = self.project.data["classes"][ci] if 0 <= ci < len(self.project.data["classes"]) else str(ci)
                    draw_label_tag(draw, x1, max(0, y1 - 14), cn, color)
            img.thumbnail((260, 220))
            self._preview_ref = ImageTk.PhotoImage(img)
            self.lbl_preview.config(image=self._preview_ref, text="")
            n_obj = 0
            if lbl.exists() and lbl.stat().st_size > 0: n_obj = len([l for l in lbl.read_text().splitlines() if l.strip()])
            info = f"{fname}\n{n_obj} objek"
            if n_obj > 0:
                detail = {}
                for line in lbl.read_text().splitlines():
                    parts = line.split()
                    if not parts: continue
                    try:
                        ci = int(parts[0]); cn = self.project.data["classes"][ci] if 0 <= ci < len(self.project.data["classes"]) else str(ci)
                        detail[cn] = detail.get(cn, 0) + 1
                    except: pass
                for cn, k in detail.items(): info += f"\n  • {cn}: {k}"
            self.lbl_preview_info.config(text=info)
        except Exception as e:
            self.lbl_preview.config(image="", text=f"Gagal memuat:\n{e}")

    def open_annot(self):
        if not self.project.root:
            messagebox.showwarning("Belum ada proyek", "Buat proyek dulu."); return
        if not HAS_PIL:
            messagebox.showerror("Pillow tidak ada", "pip install pillow"); return
        AnnotatorWindow(self, self.project, on_close=self.refresh)

    def open_preprocessing(self):
        if not self.project.root:
            messagebox.showwarning("Belum ada proyek", "Buat proyek dulu.")
            return
        if not HAS_CV or not HAS_NP:
            messagebox.showerror("Error", "Fitur ini butuh opencv-python dan numpy.")
            return
        # Buka jendela, dan refresh Tab 3 saat ditutup
        win = PreprocessingWindow(self, self.project, on_close=self.refresh)
        self.wait_window(win)
# ============================================================
#  Tab 4: Split
# ============================================================
class SplitTab(ttk.Frame):
    def __init__(self, master, project: Project, app):
        super().__init__(master, padding=16)
        self.project = project
        self.app = app
        self._build()

    def _build(self):
        ttk.Label(self, text="4. Split Dataset", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 4))
        ttk.Label(self, text="Bagi gambar yang sudah dianotasi ke Train / Val / Test.", foreground=tc("fg_muted")).pack(anchor="w", pady=(0, 12))

        info = ttk.LabelFrame(self, text="Data Tersedia", padding=10); info.pack(fill="x", pady=6)
        self.lbl_total = ttk.Label(info, text="...", font=("Segoe UI", 11, "bold")); self.lbl_total.pack(anchor="w")
        self.lbl_warn = ttk.Label(info, text="", foreground=tc("danger")); self.lbl_warn.pack(anchor="w")

        preset_frame = ttk.Frame(self); preset_frame.pack(fill="x", pady=6)
        ttk.Label(preset_frame, text="Preset cepat:").pack(side="left")
        for label, t, v, te in [("70/20/10", 70, 20, 10), ("80/10/10", 80, 10, 10), ("80/15/5", 80, 15, 5), ("60/20/20", 60, 20, 20)]:
            ttk.Button(preset_frame, text=label, command=lambda a=t, b=v, c=te: self._set_preset(a, b, c)).pack(side="left", padx=3)

        num = ttk.LabelFrame(self, text="Rasio Split (%)", padding=10); num.pack(fill="x", pady=6)
        self.vars = {}
        for i, (label, key) in enumerate([("Train", "train"), ("Val", "val"), ("Test", "test")]):
            ttk.Label(num, text=label, width=6).grid(row=i, column=0, sticky="w", padx=4, pady=3)
            var = tk.IntVar(value=self.project.data["split"].get(key, 0))
            self.vars[key] = var
            e = ttk.Entry(num, textvariable=var, width=8, font=("Consolas", 10))
            e.grid(row=i, column=1, sticky="w", pady=3)
            e.bind("<KeyRelease>", lambda ev: self._update_count())
            lbl = ttk.Label(num, text="", foreground=tc("fg_muted")); lbl.grid(row=i, column=2, sticky="w", padx=10)
            self.vars[key + "_lbl"] = lbl

        self.lbl_sum = ttk.Label(num, text="", font=("Segoe UI", 10, "bold")); self.lbl_sum.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 2))
        ttk.Label(num, text="Random seed:").grid(row=4, column=0, sticky="w", padx=4, pady=3)
        self.v_seed = tk.IntVar(value=self.project.data["split"].get("seed", 42))
        ttk.Entry(num, textvariable=self.v_seed, width=8, font=("Consolas", 10)).grid(row=4, column=1, sticky="w", pady=3)

        act = ttk.Frame(self); act.pack(fill="x", pady=12)
        ttk.Button(act, text="🎲 Jalankan Split", command=self.run_split).pack(side="left", padx=4)
        ttk.Button(act, text="💾 Simpan Rasio", command=self.save_ratio).pack(side="left", padx=4)
        ttk.Button(act, text="🔄 Refresh Data", command=self.refresh).pack(side="left", padx=4)

        self.info = tk.Text(self, height=12, width=100, state="disabled", relief="sunken", font=("Consolas", 9))
        self.info.pack(fill="x", pady=6)
        self.refresh()

    def _log(self, m):
        self.info.configure(state="normal"); self.info.insert("end", m + "\n"); self.info.see("end"); self.info.configure(state="disabled")

    def _annotated_pairs(self):
        frames = self.project.root / "01_raw" / "frames"
        labels = self.project.root / "01_raw" / "labels"
        pairs = []
        if frames.exists():
            for img in sorted(frames.iterdir()):
                if img.suffix.lower() not in IMAGE_EXTS: continue
                lbl = labels / (img.stem + ".txt")
                if lbl.exists() and lbl.stat().st_size > 0: pairs.append((img, lbl))
        return pairs

    def refresh(self):
        if not self.project.root: self.lbl_total.config(text="Belum ada proyek."); return
        pairs = self._annotated_pairs(); total = len(pairs)
        frames_dir = self.project.root / "01_raw" / "frames"
        all_img = sum(1 for p in frames_dir.glob("*") if p.suffix.lower() in IMAGE_EXTS) if frames_dir.exists() else 0
        self.lbl_total.config(text=f"Total citra teranotasi: {total}  (dari {all_img} citra terkumpul)")
        if total < 10: self.lbl_warn.config(text="⚠  Disarankan minimal 10 citra teranotasi untuk split yang wajar.")
        else: self.lbl_warn.config(text="")
        self._update_count(total)

    def _set_preset(self, t, v, te):
        self.vars["train"].set(t); self.vars["val"].set(v); self.vars["test"].set(te); self._update_count()

    def _update_count(self, total=None):
        if total is None: total = len(self._annotated_pairs()) if self.project.root else 0
        try: t = self.vars["train"].get(); v = self.vars["val"].get(); te = self.vars["test"].get()
        except: return
        s = t + v + te
        self.vars["train_lbl"].config(text=f"= {int(total * t / 100) if s else 0} gambar")
        self.vars["val_lbl"].config(text=f"= {int(total * v / 100) if s else 0} gambar")
        self.vars["test_lbl"].config(text=f"= {int(total * te / 100) if s else 0} gambar")
        mark = "✓" if s == 100 else "✗"
        color = tc("success") if s == 100 else tc("danger")
        self.lbl_sum.config(text=f"Total: {s}%  {mark}  ({total} citra)", foreground=color)

    def save_ratio(self):
        if not self.project.root: return
        try: t = self.vars["train"].get(); v = self.vars["val"].get(); te = self.vars["test"].get(); seed = self.v_seed.get()
        except: return
        self.project.data["split"] = {"train": t, "val": v, "test": te, "seed": seed}
        self.project.save()
        self._log(f"✓ Rasio disimpan: {t}/{v}/{te} (seed={seed})")

    def run_split(self):
        if not self.project.root: messagebox.showwarning("Belum ada proyek", "Buat proyek dulu."); return
        try: t = self.vars["train"].get(); v = self.vars["val"].get(); te = self.vars["test"].get(); seed = self.v_seed.get()
        except: return
        s = t + v + te
        if s != 100: messagebox.showwarning("Total salah", f"Total persen harus 100. Sekarang {s}."); return
        pairs = self._annotated_pairs()
        if not pairs: messagebox.showwarning("Kosong", "Belum ada gambar teranotasi."); return
        if len(pairs) < 5: messagebox.showwarning("Terlalu sedikit", "Minimal 5 gambar teranotasi untuk split."); return

        random.seed(seed); random.shuffle(pairs)
        n = len(pairs); n_t = int(n * t / 100); n_v = int(n * v / 100)
        splits = {"train": pairs[:n_t], "val": pairs[n_t:n_t+n_v], "test": pairs[n_t+n_v:]}

        for sp in ("train", "val", "test"):
            for sub in ("images", "labels"):
                d = self.project.root / "02_split" / sub / sp
                if d.exists():
                    for f in d.iterdir(): f.unlink()
                d.mkdir(parents=True, exist_ok=True)

        for sp, items in splits.items():
            idir = self.project.root / "02_split" / "images" / sp
            ldir = self.project.root / "02_split" / "labels" / sp
            for img, lbl in items:
                shutil.copy2(img, idir / img.name); shutil.copy2(lbl, ldir / lbl.name)

        self.save_ratio()
        self._log("=" * 50); self._log(f"✓ Split selesai ({n} citra teranotasi)")
        for sp, items in splits.items(): self._log(f"  {sp:5s}: {len(items):4d} citra")
        self.app.refresh_all()
        messagebox.showinfo("Sukses", f"Split selesai.\n{n} citra terbagi.")

# ============================================================
#  Tab 5: Export
# ============================================================
class ExportTab(ttk.Frame):
    def __init__(self, master, project: Project, app):
        super().__init__(master, padding=16)
        self.project = project
        self.app = app
        self._build()

    def _build(self):
        ttk.Label(self, text="5. Export & Upload ke Google Drive", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 4))
        ttk.Label(self, text="Siapkan folder + zip untuk di-upload ke Drive.", foreground=tc("fg_muted")).pack(anchor="w", pady=(0, 12))

        btns = ttk.Frame(self); btns.pack(anchor="w", pady=8)
        ttk.Button(btns, text="📦 Susun Folder Export + data.yaml", command=self.prepare_export).pack(side="left", padx=4)
        ttk.Button(btns, text="🗜  Buat ZIP", command=self.make_zip).pack(side="left", padx=4)
        ttk.Button(btns, text="📁 Buka Folder", command=self.open_folder).pack(side="left", padx=4)
        ttk.Button(btns, text="🧪 Validasi Label", command=self.validate).pack(side="left", padx=4)

        guide = ("Langkah upload ke Drive:\n  1. Klik 'Susun Folder Export + data.yaml'.\n  2. Klik 'Buat ZIP' (opsional).\n"
                 "  3. Buka drive.google.com → upload folder 04_export/yolo_dataset/.\n"
                 "     Letakkan di: MyDrive/yolo_projects/<nama_proyek>/yolo_dataset/\n  4. Lanjut ke tab 6 (Training).")
        box = tk.Text(self, height=8, width=95, relief="sunken", font=("Consolas", 9))
        box.insert("1.0", guide); box.configure(state="disabled"); box.pack(fill="x", pady=8)

        self.info = tk.Text(self, height=10, width=100, state="disabled", relief="sunken", font=("Consolas", 9))
        self.info.pack(fill="x")

    def _log(self, m):
        self.info.configure(state="normal"); self.info.insert("end", m + "\n"); self.info.see("end"); self.info.configure(state="disabled")

    def prepare_export(self):
        if not self.project.root: messagebox.showwarning("Belum ada proyek", "Buat proyek dulu."); return
        classes = self.project.data["classes"]
        if not classes: messagebox.showwarning("Kelas kosong", "Isi kelas di tab 1 dulu."); return
        dst = self.project.root / "04_export" / "yolo_dataset"
        if dst.exists():
            if not messagebox.askyesno("Timpa?", f"Folder {dst} sudah ada. Timpa?"): return
            shutil.rmtree(dst)
        dst.mkdir(parents=True)

        copied = 0
        for sp in ("train", "val", "test"):
            src_i = self.project.root / "02_split" / "images" / sp
            src_l = self.project.root / "02_split" / "labels" / sp
            dst_i = dst / sp / "images"; dst_i.mkdir(parents=True, exist_ok=True)
            dst_l = dst / sp / "labels"; dst_l.mkdir(parents=True, exist_ok=True)
            if src_i.exists():
                for img in src_i.glob("*"):
                    if img.suffix.lower() not in IMAGE_EXTS: continue
                    lbl = src_l / (img.stem + ".txt")
                    if lbl.exists():
                        shutil.copy2(img, dst_i / img.name); shutil.copy2(lbl, dst_l / lbl.name)
                        copied += 1

        proj = safe_name(self.project.data["name"])
        yaml = [f"path: /content/drive/MyDrive/yolo_projects/{proj}/yolo_dataset", "train: train/images", "val: val/images", "test: test/images", "", f"nc: {len(classes)}", "names:"] + [f"  - {c}" for c in classes]
        (dst / "data.yaml").write_text("\n".join(yaml), encoding="utf-8")
        self._log(f"✓ Folder export: {dst}"); self._log(f"✓ Citra disalin: {copied}"); self._log(f"✓ data.yaml: {len(classes)} kelas")

    def make_zip(self):
        if not self.project.root: return
        src = self.project.root / "04_export" / "yolo_dataset"
        if not src.exists(): messagebox.showwarning("Belum ada", "Klik 'Susun Folder Export' dulu."); return
        zip_path = self.project.root / "04_export" / "yolo_dataset.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in src.rglob("*"):
                if f.is_file(): z.write(f, f.relative_to(src.parent))
        size_mb = zip_path.stat().st_size / (1024*1024)
        self._log(f"✓ ZIP: {zip_path.name} ({size_mb:.1f} MB)")

    def open_folder(self):
        if not self.project.root: return
        p = self.project.root / "04_export"; p.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"): os.startfile(p)
        elif sys.platform == "darwin": os.system(f'open "{p}"')
        else: os.system(f'xdg-open "{p}"')

    def validate(self):
        if not self.project.root: return
        root = self.project.root / "02_split" / "labels"
        problems = []; total = 0
        for sp in ("train", "val", "test"):
            for lf in (root / sp).glob("*.txt"):
                total += 1
                for i, line in enumerate(lf.read_text().splitlines(), 1):
                    if not line.strip(): continue
                    parts = line.split()
                    if len(parts) != 5: problems.append(f"{sp}/{lf.name}:{i} field={len(parts)}"); continue
                    try:
                        cls = int(parts[0]); vals = list(map(float, parts[1:]))
                        if any(v < 0 or v > 1 for v in vals): problems.append(f"{sp}/{lf.name}:{i} koord luar [0,1]")
                        if cls < 0 or cls >= len(self.project.data["classes"]): problems.append(f"{sp}/{lf.name}:{i} kelas {cls} invalid")
                    except: problems.append(f"{sp}/{lf.name}:{i} format angka salah")
        self._log(f"Validasi: {total} file label.")
        if not problems: self._log("✓ Semua label valid.")
        else:
            self._log(f"✗ {len(problems)} masalah:")
            for p in problems[:30]: self._log("  - " + p)

# ============================================================
#  Tab 6: Training Colab
# ============================================================
class TrainTab(ttk.Frame):
    def __init__(self, master, project: Project, app):
        super().__init__(master, padding=16)
        self.project = project
        self.app = app
        self._build()

    def _build(self):
        ttk.Label(self, text="6. Training di Google Colab", font=("Segoe UI", 15, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ttk.Label(self, text="Generate notebook .ipynb sesuai versi YOLO yang dipilih.", foreground=tc("fg_muted")).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(self, text="Versi YOLO:").grid(row=2, column=0, sticky="w", pady=4)
        self.cb_ver = ttk.Combobox(self, values=list(YOLO_VERSIONS.keys()), state="readonly", width=20)
        self.cb_ver.grid(row=2, column=1, sticky="w", pady=4)
        self.cb_ver.bind("<<ComboboxSelected>>", self._on_ver)

        ttk.Label(self, text="Model dasar:").grid(row=3, column=0, sticky="w", pady=4)
        self.cb_model = ttk.Combobox(self, state="readonly", width=20)
        self.cb_model.grid(row=3, column=1, sticky="w", pady=4)

        self.vars = {}
        rows = [("Epochs", "epochs", None), ("Image size", "imgsz", [320, 416, 512, 640, 768, 1024]), ("Batch size", "batch", [4, 8, 16, 32, 64]), ("Patience", "patience", None), ("Optimizer", "optimizer", ["auto", "SGD", "Adam", "AdamW", "NAdam", "RAdam"])]
        r = 4
        for label, key, choices in rows:
            ttk.Label(self, text=label + ":").grid(row=r, column=0, sticky="w", pady=4)
            val = self.project.data["training"].get(key, 100)
            if choices:
                var = tk.StringVar(value=str(val))
                w = ttk.Combobox(self, textvariable=var, values=[str(c) for c in choices], state="readonly", width=18)
            else:
                var = tk.StringVar(value=str(val))
                w = ttk.Entry(self, textvariable=var, width=20)
            w.grid(row=r, column=1, sticky="w", pady=4)
            self.vars[key] = var
            r += 1

        btns = ttk.Frame(self); btns.grid(row=r, column=0, columnspan=3, sticky="w", pady=16)
        ttk.Button(btns, text="📓 Generate Notebook", command=self.gen_notebook).pack(side="left", padx=4)
        ttk.Button(btns, text="🌐 Buka Colab", command=lambda: webbrowser.open("https://colab.research.google.com/")).pack(side="left", padx=4)
        ttk.Button(btns, text="📁 Buka Folder Notebook", command=self.open_nb).pack(side="left", padx=4)

        r += 1
        guide = ("Cara menjalankan di Colab:\n  1. Generate Notebook → file .ipynb dibuat di folder 'notebooks/'.\n"
                 "  2. Buka colab.research.google.com → File → Upload notebook.\n  3. Runtime → Change runtime type → T4 GPU.\n"
                 "  4. Upload folder yolo_dataset/ ke Drive: MyDrive/yolo_projects/<nama>/\n  5. Jalankan cell satu per satu.\n"
                 "  6. Notebook otomatis download best.pt & train_results.zip di akhir.\n  7. Simpan best.pt ke folder '05_models/', lalu buka tab 7.")
        ttk.Label(self, text=guide, justify="left").grid(row=r, column=0, columnspan=3, sticky="w", pady=(0, 8))
        ttk.Label(self, text="Log:").grid(row=r+1, column=0, sticky="w")
        self.info = tk.Text(self, height=9, width=100, state="disabled", relief="sunken", font=("Consolas", 9))
        self.info.grid(row=r+2, column=0, columnspan=3, sticky="we")
        self.columnconfigure(1, weight=1)

        if self.project.data["yolo_version"] in YOLO_VERSIONS:
            self.cb_ver.set(self.project.data["yolo_version"])
            self._on_ver()
            if self.project.data["base_model"] in self.cb_model["values"]: self.cb_model.set(self.project.data["base_model"])

    def _on_ver(self, *_):
        v = self.cb_ver.get() or "YOLOv8"
        self.cb_model["values"] = YOLO_VERSIONS[v]["models"]
        self.cb_model.current(0)

    def _log(self, m):
        self.info.configure(state="normal"); self.info.insert("end", m + "\n"); self.info.see("end"); self.info.configure(state="disabled")

    def open_nb(self):
        if not self.project.root: return
        p = self.project.root / "notebooks"; p.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("win"): os.startfile(p)
        elif sys.platform == "darwin": os.system(f'open "{p}"')
        else: os.system(f'xdg-open "{p}"')

    def gen_notebook(self):
        if not self.project.root: messagebox.showwarning("Belum ada proyek", "Buat proyek dulu."); return
        ver = self.cb_ver.get(); model = self.cb_model.get(); cfg = YOLO_VERSIONS[ver]
        tr = {}
        try:
            for k, var in self.vars.items(): tr[k] = var.get()
            for k in ("epochs", "imgsz", "batch", "patience"): tr[k] = int(float(tr[k]))
        except: messagebox.showerror("Nilai salah", "Periksa angka hyperparameter."); return

        self.project.data["yolo_version"] = ver
        self.project.data["base_model"] = model
        self.project.data["training"].update(tr)
        self.project.save()

        nb = self._build_nb(ver, model, cfg, tr)
        out = self.project.root / "notebooks" / f"train_{ver.lower()}_{now_tag()}.ipynb"
        out.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
        self._log(f"✓ Notebook: {out.name}")
        self.app.refresh_all()
        messagebox.showinfo("Sukses", f"Notebook tersimpan:\n{out}")

    def _md(self, t):
        return {"cell_type": "markdown", "metadata": {}, "source": t.splitlines(keepends=True)}

    def _code(self, t):
        return {"cell_type": "code", "metadata": {}, "source": t.splitlines(keepends=True), "outputs": [], "execution_count": None}

    def _build_nb(self, ver, model, cfg, tr):
        proj = safe_name(self.project.data["name"])
        drive_ds = f"/content/drive/MyDrive/yolo_projects/{proj}/yolo_dataset"
        classes = self.project.data["classes"]

        cells = [
            self._md(f"# Training {ver} — {self.project.data['name']}\n\n- Kelas: {', '.join(classes)}\n- Model: `{model}`\n- Epochs: {tr['epochs']}  •  Batch: {tr['batch']}  •  imgsz: {tr['imgsz']}\n"),
            self._md("## 1. Setup\nRuntime → Change runtime type → **T4 GPU**"),
        ]

        if cfg["api"] == "ultralytics":
            cells += [
                self._code(cfg["install"]),
                self._md("## 2. Mount Google Drive"),
                self._code("from google.colab import drive\ndrive.mount('/content/drive')\n" f"DATA_YAML = '{drive_ds}/data.yaml'\nimport os; print('Dataset ada?', os.path.exists(DATA_YAML))"),
                self._md("## 3. Training"),
                self._code(f"{cfg['import']}\nmodel = YOLO('{model}')\n\nresults = model.train(\n    data=DATA_YAML, epochs={tr['epochs']}, imgsz={tr['imgsz']},\n    batch={tr['batch']}, patience={tr['patience']},\n    optimizer='{tr['optimizer']}',\n    project='/content/drive/MyDrive/yolo_projects/{proj}/runs',\n    name='train', exist_ok=True\n)"),
                self._md("## 4. Validasi"),
                self._code("metrics = model.val()\nprint(metrics)"),
                self._md("## 5. Download best.pt"),
                self._code("from google.colab import files\n" f"files.download('/content/drive/MyDrive/yolo_projects/{proj}/runs/train/weights/best.pt')"),
                self._md("## 6. Download semua hasil training (ZIP)\nSetelah selesai, import `train_results.zip` ke aplikasi via tab **7. Evaluasi → Import Hasil Training**."),
                self._code("import shutil, os\n" f"src = '/content/drive/MyDrive/yolo_projects/{proj}/runs/train'\n" "if os.path.exists(src):\n    shutil.make_archive('/content/train_results', 'zip', root_dir=os.path.dirname(src), base_dir='train')\n    from google.colab import files\n    files.download('/content/train_results.zip')\n    print('✓ train_results.zip terunduh')\nelse:\n    print('✗ Folder runs/train tidak ditemukan')"),
            ]
        else:
            cells += [
                self._code(cfg["install"]),
                self._md("## 2. Mount Google Drive"),
                self._code("from google.colab import drive\ndrive.mount('/content/drive')\n" f"DATA_YAML = '{drive_ds}/data.yaml'\nimport os; print('Dataset ada?', os.path.exists(DATA_YAML))"),
                self._md("## 3. Training YOLOv5"),
                self._code(f"!python train.py \\\n  --img {tr['imgsz']} \\\n  --batch {tr['batch']} \\\n  --epochs {tr['epochs']} \\\n  --data \"$DATA_YAML\" \\\n  --weights {model} \\\n  --project /content/drive/MyDrive/yolo_projects/{proj}/runs \\\n  --name train --exist-ok"),
                self._md("## 4. Download best.pt"),
                self._code("from google.colab import files\n" f"files.download('/content/drive/MyDrive/yolo_projects/{proj}/runs/train/weights/best.pt')"),
            ]

        return {"cells": cells, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}

# ============================================================
#  Tab 7: Evaluasi
# ============================================================
class EvalTab(ttk.Frame):
    def __init__(self, master, project: Project, app):
        super().__init__(master, padding=16)
        self.project = project
        self.app = app
        self._build()

    def _build(self):
        ttk.Label(self, text="7. Evaluasi Model", font=("Segoe UI", 15, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))
        ttk.Label(self, text="Muat best.pt hasil Colab, atau import hasil training lengkap dari Drive.", foreground=tc("fg_muted")).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(self, text="File model (.pt):").grid(row=2, column=0, sticky="w", pady=4)
        self.e_pt = ttk.Entry(self, width=55); self.e_pt.grid(row=2, column=1, sticky="we", pady=4)
        ttk.Button(self, text="Browse...", command=self.pick_pt).grid(row=2, column=2, padx=4)

        ttk.Label(self, text="results.csv (opsional):").grid(row=3, column=0, sticky="w", pady=4)
        self.e_csv = ttk.Entry(self, width=55); self.e_csv.grid(row=3, column=1, sticky="we", pady=4)
        ttk.Button(self, text="Browse...", command=self.pick_csv).grid(row=3, column=2, padx=4)

        btns1 = ttk.LabelFrame(self, text="Validasi & Prediksi", padding=8); btns1.grid(row=4, column=0, columnspan=3, sticky="we", pady=(8, 4))
        ttk.Button(btns1, text="🎯 Uji pada Split Test", command=self.run_val).pack(side="left", padx=3)
        ttk.Button(btns1, text="📊 Analisis results.csv", command=self.analyze_csv).pack(side="left", padx=3)
        ttk.Button(btns1, text="🖼  Prediksi Gambar", command=self.predict_image).pack(side="left", padx=3)
        ttk.Button(btns1, text="🎬 Prediksi Video", command=self.predict_video).pack(side="left", padx=3)
        ttk.Button(btns1, text="🎥 Prediksi Kamera", command=self.predict_camera).pack(side="left", padx=3)

        btns2 = ttk.LabelFrame(self, text="Hasil Training (dari Drive/Colab)", padding=8); btns2.grid(row=5, column=0, columnspan=3, sticky="we", pady=(4, 8))
        ttk.Button(btns2, text="📥 Import Hasil Training (ZIP)", command=self.import_training_zip).pack(side="left", padx=3)
        ttk.Button(btns2, text="📂 Lihat Hasil Training Terakhir", command=self.open_results_viewer).pack(side="left", padx=3)
        ttk.Button(btns2, text="🌐 Buka Google Drive", command=lambda: webbrowser.open("https://drive.google.com/")).pack(side="left", padx=3)

        self.info = tk.Text(self, height=18, width=100, state="disabled", relief="sunken", font=("Consolas", 9))
        self.info.grid(row=6, column=0, columnspan=3, sticky="we", pady=8)
        self.columnconfigure(1, weight=1)

    def _log(self, m):
        self.info.configure(state="normal"); self.info.insert("end", m + "\n"); self.info.see("end"); self.info.configure(state="disabled")

    def pick_pt(self):
        f = filedialog.askopenfilename(filetypes=[("YOLO weights", "*.pt"), ("All", "*.*")])
        if f: self.e_pt.delete(0, "end"); self.e_pt.insert(0, f)

    def pick_csv(self):
        f = filedialog.askopenfilename(filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if f: self.e_csv.delete(0, "end"); self.e_csv.insert(0, f)

    def run_val(self):
        pt = self.e_pt.get().strip()
        if not pt or not Path(pt).exists(): messagebox.showwarning("Kosong", "Pilih file .pt dulu."); return
        if not self.project.root: return
        export_ds = self.project.root / "04_export" / "yolo_dataset"
        if not export_ds.exists() or not (export_ds / "data.yaml").exists():
            messagebox.showwarning("Belum export", "Susun folder export dulu di tab 5."); return

        classes = self.project.data["classes"]
        local_yaml = export_ds / "data_local.yaml"
        yaml_lines = [f"path: {str(export_ds).replace(chr(92), '/')}", "train: train/images", "val: val/images", "test: test/images", "", f"nc: {len(classes)}", "names:"] + [f"  - {c}" for c in classes]
        try: local_yaml.write_text("\n".join(yaml_lines), encoding="utf-8")
        except Exception as e: self._log(f"✗ Gagal menulis yaml temporary: {e}"); return

        def worker():
            try:
                from ultralytics import YOLO
                self._log(f"Menggunakan data.yaml lokal: {local_yaml.name}")
                self._log("Menjalankan validasi...")
                m = YOLO(pt).val(data=str(local_yaml), split="test")
                self._log("")
                self._log(f"  mAP@0.5       : {m.box.map50:.4f}")
                self._log(f"  mAP@0.5:0.95  : {m.box.map:.4f}")
                self._log(f"  Precision     : {m.box.mp:.4f}")
                self._log(f"  Recall        : {m.box.mr:.4f}")
            except ImportError: self._log("✗ ultralytics belum terinstall. pip install ultralytics")
            except Exception as e: self._log(f"✗ Error: {e}")
            finally:
                try: local_yaml.unlink(missing_ok=True)
                except: pass
        threading.Thread(target=worker, daemon=True).start()

    def analyze_csv(self):
        p = self.e_csv.get().strip()
        if not p or not Path(p).exists(): messagebox.showwarning("Kosong", "Pilih results.csv dulu."); return
        try:
            with open(p, newline="", encoding="utf-8") as f: rows = list(csv.DictReader(f))
        except Exception as e: self._log(f"✗ {e}"); return
        if not rows: self._log("CSV kosong."); return
        last = rows[-1]
        self._log(f"Total epoch: {len(rows)}")
        self._log("Metrik epoch terakhir:")
        for k, v in last.items(): self._log(f"  {k:35s} = {v}")

    def predict_image(self):
        pt = self.e_pt.get().strip()
        if not pt or not Path(pt).exists(): messagebox.showwarning("Kosong", "Pilih file .pt dulu."); return
        initial_dir = None
        if self.project.root:
            test_dir = self.project.root / "02_split" / "images" / "test"
            if test_dir.exists(): initial_dir = str(test_dir)
        img = filedialog.askopenfilename(title="Pilih gambar untuk diprediksi", initialdir=initial_dir, filetypes=[("Gambar", "*.jpg *.jpeg *.png *.bmp"), ("All", "*.*")])
        if not img: return
        try:
            from ultralytics import YOLO
            import cv2
            res = YOLO(pt)(img)
            ann = res[0].plot()
            out = Path(pt).parent / f"pred_{Path(img).stem}.jpg"
            cv2.imwrite(str(out), ann)
            self._log(f"✓ Hasil prediksi: {out}")
            if HAS_CV:
                cv2.imshow("Prediksi", ann)
                cv2.waitKey(0); cv2.destroyAllWindows()
        except Exception as e: self._log(f"✗ {e}")

    def predict_video(self):
        pt = self.e_pt.get().strip()
        if not pt or not Path(pt).exists(): messagebox.showwarning("Kosong", "Pilih file .pt dulu."); return
        if not HAS_CV: messagebox.showerror("OpenCV tidak ada", "pip install opencv-python"); return
        vpath = filedialog.askopenfilename(title="Pilih file video", filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv *.webm"), ("All", "*.*")])
        if not vpath: return
        save_out = messagebox.askyesno("Simpan hasil?", "Simpan video yang sudah dianotasi ke folder proyek (06_runs/predictions)?\n\nYa → disimpan di folder proyek\nTidak → hanya ditampilkan")
        out_path = None
        if save_out:
            pred_dir = self.project.root / "06_runs" / "predictions"
            pred_dir.mkdir(parents=True, exist_ok=True)
            out_path = pred_dir / f"pred_{Path(vpath).stem}.mp4"

        def worker():
            try:
                from ultralytics import YOLO
                self._log(f"Memuat model: {Path(pt).name}")
                model = YOLO(pt)
                cap = cv2.VideoCapture(vpath)
                if not cap.isOpened(): self._log(f"✗ Tidak bisa buka video: {vpath}"); return
                fps = cap.get(cv2.CAP_PROP_FPS) or 25
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self._log(f"Video: {w}x{h} @ {fps:.1f}fps, {total} frame")
                writer = None
                if out_path:
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
                    self._log(f"Hasil akan disimpan: {out_path}")
                win = "Prediksi Video — Tekan Q untuk berhenti"
                idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret: break
                    results = model(frame, verbose=False)
                    ann = results[0].plot()
                    if writer: writer.write(ann)
                    idx += 1
                    disp = ann.copy()
                    cv2.putText(disp, f"Frame {idx}/{total}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.imshow(win, disp)
                    if cv2.waitKey(1) & 0xFF in (ord('q'), 27): self._log(f"⏹ Dihentikan di frame {idx}"); break
                cap.release()
                if writer: writer.release()
                cv2.destroyAllWindows()
                self._log(f"✓ Selesai: {idx} frame diproses.")
                if out_path and out_path.exists(): self._log(f"✓ Hasil: {out_path}")
            except ImportError: self._log("✗ ultralytics belum terinstall. pip install ultralytics")
            except Exception as e: self._log(f"✗ Error: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def predict_camera(self):
        pt = self.e_pt.get().strip()
        if not pt or not Path(pt).exists(): messagebox.showwarning("Kosong", "Pilih file .pt dulu."); return
        if not HAS_CV: messagebox.showerror("OpenCV tidak ada", "pip install opencv-python"); return
        cam_idx = simpledialog.askinteger("Pilih Kamera", "Index kamera:\n\n0 = webcam laptop\n1+ = webcam eksternal", initialvalue=0, minvalue=0, maxvalue=5)
        if cam_idx is None: return

        def worker():
            try:
                from ultralytics import YOLO
                self._log(f"Memuat model: {Path(pt).name}")
                model = YOLO(pt)
                cap = cv2.VideoCapture(cam_idx)
                if not cap.isOpened(): self._log(f"✗ Tidak bisa buka kamera index {cam_idx}"); return
                self._log(f"🎥 Kamera {cam_idx} aktif. Tekan Q untuk berhenti.")
                win = f"Prediksi Kamera {cam_idx} — Tekan Q untuk berhenti"
                fps_timer = cv2.getTickCount(); frame_count = 0; fps_display = 0
                while True:
                    ret, frame = cap.read()
                    if not ret: break
                    results = model(frame, verbose=False)
                    ann = results[0].plot()
                    frame_count += 1
                    if frame_count % 10 == 0:
                        t = cv2.getTickCount(); fps_display = 10 / ((t - fps_timer) / cv2.getTickFrequency()); fps_timer = t
                    cv2.putText(ann, f"FPS: {fps_display:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.imshow(win, ann)
                    if cv2.waitKey(1) & 0xFF in (ord('q'), 27): break
                cap.release(); cv2.destroyAllWindows()
                self._log(f"✓ Kamera {cam_idx} ditutup.")
            except ImportError: self._log("✗ ultralytics belum terinstall. pip install ultralytics")
            except Exception as e: self._log(f"✗ Error: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def import_training_zip(self):
        if not self.project.root: messagebox.showwarning("Belum ada proyek", "Buat/muat proyek dulu."); return
        zpath = filedialog.askopenfilename(title="Pilih file ZIP hasil training (train_results.zip)", filetypes=[("ZIP", "*.zip"), ("All", "*.*")])
        if not zpath: return
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst = self.project.root / "06_runs" / f"train_{ts}"
            dst.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zpath) as z: z.extractall(dst)
            entries = list(dst.iterdir())
            if len(entries) == 1 and entries[0].is_dir():
                inner = entries[0]
                for p in inner.iterdir(): shutil.move(str(p), str(dst / p.name))
                try: inner.rmdir()
                except: pass
            self._log(f"✓ Diekstrak ke: {dst}")
            TrainingResultsWindow(self, dst, self.project)
        except Exception as e:
            self._log(f"✗ Gagal import: {e}")
            messagebox.showerror("Error", str(e))

    def open_results_viewer(self):
        if not self.project.root: return
        runs_dir = self.project.root / "06_runs"
        if not runs_dir.exists(): messagebox.showinfo("Kosong", "Belum ada hasil training di folder 06_runs/.\n\nSilakan import ZIP dari Colab terlebih dahulu."); return
        candidates = [p for p in runs_dir.iterdir() if p.is_dir() and p.name.startswith("train_")]
        if not candidates: candidates = [p for p in runs_dir.iterdir() if p.is_dir()]
        if not candidates: messagebox.showinfo("Kosong", "Belum ada hasil training."); return
        latest = sorted(candidates, key=lambda p: p.stat().st_mtime)[-1]
        TrainingResultsWindow(self, latest, self.project)

# ============================================================
#  Viewer Hasil Training
# ============================================================
class TrainingResultsWindow(tk.Toplevel):
    def __init__(self, master, folder: Path, project: Project):
        super().__init__(master)
        self.folder = folder
        self.project = project
        self.title(f"Hasil Training — {folder.name}")
        self.geometry("1200x800")
        self.minsize(1000, 650)

        self._images = []
        self.pil_img = None
        self.tk_img = None
        self.scale = 1.0
        self.offset = (0, 0)

        self._build()
        self._load()
        self.after(100, self._apply_theme_to_self)

    def _build(self):
        top = ttk.LabelFrame(self, text="Ringkasan Training", padding=8)
        top.pack(fill="x", padx=8, pady=(8, 4))
        self.lbl_summary = ttk.Label(top, text="Memuat...", justify="left", font=("Consolas", 10))
        self.lbl_summary.pack(anchor="w")

        mid = ttk.Frame(self, padding=8)
        mid.pack(fill="both", expand=True)

        left = ttk.LabelFrame(mid, text="Gambar Hasil", padding=4)
        left.pack(side="left", fill="y", padx=(0, 6))
        self.listbox = tk.Listbox(left, width=34, font=("Consolas", 9), exportselection=False, activestyle="none")
        self.listbox.pack(fill="y", expand=True)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.listbox.yview)
        sb.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        right = ttk.LabelFrame(mid, text="Preview", padding=4)
        right.pack(side="right", fill="both", expand=True)
        self.canvas = tk.Canvas(right, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self._redraw())

        bot = ttk.Frame(self, padding=8)
        bot.pack(fill="x")
        ttk.Button(bot, text="📂 Buka Folder Hasil", command=self._open_folder).pack(side="left", padx=4)
        ttk.Button(bot, text="📊 Analisis results.csv", command=self._analyze_csv).pack(side="left", padx=4)
        ttk.Button(bot, text="🖼  Buka dengan Viewer Sistem", command=self._open_with_system).pack(side="left", padx=4)
        ttk.Button(bot, text="Tutup", command=self.destroy).pack(side="right", padx=4)

    def _apply_theme_to_self(self):
        try: restyle_tk_widgets(self); remap_hardcoded_colors(self)
        except: pass

    def _load(self):
        csv_path = self.folder / "results.csv"
        if csv_path.exists():
            try:
                with open(csv_path, newline="", encoding="utf-8") as f: rows = list(csv.DictReader(f))
                if rows:
                    last = rows[-1]
                    lines = [
                        f"Total epoch     : {len(rows)}",
                        f"mAP@0.5         : {last.get('metrics/mAP50(B)', '-')}",
                        f"mAP@0.5:0.95    : {last.get('metrics/mAP50-95(B)', '-')}",
                        f"Precision       : {last.get('metrics/precision(B)', '-')}",
                        f"Recall          : {last.get('metrics/recall(B)', '-')}",
                    ]
                    self.lbl_summary.config(text="\n".join(lines))
            except Exception as e: self.lbl_summary.config(text=f"Gagal baca results.csv: {e}")
        else: self.lbl_summary.config(text="(results.csv tidak ditemukan)")

        priority = ["results.png", "confusion_matrix.png", "confusion_matrix_normalized.png", "PR_curve.png", "F1_curve.png", "P_curve.png", "R_curve.png", "labels.jpg", "labels_correlogram.jpg"]
        images = []
        for name in priority:
            p = self.folder / name
            if p.exists(): images.append(p)
        for p in sorted(self.folder.glob("*")):
            if p in images: continue
            if p.suffix.lower() in (".png", ".jpg", ".jpeg"): images.append(p)

        self._images = images
        for p in images: self.listbox.insert("end", p.name)
        if images:
            self.listbox.selection_set(0)
            self._load_image(images[0])
        else:
            self.canvas.delete("all")
            self.canvas.create_text(20, 20, anchor="nw", text="Tidak ada gambar hasil di folder ini.", fill=tc("fg_muted"))

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if not sel: return
        self._load_image(self._images[sel[0]])

    def _load_image(self, path: Path):
        try:
            self.pil_img = Image.open(path).convert("RGB")
            self._redraw()
        except Exception as e:
            self.canvas.delete("all")
            self.canvas.create_text(20, 20, anchor="nw", text=f"Gagal memuat: {e}", fill=tc("danger"))

    def _redraw(self):
        if self.pil_img is None: return
        cw = self.canvas.winfo_width(); ch = self.canvas.winfo_height()
        if cw < 20 or ch < 20: self.after(100, self._redraw); return
        W, H = self.pil_img.size
        s = min(cw/W, ch/H, 1.0)
        self.scale = s
        nw, nh = max(1, int(W*s)), max(1, int(H*s))
        self.offset = ((cw-nw)//2, (ch-nh)//2)
        disp = self.pil_img.resize((nw, nh))
        self.tk_img = ImageTk.PhotoImage(disp)
        self.canvas.delete("all")
        self.canvas.create_image(self.offset[0], self.offset[1], anchor="nw", image=self.tk_img)

    def _open_folder(self):
        p = self.folder
        if sys.platform.startswith("win"): os.startfile(p)
        elif sys.platform == "darwin": os.system(f'open "{p}"')
        else: os.system(f'xdg-open "{p}"')

    def _open_with_system(self):
        sel = self.listbox.curselection()
        if not sel: return
        p = self._images[sel[0]]
        if sys.platform.startswith("win"): os.startfile(p)
        elif sys.platform == "darwin": os.system(f'open "{p}"')
        else: os.system(f'xdg-open "{p}"')

    def _analyze_csv(self):
        csv_path = self.folder / "results.csv"
        if not csv_path.exists(): messagebox.showwarning("Tidak ada", "results.csv tidak ditemukan."); return
        try:
            with open(csv_path, newline="", encoding="utf-8") as f: rows = list(csv.DictReader(f))
        except Exception as e: messagebox.showerror("Error", str(e)); return
        if not rows: return
        last = rows[-1]
        lines = [f"Total epoch: {len(rows)}", "", "Metrik epoch terakhir:"]
        for k, v in last.items(): lines.append(f"  {k:35s} = {v}")
        messagebox.showinfo("Analisis results.csv", "\n".join(lines))

# ============================================================
#  Tab 8: Panduan
# ============================================================
class GuideTab(ttk.Frame):
    def __init__(self, master, project: Project, app):
        super().__init__(master, padding=16)
        self._texts = {}
        self._font_size = self._load_font_size()

        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Label(bar, text="Panduan Penggunaan", font=("Segoe UI", 15, "bold")).pack(side="left")
        ttk.Button(bar, text="🖨 Buka sebagai file teks", command=self._save_as_txt).pack(side="right", padx=4)
        ttk.Button(bar, text="📋 Salin ke clipboard", command=self._copy_all).pack(side="right", padx=4)

        ttk.Button(bar, text="+", width=2, command=lambda: self._step_font(+1)).pack(side="right", padx=(0, 2))
        self.v_font = tk.IntVar(value=self._font_size)
        self.sp_font = ttk.Spinbox(bar, from_=10, to=20, increment=1, textvariable=self.v_font, width=4, font=("Consolas", 10))
        self.sp_font.pack(side="right")
        self.sp_font.bind("<Return>", lambda e: self._apply_font())
        self.sp_font.bind("<FocusOut>", lambda e: self._apply_font())
        ttk.Button(bar, text="−", width=2, command=lambda: self._step_font(-1)).pack(side="right", padx=(4, 0))
        ttk.Label(bar, text="  🔤 Ukuran:").pack(side="right", padx=(8, 2))

        self.sub = ttk.Notebook(self)
        self.sub.pack(fill="both", expand=True)

        sections = [
            ("Alur Singkat",      GUIDE_FLOW),
            ("Akuisisi Data",     GUIDE_ACQUIRE),
            ("Anotasi Manual",    GUIDE_ANNOT_MANUAL),
            ("Anotasi Semi-Auto", GUIDE_ANNOT_SEMI),
            ("Preprocessing",     GUIDE_PREPROC),
            ("Shortcut",          GUIDE_SHORTCUTS),
            ("Split & Export",    GUIDE_SPLIT_EXPORT),
            ("Training Colab",    GUIDE_TRAINING),
            ("Evaluasi",          GUIDE_EVAL),
            ("Prediksi Live",     GUIDE_PREDICT),
            ("Tips & FAQ",        GUIDE_TIPS_FAQ),
        ]
        for title, content in sections:
            frame = ttk.Frame(self.sub, padding=10)
            self.sub.add(frame, text=f"  {title}  ")
            txt = tk.Text(frame, wrap="word", font=("Consolas", self._font_size), relief="flat", padx=8, pady=6)
            sb = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=sb.set)
            txt.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")
            txt.insert("1.0", content)
            txt.configure(state="disabled")
            self._texts[title] = txt

    def _config_path(self) -> Path: return Path.home() / ".yolo_studio_config.json"

    def _load_font_size(self) -> int:
        p = self._config_path()
        if p.exists():
            try: return max(10, min(20, int(json.loads(p.read_text(encoding="utf-8")).get("guide_font_size", 10))))
            except: pass
        return 10

    def _save_font_size(self, size: int):
        p = self._config_path()
        try: cfg = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except: cfg = {}
        cfg["guide_font_size"] = size
        try: p.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        except: pass

    def _step_font(self, delta: int):
        self.v_font.set(max(10, min(20, self.v_font.get() + delta)))
        self._apply_font()

    def _apply_font(self):
        try: size = max(10, min(20, int(self.v_font.get())))
        except: return
        self.v_font.set(size)
        self._font_size = size
        for txt in self._texts.values(): txt.configure(font=("Consolas", size))
        self._save_font_size(size)

    def _copy_all(self):
        parts = [f"===== {t} =====\n{txt.get('1.0', 'end')}\n\n" for t, txt in self._texts.items()]
        self.clipboard_clear(); self.clipboard_append("".join(parts))
        messagebox.showinfo("Disalin", "Seluruh panduan disalin ke clipboard.")

    def _save_as_txt(self):
        f = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt"), ("Markdown", "*.md"), ("All", "*.*")], initialfile="panduan_yolo_studio.txt")
        if not f: return
        parts = [f"===== {t} =====\n{txt.get('1.0', 'end')}\n\n" for t, txt in self._texts.items()]
        Path(f).write_text("".join(parts), encoding="utf-8")
        messagebox.showinfo("Tersimpan", f"Panduan disimpan:\n{f}")

# ============================================================
#  Konten Panduan (Teks Lengkap Asli v1.1.1 + Tambahan v1.2.0)
# ============================================================
GUIDE_FLOW = """ALUR 8 LANGKAH — DARI NOL SAMPAI MODEL JADI
=============================================

Aplikasi ini membantu Anda mempersiapkan dataset deteksi objek
dan melatih model YOLO melalui Google Colab. Semua proses dari
pengambilan data, anotasi, split, hingga penyiapan training
dapat dilakukan dari dalam aplikasi ini. Tidak memerlukan
layanan pihak ketiga seperti Roboflow.


  ┌─────────────────────────────────────────────────┐
  │  1. PROYEK     →  buat proyek & kelas           │
  │  2. AKUISISI   →  webcam / video                │
  │  3. ANOTASI    →  gambar bbox (manual/auto)     │
  │  4. SPLIT      →  bagi train/val/test           │
  │  5. EXPORT     →  siapkan folder Drive          │
  │  6. TRAINING   →  jalankan di Colab             │
  │  7. EVALUASI   →  uji best.pt + import hasil    │
  │  8. PANDUAN    →  referensi (di sini)           │
  └─────────────────────────────────────────────────┘


Estimasi waktu (dataset kecil, 3 kelas, ~300 gambar):
  • Akuisisi           : 30–60 menit
  • Anotasi manual     : 3–6 jam
  • Anotasi semi-auto  : 1–2 jam  (jika kelas umum COCO)
  • Split + Export     : 5 menit
  • Training Colab     : 30–60 menit
  • Evaluasi + Prediksi: 10–30 menit
  ─────────────────────────────
  Total                : ~5–8 jam (bisa dicicil)


Prinsip penting:
  1. Kualitas anotasi > kuantitas. Kotak yang pas lebih
     berharga daripada banyak kotak yang asal.
  2. Variasi gambar > banyak gambar mirip. Model belajar
     dari perbedaan sudut, jarak, cahaya, dan latar.
  3. Split dilakukan SETELAH anotasi selesai. Aplikasi ini
     otomatis hanya menghitung gambar yang sudah dianotasi.
  4. Data pribadi tetap di komputer Anda. Aplikasi tidak
     mengirim apa pun ke internet selain Google Drive Anda
     sendiri (untuk training Colab).


── FITUR UNGGULAN (v1.2.0) ────────────────────────────

Aplikasi ini bukan sekadar anotator — ada beberapa fitur
yang jarang ditemukan di tool gratis lain:

  🧲  Magnet Mode (G)
      AI mendeteksi semua objek di layar. Arahkan mouse
      (kotak berubah kuning), lalu KLIK untuk langsung
      mengotaki secara instan (seperti Magic Wand).

  ✂️  Auto-Trim Box (T)
      Mengetatkan kotak kasar secara otomatis menggunakan
      algoritma GrabCut, Contour, atau Adaptive Threshold.

  🛠  Preprocessing Studio (P)
      Beri efek CLAHE, Sharpen, Kontras, dll. Simpan sebagai
      gambar baru (Augmentasi) atau Timpa aslinya.

  📦  Batch Preprocessing
      Augmentasi SEMUA gambar asli sekaligus dalam 1 klik.
      Nama file otomatis menyertakan nama metode & tanggal.

  🤖  Auto-Suggest Bounding Box (Ctrl+A)
      Deteksi otomatis dengan model YOLO COCO pretrained.
      Hemat waktu anotasi 30–70% untuk kelas umum.


── ALUR DETAIL PER TAB ────────────────────────────────

Tab 1. Proyek
  • Isi nama proyek & peneliti
  • Pilih folder kerja (proyek baru di folder terpisah)
  • Pilih versi YOLO (v5/v8/v9/v10/v11/v12/v13/v26)
  • Pilih model dasar (n/s/m/l/x)
  • Isi daftar kelas (1 per baris)
  • Klik "Buat Proyek Baru" → struktur folder terbentuk

Tab 2. Akuisisi
  • Video: pilih file → atur interval frame → ekstrak
  • Webcam: pilih index kamera → capture frame
  • Tips: 100–300 gambar per kelas, variasikan sudut

Tab 3. Anotasi
  • Drag mouse untuk bounding box manual.
  • Gunakan Magnet Mode (G) atau Auto-Suggest (Ctrl+A) untuk AI.
  • Gunakan Auto-Trim (T) untuk mengetatkan kotak kasar.
  • Auto-save: setiap perubahan langsung tersimpan.

Tab 4. Split
  • Pilih preset atau isi rasio manual (total = 100%)
  • Live-count menampilkan estimasi gambar per split
  • Klik "Jalankan Split"

Tab 5. Export
  • Klik "Susun Folder Export + data.yaml"
  • Upload folder ke Drive:
    MyDrive/yolo_projects/<nama_proyek>/yolo_dataset/

Tab 6. Training
  • Pilih versi YOLO & model → atur hyperparameter
  • Klik "Generate Notebook" → upload ke Colab
  • Runtime → T4 GPU → jalankan cell
  • best.pt + train_results.zip otomatis terunduh

Tab 7. Evaluasi
  • Uji pada Split Test    → mAP, precision, recall
  • Analisis results.csv   → metrik per epoch
  • Prediksi Gambar/Video/Kamera → uji visual model
  • Import Hasil Training  → viewer grafik dari Colab

Tab 8. Panduan
  • Referensi lengkap 11 sub-tab (yang sedang Anda baca)
  • Kontrol ukuran font 10–20 pt
"""


GUIDE_ACQUIRE = """AKUISISI DATA — VIDEO & WEBCAM
================================

Tujuan: mengumpulkan gambar objek dari sekitar Anda.

── A. EKSTRAK FRAME DARI VIDEO ────────────────────────
  1. Klik "Browse..." → pilih file .mp4/.avi/.mov
  2. Atur "Ambil 1 frame setiap N frame":
       15  →  default, bagus untuk gerakan lambat
       30  →  1 frame per detik (video 30 fps)
  3. Klik "▶ Ekstrak Frame"

── B. CAPTURE DARI WEBCAM ─────────────────────────────
  1. Pilih "Kamera index":  0 = laptop, 1+ = eksternal
  2. Isi "Nama sesi" (mis. mobil_pagi, buku_meja)
  3. Klik "🎥 Buka Kamera"
  4. Kontrol jendela kamera:
       SPASI  →  simpan 1 frame
       A      →  toggle mode AUTO (simpan tiap 10 frame)
       Q/ESC  →  selesai

── STRATEGI PENGAMBILAN GAMBAR ────────────────────────
  Jumlah per kelas (rule of thumb):
    • Prototipe/eksperimen cepat : 30–50
    • Hasil stabil untuk skripsi  : 100–300
  
  Variasikan:
    ✓ Sudut pandang, Jarak, Pencahayaan, Latar belakang.
    ✗ Jangan 100 gambar objek sama dari sudut yang sama.
"""


GUIDE_ANNOT_MANUAL = """ANOTASI MANUAL — BOUNDING BOX
==============================

Tujuan: menggambar kotak di setiap objek dan memberi label kelas.

── LANGKAH DASAR ──────────────────────────────────────
  1. Buka tab "3. Anotasi" → Klik "🖊 Buka Anotator".
  2. Pilih kelas di dropdown (atau tekan angka 1, 2, 3, ...).
  3. Drag mouse di atas gambar untuk menggambar kotak kasar.
  4. (Opsional) Tekan "T" untuk Auto-Trim agar kotak lebih presisi.
  5. Kotak otomatis tersimpan.
  6. Tekan SPASI untuk lanjut ke gambar berikutnya.

── AUTO-SAVE (PENTING) ────────────────────────────────
Anotasi Anda tersimpan OTOMATIS setiap kali:
  • selesai menggambar kotak
  • undo (D atau Del)
  • hapus semua (C)
  • pindah gambar (◀ ▶ atau B N atau ← →)
  • menutup jendela anotator

── ATURAN BOUNDING BOX YANG BAIK ──────────────────────
  ✓ Kotak mengelilingi objek rapat (tidak ada ruang kosong).
  ✓ Semua sisi objek yang terlihat ada di dalam kotak.
  ✓ Gunakan fitur Auto-Trim (T) untuk objek kecil.
  ✗ Jangan terlalu longgar — model akan belajar noise.
  ✗ Jangan terlalu sempit — memotong bagian objek.

── KASUS KHUSUS ───────────────────────────────────────
Objek tertutup sebagian: Buat kotak berdasarkan bagian TERLIHAT saja.
Objek di luar kelas yang dilatih: JANGAN dianotasi (negative example).
"""


GUIDE_ANNOT_SEMI = """ANOTASI SEMI-OTOMATIS — AUTO-SUGGEST & MAGNET
=============================================

Fitur ini mempercepat anotasi menggunakan model YOLO COCO (80 kelas).

── 80 KELAS COCO ──────────────────────────────────────
Person, car, bicycle, bottle, cup, laptop, mouse, keyboard, dll.

── 1. AUTO-SUGGEST (Ctrl+A) ───────────────────────────
  1. Tekan Ctrl+A → tunggu kotak oranye putus-putus.
  2. Kotak oranye = USULAN (belum final). Pilihan Anda:
       Enter      →  terima SEMUA usulan
       Esc        →  tolak semua usulan
       Klik kanan →  terima HANYA kotak yang di-klik

── 2. MAGNET MODE (G) ─────────────────────────────────
  Fitur interaktif (seperti Magic Wand di Roboflow).
  1. Tekan "G" → AI memindai seluruh frame.
  2. Kotak biru putus-putus akan muncul di setiap objek.
  3. Dekatkan mouse ke salah satu objek → kotak berubah KUNING.
  4. KLIK mouse → objek langsung dikotaki dengan warna kelas Anda.

── KAPAN BERGUNA ──────────────────────────────────────
  ✓ Jika kelas Anda ada di COCO (person, car, cup, dll).
  ✗ Tidak berguna untuk kelas khusus (helm, retakan, tomat).
"""


GUIDE_PREPROC = """PREPROCESSING STUDIO & AUTO-TRIM (v1.2.0)
==========================================
Fitur untuk memperbaiki kualitas dataset dan menduplikasi data (Augmentasi).

── CARA PAKAI PREPROCESSING STUDIO (P) ────────────────
  1. Buka Anotator → klik "🛠 Preprocess (P)".
  2. Akan muncul dua jendela: Kiri (Asli) & Kanan (Preview).
  3. Pilih metode di dropdown (CLAHE, Sharpen, Kontras, dll).
  4. Geser slider Intensitas untuk melihat efek real-time.
  5. Klik "Simpan Duplikat" untuk membuat 1 gambar baru.
     Klik "Timpa" jika ingin mengganti gambar asli.

── BATCH PROSES SEMUA ASLI ────────────────────────────
  Klik tombol "📦 Batch Proses Semua Asli" di Preprocessing Studio.
  Aplikasi akan otomatis memproses seluruh gambar asli (tanpa _aug_)
  dan menyimpannya sebagai gambar baru beserta label YOLO-nya.
  
  Nama file otomatis menjadi: 
  [nama_asli]_aug_[metode]_[tanggal_jam].jpg
  Contoh: sesi1_0001_aug_clahe_20261019_224500.jpg

── METODE YANG TERSEDIA ───────────────────────────────
  • CLAHE: Untuk menonjolkan retakan / gambar gelap.
  • Sharpen: Untuk menajamkan objek blur.
  • Contrast/Brightness: Simulasi pencahayaan berbeda.
  • Saturation: Simulasi variasi warna (misal: tomat).
  • Grayscale: Hitam putih (untuk isyarat tangan).

── AUTO-TRIM BOX (T) ──────────────────────────────────
  Gunakan saat menggambar kotak kasar. Pilih metode di toolbar:
  • GrabCut: Umum, akurat untuk objek kompleks.
  • Contour: Cepat, untuk objek kontras tinggi.
  • Adaptive Thr: Untuk objek gelap/terang (siluet).
"""


GUIDE_SHORTCUTS = """SHORTCUT KEYBOARD — ANOTATOR
=============================

Semua shortcut aktif selama jendela anotator fokus.

── NAVIGASI ───────────────────────────────────────────
  ←  atau  B           Gambar sebelumnya
  →  atau  N           Gambar berikutnya
  SPASI                Simpan & lanjut ke gambar berikutnya
  Enter                Kalau ada usulan: terima semua

── EDIT KOTAK ─────────────────────────────────────────
  Drag mouse           Bikin kotak baru (manual)
  D  atau  Delete      Hapus kotak terakhir (undo)
  C                    Hapus semua kotak di gambar ini
  Ctrl+S               Simpan label tanpa pindah gambar
  
  T                    Auto-Trim kotak terakhir
  G                    Aktifkan/Mematikan Magnet Mode
  P                    Buka Preprocessing Studio

── PILIH KELAS ────────────────────────────────────────
  1  2  3  ...  9      Pilih kelas ke-N secara langsung
  0                    Pilih kelas ke-10
  Klik dropdown        Pilih kelas dengan mouse

── AUTO-SUGGEST & MAGNET ──────────────────────────────
  Ctrl+A               Jalankan deteksi COCO (Auto-Suggest)
  G                    Jalankan deteksi COCO (Magnet Mode)
  
  Enter                Terima semua usulan (Auto-Suggest)
  Esc                  Tolak semua usulan / Matikan Magnet
  Klik kanan           Terima 1 usulan

── WINDOW ─────────────────────────────────────────────
  Alt+F4 / X           Tutup jendela (auto-save + simpan posisi)
"""


GUIDE_SPLIT_EXPORT = """SPLIT DATASET & EXPORT
========================

── PRINSIP SPLIT ──────────────────────────────────────
  Train (70–80%)  →  untuk melatih model
  Val   (10–20%)  →  untuk memantau training (early stopping)
  Test  (5–15%)   →  untuk evaluasi akhir

── CARA SPLIT DI APLIKASI ────────────────────────────
  1. Buka tab "4. Split"
  2. Aplikasi otomatis menghitung gambar yang SUDAH dianotasi
  3. Pilih preset, atau isi angka manual (harus total 100):
       70 / 20 / 10    (default)
  4. Random seed untuk reproducibility
  5. Klik "🎲 Jalankan Split"

── REKOMENDASI JUMLAH MINIMAL ────────────────────────
  Train: ≥ 100 gambar | Val: ≥ 20 gambar | Test: ≥ 20 gambar

── EXPORT ─────────────────────────────────────────────
  1. Buka tab "5. Export"
  2. Klik "📦 Susun Folder Export + data.yaml"
  3. Upload ke Google Drive:
       MyDrive/yolo_projects/<nama_proyek>/yolo_dataset/
"""


GUIDE_TRAINING = """TRAINING DI GOOGLE COLAB
=========================

── KENAPA COLAB ───────────────────────────────────────
  Gratis (akun Google standar), GPU T4, tidak perlu install CUDA.

── PERSIAPAN ──────────────────────────────────────────
  1. Pastikan folder yolo_dataset/ sudah di Drive.
  2. Buka tab "6. Training":
       • Pilih versi YOLO & model dasar.
       • Atur hyperparameter.
       • Klik "📓 Generate Notebook".
  3. Buka https://colab.research.google.com → Upload notebook.
  4. Runtime → Change runtime type → T4 GPU → Save.
  5. Jalankan cell dari atas ke bawah (Shift+Enter).

── NOTEBOOK COLAb OTOMATIS ────────────────────────────
Notebook yang digenerate berisi 7 cell:
  1. Install ultralytics
  2. Mount Google Drive
  3. Set path dataset
  4. Training
  5. Validasi akhir
  6. Download best.pt
  7. Download train_results.zip (results.csv, confusion matrix, dll)

── MASALAH UMUM ───────────────────────────────────────
Colab "Runtime disconnected": Batas gratis 12 jam / idle 90 menit.
CUDA out of memory: Turunkan batch size (16 → 8 → 4) atau imgsz.
Dataset tidak ditemukan: Cek kapitalisasi nama folder di Drive.
"""


GUIDE_EVAL = """EVALUASI MODEL
===============

Tab Evaluasi punya 7 fitur utama:
  1. Uji pada Split Test       — hitung mAP, precision, recall
  2. Analisis results.csv      — lihat metrik per epoch
  3. Prediksi Gambar           — uji 1 gambar tunggal
  4. Prediksi Video            — proses seluruh frame video
  5. Prediksi Kamera           — real-time webcam + FPS counter
  6. Import Hasil Training ZIP — ekstrak grafik dari Colab
  7. Lihat Hasil Training      — buka eksperimen sebelumnya

── METRIK YANG DILAPORKAN ─────────────────────────────
  mAP@0.5       : Target > 0.5
  mAP@0.5:0.95  : Target > 0.3
  Precision     : Sedikit false positive.
  Recall        : Sedikit objek terlewat.

── IMPORT HASIL TRAINING (ZIP) ────────────────────────
  Notebook Colab otomatis mengunduh train_results.zip.
  Import via tab 7 → Viewer otomatis terbuka menampilkan
  confusion_matrix.png, PR_curve.png, grafik mAP, dll.

── INTERPRETASI HASIL ─────────────────────────────────
  mAP < 0.3    →  Model belum belajar baik
  mAP 0.3–0.6  →  Wajar untuk dataset kecil
  mAP 0.6–0.8  →  Bagus
  mAP > 0.8    →  Sangat bagus (Cek data leakage)
"""


GUIDE_PREDICT = """PREDIKSI LIVE — GAMBAR, VIDEO, KAMERA
=======================================

Tab Evaluasi menyediakan 3 mode prediksi menggunakan model .pt
yang sudah dilatih. Semua berjalan real-time tanpa internet.

── PERSIAPAN ──────────────────────────────────────────
  1. Pastikan ultralytics terinstall (pip install ultralytics).
  2. Punya file model .pt (best.pt dari Colab) di folder 05_models/.
  3. Buka tab 7. Evaluasi → Browse file .pt.

── PREDIKSI GAMBAR ────────────────────────────────────
  Klik "🖼 Prediksi Gambar" → pilih gambar.
  Hasil disimpan otomatis sebagai pred_<nama_gambar>.jpg.

── PREDIKSI VIDEO ─────────────────────────────────────
  Klik "🎬 Prediksi Video" → pilih video.
  Jika disimpan, hasil masuk ke 06_runs/predictions/pred_<nama>.mp4.

── PREDIKSI KAMERA ────────────────────────────────────
  Klik "🎥 Prediksi Kamera" → pilih index kamera (0=laptop).
  Real-time webcam + FPS counter. Tekan Q untuk berhenti.

── TIPS PERFORMA ──────────────────────────────────────
  Gunakan model nano (yolov8n.pt) untuk kecepatan maksimal.
"""


GUIDE_TIPS_FAQ = """TIPS & PERTANYAAN UMUM
========================

── TIPS PRODUKTIVITAS ─────────────────────────────────
1. Batch anotasi per kelas.
2. Cek progres berkala di tab 3.
3. Backup rutin folder proyek ke cloud.
4. Gunakan versi YOLO yang stabil (v8 atau v11).

── PERTANYAAN UMUM ────────────────────────────────────
Q: Berapa gambar minimal?
A: Prototipe: 30–50 per kelas. Stabil: 100–300 per kelas.

Q: Berapa lama training di Colab?
A: 100 epoch, 500 gambar, T4: 15–40 menit.

Q: Anotasi hilang saat aplikasi crash?
A: Kemungkinan kecil. Auto-save setiap perubahan.

Q: Kenapa auto-suggest tidak deteksi apa pun?
A: ultralytics belum install, atau kelas tidak ada di COCO.

Q: Apa arti warna kotak di anotator?
A: Warna tetap per kelas (lihat legend). Oranye dashed = usulan.
   Biru/Kuning dashed = Magnet Mode. Solid = anotasi final.

── SUMBER BELAJAR ─────────────────────────────────────
Dokumentasi: https://docs.ultralytics.com/
Paper YOLO: Jocher et al. (2023), Wang et al. (2024).
"""


# ============================================================
#  Main App
# ============================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("1160x840")
        self.minsize(1000, 700)

        self._theme_name = load_theme_pref()
        apply_theme(self, self._theme_name)

        self.project = Project()

        hdr = ttk.Frame(self)
        hdr.pack(fill="x", padx=12, pady=(8, 0))
        ttk.Label(hdr, text=f"🎯 {APP_TITLE}", font=("Segoe UI", 16, "bold")).pack(side="left")
        self.lbl_status = ttk.Label(hdr, text="Belum ada proyek aktif", font=("Segoe UI", 10))
        self.lbl_status.pack(side="right", padx=(0, 12))

        ttk.Label(hdr, text="🎨 Tema:", font=("Segoe UI", 9)).pack(side="right")
        self.cb_theme = ttk.Combobox(hdr, state="readonly", width=12, values=[THEMES[k]["name"] for k in THEMES])
        theme_keys = list(THEMES.keys())
        idx = theme_keys.index(self._theme_name) if self._theme_name in theme_keys else 0
        self.cb_theme.current(idx)
        self.cb_theme.pack(side="right", padx=(4, 10))
        self.cb_theme.bind("<<ComboboxSelected>>", self._on_theme_change)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=10, pady=8)

        specs = [
            ("1. Proyek",   ProjectTab),
            ("2. Akuisisi", AcquireTab),
            ("3. Anotasi",  AnnotTab),
            ("4. Split",    SplitTab),
            ("5. Export",   ExportTab),
            ("6. Training", TrainTab),
            ("7. Evaluasi", EvalTab),
            ("8. Panduan",  GuideTab),
        ]
        self.tabs = {}
        for label, cls in specs:
            tab = cls(self.nb, self.project, self)
            self.nb.add(tab, text=f"  {label}  ")
            self.tabs[label] = tab

        self.nb.bind("<<NotebookTabChanged>>", lambda e: self._on_tab_change())

        ftr = ttk.Frame(self)
        ftr.pack(fill="x", side="bottom")
        ttk.Separator(ftr).pack(fill="x")
        dep = [
            f"OpenCV: {'✓' if HAS_CV else '✗'}",
            f"Pillow: {'✓' if HAS_PIL else '✗'}",
            f"Numpy: {'✓' if HAS_NP else '✗'}",
        ]
        ttk.Label(ftr, text="   " + "  |  ".join(dep)).pack(side="left", padx=6, pady=4)

        def _post_init():
            restyle_tk_widgets(self)
            remap_hardcoded_colors(self)
        self.after(150, _post_init)

    def _on_theme_change(self, *_):
        label = self.cb_theme.get()
        name = next((k for k, v in THEMES.items() if v["name"] == label), "midnight")
        self._theme_name = name
        save_theme_pref(name)
        apply_theme(self, name)
        self.after(50, lambda: (restyle_tk_widgets(self), remap_hardcoded_colors(self)))
        self.refresh_all()
        try: self.tabs["3. Anotasi"].refresh()
        except: pass

    def _on_tab_change(self):
        try:
            current = self.nb.index(self.nb.select())
            tab_key = list(self.tabs.keys())[current]
            tab = self.tabs[tab_key]
        except: return
        if hasattr(tab, "refresh"):
            try: tab.refresh()
            except: pass
        if hasattr(tab, "refresh_dashboard"):
            try: tab.refresh_dashboard()
            except: pass

    def refresh_all(self):
        d = self.project.data
        if d["root"]:
            self.lbl_status.config(text=f"📁 {d['name']}  •  {d['yolo_version']}  •  {d['base_model']}", foreground=THEME.get("success", "#080"))
        else:
            self.lbl_status.config(text="Belum ada proyek aktif", foreground=THEME.get("danger", "#a00"))
        try: self.tabs["1. Proyek"].refresh_dashboard()
        except: pass

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()