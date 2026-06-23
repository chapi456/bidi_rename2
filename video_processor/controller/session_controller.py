"""
File: session_controller.py
Path: video_processor/controller/session_controller.py

Version: 0.3.0
Date: 2026-06-23

Changelog:
- 0.3.0 (2026-06-23): Suppression config du __init__ — AppConfig.instance() en interne
  * Plus de passage de config au constructeur
  * Correction typage : _vf déclaré Optional[VideoFile] avec valeur par défaut
  * _invalidate_and_reload : guard _require_vf() déjà présent, accès à active_index sécurisé
- 0.2.0 (2026-06-23): Fichier complet — handlers manquants ajoutés
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

from video_processor.domain.session   import VideoSession
from video_processor.domain.video_file import VideoFile
from video_processor.domain.chapter   import Chapter
from video_processor.domain.crop_zone  import CropZone
from video_processor.controller import commands as CMD
from video_processor.controller import events   as EVT

log = logging.getLogger("controller.session")

EventHandler = Callable[[object], None]


class SessionController:
    """Orchestre session, domaine et infrastructure.
    Reçoit des commandes (send), émet des événements (subscribe).
    Thread-safe : les commandes peuvent venir de n'importe quel thread.
    """

    def __init__(self, session: VideoSession) -> None:
        log.debug("BOUCHON SessionController.__init__()")
        self._session:    VideoSession         = session
        self._vf:         Optional[VideoFile]  = None
        self._handlers:   list[EventHandler]   = []
        self._lock        = threading.Lock()
        self._current_ts: int                  = 0   # timestamp affiché (secondes)

    # ── Config interne ────────────────────────────────────────────────────

    @property
    def _cfg(self):
        """Accès lazy à AppConfig — pas de dépendance au constructeur."""
        from video_processor.infra.config_loader import AppConfig
        return AppConfig.instance()

    # ── Abonnements événements ────────────────────────────────────────────

    def subscribe(self, handler: EventHandler) -> None:
        """La vue appelle subscribe(self._on_event) pour recevoir tous les évts."""
        self._handlers.append(handler)

    def _emit(self, event: object) -> None:
        """Diffuse un événement à tous les abonnés (dans le thread appelant)."""
        log.debug("SessionController._emit(%s)", type(event).__name__)
        for h in self._handlers:
            h(event)

    # ── Point d'entrée ────────────────────────────────────────────────────

    def open_current(self) -> None:
        """Charge le fichier courant de la session et émet EvtSessionLoaded."""
        log.debug("BOUCHON SessionController.open_current()")
        entry = self._session.current_entry
        if entry is None:
            self._emit(EVT.EvtStatus("Aucun fichier dans la session."))
            return
        self._load_entry(entry.physical_path)

    # ── Dispatch commandes ────────────────────────────────────────────────

    def send(self, cmd: object) -> None:
        """Point d'entrée unique pour toutes les commandes."""
        log.debug("SessionController.send(%s)", type(cmd).__name__)
        dispatch = {
            CMD.CmdJump:             self._on_jump,
            CMD.CmdSeekAbs:          self._on_seek_abs,
            CMD.CmdSeekDelta:        self._on_seek_delta,
            CMD.CmdAddCrop:          self._on_add_crop,
            CMD.CmdDelCrop:          self._on_del_crop,
            CMD.CmdSetCrop:          self._on_set_crop,
            CMD.CmdSetPosition:      self._on_set_position,
            CMD.CmdValidateChapter:  self._on_validate_chapter,
            CMD.CmdPrevChapter:      self._on_prev_chapter,
            CMD.CmdAddChapter:       self._on_add_chapter,
            CMD.CmdEditChapter:      self._on_edit_chapter,
            CMD.CmdChapterEdge:      self._on_chapter_edge,
            CMD.CmdSave:             self._on_save,
            CMD.CmdNextFile:         self._on_next_file,
            CMD.CmdLoadFile:         self._on_load_file,
            CMD.CmdQuit:             self._on_quit,
        }
        handler = dispatch.get(type(cmd))
        if handler:
            handler(cmd)
        else:
            log.warning("Commande inconnue : %s", type(cmd).__name__)

    # ── Chargement fichier ────────────────────────────────────────────────

    def _load_entry(self, path: Path) -> None:
        """Parse, ffprobe, résout héritage, émet EvtSessionLoaded + lance preload.

        Séquence à implémenter :
        1. TocutFile.load(dir/#toCut.txt).get(short_name) → complement
        2. FilenameParser.parse(long_name) → métadonnées
        3. FrameExtractor.probe(path) → (vw, vh, total_sec)
        4. Construire VideoFile + list[Chapter] depuis métadonnées
        5. CropZone.from_parsed() pour chaque chapitre
        6. vf.resolve_inheritance()
        7. self._vf = vf
        8. self._emit(EvtSessionLoaded(vf))
        9. self._preload_thumbs() + self._load_frame(0)
        """
        log.debug("BOUCHON SessionController._load_entry(%s)", path)
        self._emit(EVT.EvtStatus(f"BOUCHON chargement {path.name}"))

    def _preload_thumbs(self) -> None:
        """Extraction des vignettes de tous les chapitres en arrière-plan."""
        log.debug("BOUCHON SessionController._preload_thumbs()")

    def _load_frame(self, chapter_index: int, ts_sec: Optional[int] = None) -> None:
        """Extrait la frame principale pour un chapitre (thread démon)."""
        log.debug("BOUCHON SessionController._load_frame(ch=%d, ts=%s)",
                  chapter_index, ts_sec)

    # ── Helpers internes ──────────────────────────────────────────────────

    @property
    def _active_chapter(self) -> Optional[Chapter]:
        """Raccourci vers le chapitre actif du VideoFile courant."""
        if self._vf is None:
            return None
        return self._vf.active_chapter   # type: ignore[attr-defined]

    def _require_vf(self) -> bool:
        """Retourne True si un VideoFile est chargé, sinon émet EvtStatus."""
        if self._vf is None:
            self._emit(EVT.EvtStatus("Aucun fichier chargé."))
            return False
        return True

    def _invalidate_and_reload(self) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None   # type narrowing pour Pylance
        self._vf.invalidate_all_displays()
        self._emit(EVT.EvtAllCropsInvalidated())
        self._load_frame(self._vf.active_index)
        self._preload_thumbs()

    # ── Handlers commandes ────────────────────────────────────────────────

    def _on_jump(self, cmd: CMD.CmdJump) -> None:
        log.debug("BOUCHON _on_jump(ch=%d)", cmd.chapter_index)
        if not self._require_vf():
            return
        self._vf.active_index = cmd.chapter_index   # type: ignore[union-attr]
        ch = self._active_chapter
        if ch:
            self._current_ts = ch.timestamp_sec     # type: ignore[union-attr]
        self._emit(EVT.EvtChapterChanged(index=cmd.chapter_index))
        self._load_frame(cmd.chapter_index)

    def _on_seek_abs(self, cmd: CMD.CmdSeekAbs) -> None:
        log.debug("BOUCHON _on_seek_abs(ts=%d)", cmd.timestamp_sec)
        if not self._require_vf():
            return
        self._current_ts = cmd.timestamp_sec
        self._load_frame(self._vf.active_index,     # type: ignore[union-attr]
                         ts_sec=cmd.timestamp_sec)

    def _on_seek_delta(self, cmd: CMD.CmdSeekDelta) -> None:
        log.debug("BOUCHON _on_seek_delta(delta=%d)", cmd.delta_sec)
        new_ts = max(0, self._current_ts + cmd.delta_sec)
        self._on_seek_abs(CMD.CmdSeekAbs(timestamp_sec=new_ts))

    def _on_add_crop(self, cmd: CMD.CmdAddCrop) -> None:
        log.debug("BOUCHON _on_add_crop()")
        if not self._require_vf():
            return
        self._invalidate_and_reload()
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_del_crop(self, cmd: CMD.CmdDelCrop) -> None:
        log.debug("BOUCHON _on_del_crop()")
        if not self._require_vf():
            return
        self._invalidate_and_reload()
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_set_crop(self, cmd: CMD.CmdSetCrop) -> None:
        log.debug("BOUCHON _on_set_crop(w=%s h=%s x=%s y=%s)",
                  cmd.w, cmd.h, cmd.pos_x, cmd.pos_y)
        if not self._require_vf():
            return
        ch = self._active_chapter
        if ch:
            self._emit(EVT.EvtCropChanged(
                chapter_index=self._vf.active_index,    # type: ignore[union-attr]
                inherited=ch.crop_inherited,            # type: ignore[union-attr]
            ))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_set_position(self, cmd: CMD.CmdSetPosition) -> None:
        log.debug("BOUCHON _on_set_position(preset=%s x=%s y=%s)",
                  cmd.preset, cmd.pos_x, cmd.pos_y)
        if not self._require_vf():
            return
        ch = self._active_chapter
        if ch:
            self._emit(EVT.EvtCropChanged(
                chapter_index=self._vf.active_index,    # type: ignore[union-attr]
                inherited=ch.crop_inherited,            # type: ignore[union-attr]
            ))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_validate_chapter(self, cmd: CMD.CmdValidateChapter) -> None:
        log.debug("BOUCHON _on_validate_chapter()")
        if not self._require_vf():
            return
        next_idx = min(self._vf.active_index + 1,       # type: ignore[union-attr]
                       len(self._vf.chapters) - 1)      # type: ignore[union-attr]
        self._emit(EVT.EvtChapterChanged(index=next_idx))
        self._load_frame(next_idx)

    def _on_prev_chapter(self, cmd: CMD.CmdPrevChapter) -> None:
        log.debug("BOUCHON _on_prev_chapter()")
        if not self._require_vf():
            return
        prev_idx = max(self._vf.active_index - 1, 0)   # type: ignore[union-attr]
        self._vf.active_index = prev_idx                # type: ignore[union-attr]
        self._emit(EVT.EvtChapterChanged(index=prev_idx))
        self._load_frame(prev_idx)

    def _on_add_chapter(self, cmd: CMD.CmdAddChapter) -> None:
        log.debug("BOUCHON _on_add_chapter(ts=%s)", cmd.timestamp_sec)
        if not self._require_vf():
            return
        self._emit(EVT.EvtChaptersUpdated(chapters=self._vf.chapters))  # type: ignore[union-attr]
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_edit_chapter(self, cmd: CMD.CmdEditChapter) -> None:
        log.debug("BOUCHON _on_edit_chapter(idx=%s title=%s ts=%s)",
                  cmd.index, cmd.title, cmd.timestamp_sec)
        if not self._require_vf():
            return
        self._emit(EVT.EvtChaptersUpdated(chapters=self._vf.chapters))  # type: ignore[union-attr]
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_chapter_edge(self, cmd: CMD.CmdChapterEdge) -> None:
        log.debug("BOUCHON _on_chapter_edge(idx=%s side=%s ts=%s)",
                  cmd.index, cmd.kind, cmd.timestamp_sec)
        if not self._require_vf():
            return
        self._emit(EVT.EvtChaptersUpdated(chapters=self._vf.chapters))  # type: ignore[union-attr]
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_save(self, cmd: CMD.CmdSave) -> None:
        log.debug("BOUCHON _on_save()")
        if not self._require_vf():
            return
        self._emit(EVT.EvtStatus("BOUCHON _on_save() — non implémenté"))
        self._emit(EVT.EvtDirty(is_dirty=False))

    def _on_next_file(self, cmd: CMD.CmdNextFile) -> None:
        log.debug("BOUCHON _on_next_file()")
        if not self._session.advance():
            self._emit(EVT.EvtStatus("Fin de session — aucun fichier suivant."))
            return
        entry = self._session.current_entry
        if entry:
            self._load_entry(entry.physical_path)

    def _on_load_file(self, cmd: CMD.CmdLoadFile) -> None:
        log.debug("BOUCHON _on_load_file(%s)", cmd.path)
        self._load_entry(cmd.path)

    def _on_quit(self, cmd: CMD.CmdQuit) -> None:
        log.debug("BOUCHON _on_quit()")
        import sys
        self._emit(EVT.EvtStatus("Au revoir."))
        sys.exit(0)