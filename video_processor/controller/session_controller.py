"""
File: session_controller.py
Path: video_processor/controller/session_controller.py

Version: 0.5.0
Date: 2026-06-23

Changelog:
- 0.5.0 (2026-06-23): Nouveaux handlers commandes navigation
  * _on_seek_begin        : seek à 0
  * _on_seek_end          : seek à total_duration_sec
  * _on_seek_chapter_start: seek au début du chapitre actif
  * _on_seek_chapter_end  : seek à la fin du chapitre actif
  * _on_copy_prev_crop    : copie crop_effective[i-1] → crop_explicit[i]
  * _on_save_and_next     : _on_save() + _on_next_file() enchaîné
  * dispatch mis à jour pour les 6 nouvelles commandes
- 0.4.0 (2026-06-23): _load_entry, _preload_thumbs, _load_frame implémentés
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
        self._session:    VideoSession        = session
        self._vf:         Optional[VideoFile] = None
        self._handlers:   list[EventHandler]  = []
        self._lock        = threading.Lock()
        self._current_ts: float = 0.0

    # ── Config interne ────────────────────────────────────────────────────

    @property
    def _cfg(self):
        from video_processor.infra.config_loader import AppConfig
        return AppConfig.instance()

    # ── Abonnements événements ────────────────────────────────────────────

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def _emit(self, event: object) -> None:
        for h in self._handlers:
            h(event)

    # ── Point d'entrée ────────────────────────────────────────────────────

    def open_current(self) -> None:
        entry = self._session.current_entry
        if entry is None:
            self._emit(EVT.EvtStatus("Aucun fichier dans la session."))
            return
        self._load_entry(entry.physical_path)

    # ── Dispatch commandes ────────────────────────────────────────────────

    def send(self, cmd: object) -> None:
        log.debug("SessionController.send(%s)", type(cmd).__name__)
        dispatch = {
            CMD.CmdJump:             self._on_jump,
            CMD.CmdSeekAbs:          self._on_seek_abs,
            CMD.CmdSeekDelta:        self._on_seek_delta,
            CMD.CmdSeekBegin:        self._on_seek_begin,
            CMD.CmdSeekEnd:          self._on_seek_end,
            CMD.CmdSeekChapterStart: self._on_seek_chapter_start,
            CMD.CmdSeekChapterEnd:   self._on_seek_chapter_end,
            CMD.CmdAddCrop:          self._on_add_crop,
            CMD.CmdDelCrop:          self._on_del_crop,
            CMD.CmdSetCrop:          self._on_set_crop,
            CMD.CmdSetPosition:      self._on_set_position,
            CMD.CmdCopyPrevCrop:     self._on_copy_prev_crop,
            CMD.CmdValidateChapter:  self._on_validate_chapter,
            CMD.CmdPrevChapter:      self._on_prev_chapter,
            CMD.CmdAddChapter:       self._on_add_chapter,
            CMD.CmdEditChapter:      self._on_edit_chapter,
            CMD.CmdChapterEdge:      self._on_chapter_edge,
            CMD.CmdRefreshThumb:     self._on_refresh_thumb,
            CMD.CmdSave:             self._on_save,
            CMD.CmdSaveAndNext:      self._on_save_and_next,
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
    # (inchangé — copié tel quel depuis 0.4.0)

    def _load_entry(self, path: Path) -> None:
        from video_processor.infra.filename_parser import FilenameParser
        from video_processor.infra.tocut_rw        import TocutFile
        from video_processor.infra.frame_extractor import FrameExtractor

        self._emit(EVT.EvtStatus(f"Chargement : {path.name}"))
        cfg = self._cfg

        vw, vh, total_sec = FrameExtractor.probe(path)
        if vw == 0:
            self._emit(EVT.EvtStatus(f"Erreur probe : {path.name}"))
            return

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

        parsed = FilenameParser.parse(long_name, styles=cfg.styles)
        if parsed is None:
            self._emit(EVT.EvtStatus(f"Nom invalide (aucun style) : {path.name}"))
            return

        global_crop: Optional[CropZone] = None
        if parsed.crop:
            global_crop = CropZone(w=parsed.crop.w, h=parsed.crop.h, explicit=True)

        chapters: list[Chapter] = []
        for i, ci in enumerate(parsed.chapters):
            crop_explicit: Optional[CropZone] = None
            cw   = parsed.crop.w if parsed.crop else 0
            ch_h = parsed.crop.h if parsed.crop else 0

            if ci.pos_mode == "center":
                crop_explicit = CropZone(
                    w=cw, h=ch_h,
                    pos_x=(vw - cw) // 2, pos_y=(vh - ch_h) // 2,
                    pos_mode="center", explicit=True,
                )
            elif ci.pos_explicit and ci.pos_x is not None and ci.pos_y is not None:
                crop_explicit = CropZone(
                    w=cw, h=ch_h,
                    pos_x=ci.pos_x, pos_y=ci.pos_y,
                    pos_mode="topleft", explicit=True,
                )

            chapters.append(Chapter(
                index=i,
                timestamp_sec=ci.timestamp_seconds,
                timestamp_raw=ci.timestamp_original,
                duration_sec=ci.duration,
                title=ci.title,
                crop_explicit=crop_explicit,
            ))

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

        vf.resolve_inheritance()
        self._vf         = vf
        self._current_ts = 0
        self._emit(EVT.EvtSessionLoaded(video_file=vf))
        self._emit(EVT.EvtTitle(text=path.stem))
        self._emit(EVT.EvtStatus(
            f"Prêt : {len(chapters)} chapitre(s) — {total_sec}s"
        ))

        threading.Thread(target=self._preload_thumbs, daemon=True).start()
        threading.Thread(target=self._load_frame, args=(0,), daemon=True).start()

    def _preload_thumbs(self) -> None:
        from video_processor.infra.frame_extractor import FrameExtractor
        from video_processor.infra.renderer        import Renderer

        vf = self._vf
        if vf is None:
            return

        for ch in vf.chapters:
            if self._vf is not vf:
                return
            if ch.thumb_loading or ch.thumb_raw is not None:
                continue
            ch.thumb_loading = True
            try:
                img = FrameExtractor.extract_thumb(vf.physical_path, ch.timestamp_sec)
                if img is None:
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
            self._emit_frame_from_raw(vf, ch, ts)
        finally:
            ch.frame_loading = False

    def _emit_frame_from_raw(self, vf: VideoFile, ch: Chapter, ts: int) -> None:
        """Render ch.frame_raw avec le crop courant et émet EvtFrameReady."""
        from video_processor.infra.renderer import Renderer
        scale    = min(1.0, 960 / vf.video_w) if vf.video_w > 0 else 1.0
        rendered = Renderer.render_frame(ch, scale)
        image = rendered or ch.frame_raw
        if image is None:
            return
        self._emit(EVT.EvtFrameReady(
            chapter_index=ch.index,
            image=image,
            crop=ch.crop_effective,
            inherited=ch.is_inherited,
            timestamp_sec=ts,
        ))
    # ── Helpers ───────────────────────────────────────────────────────────

    @property
    def _active_chapter(self) -> Optional[Chapter]:
        return self._vf.active_chapter if self._vf else None

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

    def _seek(self, ts: float) -> None:
        assert self._vf is not None
        self._current_ts = max(0.0, min(ts, float(self._vf.total_duration_sec)))
        idx = self._vf.chapter_at_time(int(self._current_ts))
        self._emit(EVT.EvtPositionChanged(timestamp_sec=self._current_ts))
        threading.Thread(
            target=self._load_frame, args=(idx, int(self._current_ts)), daemon=True
        ).start()

    # ── Handlers navigation ───────────────────────────────────────────────

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
        self._seek(cmd.timestamp_sec)

    def _on_seek_delta(self, cmd: CMD.CmdSeekDelta) -> None:
        if not self._require_vf():
            return
        self._seek(self._current_ts + cmd.delta_sec)

    def _on_seek_begin(self, cmd: CMD.CmdSeekBegin) -> None:
        if not self._require_vf():
            return
        self._seek(0)

    def _on_seek_end(self, cmd: CMD.CmdSeekEnd) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        self._seek(self._vf.total_duration_sec)

    def _on_seek_chapter_start(self, cmd: CMD.CmdSeekChapterStart) -> None:
        if not self._require_vf():
            return
        ch = self._active_chapter
        if ch:
            self._seek(ch.timestamp_sec)

    def _on_seek_chapter_end(self, cmd: CMD.CmdSeekChapterEnd) -> None:
        if not self._require_vf():
            return
        ch = self._active_chapter
        if ch:
            self._seek(ch.timestamp_sec + (ch.duration_sec or 0))

    # ── Handlers crop ─────────────────────────────────────────────────────

    def _on_add_crop(self, cmd: CMD.CmdAddCrop) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        ch = self._active_chapter
        if ch and ch.crop_effective is None:
            ch.crop_explicit = CropZone.default(self._vf.video_w, self._vf.video_h)
            self._vf.resolve_inheritance()
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
            eff    = ch.crop_effective
            vw, vh = self._vf.video_w, self._vf.video_h
            new_w  = cmd.w     if cmd.w     is not None else eff.w
            new_h  = cmd.h     if cmd.h     is not None else eff.h
            new_x  = cmd.pos_x if cmd.pos_x is not None else eff.pos_x
            new_y  = cmd.pos_y if cmd.pos_y is not None else eff.pos_y
            # Clamp
            new_w  = max(10, min(new_w, vw))
            new_h  = max(10, min(new_h, vh))
            new_x  = max(0,  min(new_x, vw - new_w))
            new_y  = max(0,  min(new_y, vh - new_h))
            ch.crop_explicit = CropZone(
                w=new_w, h=new_h,
                pos_x=new_x, pos_y=new_y,
                pos_mode=eff.pos_mode,
                explicit=True,
            )
            self._vf.resolve_inheritance()
            self._emit(EVT.EvtCropChanged(
                chapter_index=self._vf.active_index,
                crop=ch.crop_effective,
                inherited=ch.is_inherited,
            ))
            if ch.frame_raw is not None:
                self._emit_frame_from_raw(self._vf, ch, self._current_ts)
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_set_position(self, cmd: CMD.CmdSetPosition) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        ch = self._active_chapter
        if ch and ch.crop_effective:
            vw, vh   = self._vf.video_w, self._vf.video_h
            cw, ch_h = ch.crop_effective.w, ch.crop_effective.h
            presets  = {
                "l": (0,              (vh - ch_h) // 2),
                "c": ((vw - cw) // 2, (vh - ch_h) // 2),
                "r": (vw - cw,        (vh - ch_h) // 2),
            }
            px, py = presets.get(cmd.preset, (cmd.pos_x or 0, cmd.pos_y or 0))
            # Clamp dans les limites vidéo
            px = max(0, min(px, vw - cw))
            py = max(0, min(py, vh - ch_h))
            ch.crop_explicit = CropZone(
                w=cw, h=ch_h,
                pos_x=px, pos_y=py,
                pos_mode="center" if cmd.preset == "c" else "topleft",
                explicit=True,
            )
            self._vf.resolve_inheritance()
            self._emit(EVT.EvtCropChanged(
                chapter_index=self._vf.active_index,
                crop=ch.crop_effective,
                inherited=ch.is_inherited,
            ))
            if ch.frame_raw is not None:
                self._emit_frame_from_raw(self._vf, ch, self._current_ts)
        self._emit(EVT.EvtDirty(is_dirty=True))
        

    def _on_copy_prev_crop(self, cmd: CMD.CmdCopyPrevCrop) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        idx = self._vf.active_index
        if idx == 0:
            self._emit(EVT.EvtStatus("Pas de chapitre précédent."))
            return
        prev_crop = self._vf.chapters[idx - 1].crop_effective
        if prev_crop is None:
            self._emit(EVT.EvtStatus("Le chapitre précédent n'a pas de crop."))
            return
        ch = self._active_chapter
        if ch:
            ch.crop_explicit = CropZone(
                w=prev_crop.w, h=prev_crop.h,
                pos_x=prev_crop.pos_x, pos_y=prev_crop.pos_y,
                pos_mode=prev_crop.pos_mode,
                explicit=True,
            )
            self._vf.resolve_inheritance()
            self._invalidate_and_reload()
        self._emit(EVT.EvtDirty(is_dirty=True))

    # ── Handlers chapitres ────────────────────────────────────────────────

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
            old_end          = ch.timestamp_sec + (ch.duration_sec or 0)
            ch.timestamp_sec = cmd.timestamp_sec
            ch.timestamp_raw = str(cmd.timestamp_sec)
            if ch.duration_sec is not None:
                ch.duration_sec = max(1, old_end - cmd.timestamp_sec)
        else:
            ch.duration_sec = max(1, cmd.duration_sec)
        self._emit(EVT.EvtChaptersUpdated(
            chapters=self._vf.chapters,
            full_rebuild=False,
            chapter_index=cmd.index,
        ))
        self._emit(EVT.EvtDirty(is_dirty=True))

    def _on_refresh_thumb(self, cmd: CMD.CmdRefreshThumb) -> None:
        if not self._require_vf():
            return
        assert self._vf is not None
        if cmd.chapter_index >= len(self._vf.chapters):
            return
        ch = self._vf.chapters[cmd.chapter_index]
        if ch.thumb_raw is None:
            return
        from video_processor.infra.renderer import Renderer
        rendered = Renderer.render_thumb_scaled(ch, self._vf.video_w, self._vf.video_h)
        if rendered:
            self._emit(EVT.EvtThumbReady(
                chapter_index=cmd.chapter_index,
                image=rendered,
                crop=ch.crop_effective,
                inherited=ch.is_inherited,
            ))


    # ── Handlers session ──────────────────────────────────────────────────

    def _on_save(self, cmd=None) -> None:
        if not self._require_vf():
            return
        vf = self._vf
        try:
            self._write_output(vf)
            self._emit(EVT.EvtDirty(is_dirty=False))
            self._emit(EVT.EvtStatus(f"Sauvegardé : {vf.short_name}"))
        except Exception as exc:
            log.error("Erreur _on_save : %s", exc)
            self._emit(EVT.EvtStatus(f"Erreur sauvegarde : {exc}"))

    def _write_output(self, vf: "VideoFile") -> None:
        """Construit le nouveau nom et renomme (ou écrit #toCut.txt)."""
        from video_processor.infra.filename_builder import FilenameBuilder
        new_name = FilenameBuilder.build(vf)
        if vf.uses_tocut:
            # Écrire le complément dans #toCut.txt
            from video_processor.infra.tocut_rw import TocutFile
            tocut_path = vf.physical_path.parent / "#toCut.txt"
            tocut = TocutFile.load(tocut_path) if tocut_path.exists() else TocutFile({})
            # Le complément = tout ce qui suit le short_name sans extension
            stem_new   = new_name.rsplit(".", 1)[0]
            stem_short = vf.short_name.rsplit(".", 1)[0]
            complement = stem_new[len(stem_short):]
            tocut.set(vf.short_name, complement)
            tocut.save(tocut_path)
            log.debug("_write_output : #toCut.txt mis à jour (%s → %s)", vf.short_name, complement)
        else:
            # Renommage physique
            new_path = vf.physical_path.parent / new_name
            if new_path != vf.physical_path:
                vf.physical_path.rename(new_path)
                log.debug("_write_output : renommé %s → %s", vf.short_name, new_name)

    def _on_save_and_next(self, cmd: CMD.CmdSaveAndNext) -> None:
        if not self._require_vf():
            return
        self._on_save(CMD.CmdSave())
        self._on_next_file(CMD.CmdNextFile())

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