"""
File: commands.py
Path: video_processor/controller/commands.py

Version: 0.2.0
Date: 2026-06-23

Changelog:
- 0.2.0 (2026-06-23): frozen=True sur tous les dataclasses (immutabilité garantie)
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
class CmdAddCrop:
    pass

@dataclass(frozen=True)
class CmdDelCrop:
    pass

@dataclass(frozen=True)
class CmdSetCrop:
    """Modifie taille ET/OU position du crop."""
    w:     Optional[int] = None
    h:     Optional[int] = None
    pos_x: Optional[int] = None
    pos_y: Optional[int] = None

@dataclass(frozen=True)
class CmdSetPosition:
    preset: str          # "l" | "c" | "r" | "topleft"
    pos_x:  Optional[int] = None
    pos_y:  Optional[int] = None

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
class CmdNextFile:
    pass

@dataclass(frozen=True)
class CmdLoadFile:
    path: Path

@dataclass(frozen=True)
class CmdQuit:
    pass