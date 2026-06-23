"""
File: events.py
Path: video_processor/controller/events.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial — tous les événements contrôleur → vue
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image as PILImage
    from video_processor.domain.crop_zone import CropZone
    from video_processor.domain.video_file import VideoFile
    from video_processor.domain.chapter import Chapter


# ── Chargement ────────────────────────────────────────────────────────────────

@dataclass
class EvtSessionLoaded:
    """Nouveau fichier chargé et prêt."""
    video_file: "VideoFile"

@dataclass
class EvtStatus:
    text: str

@dataclass
class EvtTitle:
    text: str

@dataclass
class EvtDirty:
    """L'état courant a des modifications non sauvegardées."""
    is_dirty: bool


# ── Navigation chapitres ──────────────────────────────────────────────────────

@dataclass
class EvtChapterChanged:
    """Le chapitre actif a changé."""
    chapter: "Chapter"
    index:   int

@dataclass
class EvtChaptersUpdated:
    """La liste des chapitres a été modifiée (ajout, suppression, bords)."""
    chapters: list


# ── Crop ──────────────────────────────────────────────────────────────────────

@dataclass
class EvtCropChanged:
    """Le crop effectif d'un chapitre a changé."""
    chapter_index: int
    crop:          Optional["CropZone"]
    inherited:     bool

@dataclass
class EvtAllCropsInvalidated:
    """La taille globale a changé — toutes les vignettes sont à redessiner."""
    crops: list   # list[Optional[CropZone]], un par chapitre


# ── Media ─────────────────────────────────────────────────────────────────────

@dataclass
class EvtFrameReady:
    """Image principale prête pour affichage."""
    chapter_index: int
    image:         "PILImage"
    crop:          Optional["CropZone"]
    inherited:     bool
    timestamp_sec: int

@dataclass
class EvtThumbReady:
    """Vignette prête pour le strip."""
    chapter_index: int
    image:         "PILImage"
    crop:          Optional["CropZone"]
    inherited:     bool
