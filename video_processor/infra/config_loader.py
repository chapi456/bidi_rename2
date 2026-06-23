"""
File: config_loader.py
Path: video_processor/infra/config_loader.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("infra.config_loader")


def load_config(config_path: Optional[str] = None) -> dict:
    """Charge la configuration depuis un fichier YAML.

    Priorité de résolution :
    1. config_path si fourni
    2. ./config/config.yaml
    3. ~/.bidi_rename2/config.yaml
    4. Configuration par défaut (dict codé en dur)

    Retourne toujours un dict valide.
    """
    log.debug("BOUCHON load_config(%s)", config_path)
    # À implémenter : charger YAML, valider clés, merger avec défauts
    return _default_config()


def _default_config() -> dict:
    """Configuration minimale utilisée en l'absence de fichier."""
    log.debug("BOUCHON _default_config()")
    return {
        "directories": [],
        "system_files": {
            "tocut_file": "#toCut.txt",
        },
        "ui": {
            "thumb_height": 90,
            "window_width": 1600,
            "window_height": 950,
        },
    }
