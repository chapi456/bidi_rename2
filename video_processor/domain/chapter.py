"""
File: chapter.py
Path: video_processor/domain/chapter.py

Version: 2.0.0
Date: 2026-06-26

Changelog:
- 2.0.0 (2026-06-26): Refactoring CropZone → CropPos
  * crop_explicit / crop_effective supprimés
  * crop_pos (CropPos) : position explicite ou héritée du chapitre précédent
  * pos_inherited : True si position héritée
  * is_inherited supprimé (remplacé par pos_inherited)
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from PIL import Image as PILImage
    from .crop_pos import CropPos

log = logging.getLogger("domain.chapter")


@dataclass
class Chapter:
    index:           int
    timestamp_sec:   int
    timestamp_raw:   str
    duration_sec:    int
    title:           Optional[str] = None

    # ── Position crop (niveau chapitre) ───────────────────────────────────
    # None  → aucune position définie (pas de crop pour ce chapitre)
    # CropPos(explicit=True)  → posé par l'utilisateur
    # CropPos(explicit=False) → hérité du chapitre précédent
    crop_pos:      Optional["CropPos"] = field(default=None, repr=False)
    pos_inherited: bool                = False

    # ── Cache media (lazy) ────────────────────────────────────────────────
    frame_raw:     Optional["PILImage"] = field(default=None, repr=False)
    thumb_raw:     Optional["PILImage"] = field(default=None, repr=False)

    frame_loading: bool = False
    thumb_loading: bool = False

    frame_display: Optional["PILImage"] = field(default=None, repr=False)
    thumb_display: Optional["PILImage"] = field(default=None, repr=False)

    # ── Propriétés ────────────────────────────────────────────────────────

    @property
    def has_crop(self) -> bool:
        return self.crop_pos is not None

    @property
    def label(self) -> str:
        m, s = divmod(self.timestamp_sec, 60)
        h, m = divmod(m, 60)
        ts = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        return f"Ch{self.index + 1} — {ts}"

    # ── Invalidation cache ────────────────────────────────────────────────

    def invalidate_display(self) -> None:
        log.debug("Chapter[%d].invalidate_display()", self.index)
        self.frame_display = None
        self.thumb_display = None

    def invalidate_all(self) -> None:
        log.debug("Chapter[%d].invalidate_all()", self.index)
        self.frame_raw     = None
        self.thumb_raw     = None
        self.frame_display = None
        self.thumb_display = None
        self.frame_loading = False
        self.thumb_loading = False

    # ── Token nom de fichier ──────────────────────────────────────────────

    def to_filename_token(self) -> str:
        """Génère le token chapitre pour build_filename().
        La taille crop (w/h) est portée par VideoFile, pas ici.
        Seule la position est incluse si explicite.
        """
        log.debug("Chapter[%d].to_filename_token()", self.index)
        parts = [self.timestamp_raw]
        if self.duration_sec:
            parts.append(f"({self.duration_sec})")
        if self.title:
            parts.append(f"({self.title})")
        if self.crop_pos is not None:
            token = self.crop_pos.to_filename_token()
            if token:
                parts.append(token)
        return "".join(parts)