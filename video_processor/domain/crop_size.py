"""
File: crop_size.py
Path: video_processor/domain/crop_size.py

Version: 1.0.0
Date: 2026-06-26

Changelog:
- 1.0.0 (2026-06-26): Création — extrait de CropZone (taille uniquement, niveau vidéo)
"""

from __future__ import annotations
import logging
from dataclasses import dataclass

log = logging.getLogger("domain.crop_size")


@dataclass
class CropSize:
    """Taille du crop — propriété de la vidéo, partagée entre tous les chapitres."""
    w: int
    h: int

    def to_filename_token(self) -> str:
        """Génère le token CROP(WxH) pour le nom de fichier."""
        return f"CROP({self.w}x{self.h})"

    def to_ffmpeg_crop(self, pos: "CropPos") -> str:  # noqa: F821
        """Génère le filtre crop= pour ffmpeg, combiné avec une CropPos."""
        return f"crop={self.w}:{self.h}:{pos.x}:{pos.y}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CropSize):
            return False
        return self.w == other.w and self.h == other.h