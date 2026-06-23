"""
File: video_file.py
Path: video_processor/domain/video_file.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
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
    physical_path:  Path
    short_name:     str          # nom réel sur disque
    long_name:      str          # nom enrichi (#toCut.txt ou = short_name)
    uses_tocut:     bool = False
    complement:     str  = ""    # partie stockée dans #toCut.txt

    # ── Métadonnées parsées ───────────────────────────────────────────────
    title:          Optional[str]      = None
    studio:         Optional[str]      = None
    actors:         list[str]          = field(default_factory=list)
    styles:         list[str]          = field(default_factory=list)
    date:           Optional[str]      = None
    booleans:       dict               = field(default_factory=dict)   # POV, 3D, NOCUT…
    options:        dict               = field(default_factory=dict)   # ENCODE, RESIZE…
    file_id:        Optional[str]      = None

    # ── Dimensions vidéo ──────────────────────────────────────────────────
    video_w:              int = 0
    video_h:              int = 0
    total_duration_sec:   int = 0

    # ── Crop GLOBAL (taille partagée) ────────────────────────────────────
    # Seuls w et h sont globaux ; pos_x/pos_y sont par chapitre (crop_explicit)
    global_crop_size: Optional[CropZone] = None   # None = pas de crop

    # ── Chapitres ────────────────────────────────────────────────────────
    chapters:       list[Chapter] = field(default_factory=list)

    # ── État session ──────────────────────────────────────────────────────
    active_index:   int  = 0
    dirty:          bool = False

    # ── Propriétés ────────────────────────────────────────────────────────

    @property
    def active_chapter(self) -> Optional[Chapter]:
        if not self.chapters:
            return None
        return self.chapters[self.active_index]

    @property
    def has_crop(self) -> bool:
        return self.global_crop_size is not None

    @property
    def extension(self) -> str:
        return self.physical_path.suffix

    # ── Héritage crop ────────────────────────────────────────────────────

    def resolve_inheritance(self) -> None:
        """Recalcule crop_effective et is_inherited pour tous les chapitres.
        Règle : chaque chapitre sans crop_explicit hérite du dernier explicite.
        Si aucun explicite précédent : crop_effective = None.
        La taille globale (global_crop_size) est appliquée à tous les effectifs.
        """
        log.debug("BOUCHON VideoFile.resolve_inheritance() — %d chapitres",
                  len(self.chapters))
        last_explicit: Optional[CropZone] = None
        for ch in self.chapters:
            log.debug(
                "BOUCHON   ch[%d] crop_explicit=%s", ch.index, ch.crop_explicit
            )
            # À implémenter :
            # 1. Si ch.crop_explicit → crop_effective = ch.crop_explicit avec taille globale
            #    last_explicit = crop_effective ; is_inherited = False
            # 2. Sinon si last_explicit → crop_effective = last_explicit avec taille globale
            #    is_inherited = True
            # 3. Sinon → crop_effective = None ; is_inherited = False
            ch.invalidate_display()

    def invalidate_all_displays(self) -> None:
        """Invalide tous les caches de rendu (appelé quand taille globale change)."""
        log.debug("BOUCHON VideoFile.invalidate_all_displays()")
        for ch in self.chapters:
            ch.invalidate_display()

    # ── Construction nom de fichier ───────────────────────────────────────

    def build_filename(self) -> str:
        """Reconstruit le nom long depuis les métadonnées et les chapitres."""
        log.debug("BOUCHON VideoFile.build_filename()")
        # À implémenter : assembler studio, actors, title, styles, date,
        # booleans, options, global_crop_size.to_filename_token(),
        # chapitres, file_id → " - ".join(parts) + extension
        return self.long_name   # stub

    def build_short_filename(self) -> str:
        """Nom court : tronqué avant CROP/chapitres (pour #toCut.txt)."""
        log.debug("BOUCHON VideoFile.build_short_filename()")
        return self.short_name  # stub

    def chapter_at_time(self, ts_sec: int) -> int:
        """Retourne l'index du chapitre correspondant à ts_sec."""
        log.debug("BOUCHON VideoFile.chapter_at_time(%d)", ts_sec)
        best = 0
        for ci, ch in enumerate(self.chapters):
            if ch.timestamp_sec <= ts_sec:
                best = ci
            else:
                break
        return best
