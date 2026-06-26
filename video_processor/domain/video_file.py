"""
File: video_file.py
Path: video_processor/domain/video_file.py

Version: 1.1.0
Date: 2026-06-26

Changelog:
- 1.1.0 (2026-06-26): BUG-28 — _apply_global_size corrigé
  * Taille propre du crop_explicit (w>0, h>0) conservée ; global_crop_size ne
    remplace plus une taille explicitement définie
  * Recalcul pos_x/pos_y en mode "center" UNIQUEMENT (pos topleft conservée)
  * Optimisation : retourne crop inchangé si aucune valeur ne diffère
- 1.0.0 (2026-06-23): Implémentation complète
  * resolve_inheritance() : héritage crop chapitre par chapitre
  * build_filename() / build_short_filename() : reconstruction nom
  * invalidate_all_displays(), chapter_at_time()
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .chapter import Chapter
from .crop_zone import CropZone

log = logging.getLogger("domain.video_file")


@dataclass
class VideoFile:
    # ── Identité ──────────────────────────────────────────────────────────
    physical_path: Path
    short_name: str
    long_name: str
    uses_tocut: bool = False
    complement: str = ""

    # ── Métadonnées parsées ───────────────────────────────────────────────
    title: Optional[str] = None
    studio: Optional[str] = None
    actors: list[str] = field(default_factory=list)
    styles: list[str] = field(default_factory=list)
    date: Optional[str] = None
    booleans: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)
    file_id: Optional[str] = None

    # ── Dimensions vidéo ──────────────────────────────────────────────────
    video_w: int = 0
    video_h: int = 0
    total_duration_sec: int = 0

    # ── Crop GLOBAL (taille partagée) ─────────────────────────────────────
    global_crop_size: Optional[CropZone] = None

    # ── Chapitres ─────────────────────────────────────────────────────────
    chapters: list[Chapter] = field(default_factory=list)

    # ── État session ──────────────────────────────────────────────────────
    active_index: int = 0
    dirty: bool = False

    @property
    def active_chapter(self) -> Optional[Chapter]:
        if not self.chapters:
            return None
        idx = max(0, min(self.active_index, len(self.chapters) - 1))
        return self.chapters[idx]

    @property
    def has_crop(self) -> bool:
        return self.global_crop_size is not None

    @property
    def extension(self) -> str:
        return self.physical_path.suffix

    def resolve_inheritance(self) -> None:
        """Recalcule crop_effective et is_inherited pour tous les chapitres.

        Règle 1 : crop_explicit défini  → effective = _apply_global_size(explicit)
                                           is_inherited = False, devient last_explicit
        Règle 2 : pas d'explicit + last_explicit → effective = last_explicit
                                                   is_inherited = True
        Règle 3 : pas d'explicit + rien → effective = None, is_inherited = False
        """
        log.debug("VideoFile.resolve_inheritance() — %d chapitres", len(self.chapters))
        last_explicit: Optional[CropZone] = None

        for ch in self.chapters:
            if ch.crop_explicit is not None:
                effective = self._apply_global_size(ch.crop_explicit)
                ch.crop_effective = effective
                ch.is_inherited = False
                last_explicit = effective
            elif last_explicit is not None:
                ch.crop_effective = last_explicit
                ch.is_inherited = True
            else:
                ch.crop_effective = None
                ch.is_inherited = False

            ch.invalidate_display()
            log.debug(
                "  ch[%d] explicit=%s effective=%s inherited=%s",
                ch.index, ch.crop_explicit, ch.crop_effective, ch.is_inherited,
            )

    def _apply_global_size(self, crop: CropZone) -> CropZone:
        """Retourne crop avec taille globale appliquée si le crop n'en a pas.

        BUG-28 — Règles corrigées :
        - crop.w > 0 et crop.h > 0  → taille propre conservée
        - crop.w == 0 ou crop.h == 0 → global_crop_size.w/h utilisés
        - pos_mode == "center" → pos_x/pos_y recalculés depuis video_w/video_h
        - pos_mode != "center" → pos_x/pos_y conservés
        - global_crop_size is None → retourne crop inchangé
        """
        if self.global_crop_size is None:
            return crop

        final_w = crop.w if crop.w > 0 else self.global_crop_size.w
        final_h = crop.h if crop.h > 0 else self.global_crop_size.h

        if crop.pos_mode == "center":
            final_x = (self.video_w - final_w) // 2 if self.video_w > 0 else crop.pos_x
            final_y = (self.video_h - final_h) // 2 if self.video_h > 0 else crop.pos_y
        else:
            final_x = crop.pos_x
            final_y = crop.pos_y

        if (
            final_w == crop.w
            and final_h == crop.h
            and final_x == crop.pos_x
            and final_y == crop.pos_y
        ):
            return crop

        return CropZone(
            w=final_w,
            h=final_h,
            pos_x=final_x,
            pos_y=final_y,
            pos_mode=crop.pos_mode,
            explicit=crop.explicit,
        )

    def invalidate_all_displays(self) -> None:
        log.debug("VideoFile.invalidate_all_displays()")
        for ch in self.chapters:
            ch.invalidate_display()

    def build_filename(self) -> str:
        parts: list[str] = []

        if self.file_id:
            parts.append(self.file_id)
        if self.studio:
            parts.append(self.studio)
        if self.actors:
            parts.append(" & ".join(self.actors))
        if self.title:
            parts.append(self.title)
        if self.styles:
            parts.append(" ".join(self.styles))
        if self.date:
            parts.append(self.date)

        for key, val in self.booleans.items():
            if val:
                parts.append(key)

        for key, val in self.options.items():
            if val:
                parts.append(f"{key}={val}" if val is not True else key)

        if self.global_crop_size is not None:
            parts.append(self.global_crop_size.to_filename_token())

        for ch in self.chapters:
            parts.append(ch.to_filename_token())

        return " - ".join(parts) + self.extension

    def build_short_filename(self) -> str:
        parts: list[str] = []

        if self.file_id:
            parts.append(self.file_id)
        if self.studio:
            parts.append(self.studio)
        if self.actors:
            parts.append(" & ".join(self.actors))
        if self.title:
            parts.append(self.title)
        if self.styles:
            parts.append(" ".join(self.styles))
        if self.date:
            parts.append(self.date)

        for key, val in self.booleans.items():
            if val:
                parts.append(key)

        for key, val in self.options.items():
            if val:
                parts.append(f"{key}={val}" if val is not True else key)

        return " - ".join(parts) + self.extension

    def chapter_at_time(self, ts_sec: int) -> int:
        best = 0
        for ci, ch in enumerate(self.chapters):
            if ch.timestamp_sec <= ts_sec:
                best = ci
            else:
                break
        return best