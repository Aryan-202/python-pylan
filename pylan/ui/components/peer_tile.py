"""Peer tile widget displaying discovered PyLan network nodes."""

from typing import Any, Callable, Optional

import flet as ft

from pylan.core.models import StatefulDevice


def create_peer_tile(
    device: StatefulDevice,
    is_selected: bool = False,
    on_select: Optional[Callable[[StatefulDevice], None]] = None,
    on_quick_send: Optional[Callable[[StatefulDevice], None]] = None,
) -> ft.Control:
    """Create a card widget representing a discovered network peer.

    Args:
        device: Discovered StatefulDevice model instance.
        is_selected: Whether this peer is currently marked as target.
        on_select: Callback fired when the tile is clicked.
        on_quick_send: Optional callback fired on quick-send action.

    Returns:
        A styled Flet Container control.
    """
    dev = device.device
    alias = getattr(dev, "alias", "Unknown Peer")
    model = getattr(dev, "device_model", "PyLan Node") or "PyLan Node"
    fingerprint = getattr(dev, "fingerprint", "N/A")[:8]
    channel = getattr(dev, "channel", None)
    address = f"{channel.host}:{channel.port}" if channel else "Unknown"

    border_color = (
        ft.Colors.PRIMARY if is_selected else ft.Colors.OUTLINE_VARIANT
    )
    bg_color = (
        ft.Colors.SURFACE_CONTAINER_HIGHEST
        if is_selected
        else ft.Colors.SURFACE_CONTAINER
    )

    def handle_click(_: Any = None) -> None:
        if on_select is not None:
            on_select(device)

    def handle_send_click(_: Any = None) -> None:
        if on_quick_send is not None:
            on_quick_send(device)

    actions: list[ft.Control] = [
        ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ft.Icons.CIRCLE,
                        size=8,
                        color=ft.Colors.GREEN_ACCENT_400,
                    ),
                    ft.Text(
                        "ONLINE",
                        size=10,
                        weight=ft.FontWeight.W_600,
                        color=ft.Colors.GREEN_ACCENT_400,
                    ),
                ],
                spacing=4,
            ),
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
            border_radius=8,
            bgcolor=(
                ft.Colors.GREEN_900
                if is_selected
                else ft.Colors.SURFACE_CONTAINER_HIGH
            ),
        )
    ]

    if on_quick_send is not None:
        actions.append(
            ft.IconButton(
                icon=ft.Icons.SEND_ROUNDED,
                tooltip="Send files to this device",
                icon_color=ft.Colors.PRIMARY,
                on_click=handle_send_click,
            )
        )

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.DEVICES_ROUNDED,
                        size=28,
                        color=ft.Colors.PRIMARY,
                    ),
                    padding=10,
                    border_radius=10,
                    bgcolor=ft.Colors.PRIMARY_CONTAINER,
                ),
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    alias,
                                    size=15,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.ON_SURFACE,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    max_lines=1,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        f"#{fingerprint}",
                                        size=10,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                    padding=ft.Padding.symmetric(
                                        horizontal=6, vertical=2
                                    ),
                                    border_radius=6,
                                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                                ),
                            ],
                            spacing=8,
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        ft.Text(
                            f"{model}  •  {address}",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            overflow=ft.TextOverflow.ELLIPSIS,
                            max_lines=1,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Row(controls=actions, spacing=6),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=12,
        border_radius=12,
        bgcolor=bg_color,
        border=ft.Border.all(1.5 if is_selected else 1.0, border_color),
        ink=True,
        on_click=handle_click,
    )
