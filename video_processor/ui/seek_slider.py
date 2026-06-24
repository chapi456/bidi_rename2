"""
File: seek_slider.py
Path: video_processor/ui/seek_slider.py

Version: 1.0.0
Date: 2026-06-24

Changelog:
- 1.0.0 (2026-06-24): Implémentation complète
  * SeekSlider : widget Canvas Tkinter autonome
  * Segments colorés par chapitre, poignées de bord drag start/end
  * Clic → CmdSeekAbs, drag start/end → CmdChapterEdge via callback send
  * Mise à jour position curseur via set_position()
  * reset() pour rechargement complet (nouveau VideoFile)
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from video_processor.domain.chapter import Chapter

# Constantes visuelles
H            = 28       # hauteur du canvas
CURSOR_W     = 2        # largeur du curseur de position
HANDLE_W     = 8        # largeur des poignées start/end
COLORS = [
    "#4A90D9", "#E67E22", "#2ECC71", "#9B59B6",
    "#E74C3C", "#1ABC9C", "#F39C12", "#3498DB",
]
COLOR_CURSOR  = "#FFFFFF"
COLOR_HANDLE  = "#FFD700"
COLOR_BG      = "#1A1A1A"


class SeekSlider(tk.Canvas):
    """Barre de seek avec segments chapitres et poignées de bord.

    Usage :
        slider = SeekSlider(parent, send=controller.send)
        slider.reset(chapters, total_duration_sec)
        slider.set_position(ts_sec)
    """

    def __init__(self, parent: tk.Widget, send: Callable[[object], None]) -> None:
        super().__init__(parent, height=H, bg=COLOR_BG, cursor="crosshair",
                         highlightthickness=0)
        self._send          = send
        self._chapters:     list["Chapter"] = []
        self._total_sec:    int             = 1
        self._current_ts:   int             = 0
        self._drag:         Optional[dict]  = None   # {kind, ch_index}

        self.bind("<Configure>",     self._redraw)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>",     self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)

    # ── API publique ───────────────────────────────────────────────────────

    def reset(self, chapters: list["Chapter"], total_sec: int) -> None:
        self._chapters  = chapters
        self._total_sec = max(total_sec, 1)
        self._redraw()

    def set_position(self, ts_sec: int) -> None:
        self._current_ts = ts_sec
        self._redraw()

    # ── Dessin ─────────────────────────────────────────────────────────────

    def _redraw(self, _event=None) -> None:
        self.delete("all")
        W = self.winfo_width()
        if W <= 1:
            return

        # Segments chapitres
        for i, ch in enumerate(self._chapters):
            x1 = self._ts_to_x(ch.timestamp_sec, W)
            end = ch.timestamp_sec + (ch.duration_sec or 0)
            x2  = self._ts_to_x(end, W) if ch.duration_sec else (
                self._ts_to_x(self._chapters[i + 1].timestamp_sec, W)
                if i + 1 < len(self._chapters) else W
            )
            color = COLORS[i % len(COLORS)]
            self.create_rectangle(x1, 2, x2, H - 2, fill=color, outline="")

            # Poignée start (sauf ch[0])
            if i > 0:
                self.create_rectangle(
                    x1 - HANDLE_W // 2, 0, x1 + HANDLE_W // 2, H,
                    fill=COLOR_HANDLE, outline="", tags=f"hs_{i}",
                )
            # Poignée end si duration explicite
            if ch.duration_sec:
                self.create_rectangle(
                    x2 - HANDLE_W // 2, 0, x2 + HANDLE_W // 2, H,
                    fill=COLOR_HANDLE, outline="", tags=f"he_{i}",
                )

        # Curseur position courante
        xc = self._ts_to_x(self._current_ts, W)
        self.create_line(xc, 0, xc, H, fill=COLOR_CURSOR, width=CURSOR_W)

    # ── Interactions ───────────────────────────────────────────────────────

    def _on_press(self, event: tk.Event) -> None:
        from video_processor.controller import commands as CMD
        W = self.winfo_width()

        # Cherche poignée start/end sous le curseur
        for i, ch in enumerate(self._chapters):
            xs = self._ts_to_x(ch.timestamp_sec, W)
            if i > 0 and abs(event.x - xs) <= HANDLE_W:
                self._drag = {"kind": "start", "ch_index": i}
                return
            if ch.duration_sec:
                xe = self._ts_to_x(ch.timestamp_sec + ch.duration_sec, W)
                if abs(event.x - xe) <= HANDLE_W:
                    self._drag = {"kind": "end", "ch_index": i}
                    return

        # Sinon : seek simple
        ts = self._x_to_ts(event.x, W)
        self._send(CMD.CmdSeekAbs(timestamp_sec=ts))

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag is None:
            return
        W  = self.winfo_width()
        ts = self._x_to_ts(event.x, W)
        ch = self._chapters[self._drag["ch_index"]]
        # Preview visuel uniquement (pas de commande avant release)
        self._current_ts = ts
        self._redraw()

    def _on_release(self, event: tk.Event) -> None:
        from video_processor.controller import commands as CMD
        if self._drag is None:
            return
        W   = self.winfo_width()
        ts  = self._x_to_ts(event.x, W)
        d   = self._drag
        ch  = self._chapters[d["ch_index"]]
        self._send(CMD.CmdChapterEdge(
            index=d["ch_index"],
            kind=d["kind"],
            timestamp_sec=ts if d["kind"] == "start" else ch.timestamp_sec,
            duration_sec=(ts - ch.timestamp_sec) if d["kind"] == "end" else ch.duration_sec,
        ))
        self._drag = None

    # ── Conversion coords ──────────────────────────────────────────────────

    def _ts_to_x(self, ts: int, W: int) -> int:
        return int(ts / self._total_sec * W)

    def _x_to_ts(self, x: int, W: int) -> int:
        return max(0, min(int(x / W * self._total_sec), self._total_sec))