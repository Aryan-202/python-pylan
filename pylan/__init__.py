"""PyLan - Fast, cross-platform local network file and data sharing.

PyLan provides peer discovery, framing protocols, and data transfer
mechanisms designed for local network environments. It operates both as an
extensible Python package and as a standalone command-line application.

Subpackages:
    core: Protocol framing, peer discovery engine, and data models.
    cli: Command-line interfaces for scanning, sending, and receiving.
"""

__version__: str = "0.0.2"

__all__: list[str] = [
    "__version__",
]
