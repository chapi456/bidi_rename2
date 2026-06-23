"""
File: events.py
Path: video_processor/controller/events.py

Version: 0.2.0
Date: 2026-06-23

Changelog:
- 0.2.0 (2026-06-23): Révision design — événements minimalistes, frozen=True
  * EvtAllCropsInvalidated : signal pur (pas de données)
  * EvtCropsResolved : nouvel événement portant les crops recalculés
  * EvtChapterChanged : transporte index uniquement (la vue a déjà le VideoFile)
  * EvtCropChanged : crop devient Optional (peut être None si supprimé)
  * frozen=True sur tous les dataclasses
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage
    from video_processor.domain.crop_zone  import CropZone
    from video_processor.domain.video_file import VideoFile


# ── Chargement ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EvtSessionLoaded:
    """Nouveau fichier chargé et prêt. La vue stocke video_file pour la session."""
    video_file: "VideoFile"

@dataclass(frozen=True)
class EvtStatus:
    text: str

@dataclass(frozen=True)
class EvtTitle:
    text: str

@dataclass(frozen=True)
class EvtDirty:
    """Modifications non sauvegardées présentes ou effacées."""
    is_dirty: bool


# ── Navigation chapitres ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class EvtChapterChanged:
    """Le chapitre actif a changé. La vue retrouve chapters[index] via son VideoFile."""
    index: int

@dataclass(frozen=True)
class EvtChaptersUpdated:
    """La liste des chapitres a été modifiée (ajout, suppression, bords)."""
    chapters: list   # list[Chapter]


# ── Crop ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EvtAllCropsInvalidated:
    """Signal pur : caches visuels obsolètes, la vue doit tout effacer.
    Suivi de EvtCropsResolved quand les nouveaux crops sont prêts.
    """
    pass

@dataclass(frozen=True)
class EvtCropsResolved:
    """Crops recalculés après resolve_inheritance(). Un par chapitre."""
    crops: list   # list[Optional[CropZone]]

@dataclass(frozen=True)
class EvtCropChanged:
    """Le crop effectif d'un chapitre a changé."""
    chapter_index: int
    crop:          Optional["CropZone"]
    inherited:     bool


# ── Media ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EvtFrameReady:
    chapter_index: int
    image:         "PILImage"   # PIL.Image.Image au runtime
    crop:          Optional["CropZone"]
    inherited:     bool
    timestamp_sec: int

@dataclass(frozen=True)
class EvtThumbReady:
    chapter_index: int
    image:         "PILImage"
    crop:          Optional["CropZone"]
    inherited:     bool