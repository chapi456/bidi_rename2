"""
File: directory_scanner.py
Path: video_processor/infra/directory_scanner.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging
from pathlib import Path

from video_processor.domain.session import SessionEntry

log = logging.getLogger("infra.directory_scanner")

VIDEO_EXT = {'.mp4', '.mkv', '.avi', '.mov', '.ts', '.m2ts', '.wmv', '.flv'}


class DirectoryScanner:
    """Scanne les répertoires configurés et retourne une liste de SessionEntry."""

    def __init__(self, config: dict):
        log.debug("BOUCHON DirectoryScanner.__init__()")
        self._config = config

    def scan(self) -> list[SessionEntry]:
        """Scanne tous les répertoires configurés.

        Pour chaque répertoire :
        1. Lire #toCut.txt via TocutRW.read()
        2. Itérer les fichiers vidéo triés
        3. Enrichir long_name avec complement si présent dans #toCut.txt
        """
        log.debug("BOUCHON DirectoryScanner.scan()")
        # À implémenter : appeler get_directories(), iter fichiers, tocut
        return []

    def _scan_dir(self, dir_path: Path, tocut_map: dict) -> list[SessionEntry]:
        """Scanne un seul répertoire et retourne ses SessionEntry."""
        log.debug("BOUCHON DirectoryScanner._scan_dir(%s)", dir_path)
        # À implémenter
        return []

    def _resolve_directories(self) -> list[Path]:
        """Retourne la liste des Path valides depuis la configuration."""
        log.debug("BOUCHON DirectoryScanner._resolve_directories()")
        # À implémenter : lire config['directories'] ou get_directories()
        return []
