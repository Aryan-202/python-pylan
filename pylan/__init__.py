"""PyLan - Fast, cross-platform local network file and data sharing.

PyLan provides peer discovery, framing protocols, and data transfer
mechanisms designed for local network environments. It operates both as an
extensible Python package and as a standalone command-line application or
graphical user interface.

Subpackages:
    cli: Command-line interfaces for scanning, sending, and receiving.
    core: Protocol framing, peer discovery engine, and data models.
    ui: Flet desktop and web graphical user interface module.
"""

__version__: str = "0.0.2"

__all__: list[str] = [
    "__version__",
]
