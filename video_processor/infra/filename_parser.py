"""
File: filename_parser.py
Path: video_processor/infra/filename_parser.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial — wraps parsing.py existant
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("infra.filename_parser")


class FilenameParser:
    """Facade sur le module parsing.py existant.
    Isole le domaine de la dépendance directe au parser legacy.
    """

    @staticmethod
    def parse(display_name: str) -> dict:
        """Parse le nom long d'un fichier vidéo.

        Retourne un dict avec les clés :
          studio, actors, title, styles, date, booleans, options,
          chapters (list[dict]), id

        Les options reconnus incluent : CROP, ENCODE, RESIZE, THUMB.
        Chaque chapitre : {timestamp_seconds, timestamp_original,
                           duration, title, raw_token}
        """
        log.debug("BOUCHON FilenameParser.parse(%r)", display_name)
        # À implémenter : from .parsing import parse_filename ; return parse_filename(name)
        return {"chapters": [], "options": {}, "booleans": {}}

    @staticmethod
    def build(title: str, studio: Optional[str], actors: list[str],
              styles: list[str], date: Optional[str], booleans: dict,
              options: dict, chapters_tokens: list[str],
              file_id: Optional[str], extension: str) -> str:
        """Reconstruit un nom de fichier depuis ses composantes.

        Implémentation cible : délègue à build_new_filename() legacy
        ou reconstruit directement depuis les tokens.
        """
        log.debug("BOUCHON FilenameParser.build(title=%r)", title)
        return ""  # stub
