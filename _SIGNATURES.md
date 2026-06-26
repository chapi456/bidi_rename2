# _SIGNATURES.md — Pense-bête signatures bidi_rename2
Mis à jour : 2026-06-26

---

## video_processor/controller/commands.py

```python
CmdJump(chapter_index: int)
CmdSeekAbs(timestamp_sec: float = 0.0)
CmdSeekDelta(delta_sec: int)
CmdSeekBegin()
CmdSeekEnd()
CmdSeekChapterStart()
CmdSeekChapterEnd()
CmdAddCrop()
CmdDelCrop()
CmdSetCrop(w: Optional[int]=None, h: Optional[int]=None,
           pos_x: Optional[int]=None, pos_y: Optional[int]=None)
CmdSetPosition(preset: str,           # "l"|"c"|"r"|"topleft"
               pos_x: Optional[int]=None, pos_y: Optional[int]=None)
CmdCopyPrevCrop()
CmdValidateChapter()
CmdPrevChapter()
CmdAddChapter(timestamp_sec: int, duration_sec: int, title: str)
CmdEditChapter(index: int, title: str, timestamp_sec: int,
               timestamp_raw: str, duration_sec: int)
CmdChapterEdge(index: int, kind: str,
               timestamp_sec: float=0.0, duration_sec: float=0.0)
CmdSave()
CmdSaveAndNext()
CmdNextFile()
CmdLoadFile(path: Path)
CmdQuit()
CmdRefreshThumb(chapter_index: int)
```

---

## video_processor/controller/events.py

```python
EvtSessionLoaded(video_file: VideoFile)
EvtSessionFilesUpdated(names: List[str], current: int)
#   names   = [e.short_name for e in session.entries]
#   current = session.current_index

EvtStatus(text: str)
EvtTitle(text: str)
EvtDirty(is_dirty: bool)
EvtChapterChanged(index: int)
EvtChaptersUpdated(chapters: list,        # list[Chapter]
                   full_rebuild: bool=True,
                   chapter_index: int=0)
EvtAllCropsInvalidated()
EvtCropsResolved(crops: list)             # list[Optional[CropZone]]
EvtCropChanged(chapter_index: int, crop: Optional[CropZone], inherited: bool)
EvtFrameReady(chapter_index: int, image: PILImage,
              crop: Optional[CropZone], inherited: bool,
              timestamp_sec: float=0.0)
EvtThumbReady(chapter_index: int, image: PILImage,
              crop: Optional[CropZone], inherited: bool)
EvtPositionChanged(timestamp_sec: float)  # float — sub-seconde
```

---

## video_processor/domain/crop_zone.py

```python
@dataclass
CropZone(w: int, h: int, pos_x: int=0, pos_y: int=0,
         pos_mode: Literal["topleft","center"]="topleft",
         explicit: bool=False)

# Factories (classmethods)
CropZone.default(vw: int, vh: int) -> CropZone         # 80% centré
CropZone.centered(w: int, h: int, vw: int, vh: int) -> CropZone
CropZone.from_parsed(data: dict) -> CropZone

# Méthodes pures (retournent une copie)
.with_position(pos_x: int, pos_y: int, mode: PosMode="topleft") -> CropZone
.with_size(w: int, h: int) -> CropZone
.clamped(vw: int, vh: int) -> CropZone

# Sérialisation
.to_ffmpeg_filter() -> str   # "crop=W:H:X:Y"
.to_filename_token() -> str  # "CROP(WxH)"
```

---

## video_processor/domain/chapter.py

```python
@dataclass
Chapter(index: int, timestamp_sec: int, timestamp_raw: str,
        duration_sec: int, title: Optional[str]=None,
        crop_explicit: Optional[CropZone]=None,
        crop_effective: Optional[CropZone]=None,
        is_inherited: bool=False,
        frame_raw: Optional[PILImage]=None,
        thumb_raw: Optional[PILImage]=None,
        frame_loading: bool=False, thumb_loading: bool=False,
        frame_display: Optional[PILImage]=None,
        thumb_display: Optional[PILImage]=None)

# Propriétés
.has_crop -> bool
.label    -> str    # "Ch1 — 00:01:23"

# Méthodes
.invalidate_display() -> None   # efface frame_display + thumb_display
.invalidate_all() -> None       # efface tout y compris raws + flags
.to_filename_token() -> str     # token chapitre pour build_filename()
```

