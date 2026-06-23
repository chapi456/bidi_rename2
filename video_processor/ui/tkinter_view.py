"""
File: tkinter_view.py
Path: video_processor/ui/tkinter_view.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging
import queue
import tkinter as tk
from typing import Optional

from .base_view import BaseView
from video_processor.controller import commands as CMD
from video_processor.controller import events as EVT

log = logging.getLogger("ui.tkinter_view")


class TkinterView(BaseView):
    """Vue Tkinter. Reçoit des EVT_*, envoie des CMD_* via self._send()."""

    def __init__(self):
        log.debug("BOUCHON TkinterView.__init__()")
        self._root:  Optional[tk.Tk] = None
        self._evt_q: queue.Queue     = queue.Queue()  # bridge thread-safe

    # ── Liaison contrôleur ─────────────────────────────────────────────

    def _on_event(self, event: object) -> None:
        """Reçu depuis n'importe quel thread → mise en queue pour le thread Tk."""
        self._evt_q.put(event)

    def _poll(self) -> None:
        """Dépile les événements en attente dans le thread Tk (via after)."""
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
        """Route chaque type d'événement vers le bon handler UI."""
        log.debug("BOUCHON TkinterView._dispatch(%s)", type(event).__name__)
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
        }
        h = handlers.get(type(event))
        if h:
            h(event)
        else:
            log.warning("BOUCHON événement non géré : %s", type(event).__name__)

    # ── Construction UI ────────────────────────────────────────────────

    def _build(self) -> None:
        """Construit tous les widgets.
        Règle pack : BOTTOM d'abord (strip, seekbar, status), puis body au centre.
        """
        log.debug("BOUCHON TkinterView._build()")
        self._build_title_bar()
        self._build_file_selector()
        self._build_status_bar()
        self._build_thumb_strip()
        self._build_seek_slider()
        self._build_left_panel()
        self._build_right_panel()
        self._build_canvas()

    def _build_title_bar(self) -> None:
        log.debug("BOUCHON TkinterView._build_title_bar()")

    def _build_file_selector(self) -> None:
        """Combobox liste des fichiers de la session."""
        log.debug("BOUCHON TkinterView._build_file_selector()")

    def _build_status_bar(self) -> None:
        """Barre de statut en bas de fenêtre."""
        log.debug("BOUCHON TkinterView._build_status_bar()")

    def _build_canvas(self) -> None:
        """Canvas principal d'affichage de la frame courante + overlay crop."""
        log.debug("BOUCHON TkinterView._build_canvas()")

    def _build_seek_slider(self) -> None:
        """Slider horizontal avec segments chapitres et poignées de bord."""
        log.debug("BOUCHON TkinterView._build_seek_slider()")

    def _build_thumb_strip(self) -> None:
        """Bande horizontale de vignettes (une par chapitre)."""
        log.debug("BOUCHON TkinterView._build_thumb_strip()")

    def _build_left_panel(self) -> None:
        """Panneau gauche : taille crop (L/H), navigation, actions."""
        log.debug("BOUCHON TkinterView._build_left_panel()")

    def _build_right_panel(self) -> None:
        """Panneau droit : position crop (X/Y), presets, seek."""
        log.debug("BOUCHON TkinterView._build_right_panel()")

    # ── Handlers événements → UI ──────────────────────────────────────────

    def _on_session_loaded(self, evt: EVT.EvtSessionLoaded) -> None:
        """Reconstruire le strip, réinitialiser canvas, mettre à jour combobox."""
        log.debug("BOUCHON _on_session_loaded(%s)", evt.video_file.short_name)

    def _on_status(self, evt: EVT.EvtStatus) -> None:
        """Mettre à jour la barre de statut."""
        log.debug("BOUCHON _on_status(%s)", evt.text)

    def _on_title(self, evt: EVT.EvtTitle) -> None:
        """Mettre à jour le titre de fenêtre."""
        log.debug("BOUCHON _on_title(%s)", evt.text)

    def _on_dirty(self, evt: EVT.EvtDirty) -> None:
        """Indiquer visuellement les modifications non sauvegardées."""
        log.debug("BOUCHON _on_dirty(dirty=%s)", evt.is_dirty)

    def _on_chapter_changed(self, evt: EVT.EvtChapterChanged) -> None:
        """Surligner la vignette active, mettre à jour seek slider et panneaux."""
        log.debug("BOUCHON _on_chapter_changed(idx=%d)", evt.index)

    def _on_chapters_updated(self, evt: EVT.EvtChaptersUpdated) -> None:
        """Reconstruire le strip et le seekbar."""
        log.debug("BOUCHON _on_chapters_updated(%d chapitres)", len(evt.chapters))

    def _on_crop_changed(self, evt: EVT.EvtCropChanged) -> None:
        """Mettre à jour champs L/H/X/Y si chapitre actif concerné."""
        log.debug("BOUCHON _on_crop_changed(ch=%d inherited=%s)",
                  evt.chapter_index, evt.inherited)

    def _on_all_crops_invalidated(self, evt: EVT.EvtAllCropsInvalidated) -> None:
        """Vider toutes les vignettes (EvtThumbReady vont arriver)."""
        log.debug("BOUCHON _on_all_crops_invalidated()")

    def _on_frame_ready(self, evt: EVT.EvtFrameReady) -> None:
        """Afficher evt.image sur le canvas principal."""
        log.debug("BOUCHON _on_frame_ready(ch=%d)", evt.chapter_index)

    def _on_thumb_ready(self, evt: EVT.EvtThumbReady) -> None:
        """Afficher evt.image dans la cellule du strip."""
        log.debug("BOUCHON _on_thumb_ready(ch=%d)", evt.chapter_index)

    # ── Interactions canvas (drag crop) ──────────────────────────────────

    def _on_canvas_resize(self, event=None) -> None:
        """Recalcule scale, demande re-render via CmdSetCrop si nécessaire."""
        log.debug("BOUCHON TkinterView._on_canvas_resize()")

    def _on_mouse_press(self, event) -> None:
        """Détecte hit (handle ou move), démarre drag avec snapshot position."""
        log.debug("BOUCHON TkinterView._on_mouse_press(%d,%d)", event.x, event.y)

    def _on_mouse_move(self, event) -> None:
        """Calcule delta depuis snapshot, envoie CmdSetCrop pour preview."""
        log.debug("BOUCHON TkinterView._on_mouse_move(%d,%d)", event.x, event.y)

    def _on_mouse_release(self, event) -> None:
        """Finalise drag : envoie CmdSetCrop définitif."""
        log.debug("BOUCHON TkinterView._on_mouse_release()")

    def _on_thumb_click(self, chapter_index: int) -> None:
        """Clic sur une vignette → CmdJump."""
        log.debug("BOUCHON TkinterView._on_thumb_click(ch=%d)", chapter_index)
        self._send(CMD.CmdJump(chapter_index=chapter_index))

    def _on_seek_click(self, ts_sec: int) -> None:
        """Clic sur la seekbar → CmdSeekAbs."""
        log.debug("BOUCHON TkinterView._on_seek_click(ts=%d)", ts_sec)
        self._send(CMD.CmdSeekAbs(timestamp_sec=ts_sec))

    # ── run ─────────────────────────────────────────────────────────────────

    def run(self) -> None:
        log.debug("BOUCHON TkinterView.run()")
        self._root = tk.Tk()
        self._build()
        self._root.after(50, self._poll)
        self._root.mainloop()
