"""
File: commands.py
Path: video_processor/controller/commands.py

Version: 0.3.0
Date: 2026-06-23

Changelog:
- 0.3.0 (2026-06-23): Nouvelles commandes navigation et crop
  * CmdSeekChapterStart : seek au début du chapitre actif
  * CmdSeekChapterEnd   : seek à la fin du chapitre actif (ts + duration)
  * CmdSeekBegin        : seek à 0 (début absolu)
  * CmdSeekEnd          : seek à la fin absolue (total_duration_sec)
  * CmdCopyPrevCrop     : copie crop_effective du chapitre précédent vers actif
  * CmdSaveAndNext      : sauvegarde + passage au fichier suivant
- 0.2.0 (2026-06-23): frozen=True sur tous les dataclasses
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class CmdJump:
    chapter_index: int

@dataclass(frozen=True)
class CmdSeekAbs:
    timestamp_sec: int

@dataclass(frozen=True)
class CmdSeekDelta:
    delta_sec: int

@dataclass(frozen=True)
class CmdSeekBegin:
    """Seek à 0 — début absolu du fichier."""
    pass

@dataclass(frozen=True)
class CmdSeekEnd:
    """Seek à total_duration_sec — fin absolue du fichier."""
    pass

@dataclass(frozen=True)
class CmdSeekChapterStart:
    """Seek au timestamp_sec du chapitre actif."""
    pass

@dataclass(frozen=True)
class CmdSeekChapterEnd:
    """Seek à timestamp_sec + duration_sec du chapitre actif."""
    pass

@dataclass(frozen=True)
class CmdAddCrop:
    pass

@dataclass(frozen=True)
class CmdDelCrop:
    pass

@dataclass(frozen=True)
class CmdSetCrop:
    """Modifie taille ET/OU position du crop du chapitre actif."""
    w:     Optional[int] = None
    h:     Optional[int] = None
    pos_x: Optional[int] = None
    pos_y: Optional[int] = None

@dataclass(frozen=True)
class CmdSetPosition:
    preset: str           # "l" | "c" | "r" | "topleft"
    pos_x:  Optional[int] = None
    pos_y:  Optional[int] = None

@dataclass(frozen=True)
class CmdCopyPrevCrop:
    """Copie crop_effective du chapitre précédent vers le chapitre actif."""
    pass

@dataclass(frozen=True)
class CmdValidateChapter:
    pass

@dataclass(frozen=True)
class CmdPrevChapter:
    pass

@dataclass(frozen=True)
class CmdAddChapter:
    timestamp_sec: int
    duration_sec:  int
    title:         str

@dataclass(frozen=True)
class CmdEditChapter:
    index:         int
    title:         str
    timestamp_sec: int
    timestamp_raw: str
    duration_sec:  int

@dataclass(frozen=True)
class CmdChapterEdge:
    index:         int
    kind:          str   # "start" | "end"
    timestamp_sec: int
    duration_sec:  int

@dataclass(frozen=True)
class CmdSave:
    pass

@dataclass(frozen=True)
class CmdSaveAndNext:
    """Sauvegarde le fichier courant puis charge le suivant."""
    pass

@dataclass(frozen=True)
class CmdNextFile:
    pass

@dataclass(frozen=True)
class CmdLoadFile:
    path: Path

@dataclass(frozen=True)
class CmdQuit:
    pass