---

## video_processor/domain/video_file.py

```python
@dataclass
VideoFile(
    physical_path: Path, short_name: str, long_name: str,
    uses_tocut: bool=False, complement: str="",
    title: Optional[str]=None, studio: Optional[str]=None,
    actors: list[str]=[], styles: list[str]=[], date: Optional[str]=None,
    booleans: dict={}, options: dict={}, file_id: Optional[str]=None,
    video_w: int=0, video_h: int=0, total_duration_sec: int=0,
    global_crop_size: Optional[CropZone]=None,  # taille partagée tous chapitres
    chapters: list[Chapter]=[],
    active_index: int=0, dirty: bool=False
)

# Propriétés
.active_chapter -> Optional[Chapter]
.has_crop       -> bool
.extension      -> str

# Méthodes
.resolve_inheritance() -> None
    # Règle 1 : crop_explicit → effective = _apply_global_size(explicit), is_inherited=False
    # Règle 2 : pas explicit + last_explicit → effective = last_explicit, is_inherited=True
    # Règle 3 : pas explicit + rien → effective=None, is_inherited=False

._apply_global_size(crop: CropZone) -> CropZone
    # Remplace w/h par global_crop_size.w/h, conserve pos_x/pos_y/pos_mode
    # Retourne crop tel quel si global_crop_size is None

.invalidate_all_displays() -> None
.build_filename() -> str          # long_name complet reconstruit
.build_short_filename() -> str    # nom physique sans CROP ni chapitres
.chapter_at_time(ts_sec: int) -> int
```

---

## video_processor/domain/session.py

```python
@dataclass
SessionEntry(physical_path: Path, short_name: str, long_name: str,
             complement: str="", target_name: Optional[str]=None)
# Propriétés
.display_name -> str   # = long_name
.directory    -> Path
.extension    -> str
.is_dirty     -> bool

class VideoSession:   # Singleton — VideoSession.get()
.entries        -> list[SessionEntry]   # délègue à DirectoryScanner
.current_entry  -> Optional[SessionEntry]
.current_index  -> int   # getter + setter (clampé)
.get_entry(index: int) -> Optional[SessionEntry]
.get_count() -> int
.set_current_by_path(path: Path) -> bool
.advance() -> bool
.go_back()  -> bool
.go_to(index: int) -> bool
.refresh()  -> None
```

---

## video_processor/controller/session_controller.py

```python
class SessionController:
    __init__(session: VideoSession) -> None

    .subscribe(handler: Callable[[object], None]) -> None
    .send(cmd: object) -> None    # dispatch vers _on_*
    .open_current() -> None       # charge session.current_entry

# Commandes dispatchées (privé)
._on_jump(CmdJump)
._on_seek_abs(CmdSeekAbs)
._on_seek_delta(CmdSeekDelta)
._on_seek_begin(CmdSeekBegin)
._on_seek_end(CmdSeekEnd)
._on_seek_chapter_start(CmdSeekChapterStart)
._on_seek_chapter_end(CmdSeekChapterEnd)
._on_add_crop(CmdAddCrop)
._on_del_crop(CmdDelCrop)
._on_set_crop(CmdSetCrop)         # ⚠ propage w/h à vf.global_crop_size si changés
._on_set_position(CmdSetPosition)
._on_copy_prev_crop(CmdCopyPrevCrop)
._on_validate_chapter(CmdValidateChapter)
._on_prev_chapter(CmdPrevChapter)
._on_add_chapter(CmdAddChapter)
._on_edit_chapter(CmdEditChapter)
._on_chapter_edge(CmdChapterEdge)
._on_refresh_thumb(CmdRefreshThumb)
._on_save(cmd=None)
._on_save_and_next(CmdSaveAndNext)
._on_next_file(CmdNextFile)
._on_load_file(CmdLoadFile)
._on_quit(CmdQuit)

# Helpers internes
._emit_session_files() -> None
    # Émet EvtSessionFilesUpdated(names=[e.short_name ...], current=index)
._load_entry(path: Path) -> None
._preload_thumbs() -> None        # thread daemon
._load_frame(chapter_index: int, ts_sec: Optional[int]=None) -> None
._emit_frame_from_raw(vf, ch, ts) -> None   # scale=1.0, letterbox côté UI
._seek(ts: float) -> None
```

