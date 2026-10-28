"""Command-line interface commands and entry points for PyLan.

This package provides the console commands and interactive CLI workflows
for scanning nearby peers, transmitting files over framed TCP connections,
and hosting the background receiver daemon.

Modules:
    cli: Root Click command group registering all CLI subcommands.
    receive: TCP receiver daemon and multicast presence broadcaster.
    scan: Staged local network scanner discovering active PyLan nodes.
    send: Client transfer initiator negotiating and streaming files.
"""

from pylan.cli.cli import cli, gui
from pylan.cli.receive import receive
from pylan.cli.scan import scan
from pylan.cli.send import send

__all__: list[str] = [
    "cli",
    "gui",
    "receive",
    "scan",
    "send",
]
