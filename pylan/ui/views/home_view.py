"""Home dashboard view displaying nearby devices and primary actions."""

from typing import Callable, Optional

import flet as ft

from pylan.core.models import StatefulDevice
from pylan.ui.components.peer_tile import create_peer_tile
from pylan.ui.components.transfer_row import create_transfer_row
from pylan.ui.state import AppState, TransferStatus


def create_home_view(
    state: AppState,
    on_send_click: Optional[Callable[[], None]] = None,
    on_receive_click: Optional[Callable[[], None]] = None,
    on_quick_send: Optional[Callable[[StatefulDevice], None]] = None,
    page_width: Optional[float] = None,
) -> ft.Control:
    """Construct the unified Home view.

    Args:
        state: Reactive application state store.
        on_send_click: Callback to open the Send files workflow.
        on_receive_click: Callback to open the Receive files workflow.
        on_quick_send: Callback to send files directly to a clicked device.
        page_width: Current viewport width for responsive layout adjustments.

    Returns:
        A Flet Control containing the complete home screen.
    """
    is_mobile = page_width is not None and page_width < 500

    def handle_device_select(device: StatefulDevice) -> None:
        state.select_device(device)
        if on_quick_send is not None:
            on_quick_send(device)
        elif on_send_click is not None:
            on_send_click()

    # Nearby devices listing
    devices_controls: list[ft.Control] = []
    if state.devices:
        for dev in state.devices:
            is_sel = (
                state.selected_device is not None
                and state.selected_device.device.fingerprint
                == dev.device.fingerprint
            )
            devices_controls.append(
                create_peer_tile(
                    device=dev,
                    is_selected=is_sel,
                    on_select=lambda d: state.select_device(d),
                    on_quick_send=handle_device_select,
                )
            )
    else:
        empty_device_message = (
            "Looking for nearby devices..."
            if state.is_scanning
            else "No nearby devices found."
        )
        devices_controls.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(
                            ft.Icons.ROUTER_ROUNDED,
                            size=44,
                            color=ft.Colors.OUTLINE,
                        ),
                        ft.Text(
                            empty_device_message,
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Text(
                            "Make sure other devices are connected to the "
                            "same Wi-Fi and have PyLan open.",
                            size=12,
                            color=ft.Colors.OUTLINE,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=6),
                        ft.FilledTonalButton(
                            "Find Devices",
                            icon=ft.Icons.SEARCH_ROUNDED,
                            height=38,
                            on_click=lambda _: state.trigger_discovery(),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=6,
                ),
                padding=22 if is_mobile else 36,
                border_radius=12,
                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                alignment=ft.Alignment.CENTER,
            )
        )

    devices_section = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text(
                        "Nearby Devices",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE,
                    ),
                    ft.FilledTonalButton(
                        "Find Devices",
                        icon=ft.Icons.REFRESH_ROUNDED,
                        height=32,
                        on_click=lambda _: state.trigger_discovery(),
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Column(controls=devices_controls, spacing=8),
        ],
        spacing=12,
    )

    # Active and pending transfers section
    active_transfers = [
        t
        for t in state.transfers
        if t.status in (TransferStatus.PENDING, TransferStatus.TRANSFERRING)
    ]
    transfer_rows: list[ft.Control] = []
    transfers_section: ft.Control
    if active_transfers:
        for t in active_transfers:
            transfer_rows.append(
                create_transfer_row(
                    item=t,
                    on_accept=state.accept_incoming,
                    on_reject=state.reject_incoming,
                    on_cancel=state.cancel_transfer
                    if hasattr(state, "cancel_transfer")
                    else None,
                )
            )
        transfers_section = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "Active Transfers",
                            size=15,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.AMBER_400,
                        ),
                        ft.TextButton(
                            "View history",
                            icon=ft.Icons.ARROW_FORWARD_ROUNDED,
                            on_click=lambda _: on_receive_click()
                            if on_receive_click
                            else None,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Column(controls=transfer_rows, spacing=8),
            ],
            spacing=10,
        )
    else:
        transfers_section = ft.Container(height=0)

    # Primary bottom actions: Send and Receive
    btn_height = 48 if is_mobile else 52
    icon_size = 20 if is_mobile else 22
    text_size = 15 if is_mobile else 16

    bottom_actions = ft.Container(
        content=ft.Row(
            controls=[
                ft.FilledButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.SEND_ROUNDED, size=icon_size),
                            ft.Text(
                                "Send",
                                size=text_size,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6 if is_mobile else 8,
                    ),
                    height=btn_height,
                    expand=True,
                    on_click=lambda _: (
                        on_send_click() if on_send_click else None
                    ),
                ),
                ft.FilledTonalButton(
                    content=ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.DOWNLOAD_ROUNDED, size=icon_size
                            ),
                            ft.Text(
                                "Receive",
                                size=text_size,
                                weight=ft.FontWeight.BOLD,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        spacing=6 if is_mobile else 8,
                    ),
                    height=btn_height,
                    expand=True,
                    on_click=lambda _: (
                        on_receive_click() if on_receive_click else None
                    ),
                ),
            ],
            spacing=10 if is_mobile else 16,
        ),
        padding=ft.Padding.symmetric(
            vertical=6 if is_mobile else 8, horizontal=0
        ),
    )

    return ft.ListView(
        controls=[
            devices_section,
            ft.Container(height=10),
            transfers_section,
            ft.Container(height=14),
            bottom_actions,
        ],
        spacing=10,
        padding=12 if is_mobile else 20,
        expand=True,
    )
