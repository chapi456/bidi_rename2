"""
File: renderer.py
Path: video_processor/infra/renderer.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage
    from video_processor.domain.chapter import Chapter
    from video_processor.domain.crop_zone import CropZone

log = logging.getLogger("infra.renderer")

COLOR_EXPLICIT  = (255, 140,   0)
COLOR_INHERITED = ( 77, 166, 255)
HANDLE_R        = 6


class Renderer:
    """Rendu PIL : overlay crop sur une frame. Fonctions pures, sans état."""

    @staticmethod
    def render_frame(chapter: "Chapter", scale: float) -> Optional["PILImage"]:
        """Retourne frame_raw avec overlay crop redimensionné à l'écran.

        - Si chapter.frame_raw est None : retourne None
        - Redimensionne à scale
        - Applique _overlay si chapter.crop_effective
        - Stocke dans chapter.frame_display
        - Retourne chapter.frame_display
        """
        log.debug("BOUCHON Renderer.render_frame(ch=%d, scale=%.2f)",
                  chapter.index, scale)
        return None  # stub

    @staticmethod
    def render_thumb(chapter: "Chapter",
                     size: Tuple[int, int] = (160, 90)) -> Optional["PILImage"]:
        """Retourne thumb_raw avec overlay crop adapté à la taille vignette.

        - Si chapter.thumb_raw est None : retourne None
        - Applique _overlay si chapter.crop_effective
        - Stocke dans chapter.thumb_display
        - Retourne chapter.thumb_display
        """
        log.debug("BOUCHON Renderer.render_thumb(ch=%d)", chapter.index)
        return None  # stub

    @staticmethod
    def _overlay(img: "PILImage", crop: "CropZone",
                 scale: float, inherited: bool) -> "PILImage":
        """Applique l'overlay crop+handles sur une image PIL. Fonction pure.

        - Masque sombre sur les zones hors crop
        - Rectangle crop en couleur (orange=explicit, bleu=inherited)
        - 8 poignées de redimensionnement
        """
        log.debug("BOUCHON Renderer._overlay(crop=%s, scale=%.2f, inh=%s)",
                  crop, scale, inherited)
        return img  # stub

    @staticmethod
    def _draw_grid(img: "PILImage", scale: float,
                   vw: int, vh: int) -> "PILImage":
        """Grille semi-transparente tous les 200px vidéo avec valeurs affichées."""
        log.debug("BOUCHON Renderer._draw_grid(scale=%.2f)", scale)
        return img  # stub

    @staticmethod
    def _handles(crop: "CropZone", scale: float) -> list[Tuple[int, int]]:
        """Retourne les 8 positions (x,y) des poignées en coordonnées écran."""
        log.debug("BOUCHON Renderer._handles()")
        return []  # stub
