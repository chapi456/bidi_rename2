"""
File: chapter.py
Path: video_processor/domain/chapter.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from PIL import Image as PILImage
    from .crop_zone import CropZone

log = logging.getLogger("domain.chapter")


@dataclass
class Chapter:
    index:           int
    timestamp_sec:   int
    timestamp_raw:   str          # "01-23" tel que dans le nom fichier
    duration_sec:    int
    title:           Optional[str] = None

    # ── Crop ──────────────────────────────────────────────────────────────
    # crop_explicit  : ce que l'utilisateur a défini pour CE chapitre
    # crop_effective : résultat après héritage (calculé par resolve_inheritance)
    crop_explicit:   Optional["CropZone"] = field(default=None, repr=False)
    crop_effective:  Optional["CropZone"] = field(default=None, repr=False)
    is_inherited:    bool                  = False

    # ── Cache media (lazy) ────────────────────────────────────────────────
    # Jamais manipulé directement par l'UI — via SessionController uniquement
    frame_raw:       Optional["PILImage"] = field(default=None, repr=False)
    thumb_raw:       Optional["PILImage"] = field(default=None, repr=False)

    # Flags d'état asynchrone
    frame_loading:   bool = False
    thumb_loading:   bool = False

    # ── Rendu calculé (invalidé quand crop ou frame change) ───────────────
    frame_display:   Optional["PILImage"] = field(default=None, repr=False)
    thumb_display:   Optional["PILImage"] = field(default=None, repr=False)

    # ── Propriétés ────────────────────────────────────────────────────────

    @property
    def has_crop(self) -> bool:
        return self.crop_effective is not None

    @property
    def label(self) -> str:
        """Label court pour UI : 'Ch1 — 00:01:23'."""
        m, s = divmod(self.timestamp_sec, 60)
        h, m = divmod(m, 60)
        ts = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        return f"Ch{self.index + 1} — {ts}"

    # ── Invalidation cache ────────────────────────────────────────────────

    def invalidate_display(self) -> None:
        """Invalide les images rendues (frame + thumb).
        À appeler dès que crop_effective ou frame_raw change.
        """
        log.debug("BOUCHON Chapter[%d].invalidate_display()", self.index)
        self.frame_display = None
        self.thumb_display = None

    def invalidate_all(self) -> None:
        """Invalide tout y compris les raws (changement de fichier)."""
        log.debug("BOUCHON Chapter[%d].invalidate_all()", self.index)
        self.frame_raw     = None
        self.thumb_raw     = None
        self.frame_display = None
        self.thumb_display = None
        self.frame_loading = False
        self.thumb_loading = False

    # ── Token nom de fichier ──────────────────────────────────────────────

    def to_filename_token(self) -> str:
        """Génère le token chapitre pour build_filename().
        Inclut la position du crop si explicite.
        """
        log.debug("BOUCHON Chapter[%d].to_filename_token()", self.index)
        parts = [self.timestamp_raw]
        if self.duration_sec:
            parts.append(f"({self.duration_sec})")
        if self.title:
            parts.append(f"({self.title})")
        if self.crop_explicit and self.crop_explicit.explicit:
            c = self.crop_explicit
            if c.pos_mode == "center":
                parts.append("(CENTER)")
            elif c.pos_x != 0 or c.pos_y != 0:
                parts.append(f"({c.pos_x}x{c.pos_y})")
        return "".join(parts)
