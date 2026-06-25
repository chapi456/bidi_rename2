"""
File: events.py
Path: video_processor/controller/events.py

Version: 0.3.0
Date: 2026-06-25

Changelog:
- 0.3.0 (2026-06-25): Ajouts TODO-13 + TODO-22/23
  * EvtPositionChanged : timestamp_sec passe de int à float (sub-seconde)
  * EvtSessionFilesUpdated : liste des fichiers de la session pour la combobox
- 0.2.0 (2026-06-23): Révision design — événements minimalistes, frozen=True
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations 
from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

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
class EvtSessionFilesUpdated:
    """Liste de tous les fichiers de la session (pour alimenter la combobox).

    Émis une fois au démarrage et à chaque avancement de session.
    names      : noms affichés dans la combobox (short_name)
    current    : index du fichier actuellement chargé
    """
    names:   List[str]
    current: int

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
    full_rebuild:  bool = True    # False = seul chapter_index a changé
    chapter_index: int  = 0

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
    timestamp_sec: float = 0.0

@dataclass(frozen=True)
class EvtThumbReady:
    chapter_index: int
    image:         "PILImage"
    crop:          Optional["CropZone"]
    inherited:     bool


# ── Position ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EvtPositionChanged:
    """Position courante dans la vidéo.

    timestamp_sec est un float pour supporter le seek sub-seconde (TODO-22/23).
    La vue passe cette valeur directement à SeekSlider.set_position().
    """
    timestamp_sec: float