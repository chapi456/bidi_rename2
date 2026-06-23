"""
File: session_controller.py
Path: video_processor/controller/session_controller.py

Version: 0.2.0
Date: 2026-06-23

Changelog:
- 0.2.0 (2026-06-23): Fichier complet — handlers manquants ajoutés
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
        self._current_ts: int = 0          # timestamp affiché (secondes)

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
        1. Lire #toCut.txt (TocutFile) → display_name
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

    # ── Helpers internes ──────────────────────────────────────────────────

    @property
    def _active_chapter(self) -> Optional[Chapter]:
        """Raccourci vers le chapitre actif du VideoFile courant."""
        if self._vf is None:
            return None
        return self._vf.active_chapter

    def _require_vf(self) -> bool:
        """Retourne True si un VideoFile est chargé, sinon émet EvtStatus et False."""
        if self._vf is None:
            self._emit(EVT.EvtStatus("Aucun fichier chargé."))
            return False
        return True

    def _invalidate_and_reload(self) -> None:
        """Invalide tous les displays, émet EvtAllCropsInvalidated, recharge frame et thumbs."""
        if not self._require_vf():
            return
        self._vf.invalidate_all_displays()
        self._emit(EVT.EvtAllCropsInvalidated())
        self._load_frame(self._vf.active_index)
        self._preload_thumbs()

    # ── Handlers commandes ────────────────────────────────────────────────

    def _on_jump(self, cmd: CMD.CmdJump) -> None:
        """Sauvegarde chapitre courant, change active_index, charge frame."""
        log.debug("BOUCHON _on_jump(ch=%d)", cmd.chapter_index)
        if not self._require_vf():
            return
        self._vf.active_index = cmd.chapter_index
        ch = self._active_chapter
        if ch:
            self._current_ts = ch.timestamp_sec
        self._emit(EVT.EvtChapterChanged(index=cmd.chapter_index))
        self._load_frame(cmd.chapter_index)

    def _on_seek_abs(self, cmd: CMD.CmdSeekAbs) -> None:
        """Met à jour chapitre actif si besoin, charge frame au timestamp."""
        log.debug("BOUCHON _on_seek_abs(ts=%d)", cmd.timestamp_sec)
        if not self._require_vf():
            return
        self._current_ts = cmd.timestamp_sec
        # Trouver le chapitre correspondant au timestamp
        # (le chapitre dont ts <= timestamp < ts_suivant)
        # À implémenter avec vf.chapter_at_ts(ts)
        self._load_frame(self._vf.active_index, ts_sec=cmd.timestamp_sec)

    def _on_seek_delta(self, cmd: CMD.CmdSeekDelta) -> None:
        """Calcule nouveau ts depuis position courante, délègue à _on_seek_abs."""
        log.debug("BOUCHON _on_seek_delta(delta=%d)", cmd.delta_sec)
        new_ts = max(0, self._current_ts + cmd.delta_sec)
        self._on_seek_abs(CMD.CmdSeekAbs(timestamp_sec=new_ts))

    def _on_add_crop(self, cmd: CMD.CmdAddCrop) -> None:
        """Crée CropZone.default, pose sur chapitre actif, resolve, invalide, émet."""
        log.debug("BOUCHON _on_add_crop()")
        if not self._require_vf():
            return
        # 1. zone = CropZone.default(vf.video_w, vf.video_h)
        # 2. vf.active_chapter.crop_explicit = zone
        # 3. vf.global_crop_size = zone (taille seulement)
        # 4. vf.resolve_inheritance()
        # 5. Invalider + recharger
        self._invalidate_and_reload()
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_del_crop(self, cmd: CMD.CmdDelCrop) -> None:
        """Efface tous les crop_explicit, global_crop_size = None, resolve, invalide."""
        log.debug("BOUCHON _on_del_crop()")
        if not self._require_vf():
            return
        # À implémenter :
        # for ch in vf.chapters: ch.crop_explicit = None
        # vf.global_crop_size = None
        # vf.resolve_inheritance()
        self._invalidate_and_reload()
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_set_crop(self, cmd: CMD.CmdSetCrop) -> None:
        """Modifie taille globale et/ou position du chapitre actif."""
        log.debug("BOUCHON _on_set_crop(w=%s h=%s x=%s y=%s)",
                  cmd.w, cmd.h, cmd.pos_x, cmd.pos_y)
        if not self._require_vf():
            return
        # À implémenter :
        # if cmd.w or cmd.h : vf.global_crop_size = CropZone(w, h, ...)
        # if cmd.pos_x or cmd.pos_y : active_chapter.crop_explicit.pos_x = ...
        # vf.resolve_inheritance()
        ch = self._active_chapter
        if ch:
            self._emit(EVT.EvtCropChanged(
                chapter_index=self._vf.active_index,
                inherited=ch.crop_inherited,
            ))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_set_position(self, cmd: CMD.CmdSetPosition) -> None:
        """Applique un preset de position (gauche, centre, droite) ou coordonnées."""
        log.debug("BOUCHON _on_set_position(preset=%s x=%s y=%s)",
                  cmd.preset, cmd.pos_x, cmd.pos_y)
        if not self._require_vf():
            return
        # À implémenter :
        # Résoudre preset → (x, y) selon vw, vh, crop.w, crop.h
        # Poser sur active_chapter.crop_explicit
        # vf.resolve_inheritance()
        ch = self._active_chapter
        if ch:
            self._emit(EVT.EvtCropChanged(
                chapter_index=self._vf.active_index,
                inherited=ch.crop_inherited,
            ))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_validate_chapter(self, cmd: CMD.CmdValidateChapter) -> None:
        """Fige crop_explicit du chapitre courant, avance au suivant."""
        log.debug("BOUCHON _on_validate_chapter()")
        if not self._require_vf():
            return
        # À implémenter :
        # ch.crop_explicit = ch.crop_effective   (fige l'héritage)
        # vf.active_index = min(active+1, len-1)
        next_idx = min(self._vf.active_index + 1, len(self._vf.chapters) - 1)
        self._emit(EVT.EvtChapterChanged(index=next_idx))
        self._load_frame(next_idx)

    def _on_prev_chapter(self, cmd: CMD.CmdPrevChapter) -> None:
        """Recule au chapitre précédent."""
        log.debug("BOUCHON _on_prev_chapter()")
        if not self._require_vf():
            return
        prev_idx = max(self._vf.active_index - 1, 0)
        self._vf.active_index = prev_idx
        self._emit(EVT.EvtChapterChanged(index=prev_idx))
        self._load_frame(prev_idx)

    def _on_add_chapter(self, cmd: CMD.CmdAddChapter) -> None:
        """Insère un nouveau chapitre au timestamp courant.

        À implémenter :
        - Créer Chapter(timestamp_sec=current_ts, ...)
        - vf.chapters.insert(position, ch)  (trié par ts)
        - vf.resolve_inheritance()
        - Émettre EvtChaptersUpdated
        - Émettre EvtDirty
        """
        log.debug("BOUCHON _on_add_chapter(ts=%s)", cmd.timestamp_sec)
        if not self._require_vf():
            return
        self._emit(EVT.EvtChaptersUpdated(chapters=self._vf.chapters))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_edit_chapter(self, cmd: CMD.CmdEditChapter) -> None:
        """Modifie titre ou timestamp d'un chapitre existant.

        À implémenter :
        - vf.chapters[cmd.index].title = cmd.title  si fourni
        - vf.chapters[cmd.index].timestamp_sec = cmd.ts  si fourni
        - Re-trier si ts modifié
        - Émettre EvtChaptersUpdated + EvtDirty
        """
        log.debug("BOUCHON _on_edit_chapter(idx=%s title=%s ts=%s)",
                  cmd.chapter_index, cmd.title, cmd.timestamp_sec)
        if not self._require_vf():
            return
        self._emit(EVT.EvtChaptersUpdated(chapters=self._vf.chapters))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_chapter_edge(self, cmd: CMD.CmdChapterEdge) -> None:
        """Déplace le bord (début ou fin) d'un chapitre.

        À implémenter :
        - Ajuster timestamp_sec du chapitre (bord gauche)
          ou duration implicite (bord droit = début du suivant)
        - Re-trier si nécessaire
        - Émettre EvtChaptersUpdated + EvtDirty
        """
        log.debug("BOUCHON _on_chapter_edge(idx=%s side=%s ts=%s)",
                  cmd.chapter_index, cmd.side, cmd.timestamp_sec)
        if not self._require_vf():
            return
        self._emit(EVT.EvtChaptersUpdated(chapters=self._vf.chapters))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_save(self, cmd: CMD.CmdSave) -> None:
        """Construit le nouveau nom, renomme le fichier, met à jour #toCut.txt.

        À implémenter :
        1. FilenameParser.build(...) → new_display_name
        2. Séparer short_name + complement
        3. TocutFile(dir).set(short_name, complement).write()
        4. os.rename(physical_path, new_physical_path)  si renommage disque
        5. Mettre à jour entry dans session
        6. Émettre EvtTitle + EvtDirty(False) + EvtStatus
        """
        log.debug("BOUCHON _on_save()")
        if not self._require_vf():
            return
        self._emit(EVT.EvtStatus("BOUCHON _on_save() — non implémenté"))
        self._emit(EVT.EvtDirty(is_dirty=False))

    def _on_next_file(self, cmd: CMD.CmdNextFile) -> None:
        """Passe au fichier suivant dans la session.

        À implémenter :
        - Vérifier dirty → demander confirmation ou sauvegarder
        - session.advance()
        - _load_entry(session.current_entry.physical_path)
        """
        log.debug("BOUCHON _on_next_file()")
        advanced = self._session.advance()
        if not advanced:
            self._emit(EVT.EvtStatus("Fin de session — aucun fichier suivant."))
            return
        entry = self._session.current_entry
        if entry:
            self._load_entry(entry.physical_path)

    def _on_load_file(self, cmd: CMD.CmdLoadFile) -> None:
        """Charge un fichier arbitraire (drag-drop, CLI, combobox).

        À implémenter :
        - Vérifier dirty → demander confirmation
        - session.set_current_by_path(cmd.path)
        - _load_entry(cmd.path)
        """
        log.debug("BOUCHON _on_load_file(%s)", cmd.path)
        self._load_entry(cmd.path)

    def _on_quit(self, cmd: CMD.CmdQuit) -> None:
        """Quitte proprement.

        À implémenter :
        - Vérifier dirty → proposer save
        - Arrêter threads démons
        - sys.exit(0) ou signal vue
        """
        log.debug("BOUCHON _on_quit()")
        import sys
        self._emit(EVT.EvtStatus("Au revoir."))
        sys.exit(0)
