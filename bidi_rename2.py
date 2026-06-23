"""
File: bidi_rename2.py
Path: bidi_rename2.py

Version: 0.1.0
Date: 2026-06-23

Changelog:
- 0.1.0 (2026-06-23): Squelette initial — point d'entrée, routing vue
"""

import argparse
import logging
import sys
from pathlib import Path

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
    log.debug("BOUCHON resolve_target(%s)", target_str)
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
    Retourne une instance implémentant BaseView.
    """
    log.debug("BOUCHON build_view(headless=%s, web=%s)", headless, web)

    if web:
        log.debug("BOUCHON → WebView (non implémenté)")
        from video_processor.ui.web_view import WebView
        return WebView()

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

    from video_processor.infra.config_loader import load_config
    from video_processor.infra.directory_scanner import DirectoryScanner
    from video_processor.domain.session import VideoSession
    from video_processor.controller.session_controller import SessionController

    config  = load_config(args.config)
    scanner = DirectoryScanner(config)
    session = VideoSession(scanner.scan(), config)

    if target:
        session.set_current_by_path(target)

    view       = build_view(args.headless, args.web)
    controller = SessionController(session, config)

    # La vue s'abonne aux événements du contrôleur
    view.bind(controller)

    # Le contrôleur charge le fichier courant (extraction dims, parse, héritage)
    controller.open_current()

    # Démarre la boucle principale de la vue
    view.run()


if __name__ == "__main__":
    main()
