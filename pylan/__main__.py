"""Main package entrypoint handling CLI vs GUI dispatch for PyLan."""

import sys


def main() -> None:
    """Dispatch execution to GUI or CLI based on command-line arguments."""
    if len(sys.argv) > 1 and sys.argv[1] == "gui":
        sys.argv.pop(1)
        from pathlib import Path

        import flet as ft

        from pylan.ui.app import main as ui_main

        assets_dir = str(Path(__file__).parent / "ui" / "assets")
        app_fn = getattr(ft, "app", None)
        if callable(app_fn):
            app_fn(target=ui_main, assets_dir=assets_dir)
        else:
            ft.run(ui_main, assets_dir=assets_dir)
    else:
        from pylan.cli.cli import cli

        cli()


if __name__ == "__main__":
    main()
