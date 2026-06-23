"""
File: session_controller.py
Path: video_processor/controller/session_controller.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging
import threading
from pathlib import Path
from typing import Callable, Optional

from video_processor.domain.session import VideoSession
from video_processor.domain.video_file import VideoFile
from video_processor.domain.chapter import Chapter
from video_processor.domain.crop_zone import CropZone
from video_processor.controller import commands as CMD
from video_processor.controller import events as EVT

log = logging.getLogger("controller.session")

EventHandler = Callable[[object], None]


class SessionController:
    """Orchestre session, domaine et infrastructure.
    Reçoit des commandes (send), émet des événements (subscribe).
    Thread-safe : les commandes peuvent venir de n'importe quel thread.
    """

    def __init__(self, session: VideoSession, config: dict):
        log.debug("BOUCHON SessionController.__init__()")
        self._session  = session
        self._config   = config
        self._vf:      Optional[VideoFile] = None
        self._handlers: list[EventHandler] = []
        self._lock     = threading.Lock()

    # ── Abonnements événements ────────────────────────────────────────────

    def subscribe(self, handler: EventHandler) -> None:
        """La vue appelle subscribe(self._on_event) pour recevoir tous les évts."""
        log.debug("BOUCHON SessionController.subscribe(%s)", handler)
        self._handlers.append(handler)

    def _emit(self, event: object) -> None:
        """Diffuse un événement à tous les abonnés (dans le thread appelant)."""
        log.debug("BOUCHON SessionController._emit(%s)", type(event).__name__)
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
        log.debug("BOUCHON SessionController.send(%s)", type(cmd).__name__)
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
            log.warning("BOUCHON commande inconnue : %s", type(cmd).__name__)

    # ── Chargement fichier ────────────────────────────────────────────────

    def _load_entry(self, path: Path) -> None:
        """Parse, ffprobe, résout héritage, émet EvtSessionLoaded + lance preload.

        Séquence complète à implémenter :
        1. Lire #toCut.txt (ToСutReader) → display_name
        2. FilenameParser.parse(display_name) → métadonnées
        3. FrameExtractor.probe(path) → (vw, vh, total_sec)
        4. Construire VideoFile + list[Chapter] depuis métadonnées
        5. CropZone.from_parsed() pour chaque chapitre si CROP dans nom
        6. vf.resolve_inheritance()
        7. self._vf = vf
        8. self._emit(EvtSessionLoaded(vf))
        9. self._emit(EvtTitle(...))
        10. self._preload_thumbs()   ← thread démon
        11. self._load_frame(0)      ← thread démon
        """
        log.debug("BOUCHON SessionController._load_entry(%s)", path)
        self._emit(EVT.EvtStatus(f"BOUCHON chargement {path.name}"))

    def _preload_thumbs(self) -> None:
        """Lance l'extraction des vignettes de tous les chapitres en arrière-plan.

        Pour chaque chapitre :
        - Vérifier ch.thumb_raw is None (skip si déjà en cache)
        - Extraire via FrameExtractor.extract(path, ch.timestamp_sec, size='thumb')
        - Stocker ch.thumb_raw
        - Appeler Renderer.render_thumb(ch) → ch.thumb_display
        - Émettre EvtThumbReady
        """
        log.debug("BOUCHON SessionController._preload_thumbs()")

    def _load_frame(self, chapter_index: int, ts_sec: Optional[int] = None) -> None:
        """Extrait la frame principale pour un chapitre (thread démon).

        - ts = ts_sec si fourni, sinon ch.timestamp_sec
        - Extraire via FrameExtractor.extract(path, ts)
        - Stocker ch.frame_raw
        - Appeler Renderer.render_frame(ch, scale) → ch.frame_display
        - Émettre EvtFrameReady
        """
        log.debug("BOUCHON SessionController._load_frame(ch=%d, ts=%s)",
                  chapter_index, ts_sec)

    # ── Handlers commandes ────────────────────────────────────────────────

    def _on_jump(self, cmd: CMD.CmdJump) -> None:
        """Sauvegarde chapitre courant, change active_index, charge frame."""
        log.debug("BOUCHON _on_jump(ch=%d)", cmd.chapter_index)

    def _on_seek_abs(self, cmd: CMD.CmdSeekAbs) -> None:
        """Met à jour chapitre actif si besoin, charge frame au timestamp."""
        log.debug("BOUCHON _on_seek_abs(ts=%d)", cmd.timestamp_sec)

    def _on_seek_delta(self, cmd: CMD.CmdSeekDelta) -> None:
        """Calcule nouveau ts depuis position courante, délègue à _on_seek_abs."""
        log.debug("BOUCHON _on_seek_delta(delta=%d)", cmd.delta_sec)

    def _on_add_crop(self, cmd: CMD.CmdAddCrop) -> None:
        """Crée CropZone.default, pose sur chapitre actif, resolve, invalide, émet."""
        log.debug("BOUCHON _on_add_crop()")
        # 1. zone = CropZone.default(vf.video_w, vf.video_h)
        # 2. vf.active_chapter.crop_explicit = zone
        # 3. vf.global_crop_size = zone (taille seulement)
        # 4. vf.resolve_inheritance()
        # 5. vf.invalidate_all_displays()
        # 6. self._emit(EvtAllCropsInvalidated(...))
        # 7. self._emit(EvtDirty(True))
        # 8. self._load_frame(active_index)  ← re-render
        # 9. self._preload_thumbs()

    def _on_del_crop(self, cmd: CMD.CmdDelCrop) -> None:
        """Efface tous les crop_explicit, global_crop_size = None, resolve, invalide."""
        log.debug("BOUCHON _on_del_crop()")

    def _on_set_crop(self, cmd: CMD.CmdSetCrop) -> None:
        """Modifie taille globale et/ou position du chapitre actif."""
        log.debug("BOUCHON _on_set_crop(w=%s h=%s x=%s y=%s)",
                  cmd.w, cmd.h, cmd.pos_x, cmd.pos_y)

    def _on_set_position(self, cmd: CMD.CmdSetPosition) -> None:
        """Applique un preset de position (gauche, centre, droite) ou coordonnées."""
        log.debug("BOUCHON _on_set_position(preset=%s)", cmd.preset)

    def _on_validate_chapter(self, cmd: CMD.CmdValidateChapter) -> None:
        """Fige crop_explicit du chapitre courant, avance au suivant."""
        log.debug("BOUCHON _on_validate_chapter()")

    def _on_prev_chap