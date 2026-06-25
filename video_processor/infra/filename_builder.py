"""
File: filename_builder.py
Path: video_processor/infra/filename_builder.py

Version: 1.0.0
Date: 2026-06-25

Changelog:
- 1.0.0 (2026-06-25): Implémentation initiale
  * FilenameBuilder.build(vf) : délègue à VideoFile.build_filename()
  * SessionController._write_output() l'appelait mais le fichier n'existait pas
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from video_processor.domain.video_file import VideoFile

log = logging.getLogger("infra.filename_builder")


class FilenameBuilder:
    """Reconstruit le nom de fichier complet à partir d'un VideoFile.

    Simple façade sur VideoFile.build_filename() — point d'entrée unique
    pour toute la couche infra (session_controller, tests).
    """

    @staticmethod
    def build(vf: "VideoFile") -> str:
        """Retourne le nouveau nom de fichier (avec extension) pour vf.

        Délègue à VideoFile.build_filename() qui encode toutes les métadonnées
        domain en tokens selon la syntaxe bidi_rename.
        """
        name = vf.build_filename()
        log.debug("FilenameBuilder.build : %s → %s", vf.short_name, name)
        return name
