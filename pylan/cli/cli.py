"""Click root command group for PyLan CLI."""

import click

from pylan.cli.receive import receive
from pylan.cli.scan import scan
from pylan.cli.send import send


@click.group()
def cli() -> None:
    """PyLan - Local network file transfer tool."""
    pass


@click.command()
def gui() -> None:
    """Launch the PyLan desktop graphical interface."""
    from pathlib import Path

    import flet as ft

    from pylan.ui.app import main as ui_main

    assets_dir = str(Path(__file__).parent.parent / "ui" / "assets")
    app_fn = getattr(ft, "app", None)
    if callable(app_fn):
        app_fn(target=ui_main, assets_dir=assets_dir)
    else:
        ft.run(ui_main, assets_dir=assets_dir)


cli.add_command(scan)
cli.add_command(receive)
cli.add_command(send)
cli.add_command(gui)