---

## video_processor/ui/tkinter_view.py

```python
class TkinterView(BaseView):
    # État
    ._vf: Optional[VideoFile]          # source de vérité UI
    ._canvas_scale: float              # nw / video_w (mis à jour dans _on_frame_ready)
    ._canvas_offset: tuple[int,int]    # (off_x, off_y) letterbox
    ._drag_state: Optional[dict]       # {mode, handle_idx, snap_x, snap_y, crop0}
    ._hover_handle_idx: Optional[int]
    ._session_paths: dict[str, Path]   # {short_name: physical_path} — après EvtSessionFilesUpdated

    # Spinbox vars
    ._var_w, ._var_h: tk.IntVar   # panneau gauche CROP
    ._var_x, ._var_y: tk.IntVar   # panneau droit POSITION

    # Combobox
    ._file_var:   tk.StringVar
    ._file_combo: ttk.Combobox

    # Handlers événements
    ._on_session_loaded(EvtSessionLoaded)
    ._on_session_files_updated(EvtSessionFilesUpdated)
        # Alimente _file_combo["values"] = evt.names
        # _file_var.set(evt.names[evt.current])
    ._on_status(EvtStatus)
    ._on_title(EvtTitle)
    ._on_dirty(EvtDirty)
    ._on_chapter_changed(EvtChapterChanged)
    ._on_chapters_updated(EvtChaptersUpdated)
    ._on_crop_changed(EvtCropChanged)
    ._on_all_crops_invalidated(EvtAllCropsInvalidated)
    ._on_frame_ready(EvtFrameReady)        # calcule scale + offset letterbox
    ._on_thumb_ready(EvtThumbReady)
    ._on_position_changed(EvtPositionChanged)

    # Interactions utilisateur
    ._on_file_combo_selected()             # → CmdLoadFile si nom ≠ courant
    ._on_canvas_resize(event=None)         # corps = pass (scale mis à jour par _on_frame_ready)
    ._on_mouse_press/_move/_release/_hover # drag crop : move + resize 8 poignées
    ._on_crop_spinbox()                    # → CmdSetCrop(w, h)
    ._on_position_spinbox()                # → CmdSetCrop(pos_x, pos_y)
    ._on_thumb_click(chapter_index)        # → CmdJump
    ._on_thumb_double_click(chapter_index) # popup titre chapitre
    ._on_add_chapter_here()               # → CmdAddChapter(ts courant)
    ._on_edit_file_info(key)               # popup (TODO-16, non câblé)
    ._on_edit_chapter_info(key)            # popup titre/durée chapitre actif

    # Helpers UI
    ._update_info_panels()
    ._update_crop_fields(crop: Optional[CropZone])
    ._canvas_to_video(x, y) -> tuple[int,int]
    ._rebuild_thumb_strip()
    ._update_thumb_cell(index: int)
    ._highlight_thumb(active_index: int)
    ._popup_edit(title, current, on_ok: Callable[[str], None])
    ._chapter_label(ch: Chapter) -> str    # statique
    ._parse_duration(s: str) -> int        # statique
```

---

## video_processor/infra/renderer.py (méthodes publiques connues)

```python
Renderer.render_frame(ch: Chapter, scale: float=1.0) -> Optional[PILImage]
    # scale=1.0 → frame native, letterbox côté UI uniquement
Renderer.render_thumb_scaled(ch: Chapter, vw: int, vh: int) -> Optional[PILImage]
Renderer._handles(crop: CropZone, canvas_scale: float) -> list[tuple[int,int]]
    # 8 poignées en coordonnées canvas (sans offset letterbox)
HANDLE_R: int   # rayon des poignées (tolérance hit-test = HANDLE_R + 5)
```

---

## video_processor/infra/frame_extractor.py (méthodes publiques connues)

```python
FrameExtractor.probe(path: Path) -> tuple[int, int, int]   # vw, vh, total_sec
FrameExtractor.extract(path: Path, ts_sec: int) -> Optional[PILImage]
FrameExtractor.extract_thumb(path: Path, ts_sec: int) -> Optional[PILImage]
```
