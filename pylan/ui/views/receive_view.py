"""Receive view for incoming transfer approvals, status, and history."""

import os
import subprocess
from pathlib import Path
from typing import Any, Callable, Optional

import flet as ft

from pylan.ui.components.transfer_row import create_transfer_row
from pylan.ui.state import AppState, TransferDirection, TransferStatus


def create_receive_view(
    state: AppState,
    on_back_click: Optional[Callable[[], None]] = None,
) -> ft.Control:
    """Construct the Receive Transfers workspace view.

    Args:
        state: Reactive application state store.
        on_back_click: Optional callback to return to the home screen.

    Returns:
        A Flet Control rendering the receiver status, approvals, and history.
    """
    settings = state.settings
    download_dir = settings.download_dir

    _ = on_back_click

    def open_downloads_folder(_: Any = None) -> None:
        target = Path(download_dir)
        target.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(str(target))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", str(target)])
        except Exception:
            pass

    def toggle_auto_accept(e: Any = None) -> None:
        val = bool(getattr(getattr(e, "control", None), "value", False))
        state.update_settings(auto_accept=val)

    # Receiver status banner
    status_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    ft.Icons.DOWNLOAD_DONE_ROUNDED,
                                    size=24,
                                    color=ft.Colors.PRIMARY,
                                ),
                                ft.Text(
                                    "Ready to Receive",
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    color=ft.Colors.ON_SURFACE,
                                ),
                            ],
                            spacing=8,
                        ),
                        ft.FilledTonalButton(
                            "Open Folder",
                            icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                            height=32,
                            on_click=open_downloads_folder,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "Save Location",
                                    size=12,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Text(
                                    download_dir,
                                    size=13,
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.ON_SURFACE,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    max_lines=1,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=16,
                ),
                ft.Switch(
                    label=(
                        "Automatically accept incoming files from nearby "
                        "devices"
                    ),
                    value=settings.auto_accept,
                    on_change=toggle_auto_accept,
                ),
            ],
            spacing=12,
        ),
        padding=16,
        border_radius=12,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
    )

    # Pending approvals
    pending = [
        t
        for t in state.transfers
        if t.direction == TransferDirection.RECEIVE
        and t.status == TransferStatus.PENDING
    ]
    pending_controls: list[ft.Control] = []
    pending_section: ft.Control
    if pending:
        for item in pending:
            pending_controls.append(
                create_transfer_row(
                    item=item,
                    on_accept=state.accept_incoming,
                    on_reject=state.reject_incoming,
                )
            )
        pending_section = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(
                                ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED,
                                size=20,
                                color=ft.Colors.AMBER_400,
                            ),
                            ft.Text(
                                f"Pending Approvals ({len(pending)})",
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.AMBER_400,
                            ),
                        ],
                        spacing=6,
                    ),
                    ft.Column(controls=pending_controls, spacing=8),
                ],
                spacing=10,
            ),
            padding=14,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            border=ft.Border.all(1.5, ft.Colors.AMBER_400),
        )
    else:
        pending_section = ft.Container(height=0)

    # Incoming history
    incoming_transfers = [
        t
        for t in state.transfers
        if t.direction == TransferDirection.RECEIVE
        and t.status != TransferStatus.PENDING
    ]
    history_rows: list[ft.Control] = []
    history_section: ft.Control
    if incoming_transfers:
        for t in incoming_transfers:
            history_rows.append(create_transfer_row(item=t))
        history_section = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "Transfer History",
                            size=15,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.ON_SURFACE,
                        ),
                        ft.TextButton(
                            "Clear history",
                            icon=ft.Icons.CLEAR_ALL_ROUNDED,
                            on_click=lambda _: (
                                state.clear_completed_transfers()
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Column(controls=history_rows, spacing=8),
            ],
            spacing=10,
        )
    else:
        history_section = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.INBOX_ROUNDED,
                        size=40,
                        color=ft.Colors.OUTLINE,
                    ),
                    ft.Text(
                        "No incoming transfers yet.",
                        size=14,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Text(
                        "Files sent to this machine from other devices "
                        "will appear here.",
                        size=12,
                        color=ft.Colors.OUTLINE,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
            ),
            padding=30,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            alignment=ft.Alignment.CENTER,
        )

    return ft.ListView(
        controls=[
            status_card,
            pending_section,
            history_section,
        ],
        spacing=16,
        padding=20,
        expand=True,
    )
