"""
File: session_controller.py
Path: video_processor/controller/session_controller.py

Version: 0.4.0
Date: 2026-06-23

Changelog:
- 0.4.0 (2026-06-23): _load_entry, _preload_thumbs, _load_frame implémentés
  * _load_entry : probe + TocutFile + FilenameParser + VideoFile + resolve_inheritance
  * _preload_thumbs : extraction des thumbs en thread démon, séquentielle par chapitre
  * _load_frame : extraction frame principale à ts_sec donné ou timestamp du chapitre
  * Correction ch.crop_inherited → ch.is_inherited dans _on_set_crop/_on_set_position
  * Correction EvtCropChanged : champ crop ajouté
- 0.3.0 (2026-06-23): Suppression config du __init__
- 0.2.0 (2026-06-23): Fichier complet
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

from video_processor.domain.session    import VideoSession
from video_processor.domain.video_file import VideoFile
from video_processor.domain.chapter    import Chapter
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
        log.debug("SessionController.__init__()")
        self._session:    VideoSession        = session
        self._vf:         Optional[VideoFile] = None
        self._handlers:   list[EventHandler]  = []
        self._lock        = threading.Lock()
        self._current_ts: int                 = 0

    # ── Config interne ────────────────────────────────────────────────────

    @property
    def _cfg(self):
        from video_processor.infra.config_loader import AppConfig
        return AppConfig.instance()

    # ── Abonnements événements ────────────────────────────────────────────

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def _emit(self, event: object) -> None:
        log.debug("SessionController._emit(%s)", type(event).__name__)
        for h in self._handlers:
            h(event)

    # ── Point d'entrée ────────────────────────────────────────────────────

    def open_current(self) -> None:
        log.debug("SessionController.open_current()")
        entry = self._session.current_entry
        if entry is None:
            self._emit(EVT.EvtStatus("Aucun fichier dans la session."))
            return
        self._load_entry(entry.physical_path)

    # ── Dispatch commandes ────────────────────────────────────────────────

    def send(self, cmd: object) -> None:
        log.debug("SessionController.send(%s)", type(cmd).__name__)
        dispatch = {
            CMD.CmdJump:            self._on_jump,
            CMD.CmdSeekAbs:         self._on_seek_abs,
            CMD.CmdSeekDelta:       self._on_seek_delta,
            CMD.CmdAddCrop:         self._on_add_crop,
            CMD.CmdDelCrop:         self._on_del_crop,
            CMD.CmdSetCrop:         self._on_set_crop,
            CMD.CmdSetPosition:     self._on_set_position,
            CMD.CmdValidateChapter: self._on_validate_chapter,
            CMD.CmdPrevChapter:     self._on_prev_chapter,
            CMD.CmdAddChapter:      self._on_add_chapter,
            CMD.CmdEditChapter:     self._on_edit_chapter,
            CMD.CmdChapterEdge:     self._on_chapter_edge,
            CMD.CmdSave:            self._on_save,
            CMD.CmdNextFile:        self._on_next_file,
            CMD.CmdLoadFile:        self._on_load_file,
            CMD.CmdQuit:            self._on_quit,
        }
        handler = dispatch.get(type(cmd))
        if handler:
            handler(cmd)
        else:
            log.warning("Commande inconnue : %s", type(cmd).__name__)

    # ── Chargement fichier ────────────────────────────────────────────────

    def _load_entry(self, path: Path) -> None:
        """Charge un fichier vidéo complet et émet EvtSessionLoaded."""
        from video_processor.infra.filename_parser import FilenameParser
        from video_processor.infra.tocut_rw        import TocutFile
        from video_processor.infra.frame_extractor import FrameExtractor

        log.debug("SessionController._load_entry(%s)", path.name)
        self._emit(EVT.EvtStatus(f"Chargement : {path.name}"))

        cfg = self._cfg

        # 1. Probe
        vw, vh, total_sec = FrameExtractor.probe(path)
        if vw == 0:
            self._emit(EVT.EvtStatus(f"Erreur probe : {path.name}"))
            return

        # 2. TocutFile → long_name
        short_name = path.name
        uses_tocut = False
        complement = ""
        long_name  = short_name

        tocut_path = path.parent / "#toCut.txt"
        if tocut_path.exists():
            tocut      = TocutFile.load(tocut_path)
            complement = tocut.get(short_name)
            if complement:
                uses_tocut = True
                long_name  = path.stem + complement + path.suffix

        # 3. Parser
        parsed = FilenameParser.parse(long_name, styles=cfg.styles)
        if parsed is None:
            self._emit(EVT.EvtStatus(f"Nom invalide (aucun style) : {path.name}"))
            return

        # 4a. Crop global
        global_crop: Optional[CropZone] = None
        if parsed.crop:
            global_crop = CropZone(w=parsed.crop.w, h=parsed.crop.h, explicit=True)

        # 4b. Chapitres
        chapters: list[Chapter] = []
        for i, ci in enumerate(parsed.chapters):
            crop_explicit: Optional[CropZone] = None
            cw = parsed.crop.w if parsed.crop else 0
            ch_h = parsed.crop.h if parsed.crop else 0

            if ci.pos_mode == "center":
                crop_explicit = CropZone(
                    w=cw, h=ch_h,
                    pos_x=(vw - cw) // 2,
                    pos_y=(vh - ch_h) // 2,
                    pos_mode="center",
                    explicit=True,
                )
            elif ci.pos_explicit and ci.pos_x is not None and ci.pos_y is not None:
                crop_explicit = CropZone(
                    w=cw, h=ch_h,
                    pos_x=ci.pos_x,
                    pos_y=ci.pos_y,
                    pos_mode="topleft",  # type: ignore[arg-type]
                    explicit=True,
                )

            chapters.append(Chapter(
                index=i,
                timestamp_sec=ci.timestamp_seconds,
                timestamp_raw=ci.timestamp_original,
                duration_sec=ci.duration,
                title=ci.title,
                crop_explicit=crop_explicit,
            ))

        # 4c. VideoFile
        vf = VideoFile(
            physical_path=path,
            short_name=short_name,
            long_name=long_name,
            uses_tocut=uses_tocut,
            complement=complement,
            title=parsed.title,
            studio=parsed.studio,
            actors=parsed.actors,
            styles=parsed.styles,
            date=parsed.date,
            booleans=parsed.booleans,
            options={k: v for k, v in {
                "encode": parsed.encode,
                "resize": parsed.resize,
            }.items() if v},
            file_id=str(parsed.file_id) if parsed.file_id else None,
            video_w=vw,
            video_h=vh,
            total_duration_sec=total_sec,
            global_crop_size=global_crop,
            chapters=chapters,
            active_index=0,
        )

        # 5. Héritage
        vf.resolve_inheritance()

        # 6. Émettre + lancer preload
        self._vf = vf
        self._emit(EVT.EvtSessionLoaded(video_file=vf))
        self._emit(EVT.EvtTitle(text=path.stem))
        self._emit(EVT.EvtStatus(
            f"Prêt : {len(chapters)} chapitre(s) — {total_sec}s"
        ))

        threading.Thread(target=self._preload_thumbs, daemon=True).start()
        threading.Thread(target=self._load_frame, args=(0,), daemon=True).start()

    def _preload_thumbs(self) -> None:
        """Extrait les vignettes de tous les chapitres en arrière-plan.

        Séquentiel pour ne pas saturer ffmpeg. Émet EvtThumbReady par chapitre.
        Guard : si _vf change entre deux extractions (fichier suivant), on stoppe.
        """
        from video_processor.infra.frame_extractor import FrameExtractor
        from video_processor.infra.renderer        import Renderer

        vf = self._vf   # snapshot local — thread safety
        if vf is None:
            return

        log.debug("_preload_thumbs() — %d chapitres", len(vf.chapters))
        for ch in vf.chapters:
            if self._vf is not vf:   # fichier changé entre temps → stop
                log.debug("_preload_thumbs() interrompu (fichier changé)")
                return
            if ch.thumb_loading or ch.thumb_raw is not None:
                continue

            ch.thumb_loading = True
            try:
                img = FrameExtractor.extract_thumb(vf.physical_path, ch.timestamp_sec)
                if img is None:
                    log.warning("_preload_thumbs : frame None pour ch[%d]", ch.index)
                    continue
                ch.thumb_raw = img
                rendered = Renderer.render_thumb_scaled(ch, vf.video_w, vf.video_h)
                self._emit(EVT.EvtThumbReady(
                    chapter_index=ch.index,
                    image=rendered or img,
                    crop=ch.crop_effective,
                    inherited=ch.is_inherited,
                ))
            finally:
                ch.thumb_loading = False

    def _load_frame(self, chapter_index: int, ts_sec: Optional[int] = None) -> None:
        """Extrait la frame principale pour un chapitre.

        Si ts_sec est None, utilise le timestamp du chapitre.
        Émet EvtFrameReady quand l'image est prête.
        Guard : si _vf change, on abandonne silencieusement.
        """
        from video_processor.infra.frame_extractor import FrameExtractor
        from video_processor.infra.renderer        import Renderer

        vf = self._vf
        if vf is None or chapter_index >= len(vf.chapters):
            return

        ch = vf.chapters[chapter_index]
        ts = ts_sec if ts_sec is not None else ch.timestamp_sec

        if ch.frame_loading:
            return

        ch.frame_loading = True
        try:
            img = FrameExtractor.extract(vf.physical_path, ts)
            if img is None or self._vf is not vf:
                return
            ch.frame_raw = img
            # scale pour affichage : on normalise à une largeur de 960px max
            scale = min(1.0, 960 / vf.video_w) if vf.video_w > 0 else 1.0
            rendered = Renderer.render_frame(ch, scale)
            self._emit(EVT.EvtFrameReady(
                chapter_index=chapter_index,
                image=rendered or img,
                crop=ch.crop_effective,
                inherited=ch.is_inherited,
                timestamp_sec=ts,
            ))
        finally:
            ch.frame_loading = False

    # ── Helpers internes ──────────────────────────────────────────────────

    @property
    def _active_chapter(self) -> Optional[Chapter]:
        if self._vf is None:
            return None
        return self._vf.active_chapter

    def _require_vf(self) -> bool:
        if self._vf is None:
            self._emit(EVT.EvtStatus("Aucun fichier chargé."))
            return False
        return True

    def _invalidate_and_reload(self) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        self._vf.invalidate_all_displays()
        self._emit(EVT.EvtAllCropsInvalidated())
        threading.Thread(
            target=self._load_frame, args=(self._vf.active_index,), daemon=True
        ).start()
        threading.Thread(target=self._preload_thumbs, daemon=True).start()

    # ── Handlers commandes ────────────────────────────────────────────────

    def _on_jump(self, cmd: CMD.CmdJump) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        self._vf.active_index = cmd.chapter_index
        ch = self._active_chapter
        if ch:
            self._current_ts = ch.timestamp_sec
        self._emit(EVT.EvtChapterChanged(index=cmd.chapter_index))
        threading.Thread(
            target=self._load_frame, args=(cmd.chapter_index,), daemon=True
        ).start()

    def _on_seek_abs(self, cmd: CMD.CmdSeekAbs) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        self._current_ts = cmd.timestamp_sec
        idx = self._vf.chapter_at_time(cmd.timestamp_sec)
        threading.Thread(
            target=self._load_frame, args=(idx, cmd.timestamp_sec), daemon=True
        ).start()

    def _on_seek_delta(self, cmd: CMD.CmdSeekDelta) -> None:
        new_ts = max(0, self._current_ts + cmd.delta_sec)
        self._on_seek_abs(CMD.CmdSeekAbs(timestamp_sec=new_ts))

    def _on_add_crop(self, cmd: CMD.CmdAddCrop) -> None:
        if not self._require_vf():
            return
        self._invalidate_and_reload()
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_del_crop(self, cmd: CMD.CmdDelCrop) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        ch = self._active_chapter
        if ch:
            ch.crop_explicit = None
        self._vf.resolve_inheritance()
        self._invalidate_and_reload()
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_set_crop(self, cmd: CMD.CmdSetCrop) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        ch = self._active_chapter
        if ch and ch.crop_effective:
            new_crop = CropZone(
                w=cmd.w         if cmd.w     is not None else ch.crop_effective.w,
                h=cmd.h         if cmd.h     is not None else ch.crop_effective.h,
                pos_x=cmd.pos_x if cmd.pos_x is not None else ch.crop_effective.pos_x,
                pos_y=cmd.pos_y if cmd.pos_y is not None else ch.crop_effective.pos_y,
                pos_mode=ch.crop_effective.pos_mode,
                explicit=True,
            )
            ch.crop_explicit = new_crop
            self._vf.resolve_inheritance()
            self._emit(EVT.EvtCropChanged(
                chapter_index=self._vf.active_index,
                crop=ch.crop_effective,
                inherited=ch.is_inherited,
            ))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_set_position(self, cmd: CMD.CmdSetPosition) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        ch = self._active_chapter
        if ch and ch.crop_effective:
            vw, vh = self._vf.video_w, self._vf.video_h
            cw, ch_h = ch.crop_effective.w, ch.crop_effective.h
            presets = {
                "l":       (0,              (vh - ch_h) // 2),
                "c":       ((vw - cw) // 2, (vh - ch_h) // 2),
                "r":       (vw - cw,        (vh - ch_h) // 2),
                "topleft": (0, 0),
            }
            px, py = presets.get(cmd.preset, (cmd.pos_x or 0, cmd.pos_y or 0))
            new_crop = CropZone(
                w=cw, h=ch_h,
                pos_x=px, pos_y=py,
                pos_mode="center" if cmd.preset == "c" else "topleft",
                explicit=True,
            )
            ch.crop_explicit = new_crop
            self._vf.resolve_inheritance()
            self._emit(EVT.EvtCropChanged(
                chapter_index=self._vf.active_index,
                crop=ch.crop_effective,
                inherited=ch.is_inherited,
            ))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_validate_chapter(self, cmd: CMD.CmdValidateChapter) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        next_idx = min(self._vf.active_index + 1, len(self._vf.chapters) - 1)
        self._vf.active_index = next_idx
        self._emit(EVT.EvtChapterChanged(index=next_idx))
        threading.Thread(
            target=self._load_frame, args=(next_idx,), daemon=True
        ).start()

    def _on_prev_chapter(self, cmd: CMD.CmdPrevChapter) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        prev_idx = max(self._vf.active_index - 1, 0)
        self._vf.active_index = prev_idx
        self._emit(EVT.EvtChapterChanged(index=prev_idx))
        threading.Thread(
            target=self._load_frame, args=(prev_idx,), daemon=True
        ).start()

    def _on_add_chapter(self, cmd: CMD.CmdAddChapter) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        new_ch = Chapter(
            index=len(self._vf.chapters),
            timestamp_sec=cmd.timestamp_sec,
            timestamp_raw=str(cmd.timestamp_sec),
            duration_sec=cmd.duration_sec,
            title=cmd.title or None,
        )
        self._vf.chapters.append(new_ch)
        self._vf.chapters.sort(key=lambda c: c.timestamp_sec)
        for i, c in enumerate(self._vf.chapters):
            c.index = i
        self._vf.resolve_inheritance()
        self._emit(EVT.EvtChaptersUpdated(chapters=self._vf.chapters))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_edit_chapter(self, cmd: CMD.CmdEditChapter) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        if cmd.index >= len(self._vf.chapters):
            return
        ch = self._vf.chapters[cmd.index]
        ch.title         = cmd.title or None
        ch.timestamp_sec = cmd.timestamp_sec
        ch.timestamp_raw = cmd.timestamp_raw
        ch.duration_sec  = cmd.duration_sec
        self._vf.resolve_inheritance()
        self._emit(EVT.EvtChaptersUpdated(chapters=self._vf.chapters))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_chapter_edge(self, cmd: CMD.CmdChapterEdge) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        if cmd.index >= len(self._vf.chapters):
            return
        ch = self._vf.chapters[cmd.index]
        if cmd.kind == "start":
            ch.timestamp_sec = cmd.timestamp_sec
            ch.timestamp_raw = str(cmd.timestamp_sec)
        else:
            ch.duration_sec = cmd.duration_sec
        self._emit(EVT.EvtChaptersUpdated(chapters=self._vf.chapters))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_save(self, cmd: CMD.CmdSave) -> None:
        log.debug("BOUCHON _on_save()")
        if not self._require_vf():
            return
        self._emit(EVT.EvtStatus("BOUCHON _on_save() — non implémenté"))
        self._emit(EVT.EvtDirty(is_dirty=False))

    def _on_next_file(self, cmd: CMD.CmdNextFile) -> None:
        if not self._session.advance():
            self._emit(EVT.EvtStatus("Fin de session — aucun fichier suivant."))
            return
        entry = self._session.current_entry
        if entry:
            self._load_entry(entry.physical_path)

    def _on_load_file(self, cmd: CMD.CmdLoadFile) -> None:
        self._load_entry(cmd.path)

    def _on_quit(self, cmd: CMD.CmdQuit) -> None:
        import sys
        self._emit(EVT.EvtStatus("Au revoir."))
        sys.exit(0)