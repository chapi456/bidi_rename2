"""
File: frame_extractor.py
Path: video_processor/infra/frame_extractor.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

log = logging.getLogger("infra.frame_extractor")

THUMB_SIZE = (160, 90)   # taille cible des vignettes (px)


class FrameExtractor:
    """Extraction de frames via ffmpeg. Stateless."""

    @staticmethod
    def probe(video_path: Path) -> Tuple[int, int, int]:
        """Retourne (width, height, duration_sec) via ffprobe.
        Retourne (0, 0, 0) en cas d'échec.
        """
        log.debug("BOUCHON FrameExtractor.probe(%s)", video_path)
        # À implémenter : ffprobe -v error -select_streams v:0 -show_entries ...
        return (0, 0, 0)

    @staticmethod
    def extract(video_path: Path, ts_sec: int,
                size: Optional[Tuple[int, int]] = None) -> Optional[object]:
        """Extrait une frame à ts_sec et retourne une PIL.Image.

        - size=None : frame pleine résolution
        - size=THUMB_SIZE : vignette redimensionnée
        Retourne None si échec (ffmpeg, timeout, etc.).
        """
        log.debug("BOUCHON FrameExtractor.extract(%s, ts=%d, size=%s)",
                  video_path, ts_sec, size)
        # À implémenter :
        # cmd = ["ffmpeg", "-y", "-ss", str(ts_sec), "-i", str(video_path),
        #        "-vframes", "1", "-q:v", "2", out_jpg]
        # if size: ajouter -vf scale=W:H
        return None
