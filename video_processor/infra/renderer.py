"""
File: renderer.py
Path: video_processor/infra/renderer.py

Version: 1.0.0
Date: 2026-06-23

Changelog:
- 1.0.0 (2026-06-23): Implémentation complète
  * render_frame(chapter, scale) → PIL.Image avec overlay crop
  * render_thumb(chapter) → PIL.Image vignette avec overlay crop miniature
  * _overlay() : masque sombre hors crop + rectangle + 8 poignées
  * _draw_grid() : grille semi-transparente tous les 200px vidéo
  * _handles() : 8 positions de poignées en coords écran
  * Couleurs et tailles en constantes de module
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage
    from video_processor.domain.chapter  import Chapter
    from video_processor.domain.crop_zone import CropZone

log = logging.getLogger("infra.renderer")

# ── Constantes configurables ──────────────────────────────────────────────────
COLOR_EXPLICIT:   Tuple[int,int,int] = (255, 140,   0)   # orange
COLOR_INHERITED:  Tuple[int,int,int] = ( 77, 166, 255)   # bleu clair
COLOR_MASK:       Tuple[int,int,int,int] = (0, 0, 0, 120) # masque semi-transparent
COLOR_GRID:       Tuple[int,int,int,int] = (255, 255, 255, 40)
HANDLE_R:   int = 6      # rayon des poignées (px écran)
GRID_STEP:  int = 200    # pas de la grille (px vidéo)
RECT_WIDTH: int = 2      # épaisseur du rectangle crop


class Renderer:
    """Rendu PIL : overlay crop sur une frame. Fonctions pures, sans état."""

    # ── API publique ──────────────────────────────────────────────────────────

    @staticmethod
    def render_frame(chapter: "Chapter", scale: float) -> Optional["PILImage"]:
        """Retourne frame_raw redimensionnée + overlay crop, stockée dans frame_display.

        Returns None si frame_raw absent.
        """
        from PIL import Image

        if chapter.frame_raw is None:
            return None

        # Redimensionner à scale
        orig_w, orig_h = chapter.frame_raw.size
        new_w = max(1, int(orig_w * scale))
        new_h = max(1, int(orig_h * scale))
        # Choisir un filtre de resampling compatible avec plusieurs versions de Pillow
        try:
            resample = Image.Resampling.LANCZOS  # Pillow >= 9.1
        except AttributeError:
            # fallback: prefer LANCZOS, then ANTIALIAS, then BICUBIC, then BILINEAR, then NEAREST (numeric 0 as last resort)
            resample = getattr(
                Image, "LANCZOS",
                getattr(
                    Image, "ANTIALIAS",
                    getattr(
                        Image, "BICUBIC",
                        getattr(Image, "BILINEAR", getattr(Image, "NEAREST", 0))
                    )
                )
            )

        img: PILImage = chapter.frame_raw.resize((new_w, new_h), resample)

        # Overlay crop si présent
        if chapter.crop_effective is not None:
            img = Renderer._overlay(img, chapter.crop_effective,
                                    scale, chapter.is_inherited)

        chapter.frame_display = img
        return img

    @staticmethod
    def render_thumb(chapter: "Chapter") -> Optional["PILImage"]:
        """Retourne thumb_raw + overlay crop miniature, stockée dans thumb_display.

        Returns None si thumb_raw absent.
        """
        if chapter.thumb_raw is None:
            return None

        tw, th = chapter.thumb_raw.size
        # Scale thumb : ratio thumb / taille vidéo native inconnue ici,
        # on applique l'overlay directement en coords thumb (scale=1.0)
        img: PILImage = chapter.thumb_raw.copy()

        if chapter.crop_effective is not None:
            # On ne connaît pas vw/vh ici → on passe scale=1.0,
            # les coords crop sont déjà en px vidéo natifs.
            # Le contrôleur devra passer un scale adapté si nécessaire.
            img = Renderer._overlay(img, chapter.crop_effective,
                                    scale=1.0, inherited=chapter.is_inherited)

        chapter.thumb_display = img
        return img

    @staticmethod
    def render_thumb_scaled(
        chapter: "Chapter",
        video_w: int,
        video_h: int,
    ) -> Optional["PILImage"]:
        """Variante : calcule le scale vidéo→thumb automatiquement.

        À préférer à render_thumb() quand on connaît les dimensions vidéo.
        """
        if chapter.thumb_raw is None:
            return None

        tw, th = chapter.thumb_raw.size
        scale  = tw / video_w if video_w > 0 else 1.0

        img: PILImage = chapter.thumb_raw.copy()
        if chapter.crop_effective is not None:
            img = Renderer._overlay(img, chapter.crop_effective,
                                    scale, chapter.is_inherited)

        chapter.thumb_display = img
        return img

    # ── Overlay interne ───────────────────────────────────────────────────────

    @staticmethod
    def _overlay(
        img: "PILImage",
        crop: "CropZone",
        scale: float,
        inherited: bool,
    ) -> "PILImage":
        """Applique masque sombre hors crop + rectangle coloré + 8 poignées."""
        from PIL import Image, ImageDraw

        img = img.convert("RGBA")
        w, h = img.size

        # Coords crop en pixels écran
        cx = int(crop.pos_x * scale)
        cy = int(crop.pos_y * scale)
        cw = int(crop.w     * scale)
        ch = int(crop.h     * scale)

        # Clamp dans l'image
        cx = max(0, min(cx, w))
        cy = max(0, min(cy, h))
        cw = max(1, min(cw, w - cx))
        ch = max(1, min(ch, h - cy))

        # ── Masque sombre sur les zones hors crop ──────────────────────────
        mask = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        md   = ImageDraw.Draw(mask)
        # 4 rectangles autour du crop
        if cy > 0:
            md.rectangle([0, 0, w, cy], fill=COLOR_MASK)
        if cy + ch < h:
            md.rectangle([0, cy + ch, w, h], fill=COLOR_MASK)
        if cx > 0:
            md.rectangle([0, cy, cx, cy + ch], fill=COLOR_MASK)
        if cx + cw < w:
            md.rectangle([cx + cw, cy, w, cy + ch], fill=COLOR_MASK)
        img = Image.alpha_composite(img, mask)

        # ── Rectangle crop ─────────────────────────────────────────────────
        color = COLOR_INHERITED if inherited else COLOR_EXPLICIT
        draw  = ImageDraw.Draw(img)
        draw.rectangle(
            [cx, cy, cx + cw, cy + ch],
            outline=color,
            width=RECT_WIDTH,
        )

        # ── 8 poignées ─────────────────────────────────────────────────────
        for (hx, hy) in Renderer._handles(crop, scale):
            draw.ellipse(
                [hx - HANDLE_R, hy - HANDLE_R,
                 hx + HANDLE_R, hy + HANDLE_R],
                fill=color,
            )

        return img.convert("RGB")

    @staticmethod
    def _draw_grid(
        img: "PILImage",
        scale: float,
        vw: int,
        vh: int,
    ) -> "PILImage":
        """Grille semi-transparente tous les GRID_STEP px vidéo avec coords."""
        from PIL import Image, ImageDraw, ImageFont

        img = img.convert("RGBA")
        grid = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(grid)

        # Lignes verticales
        x = GRID_STEP
        while x < vw:
            sx = int(x * scale)
            draw.line([(sx, 0), (sx, img.height)], fill=COLOR_GRID, width=1)
            draw.text((sx + 2, 2), str(x), fill=(255, 255, 255, 120))
            x += GRID_STEP

        # Lignes horizontales
        y = GRID_STEP
        while y < vh:
            sy = int(y * scale)
            draw.line([(0, sy), (img.width, sy)], fill=COLOR_GRID, width=1)
            draw.text((2, sy + 2), str(y), fill=(255, 255, 255, 120))
            y += GRID_STEP

        return Image.alpha_composite(img, grid).convert("RGB")

    @staticmethod
    def _handles(crop: "CropZone", scale: float) -> list:
        """Retourne les 8 positions (x, y) des poignées en coordonnées écran."""
        cx = int(crop.pos_x * scale)
        cy = int(crop.pos_y * scale)
        cw = int(crop.w     * scale)
        ch = int(crop.h     * scale)
        mx = cx + cw // 2   # milieu horizontal
        my = cy + ch // 2   # milieu vertical
        return [
            (cx,      cy),        # coin haut-gauche
            (mx,      cy),        # milieu haut
            (cx + cw, cy),        # coin haut-droit
            (cx + cw, my),        # milieu droit
            (cx + cw, cy + ch),   # coin bas-droit
            (mx,      cy + ch),   # milieu bas
            (cx,      cy + ch),   # coin bas-gauche
            (cx,      my),        # milieu gauche
        ]