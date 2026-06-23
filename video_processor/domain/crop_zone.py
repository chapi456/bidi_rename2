"""
File: crop_zone.py
Path: video_processor/domain/crop_zone.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Literal

PosMode = Literal["topleft", "center"]


@dataclass
class CropZone:
    w:        int
    h:        int
    pos_x:    int      = 0
    pos_y:    int      = 0
    pos_mode: PosMode  = "topleft"
    explicit: bool     = False   # posé par l'utilisateur (vs hérité/défaut)

    # ── Factories ─────────────────────────────────────────────────────────

    @classmethod
    def default(cls, vw: int, vh: int) -> "CropZone":
        """Crop par défaut : -20% centré."""
        log = _log()
        log.debug("BOUCHON CropZone.default(%d, %d)", vw, vh)
        cw = int(vw * 0.80)
        ch = int(vh * 0.80)
        return cls(w=cw, h=ch,
                   pos_x=(vw - cw) // 2, pos_y=(vh - ch) // 2,
                   pos_mode="topleft", explicit=True)

    @classmethod
    def centered(cls, w: int, h: int, vw: int, vh: int) -> "CropZone":
        """Crée une zone de taille (w,h) centrée dans la vidéo."""
        log = _log()
        log.debug("BOUCHON CropZone.centered(%d,%d) dans %dx%d", w, h, vw, vh)
        return cls(w=w, h=h,
                   pos_x=(vw - w) // 2, pos_y=(vh - h) // 2,
                   pos_mode="center", explicit=True)

    @classmethod
    def from_parsed(cls, data: dict) -> "CropZone":
        """Construit depuis un dict issu du parser (options['CROP'])."""
        log = _log()
        log.debug("BOUCHON CropZone.from_parsed(%s)", data)
        return cls(
            w=int(data.get("w", 0)),
            h=int(data.get("h", 0)),
            pos_x=int(data.get("pos_x", 0)),
            pos_y=int(data.get("pos_y", 0)),
            pos_mode=data.get("pos_mode", "topleft"),
            explicit=bool(data.get("pos_x") is not None),
        )

    # ── Méthodes pures ────────────────────────────────────────────────────

    def with_position(self, pos_x: int, pos_y: int,
                      mode: PosMode = "topleft") -> "CropZone":
        """Retourne une copie avec nouvelle position (immutable-style)."""
        log = _log()
        log.debug("BOUCHON CropZone.with_position(%d, %d)", pos_x, pos_y)
        return CropZone(w=self.w, h=self.h,
                        pos_x=pos_x, pos_y=pos_y,
                        pos_mode=mode, explicit=True)

    def with_size(self, w: int, h: int) -> "CropZone":
        """Retourne une copie avec nouvelle taille, position conservée."""
        log = _log()
        log.debug("BOUCHON CropZone.with_size(%d, %d)", w, h)
        return CropZone(w=w, h=h,
                        pos_x=self.pos_x, pos_y=self.pos_y,
                        pos_mode=self.pos_mode, explicit=self.explicit)

    def clamped(self, vw: int, vh: int) -> "CropZone":
        """Retourne une copie dont pos_x/pos_y sont dans les bornes vidéo."""
        log = _log()
        log.debug("BOUCHON CropZone.clamped(vw=%d, vh=%d)", vw, vh)
        return CropZone(
            w=min(self.w, vw), h=min(self.h, vh),
            pos_x=max(0, min(self.pos_x, vw - self.w)),
            pos_y=max(0, min(self.pos_y, vh - self.h)),
            pos_mode=self.pos_mode, explicit=self.explicit,
        )

    def to_ffmpeg_filter(self) -> str:
        """Génère le filtre crop= pour ffmpeg."""
        log = _log()
        log.debug("BOUCHON CropZone.to_ffmpeg_filter()")
        return f"crop={self.w}:{self.h}:{self.pos_x}:{self.pos_y}"

    def to_filename_token(self) -> str:
        """Génère le token CROP(WxH) pour le nom de fichier."""
        log = _log()
        log.debug("BOUCHON CropZone.to_filename_token()")
        return f"CROP({self.w}x{self.h})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CropZone):
            return False
        return (self.w == other.w and self.h == other.h
                and self.pos_x == other.pos_x and self.pos_y == other.pos_y)


def _log():
    return logging.getLogger("domain.crop_zone")
