"""
File: commands.py
Path: video_processor/controller/commands.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial — toutes les commandes vue → contrôleur
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CmdJump:
    chapter_index: int

@dataclass
class CmdSeekAbs:
    timestamp_sec: int

@dataclass
class CmdSeekDelta:
    delta_sec: int

@dataclass
class CmdAddCrop:
    pass

@dataclass
class CmdDelCrop:
    pass

@dataclass
class CmdSetCrop:
    """Modifie taille ET/OU position."""
    w:     Optional[int] = None
    h:     Optional[int] = None
    pos_x: Optional[int] = None
    pos_y: Optional[int] = None

@dataclass
class CmdSetPosition:
    preset: str   # "l" | "c" | "r" | "topleft"
    pos_x:  Optional[int] = None
    pos_y:  Optional[int] = None

@dataclass
class CmdValidateChapter:
    pass

@dataclass
class CmdPrevChapter:
    pass

@dataclass
class CmdAddChapter:
    timestamp_sec: int
    duration_sec:  int
    title:         str

@dataclass
class CmdEditChapter:
    index:         int
    title:         str
    timestamp_sec: int
    timestamp_raw: str
    duration_sec:  int

@dataclass
class CmdChapterEdge:
    index:         int
    kind:          str   # "start" | "end"
    timestamp_sec: int
    duration_sec:  int

@dataclass
class CmdSave:
    pass

@dataclass
class CmdNextFile:
    pass

@dataclass
class CmdLoadFile:
    path: Path

@dataclass
class CmdQuit:
    pass
