"""
File: video_file.py
Path: video_processor/domain/video_file.py

Version: 1.0.0
Date: 2026-06-23

Changelog:
- 1.0.0 (2026-06-23): Implémentation complète
  * resolve_inheritance() : héritage crop chapitre par chapitre, taille globale appliquée
  * build_filename() : reconstruit le long_name depuis toutes les métadonnées
  * build_short_filename() : nom tronqué avant CROP/chapitres (pour #toCut.txt)
  * invalidate_all_displays() et chapter_at_time() : déjà corrects, logs nettoyés
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .chapter  import Chapter
from .crop_zone import CropZone

log = logging.getLogger("domain.video_file")


@dataclass
class VideoFile:
    # ── Identité ──────────────────────────────────────────────────────────
    physical_path: Path
    short_name:    str          # nom réel sur disque
    long_name:     str          # nom enrichi (#toCut.txt ou = short_name)
    uses_tocut:    bool = False
    complement:    str  = ""    # partie stockée dans #toCut.txt

    # ── Métadonnées parsées ───────────────────────────────────────────────
    title:    Optional[str] = None
    studio:   Optional[str] = None
    actors:   list[str]     = field(default_factory=list)
    styles:   list[str]     = field(default_factory=list)
    date:     Optional[str] = None
    booleans: dict          = field(default_factory=dict)   # POV, 3D, NOCUT…
    options:  dict          = field(default_factory=dict)   # ENCODE, RESIZE…
    file_id:  Optional[str] = None

    # ── Dimensions vidéo ──────────────────────────────────────────────────
    video_w:            int = 0
    video_h:            int = 0
    total_duration_sec: int = 0

    # ── Crop GLOBAL (taille partagée) ─────────────────────────────────────
    # Seuls w et h sont globaux ; pos_x/pos_y sont par chapitre (crop_explicit)
    global_crop_size: Optional[CropZone] = None

    # ── Chapitres ─────────────────────────────────────────────────────────
    chapters: list[Chapter] = field(default_factory=list)

    # ── État session ──────────────────────────────────────────────────────
    active_index: int  = 0
    dirty:        bool = False

    # ── Propriétés ────────────────────────────────────────────────────────

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

    # ── Héritage crop ─────────────────────────────────────────────────────

    def resolve_inheritance(self) -> None:
        """Recalcule crop_effective et is_inherited pour tous les chapitres.

        Règles :
        1. Chapitre avec crop_explicit → crop_effective = crop_explicit
           mais taille remplacée par global_crop_size si définie.
           is_inherited = False. Devient le nouveau last_explicit.
        2. Chapitre sans crop_explicit + last_explicit existe →
           crop_effective = last_explicit (taille globale appliquée si définie).
           is_inherited = True.
        3. Chapitre sans crop_explicit + aucun précédent →
           crop_effective = None. is_inherited = False.
        """
        log.debug("VideoFile.resolve_inheritance() — %d chapitres", len(self.chapters))
        last_explicit: Optional[CropZone] = None

        for ch in self.chapters:
            if ch.crop_explicit is not None:
                # Appliquer la taille globale si définie, conserver la position
                effective = self._apply_global_size(ch.crop_explicit)
                ch.crop_effective = effective
                ch.is_inherited   = False
                last_explicit     = effective

            elif last_explicit is not None:
                ch.crop_effective = last_explicit
                ch.is_inherited   = True

            else:
                ch.crop_effective = None
                ch.is_inherited   = False

            ch.invalidate_display()
            log.debug(
                "  ch[%d] explicit=%s effective=%s inherited=%s",
                ch.index,
                ch.crop_explicit,
                ch.crop_effective,
                ch.is_inherited,
            )

    def _apply_global_size(self, crop: CropZone) -> CropZone:
        """Retourne crop avec la taille de global_crop_size si définie.
        La position (pos_x, pos_y) du crop d'origine est conservée.
        """
        if self.global_crop_size is None:
            return crop
        return CropZone(
            w=self.global_crop_size.w,
            h=self.global_crop_size.h,
            pos_x=crop.pos_x,
            pos_y=crop.pos_y,
            pos_mode=crop.pos_mode,
            explicit=crop.explicit,
        )

    def invalidate_all_displays(self) -> None:
        """Invalide tous les caches de rendu (appelé quand taille globale change)."""
        log.debug("VideoFile.invalidate_all_displays()")
        for ch in self.chapters:
            ch.invalidate_display()

    # ── Construction nom de fichier ────────────────────────────────────────

    def build_filename(self) -> str:
        """Reconstruit le long_name complet depuis les métadonnées.

        Format : <id> - <studio> - <actors> - <title> - <styles> - <date>
                 - <booleans> - <options> - CROP(WxH) - <chapitres><ext>

        Seules les parties non vides/non nulles sont incluses.
        """
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

        # Booléens (POV, 3D, NOCUT…) — clés dont la valeur est True
        for key, val in self.booleans.items():
            if val:
                parts.append(key)

        # Options (ENCODE=hevc, RESIZE=1080p…)
        for key, val in self.options.items():
            if val:
                parts.append(f"{key}={val}" if val is not True else key)

        # Taille crop globale
        if self.global_crop_size is not None:
            parts.append(self.global_crop_size.to_filename_token())

        # Chapitres
        for ch in self.chapters:
            parts.append(ch.to_filename_token())

        stem = " - ".join(parts)
        return stem + self.extension

    def build_short_filename(self) -> str:
        """Nom court : tout avant CROP et chapitres (stocké sur disque).

        C'est le nom physique réel — sans complement #toCut.txt.
        """
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

        stem = " - ".join(parts)
        return stem + self.extension

    # ── Navigation ────────────────────────────────────────────────────────

    def chapter_at_time(self, ts_sec: int) -> int:
        """Retourne l'index du chapitre correspondant à ts_sec.

        Le chapitre retourné est le dernier dont timestamp_sec <= ts_sec.
        """
        best = 0
        for ci, ch in enumerate(self.chapters):
            if ch.timestamp_sec <= ts_sec:
                best = ci
            else:
                break
        return best