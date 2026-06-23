"""
File: bidi_rename2.py
Path: bidi_rename2.py

Version: 0.2.0
Date: 2026-06-23

Changelog:
- 0.2.0 (2026-06-23): Fix sys.path + lazy imports corrigés
  * SCRIPT_DIR injecté dans sys.path dès le top du module
  * Imports video_processor déplacés après injection path
  * Pattern identique à bidi_rename/config.py
- 0.1.0 (2026-06-23): Squelette initial
"""

import argparse
import logging
import sys
from pathlib import Path

# ── Injection sys.path ─────────────────────────────────────────────────────
# Doit être fait AVANT tout import video_processor.
# SCRIPT_DIR = répertoire de bidi_rename2.py (racine du projet).
# On l'ajoute en tête de sys.path pour que `import video_processor` fonctionne
# quel que soit le répertoire de travail courant.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
# ──────────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.DEBUG,
                    format="%(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("bidi_rename2")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="bidi_rename2 — crop/chapter editor")
    p.add_argument("target", nargs="?", help="Fichier vidéo ou dossier cible")
    p.add_argument("--headless", action="store_true", help="Forcer mode CLI texte")
    p.add_argument("--web",      action="store_true", help="Mode web (futur)")
    p.add_argument("--config",   default=None,        help="Chemin config.yaml alternatif")
    return p.parse_args()


def resolve_target(target_str: str | None) -> Path | None:
    """Résout l'argument cible en Path absolu.
    Retourne None si absent (→ scan répertoires config).
    """
    if target_str is None:
        return None
    p = Path(target_str).resolve()
    if not p.exists():
        log.error("Cible introuvable : %s", p)
        sys.exit(1)
    return p


def build_view(headless: bool, web: bool):
    """Instancie la vue appropriée selon l'environnement.
    Priorité : web > tk > cli.
    """
    if web:
        log.warning("WebView non implémenté — bascule CLI")
        headless = True

    if not headless:
        try:
            import tkinter  # noqa: F401
            from video_processor.ui.tkinter_view import TkinterView
            log.debug("→ TkinterView")
            return TkinterView()
        except ImportError:
            log.warning("tkinter indisponible — bascule CLI")

    from video_processor.ui.cli_view import CliView
    log.debug("→ CliView")
    return CliView()


def main():
    args   = parse_args()
    target = resolve_target(args.target)

    # Imports après injection sys.path (garantie ci-dessus)
    from video_processor.infra.config_loader   import AppConfig
    from video_processor.infra.directory_scanner import DirectoryScanner
    from video_processor.domain.session        import VideoSession
    from video_processor.controller.session_controller import SessionController

    cfg     = AppConfig.load(args.config)
    scanner = DirectoryScanner(cfg)
    session = VideoSession(scanner.scan(), cfg)

    if target:
        session.set_current_by_path(target)

    view       = build_view(args.headless, args.web)
    controller = SessionController(session, cfg)
    view.bind(controller)
    controller.open_current()
    view.run()


if __name__ == "__main__":
    main()
