"""
File: seek_slider.py
Path: video_processor/ui/seek_slider.py

Version: 2.0.0
Date: 2026-06-24

Changelog:
- 2.0.0 (2026-06-24): Refonte visuelle et interactions
  * Layout : ruler (haut, H_RULER px) + piste seek (bas, H_SEEK px)
  * Triangles pointant vers le bas dans la piste, sur les bornes de chapitres
  * Durée du chapitre affichée dans le segment pendant le drag
  * Clic dans la piste → seek ; clic/drag sur triangle → déplace borne
  * Double-clic sur triangle → seek précis à la borne
  * Hit-test séparé : y < H_RULER → poignée ; y >= H_RULER → seek
- 1.0.0 (2026-06-24): Implémentation initiale
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from video_processor.domain.chapter import Chapter

# ── Constantes visuelles ──────────────────────────────────────────────────────
H_RULER  = 9   # hauteur ruler (segments colorés + triangles)
H_SEEK   = 19   # hauteur piste seek (fond sombre)
H        = H_RULER + H_SEEK

CURSOR_W    = 2
HANDLE_W    = 10   # demi-base du triangle
HANDLE_TOL  = 8    # tolérance hit-test en px
COLORS = [
    "#4A90D9", "#E67E22", "#2ECC71", "#9B59B6",
    "#E74C3C", "#1ABC9C", "#F39C12", "#3498DB",
]
COLOR_CURSOR   = "#FFFFFF"
COLOR_HANDLE   = "#FFD700"
COLOR_HANDLE_H = "#FFFFFF"   # triangle survolé
COLOR_BG_SEEK  = "#2A2A2A"
COLOR_ACTIVE_SEG = "#1A3A5C"   # bleu sombre pour chapitre actif dans la piste
COLOR_BG       = "#1A1A1A"
COLOR_DURATION = "#FFFFFF"
FONT_DUR       = ("Helvetica", 8)


class SeekSlider(tk.Canvas):
    """Barre de seek avec segments chapitres et poignées triangulaires.

    Layout vertical :
      [0 .. H_RULER]  ruler : segments colorés par chapitre + triangles bornes
      [H_RULER .. H]  piste : fond sombre, curseur position courante

    Interactions :
      - Clic dans piste (y >= H_RULER)      → CmdSeekAbs
      - Clic/drag sur triangle (y < H_RULER) → déplace borne chapitre
      - Double-clic sur triangle             → seek précis à la borne
      - Drag : durée affichée en live dans le segment
    """

    def __init__(self, parent: tk.Widget, send: Callable[[object], None]) -> None:
        super().__init__(parent, height=H, bg=COLOR_BG, cursor="crosshair",
                         highlightthickness=0)
        self._send       = send
        self._chapters:  list["Chapter"] = []
        self._total_sec: int             = 1
        self._current_ts: int            = 0
        self._drag:      Optional[dict]  = None   # {kind, ch_index, ts_preview}
        self._hover_tag: Optional[str]   = None
        self._active_index: int          = 0

        self.bind("<Configure>",       self._redraw)
        self.bind("<ButtonPress-1>",   self._on_press)
        self.bind("<Double-Button-1>", self._on_double_click)
        self.bind("<B1-Motion>",       self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Motion>",          self._on_hover)
        self.bind("<Leave>",           self._on_leave)

    # ── API publique ───────────────────────────────────────────────────────

    def reset(self, chapters: list["Chapter"], total_sec: int) -> None:
        self._chapters   = chapters
        self._total_sec  = max(total_sec, 1)
        self._drag       = None
        self._redraw()

    def set_position(self, ts_sec: int) -> None:
        self._current_ts = ts_sec
        self._redraw()

    def update_chapter(self, index: int) -> None:
        """Mise à jour légère d'un seul chapitre (timestamp/durée changés)."""
        self._redraw()

    def set_active(self, index: int) -> None:
        self._active_index = index
        self._redraw()

    # ── Dessin ─────────────────────────────────────────────────────────────

    def _redraw(self, _event=None) -> None:
        self.delete("all")
        W = self.winfo_width()
        if W <= 1:
            return

        # ── Piste seek (bas) ──────────────────────────────────────────────

        # Fond piste : bleu clair pour actif, orange pour les autres
        for i, ch in enumerate(self._chapters):
            x1    = self._ts_to_x(ch.timestamp_sec, W)
            x2    = self._chapter_end_x(i, W)
            color = "#1A4A7A" if i == self._active_index else "#5A3010"
            self.create_rectangle(x1, H_RULER, x2, H, fill=color, outline="")
        # Zones hors chapitres (avant ch[0] et après dernier)
        if self._chapters:
            x0 = self._ts_to_x(self._chapters[0].timestamp_sec, W)
            if x0 > 0:
                self.create_rectangle(0, H_RULER, x0, H,
                                      fill=COLOR_BG_SEEK, outline="")
            xl = self._chapter_end_x(len(self._chapters) - 1, W)
            if xl < W:
                self.create_rectangle(xl, H_RULER, W, H,
                                      fill=COLOR_BG_SEEK, outline="")

        # ── Ruler : segments + triangles ──────────────────────────────────
        for i, ch in enumerate(self._chapters):
            x1   = self._ts_to_x(ch.timestamp_sec, W)
            x2   = self._chapter_end_x(i, W)
            # Pas de couleur dans le ruler — triangles seulement
            # Durée live dans le ruler si drag en cours sur CE chapitre
            if self._drag and self._drag["ch_index"] == i:
                label = self._segment_label(i)
                if label and (x2 - x1) > 20:
                    self.create_text(
                        (x1 + x2) // 2, H_RULER // 2,
                        text=label, fill=COLOR_DURATION,
                        font=FONT_DUR, anchor=tk.CENTER,
                    )

            # Triangle borne start
            self._draw_triangle(x1, f"hs_{i}", COLOR_HANDLE)

            # Triangle borne end si duration explicite
            if ch.duration_sec:
                self._draw_triangle(x2, f"he_{i}", COLOR_HANDLE)

        # ── Curseur position courante (toute hauteur) ──────────────────────
        xc = self._ts_to_x(self._current_ts, W)
        self.create_line(xc, 0, xc, H,
                         fill=COLOR_CURSOR, width=CURSOR_W, tags="cursor")

    def _draw_triangle(self, x: int, tag: str, color: str) -> None:
        """Triangle pointant vers le bas, base en haut du ruler."""
        self.create_polygon(
            x - HANDLE_W // 2, 0,
            x + HANDLE_W // 2, 0,
            x,                 H_RULER - 2,
            fill=color, outline="", tags=tag,
        )

    def _segment_label(self, i: int) -> str:
        """Retourne la durée à afficher dans le segment (live pendant drag)."""
        ch = self._chapters[i]
        # Pendant drag sur ce chapitre : durée preview
        if self._drag and self._drag["ch_index"] == i:
            ts_preview = self._drag.get("ts_preview", ch.timestamp_sec)
            if self._drag["kind"] == "start":
                dur = (ch.timestamp_sec + (ch.duration_sec or 0)) - ts_preview
            else:
                dur = ts_preview - ch.timestamp_sec
            return self._fmt_dur(max(0, dur))
        # Sinon durée normale
        if ch.duration_sec:
            return self._fmt_dur(ch.duration_sec)
        return ""

    @staticmethod
    def _fmt_dur(sec: int) -> str:
        m, s = divmod(sec, 60)
        return f"{m}:{s:02d}"

    # ── Hit-test poignées ──────────────────────────────────────────────────

    def _find_handle(self, x: int) -> Optional[dict]:
        """Retourne {kind, ch_index} si x est sur une poignée, None sinon."""
        W = self.winfo_width()
        for i, ch in enumerate(self._chapters):
            if i > 0:
                xs = self._ts_to_x(ch.timestamp_sec, W)
                if abs(x - xs) <= HANDLE_TOL:
                    return {"kind": "start", "ch_index": i}
            if ch.duration_sec:
                xe = self._ts_to_x(ch.timestamp_sec + ch.duration_sec, W)
                if abs(x - xe) <= HANDLE_TOL:
                    return {"kind": "end", "ch_index": i}
        return None

    # ── Interactions ───────────────────────────────────────────────────────

    def _on_press(self, event: tk.Event) -> None:
        from video_processor.controller import commands as CMD

        # Zone ruler → cherche poignée uniquement
        if event.y < H_RULER:
            h = self._find_handle(event.x)
            if h:
                self._drag = {**h, "ts_preview": None}
            return

        # Zone piste → seek
        ts      = self._x_to_ts(event.x)
        ch_idx  = self._chapter_at_ts(ts)
        if ch_idx != self._active_index:
            self._send(CMD.CmdJump(chapter_index=ch_idx))
        else:
            self._send(CMD.CmdSeekAbs(timestamp_sec=ts))

    def _on_double_click(self, event: tk.Event) -> None:
        """Double-clic sur triangle → seek précis à la borne."""
        from video_processor.controller import commands as CMD
        if event.y >= H_RULER:
            return
        h = self._find_handle(event.x)
        if h is None:
            return
        ch = self._chapters[h["ch_index"]]
        ts = ch.timestamp_sec if h["kind"] == "start" else (
            ch.timestamp_sec + (ch.duration_sec or 0)
        )
        self._send(CMD.CmdSeekAbs(timestamp_sec=ts))

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag is None:
            return
        from video_processor.controller import commands as CMD
        ts = self._x_to_ts(event.x)
        self._drag["ts_preview"] = ts
        self._redraw()
        # Preview live : charge la frame à la position draguée
        self._send(CMD.CmdSeekAbs(timestamp_sec=ts))

    def _on_release(self, event: tk.Event) -> None:
        from video_processor.controller import commands as CMD
        if self._drag is None:
            return
        d  = self._drag
        ts = self._x_to_ts(event.x)
        ch = self._chapters[d["ch_index"]]
        self._send(CMD.CmdChapterEdge(
            index=d["ch_index"],
            kind=d["kind"],
            timestamp_sec=ts         if d["kind"] == "start" else ch.timestamp_sec,
            duration_sec=(ts - ch.timestamp_sec) if d["kind"] == "end"   else (ch.duration_sec or 0),
        ))
        self._drag = None
        self._redraw()

    def _on_hover(self, event: tk.Event) -> None:
        if event.y >= H_RULER:
            self.configure(cursor="crosshair")
            return
        h = self._find_handle(event.x)
        if h:
            self.configure(cursor="sb_h_double_arrow")
        else:
            self.configure(cursor="crosshair")

    def _on_leave(self, _event=None) -> None:
        self.configure(cursor="crosshair")

    # ── Conversion coords ──────────────────────────────────────────────────

    def _chapter_at_ts(self, ts: int) -> int:
        """Retourne l'index du chapitre contenant ts."""
        result = 0
        for i, ch in enumerate(self._chapters):
            if ch.timestamp_sec <= ts:
                result = i
        return result

    def _ts_to_x(self, ts: int, W: Optional[int] = None) -> int:
        if W is None:
            W = self.winfo_width()
        return int(ts / self._total_sec * W)

    def _x_to_ts(self, x: int, W: Optional[int] = None) -> int:
        if W is None:
            W = self.winfo_width()
        return max(0, min(int(x / W * self._total_sec), self._total_sec))

    def _chapter_end_x(self, i: int, W: int) -> int:
        ch = self._chapters[i]
        if ch.duration_sec:
            return self._ts_to_x(ch.timestamp_sec + ch.duration_sec, W)
        if i + 1 < len(self._chapters):
            return self._ts_to_x(self._chapters[i + 1].timestamp_sec, W)
        return W