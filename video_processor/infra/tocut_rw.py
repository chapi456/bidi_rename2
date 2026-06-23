"""
File: tocut_rw.py
Path: video_processor/infra/tocut_rw.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging
from pathlib import Path

log = logging.getLogger("infra.tocut_rw")


class TocutRW:
    """Lecture et écriture du fichier #toCut.txt.

    Format de chaque ligne : <short_name><complement>
    Exemple : "MonFilm.mp4 - CROP(1800x800) 00-00(120)(Intro)"
    """

    @staticmethod
    def read(tocut_path: Path) -> dict[str, str]:
        """Retourne un dict {short_name: complement}.
        Retourne un dict vide si le fichier n'existe pas.
        """
        log.debug("BOUCHON TocutRW.read(%s)", tocut_path)
        # À implémenter : parser chaque ligne, séparer short_name et complement
        return {}

    @staticmethod
    def write_entry(tocut_path: Path, short_name: str, complement: str) -> None:
        """Ajoute ou met à jour l'entrée d'un fichier dans #toCut.txt."""
        log.debug("BOUCHON TocutRW.write_entry(%s, %s)", short_name, complement)
        # À implémenter : lire existant, upsert, réécrire

    @staticmethod
    def remove_entry(tocut_path: Path, short_name: str) -> None:
        """Supprime l'entrée d'un fichier dans #toCut.txt."""
        log.debug("BOUCHON TocutRW.remove_entry(%s)", short_name)
        # À implémenter : lire existant, filtrer, réécrire
