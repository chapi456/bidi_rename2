"""
File: tkinter_view.py
Path: video_processor/ui/tkinter_view.py

Version: 1.0.0
Date: 2026-06-24

Changelog:
- 1.0.0 (2026-06-24): Implémentation complète
  * Layout : canvas central, panneaux L/R, thumb strip, seek slider, status bar
  * Drag crop sur canvas : move + 8 poignées resize → CmdSetCrop
  * Thumb strip : clic → CmdJump, highlight chapitre actif
  * SeekSlider intégré (seek_slider.py)
  * Tous les handlers EVT_ implémentés
  * _vf stocké localement — source de vérité pour accès sans paramètres
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations

import logging
import queue
import tkinter as tk
from tkinter import ttk
from typing import Optional, TYPE_CHECKING

from PIL import ImageTk

from .base_view   import BaseView
from .seek_slider import SeekSlider
from video_processor.controller import commands as CMD
from video_processor.controller import events   as EVT

if TYPE_CHECKING:
    from video_processor.domain.video_file import VideoFile
    from video_processor.domain.chapter    import Chapter
    from video_processor.domain.crop_zone  import CropZone

log = logging.getLogger("ui.tkinter_view")

# ── Constantes visuelles ──────────────────────────────────────────────────────
THUMB_W       = 120
THUMB_H       = 68
PANEL_W       = 180
BG            = "#1E1E1E"
BG_PANEL      = "#252525"
FG            = "#DDDDDD"
ACCENT        = "#4A90D9"
FONT_LABEL    = ("Helvetica", 9)
FONT_TITLE    = ("Helvetica", 11, "bold")

HANDLE_CURSORS = [
    "top_left_corner",   # 0 haut-gauche
    "top_side",          # 1 milieu haut
    "top_right_corner",  # 2 haut-droit
    "right_side",        # 3 milieu droit
    "bottom_right_corner", # 4 bas-droit
    "bottom_side",       # 5 milieu bas
    "bottom_left_corner", # 6 bas-gauche
    "left_side",         # 7 milieu gauche
]

class TkinterView(BaseView):
    """Vue Tkinter.

    Règles d'architecture :
    - self._vf : référence locale au VideoFile courant (source de vérité UI)
    - Toute lecture de données passe par self._vf, jamais en paramètre
    - Les commandes ne transportent que des deltas/indices, pas des objets domain
    """

    def __init__(self) -> None:
        self._root:    Optional[tk.Tk]   = None
        self._evt_q:   queue.Queue       = queue.Queue()
        self._vf:      Optional["VideoFile"] = None

        # Widgets principaux (initialisés dans _build)
        self._canvas:       Optional[tk.Canvas]  = None
        self._status_var:   Optional[tk.StringVar] = None
        self._title_var:    Optional[tk.StringVar] = None
        self._dirty_var:    Optional[tk.StringVar] = None
        self._seek_slider:  Optional[SeekSlider]   = None
        self._thumb_frames: list[tk.Label]         = []
        self._thumb_images: list[Optional[ImageTk.PhotoImage]] = []
        self._thumb_labels: list[tk.Label] = []
        
        # État canvas
        self._canvas_image: Optional[ImageTk.PhotoImage] = None
        self._canvas_scale: float = 1.0
        self._drag_state:   Optional[dict] = None   # {mode, handle_idx, snap_x, snap_y, crop0}

        # Spinbox vars crop
        self._var_w:   Optional[tk.IntVar] = None
        self._var_h:   Optional[tk.IntVar] = None
        self._var_x:   Optional[tk.IntVar] = None
        self._var_y:   Optional[tk.IntVar] = None

    # ── Liaison contrôleur ─────────────────────────────────────────────────

    def _on_event(self, event: object) -> None:
        self._evt_q.put(event)

    def _poll(self) -> None:
        try:
            while True:
                self._dispatch(self._evt_q.get_nowait())
        except queue.Empty:
            pass
        try:
            self._root.after(50, self._poll)
        except tk.TclError:
            pass

    def _dispatch(self, event: object) -> None:
        handlers = {
            EVT.EvtSessionLoaded:       self._on_session_loaded,
            EVT.EvtStatus:              self._on_status,
            EVT.EvtTitle:               self._on_title,
            EVT.EvtDirty:               self._on_dirty,
            EVT.EvtChapterChanged:      self._on_chapter_changed,
            EVT.EvtChaptersUpdated:     self._on_chapters_updated,
            EVT.EvtCropChanged:         self._on_crop_changed,
            EVT.EvtAllCropsInvalidated: self._on_all_crops_invalidated,
            EVT.EvtFrameReady:          self._on_frame_ready,
            EVT.EvtThumbReady:          self._on_thumb_ready,
            EVT.EvtPositionChanged:     self._on_position_changed
        }
        h = handlers.get(type(event))
        if h:
            h(event)
        else:
            log.warning("Événement non géré : %s", type(event).__name__)

    # ── Construction UI ────────────────────────────────────────────────────

    def _build(self) -> None:
        r = self._root
        r.configure(bg=BG)
        r.title("bidi_rename2")

        # Ordre pack : bas d'abord
        self._build_status_bar()
        self._build_seek_slider()
        self._build_thumb_strip()

        # Corps central
        body = tk.Frame(r, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        self._build_left_panel(body)
        self._build_right_panel(body)
        self._build_canvas(body)

        self._build_title_bar()
        self._build_file_selector()

    def _build_title_bar(self) -> None:
        self._title_var = tk.StringVar(value="bidi_rename2")
        self._dirty_var = tk.StringVar(value="")
        bar = tk.Frame(self._root, bg=BG_PANEL, height=28)
        bar.pack(side=tk.TOP, fill=tk.X, before=self._root.winfo_children()[0])
        tk.Label(bar, textvariable=self._title_var,
                 bg=BG_PANEL, fg=FG, font=FONT_TITLE).pack(side=tk.LEFT, padx=8)
        tk.Label(bar, textvariable=self._dirty_var,
                 bg=BG_PANEL, fg="#FF6B6B").pack(side=tk.LEFT)

    def _build_file_selector(self) -> None:
        self._file_var   = tk.StringVar()
        self._file_combo = ttk.Combobox(
            self._root, textvariable=self._file_var, state="readonly", width=60
        )
        self._file_combo.pack(side=tk.TOP, fill=tk.X, padx=4, pady=2)
        self._file_combo.bind(
            "<<ComboboxSelected>>",
            lambda _: self._on_file_combo_selected()
        )

    def _build_status_bar(self) -> None:
        self._status_var = tk.StringVar(value="Prêt.")
        bar = tk.Frame(self._root, bg=BG_PANEL, height=22)
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(bar, textvariable=self._status_var,
                 bg=BG_PANEL, fg=FG, font=FONT_LABEL,
                 anchor=tk.W).pack(fill=tk.X, padx=6)

    def _build_seek_slider(self) -> None:
        self._seek_slider = SeekSlider(self._root, send=self._send)
        self._seek_slider.pack(side=tk.BOTTOM, fill=tk.X, padx=2, pady=1)

    def _build_thumb_strip(self) -> None:
        self._strip_frame = tk.Frame(self._root, bg=BG_PANEL, height=THUMB_H + 8)
        self._strip_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self._thumb_frames = []
        self._thumb_images = []

    def _build_canvas(self, parent: tk.Widget) -> None:
        self._canvas = tk.Canvas(parent, bg="#000000", cursor="crosshair",
                                 highlightthickness=0)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._canvas.bind("<Configure>",       self._on_canvas_resize)
        self._canvas.bind("<ButtonPress-1>",   self._on_mouse_press)
        self._canvas.bind("<B1-Motion>",       self._on_mouse_move)
        self._canvas.bind("<ButtonRelease-1>", self._on_mouse_release)
        self._canvas.bind("<Motion>", self._on_mouse_hover)

    def _build_left_panel(self, parent: tk.Widget) -> None:
        panel = tk.Frame(parent, bg=BG_PANEL, width=PANEL_W)
        panel.pack(side=tk.LEFT, fill=tk.Y)
        panel.pack_propagate(False)

        tk.Label(panel, text="CROP", bg=BG_PANEL, fg=ACCENT,
                 font=FONT_TITLE).pack(pady=(8, 2))

        self._var_w = tk.IntVar(value=0)
        self._var_h = tk.IntVar(value=0)
        for label, var, cmd_field in [("W", self._var_w, "w"), ("H", self._var_h, "h")]:
            row = tk.Frame(panel, bg=BG_PANEL)
            row.pack(fill=tk.X, padx=6, pady=2)
            tk.Label(row, text=label, bg=BG_PANEL, fg=FG,
                     width=3).pack(side=tk.LEFT)
            sp = tk.Spinbox(row, from_=-9999, to=9999, textvariable=var,
                            width=6, command=self._on_position_spinbox)
            sp.bind("<Return>",   lambda _e: self._on_position_spinbox())
            sp.bind("<FocusOut>", lambda _e: self._on_position_spinbox())
            sp.pack(side=tk.LEFT)

        ttk.Separator(panel, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=6)

        # Navigation
        for text, cmd in [
            ("◀◀ Début",   CMD.CmdSeekBegin()),
            ("◀ Prev",     CMD.CmdPrevChapter()),
            ("Next ▶",     CMD.CmdValidateChapter()),
            ("Fin ▶▶",     CMD.CmdSeekEnd()),
        ]:
            tk.Button(panel, text=text, bg=BG_PANEL, fg=FG,
                      command=lambda c=cmd: self._send(c),
                      relief=tk.FLAT).pack(fill=tk.X, padx=6, pady=1)

        ttk.Separator(panel, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=6)

        # Actions crop
        for text, cmd in [
            ("+ Crop",         CMD.CmdAddCrop()),
            ("- Crop",         CMD.CmdDelCrop()),
            ("Copier préc.",   CMD.CmdCopyPrevCrop()),
        ]:
            tk.Button(panel, text=text, bg=BG_PANEL, fg=FG,
                      command=lambda c=cmd: self._send(c),
                      relief=tk.FLAT).pack(fill=tk.X, padx=6, pady=1)

        ttk.Separator(panel, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=6)

        tk.Button(panel, text="💾 Save",
                  bg="#2A4A2A", fg="#88FF88",
                  command=lambda: self._send(CMD.CmdSave()),
                  relief=tk.FLAT).pack(fill=tk.X, padx=6, pady=2)
        tk.Button(panel, text="💾 Save + Next",
                  bg="#2A4A2A", fg="#88FF88",
                  command=lambda: self._send(CMD.CmdSaveAndNext()),
                  relief=tk.FLAT).pack(fill=tk.X, padx=6, pady=2)

    def _build_right_panel(self, parent: tk.Widget) -> None:
        panel = tk.Frame(parent, bg=BG_PANEL, width=PANEL_W)
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)

        tk.Label(panel, text="POSITION", bg=BG_PANEL, fg=ACCENT,
                 font=FONT_TITLE).pack(pady=(8, 2))

        self._var_x = tk.IntVar(value=0)
        self._var_y = tk.IntVar(value=0)
        for label, var in [("X", self._var_x), ("Y", self._var_y)]:
            row = tk.Frame(panel, bg=BG_PANEL)
            row.pack(fill=tk.X, padx=6, pady=2)
            tk.Label(row, text=label, bg=BG_PANEL, fg=FG, width=3).pack(side=tk.LEFT)
            sp = tk.Spinbox(row, from_=-9999, to=9999, textvariable=var,
                            width=6, command=self._on_position_spinbox)
            sp.bind("<Return>",   lambda _: self._on_position_spinbox())
            sp.bind("<FocusOut>", lambda _: self._on_position_spinbox())
            sp.pack(side=tk.LEFT)

        ttk.Separator(panel, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=6)

        # Presets
        tk.Label(panel, text="Présets", bg=BG_PANEL, fg=FG,
                 font=FONT_LABEL).pack()
        presets_frame = tk.Frame(panel, bg=BG_PANEL)
        presets_frame.pack(padx=6, pady=2)
        for text, preset in [("◀ G", "l"), ("● C", "c"), ("D ▶", "r")]:
            tk.Button(presets_frame, text=text, width=4,
                      bg=BG_PANEL, fg=FG, relief=tk.FLAT,
                      command=lambda p=preset: self._send(
                          CMD.CmdSetPosition(preset=p)
                      )).pack(side=tk.LEFT, padx=2)

        ttk.Separator(panel, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=6)

        # Seek ch start/end
        for text, cmd in [
            ("⏮ Ch Start",  CMD.CmdSeekChapterStart()),
            ("⏭ Ch End",    CMD.CmdSeekChapterEnd()),
        ]:
            tk.Button(panel, text=text, bg=BG_PANEL, fg=FG,
                      command=lambda c=cmd: self._send(c),
                      relief=tk.FLAT).pack(fill=tk.X, padx=6, pady=1)

        ttk.Separator(panel, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=4, pady=6)

        tk.Button(panel, text="✕ Quitter",
                  bg="#4A1A1A", fg="#FF8888",
                  command=lambda: self._send(CMD.CmdQuit()),
                  relief=tk.FLAT).pack(fill=tk.X, padx=6, pady=2)

    # ── Handlers événements ────────────────────────────────────────────────

    def _on_session_loaded(self, evt: EVT.EvtSessionLoaded) -> None:
        self._vf = evt.video_file
        self._rebuild_thumb_strip()
        self._seek_slider.reset(self._vf.chapters, self._vf.total_duration_sec)
        # Mettre à jour la combobox
        if hasattr(self, "_file_combo") and self._file_combo:
            entry = self._vf.short_name
            values = list(self._file_combo["values"]) or []
            if entry not in values:
                values.append(entry)
                self._file_combo["values"] = values
            self._file_var.set(entry)

    def _on_status(self, evt: EVT.EvtStatus) -> None:
        if self._status_var:
            self._status_var.set(evt.text)

    def _on_title(self, evt: EVT.EvtTitle) -> None:
        if self._title_var:
            self._title_var.set(evt.text)
        if self._root:
            self._root.title(f"bidi_rename2 — {evt.text}")

    def _on_dirty(self, evt: EVT.EvtDirty) -> None:
        if self._dirty_var:
            self._dirty_var.set(" ●" if evt.is_dirty else "")

    def _on_chapter_changed(self, evt: EVT.EvtChapterChanged) -> None:
        self._highlight_thumb(evt.index)
        if self._vf:
            ch = self._vf.chapters[evt.index] if evt.index < len(self._vf.chapters) else None
            if ch:
                self._seek_slider.set_position(ch.timestamp_sec)
                self._update_crop_fields(ch.crop_effective)
        if self._seek_slider:
            self._seek_slider.set_active(evt.index)
            
    def _on_chapters_updated(self, evt: EVT.EvtChaptersUpdated) -> None:
        if self._vf is None:
            return
        if evt.full_rebuild:
            # Ajout/suppression de chapitre → recréer tous les widgets
            self._rebuild_thumb_strip()
        else:
            # Juste timestamp/durée modifiés → update label uniquement
            self._update_thumb_cell(evt.chapter_index)
        self._seek_slider.reset(self._vf.chapters, self._vf.total_duration_sec)

    def _on_crop_changed(self, evt: EVT.EvtCropChanged) -> None:
        if self._vf and evt.chapter_index == self._vf.active_index:
            self._update_crop_fields(evt.crop)

    def _on_all_crops_invalidated(self, evt: EVT.EvtAllCropsInvalidated) -> None:
        for lbl in self._thumb_frames:
            lbl.configure(image="")
        if self._canvas:
            self._canvas.delete("all")

    def _on_frame_ready(self, evt: EVT.EvtFrameReady) -> None:
        if self._canvas is None:
            return
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return
        img  = evt.image.resize((cw, ch))
        photo = ImageTk.PhotoImage(img)
        self._canvas_image = photo   # garder référence
        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        # Mémoriser scale pour le drag
        if self._vf and self._vf.video_w > 0:
            self._canvas_scale = cw / self._vf.video_w

    def _on_thumb_ready(self, evt: EVT.EvtThumbReady) -> None:
        idx = evt.chapter_index
        if idx >= len(self._thumb_frames):
            return
        lbl   = self._thumb_frames[idx]
        img   = evt.image.resize((THUMB_W, THUMB_H))
        photo = ImageTk.PhotoImage(img)
        # Garder la référence dans la liste
        while len(self._thumb_images) <= idx:
            self._thumb_images.append(None)
        self._thumb_images[idx] = photo
        lbl.configure(image=photo)

    def _on_position_changed(self, evt: EVT.EvtPositionChanged) -> None:
        if self._seek_slider:
            self._seek_slider.set_position(evt.timestamp_sec)

    # ── Thumb strip ────────────────────────────────────────────────────────

    def _rebuild_thumb_strip(self) -> None:
        """Recrée tous les widgets (ajout/suppression de chapitre)."""
        if self._vf is None:
            return
        for w in self._strip_frame.winfo_children():
            w.destroy()
        self._thumb_frames  = []
        self._thumb_images  = []
        self._thumb_labels  = []   # labels texte (timestamp + durée)
        for i, ch in enumerate(self._vf.chapters):
            cell = tk.Frame(self._strip_frame, bg="#111", bd=1, relief=tk.RAISED)
            cell.pack(side=tk.LEFT, padx=2, pady=2)
            lbl_img = tk.Label(cell, bg="#111", width=THUMB_W, height=THUMB_H,
                               cursor="hand2")
            lbl_img.pack()
            lbl_img.bind("<Button-1>", lambda _, idx=i: self._on_thumb_click(idx))
            lbl_txt = tk.Label(cell, text=self._chapter_label(ch),
                               bg="#111", fg=FG, font=FONT_LABEL)
            lbl_txt.pack()
            self._thumb_frames.append(lbl_img)
            self._thumb_images.append(None)
            self._thumb_labels.append(lbl_txt)

    def _update_thumb_cell(self, index: int) -> None:
        """Met à jour label texte d'une cellule existante (sans recréer les widgets)."""
        if self._vf is None or index >= len(self._thumb_labels):
            return
        ch = self._vf.chapters[index]
        self._thumb_labels[index].configure(text=self._chapter_label(ch))

    @staticmethod
    def _chapter_label(ch: "Chapter") -> str:
        dur = f" {ch.duration_sec}s" if ch.duration_sec else ""
        return f"{ch.timestamp_raw}{dur}"
        
    def _highlight_thumb(self, active_index: int) -> None:
        for i, lbl in enumerate(self._thumb_frames):
            lbl.master.configure(bg=ACCENT if i == active_index else "#111")

    # ── Drag crop sur canvas ───────────────────────────────────────────────

    def _on_canvas_resize(self, event=None) -> None:
        if self._vf and self._vf.video_w > 0 and self._canvas:
            self._canvas_scale = self._canvas.winfo_width() / self._vf.video_w

    def _on_mouse_press(self, event: tk.Event) -> None:
        if self._vf is None:
            return
        ch = self._vf.active_chapter
        if ch is None or ch.crop_effective is None:
            return
        from video_processor.infra.renderer import Renderer
        handles = Renderer._handles(ch.crop_effective, self._canvas_scale)
        from video_processor.infra.renderer import Renderer, HANDLE_R
        handles = Renderer._handles(ch.crop_effective, self._canvas_scale)
        tol = max(HANDLE_R, int(HANDLE_R * self._canvas_scale)) + 4
        for i, (hx, hy) in enumerate(handles):
            if abs(event.x - hx) <= tol and abs(event.y - hy) <= tol:
                self._drag_state = {
                    "mode": "resize", "handle_idx": i,
                    "snap_x": event.x, "snap_y": event.y,
                    "crop0": ch.crop_effective,
                }
                return
        # Cherche move (clic dans le rectangle crop)
        c    = ch.crop_effective
        s    = self._canvas_scale
        cx1  = int(c.pos_x * s)
        cy1  = int(c.pos_y * s)
        cx2  = cx1 + int(c.w * s)
        cy2  = cy1 + int(c.h * s)
        if cx1 <= event.x <= cx2 and cy1 <= event.y <= cy2:
            self._drag_state = {
                "mode": "move",
                "snap_x": event.x, "snap_y": event.y,
                "crop0": c,
            }

    def _on_mouse_move(self, event: tk.Event) -> None:
        if self._drag_state is None or self._vf is None:
            return
        d  = self._drag_state
        s  = self._canvas_scale
        # Toujours lire le crop effectif courant (pas crop0 figé)
        ch = self._vf.active_chapter if self._vf else None
        if ch is None or ch.crop_effective is None:
            return
        c0 = ch.crop_effective
        # Snap relatif à la position actuelle (pas au press initial)
        dx = int((event.x - d["snap_x"]) / s)
        dy = int((event.y - d["snap_y"]) / s)
        d["snap_x"] = event.x   # glissement relatif au pixel précédent
        d["snap_y"] = event.y

        if d["mode"] == "move":
            self._send(CMD.CmdSetCrop(
                pos_x=c0.pos_x + dx,
                pos_y=c0.pos_y + dy,
            ))
        else:
            # Resize selon poignée (8 poignées : coins + milieux)
            h_idx = d["handle_idx"]
            new_w, new_h = c0.w, c0.h
            new_x, new_y = c0.pos_x, c0.pos_y
            # Poignées 0,1,2 → bord haut (modifie y et h)
            if h_idx in (0, 1, 2):
                new_y = c0.pos_y + dy
                new_h = c0.h    - dy
            # Poignées 4,5,6 → bord bas (modifie h)
            if h_idx in (4, 5, 6):
                new_h = c0.h + dy
            # Poignées 0,7,6 → bord gauche (modifie x et w)
            if h_idx in (0, 7, 6):
                new_x = c0.pos_x + dx
                new_w = c0.w     - dx
            # Poignées 2,3,4 → bord droit (modifie w)
            if h_idx in (2, 3, 4):
                new_w = c0.w + dx
            self._send(CMD.CmdSetCrop(
                w=max(10, new_w), h=max(10, new_h),
                pos_x=new_x, pos_y=new_y,
            ))

    def _on_mouse_release(self, event: tk.Event) -> None:
        if self._drag_state is not None and self._vf is not None:
            # Demander un re-render du thumbnail du chapitre actif
            self._send(CMD.CmdRefreshThumb(
                chapter_index=self._vf.active_index
            ))
        self._drag_state = None

    def _on_mouse_hover(self, event: tk.Event) -> None:
        if self._vf is None or self._canvas is None:
            return
        ch = self._vf.active_chapter
        if ch is None or ch.crop_effective is None:
            self._canvas.configure(cursor="crosshair")
            return
        from video_processor.infra.renderer import Renderer, HANDLE_R
        handles = Renderer._handles(ch.crop_effective, self._canvas_scale)
        tol = max(HANDLE_R, int(HANDLE_R * self._canvas_scale)) + 4
        for i, (hx, hy) in enumerate(handles):
            if abs(event.x - hx) <= tol and abs(event.y - hy) <= tol:
                self._canvas.configure(cursor=HANDLE_CURSORS[i])
                return
        # Dans le rectangle crop → fleur (move)
        c   = ch.crop_effective
        s   = self._canvas_scale
        cx1 = int(c.pos_x * s)
        cy1 = int(c.pos_y * s)
        cx2 = cx1 + int(c.w * s)
        cy2 = cy1 + int(c.h * s)
        if cx1 <= event.x <= cx2 and cy1 <= event.y <= cy2:
            self._canvas.configure(cursor="fleur")
        else:
            self._canvas.configure(cursor="crosshair")

    # ── Spinbox crop ──────────────────────────────────────────────────────

    def _on_crop_spinbox(self) -> None:
        if self._var_w and self._var_h:
            self._send(CMD.CmdSetCrop(
                w=self._var_w.get(),
                h=self._var_h.get(),
            ))

    def _on_position_spinbox(self) -> None:
        if self._var_x and self._var_y:
            self._send(CMD.CmdSetCrop(
                pos_x=self._var_x.get(),
                pos_y=self._var_y.get(),
            ))

    def _update_crop_fields(self, crop: Optional["CropZone"]) -> None:
        if crop is None:
            return
        if self._var_w:
            self._var_w.set(crop.w)
        if self._var_h:
            self._var_h.set(crop.h)
        if self._var_x:
            self._var_x.set(crop.pos_x)
        if self._var_y:
            self._var_y.set(crop.pos_y)

    # ── Interactions ──────────────────────────────────────────────────────

    def _on_thumb_click(self, chapter_index: int) -> None:
        self._send(CMD.CmdJump(chapter_index=chapter_index))

    def _on_seek_click(self, ts_sec: int) -> None:
        self._send(CMD.CmdSeekAbs(timestamp_sec=ts_sec))

    def _on_file_combo_selected(self) -> None:
        from pathlib import Path
        name = self._file_var.get()
        if self._vf and name != self._vf.short_name:
            self._send(CMD.CmdLoadFile(path=self._vf.physical_path.parent / name))

    # ── run ───────────────────────────────────────────────────────────────

    def run(self) -> None:
        self._root = tk.Tk()
        self._root.geometry("1280x800")
        self._build()
        self._root.after(50, self._poll)
        self._root.mainloop()