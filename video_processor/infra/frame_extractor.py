"""
File: frame_extractor.py
Path: video_processor/infra/frame_extractor.py

Version: 1.0.0
Date: 2026-06-23

Changelog:
- 1.0.0 (2026-06-23): Implémentation complète — probe + extract via ffmpeg/ffprobe
  * FrameExtractor.probe(path) → (width, height, duration_sec)
  * FrameExtractor.extract(path, ts_sec, size) → PIL.Image | None
  * Timeout configurable, échec silencieux (retourne None/zéros)
  * Taille vignette et timeout en constantes de module
- 0.1.0 (2026-06-23): Squelette initial
"""

from __future__ import annotations
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage
    
log = logging.getLogger("infra.frame_extractor")

# ── Constantes configurables ──────────────────────────────────────────────────
THUMB_WIDTH:   int = 160     # largeur cible des vignettes (px)
THUMB_HEIGHT:  int = 90      # hauteur cible des vignettes (px)
FFMPEG_TIMEOUT: int = 15     # secondes avant abandon (extract)
FFPROBE_TIMEOUT: int = 10    # secondes avant abandon (probe)

THUMB_SIZE: Tuple[int, int] = (THUMB_WIDTH, THUMB_HEIGHT)


class FrameExtractor:
    """Extraction de frames et métadonnées vidéo via ffmpeg/ffprobe.

    Stateless — toutes les méthodes sont statiques.
    ffmpeg et ffprobe doivent être dans le PATH.
    """

    # ── Probe ─────────────────────────────────────────────────────────────────

    @staticmethod
    def probe(video_path: Path) -> Tuple[int, int, int]:
        """Retourne (width, height, duration_sec) du premier flux vidéo.

        Retourne (0, 0, 0) en cas d'échec (fichier absent, ffprobe KO, timeout).
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "json",
            str(video_path),
        ]
        log.debug("FrameExtractor.probe(%s)", video_path.name)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=FFPROBE_TIMEOUT,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            log.error("ffprobe indisponible ou timeout : %s", exc)
            return (0, 0, 0)

        if result.returncode != 0:
            log.error("ffprobe erreur (%s) : %s", video_path.name, result.stderr[:200])
            return (0, 0, 0)

        try:
            data    = json.loads(result.stdout)
            streams = data.get("streams", [])
            if not streams:
                log.warning("ffprobe : aucun flux vidéo dans %s", video_path.name)
                return (0, 0, 0)
            s        = streams[0]
            width    = int(s.get("width",    0))
            height   = int(s.get("height",   0))
            duration = int(float(s.get("duration", 0)))
            log.debug("probe OK : %dx%d %ds (%s)", width, height, duration, video_path.name)
            return (width, height, duration)
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            log.error("ffprobe : parsing JSON échoué (%s) : %s", video_path.name, exc)
            return (0, 0, 0)

    # ── Extract ───────────────────────────────────────────────────────────────

    @staticmethod
    def extract(
        video_path: Path,
        ts_sec: int,
        size: Optional[Tuple[int, int]] = None,
    ) -> Optional["PILImage"]:
        """Extrait une frame à ts_sec et retourne une PIL.Image.

        Args:
            video_path : chemin du fichier vidéo
            ts_sec     : timestamp en secondes
            size       : (w, h) pour redimensionner, None = pleine résolution

        Returns:
            PIL.Image.Image ou None si échec
        """
        try:
            from PIL import Image
        except ImportError:
            log.error("Pillow non installé — pip install Pillow")
            return None

        # Fichier temporaire .jpg dans le répertoire système
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        cmd = [
            "ffmpeg",
            "-y",                        # écraser sans confirmation
            "-ss", str(ts_sec),          # seek AVANT -i = seek rapide (keyframe)
            "-i", str(video_path),
            "-vframes", "1",             # une seule frame
            "-q:v", "2",                 # qualité JPEG haute (1-31, 1=meilleur)
        ]

        if size is not None:
            cmd += ["-vf", f"scale={size[0]}:{size[1]}"]

        cmd.append(str(tmp_path))

        log.debug("FrameExtractor.extract(%s, ts=%d, size=%s)",
                  video_path.name, ts_sec, size)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=FFMPEG_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            log.error("ffmpeg timeout (ts=%d, %s)", ts_sec, video_path.name)
            tmp_path.unlink(missing_ok=True)
            return None
        except FileNotFoundError:
            log.error("ffmpeg introuvable dans le PATH")
            tmp_path.unlink(missing_ok=True)
            return None

        if result.returncode != 0 or not tmp_path.exists() or tmp_path.stat().st_size == 0:
            log.error("ffmpeg échec (ts=%d, %s)", ts_sec, video_path.name)
            tmp_path.unlink(missing_ok=True)
            return None

        try:
            img = Image.open(tmp_path).copy()   # .copy() = détache du fichier
        except Exception as exc:
            log.error("PIL : impossible d'ouvrir la frame extraite : %s", exc)
            img = None
        finally:
            tmp_path.unlink(missing_ok=True)

        return img

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def extract_thumb(video_path: Path, ts_sec: int) -> Optional["PILImage"]:
        """Raccourci : extrait une vignette à THUMB_SIZE."""
        return FrameExtractor.extract(video_path, ts_sec, size=THUMB_SIZE)