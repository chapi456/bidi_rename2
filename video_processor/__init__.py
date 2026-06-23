"""
File: __init__.py
Path: video_processor/__init__.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Création — package marker
"""
# Injection sys.path identique au point d'entrée, pour usage en module isolé.
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parent.parent
if str(_PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(_PKG_ROOT))
