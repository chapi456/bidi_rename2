"""
File: crop_pos.py
Path: video_processor/domain/crop_pos.py

Version: 1.0.0
Date: 2026-06-26

Changelog:
- 1.0.0 (2026-06-26): Création — extrait de CropZone (position uniquement, niveau chapitre)
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .crop_size import CropSize

log = logging.getLogger("domain.crop_pos")

PosMode = Literal["topleft", "center"]


@dataclass
class CropPos:
    """Position du crop — propriété du chapitre, héritable du chapitre précédent."""
    x:        int     = 0
    y:        int     = 0
    mode:     PosMode = "topleft"
    explicit: bool    = False   # True si posé par l'utilisateur

    # ── Factories ─────────────────────────────────────────────────────────

    @classmethod
    def default_center(cls, size: "CropSize", vw: int, vh: int) -> "CropPos":
        """Position centrée, non explicite (position par défaut)."""
        return cls(
            x=(vw - size.w) // 2,
            y=(vh - size.h) // 2,
            mode="center",
            explicit=False,
        )

    @classmethod
    def default_topleft(cls) -> "CropPos":
        """Position haut-gauche, non explicite (position par défaut)."""
        return cls(x=0, y=0, mode="topleft", explicit=False)

    # ── Méthodes pures ────────────────────────────────────────────────────

    def clamped(self, size: "CropSize", vw: int, vh: int) -> "CropPos":
        """Retourne une copie dont x/y restent dans les bornes vidéo."""
        return CropPos(
            x=max(0, min(self.x, vw - size.w)),
            y=max(0, min(self.y, vh - size.h)),
            mode=self.mode,
            explicit=self.explicit,
        )

    def to_filename_token(self) -> str:
        """Génère le token position pour le nom de fichier (chapitre).
        Retourne '' si position par défaut (non explicite).
        """
        if not self.explicit:
            return ""
        if self.mode == "center":
            return "(CENTER)"
        if self.x != 0 or self.y != 0:
            return f"({self.x}x{self.y})"
        return ""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CropPos):
            return False
        return self.x == other.x and self.y == other.y and self.mode == other.mode