"""Transfer row widget displaying progress and controls for file transfers."""

import os
import subprocess
from typing import Any, Callable, Optional

import flet as ft

from pylan.ui.state import TransferDirection, TransferItem, TransferStatus


def create_transfer_row(
    item: TransferItem,
    on_accept: Optional[Callable[[str], None]] = None,
    on_reject: Optional[Callable[[str], None]] = None,
    on_cancel: Optional[Callable[[str], None]] = None,
    on_open_folder: Optional[Callable[[str], None]] = None,
) -> ft.Control:
    """Create a row widget representing a file transfer session.

    Args:
        item: TransferItem model instance containing session metadata.
        on_accept: Optional callback fired when accepting incoming transfer.
        on_reject: Optional callback fired when rejecting incoming transfer.
        on_cancel: Optional callback fired to cancel an in-progress transfer.
        on_open_folder: Optional callback to reveal file in system explorer.

    Returns:
        A styled Flet Container control.
    """
    is_send = item.direction == TransferDirection.SEND
    icon = ft.Icons.UPLOAD_ROUNDED if is_send else ft.Icons.DOWNLOAD_ROUNDED
    icon_color = ft.Colors.CYAN_300 if is_send else ft.Colors.BLUE_300

    def default_open_folder(_: Any = None) -> None:
        if on_open_folder is not None:
            on_open_folder(item.file_path)
            return
        folder = os.path.dirname(item.file_path)
        if os.path.exists(folder):
            try:
                if os.name == "nt":
                    os.startfile(folder)  # type: ignore[attr-defined]
                else:
                    subprocess.Popen(["xdg-open", folder])
            except Exception:
                pass

    status_badge: ft.Control
    action_controls: list[ft.Control] = []

    if item.status == TransferStatus.TRANSFERRING:
        pct = int(item.progress * 100)
        status_badge = ft.Row(
            controls=[
                ft.Text(
                    f"{pct}%",
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.PRIMARY,
                ),
                ft.Text(
                    f"({item.formatted_speed})",
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ],
            spacing=4,
        )
        if on_cancel is not None:
            action_controls.append(
                ft.IconButton(
                    icon=ft.Icons.CLOSE_ROUNDED,
                    icon_size=18,
                    tooltip="Cancel transfer",
                    on_click=lambda _: on_cancel(item.id),
                )
            )

    elif item.status == TransferStatus.COMPLETED:
        status_badge = ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.CHECK_CIRCLE_ROUNDED,
                    size=16,
                    color=ft.Colors.GREEN_400,
                ),
                ft.Text("Completed", size=12, color=ft.Colors.GREEN_400),
            ],
            spacing=4,
        )
        action_controls.append(
            ft.IconButton(
                icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                icon_size=18,
                tooltip="Open containing folder",
                on_click=default_open_folder,
            )
        )

    elif item.status == TransferStatus.PENDING:
        if item.direction == TransferDirection.RECEIVE:
            status_badge = ft.Text(
                "Awaiting approval",
                size=12,
                weight=ft.FontWeight.W_600,
                color=ft.Colors.AMBER_400,
            )
            if on_accept is not None:
                action_controls.append(
                    ft.FilledButton(
                        "Accept",
                        icon=ft.Icons.CHECK,
                        height=30,
                        on_click=lambda _: on_accept(item.id),
                    )
                )
            if on_reject is not None:
                action_controls.append(
                    ft.OutlinedButton(
                        "Decline",
                        icon=ft.Icons.CLOSE,
                        height=30,
                        on_click=lambda _: on_reject(item.id),
                    )
                )
        else:
            status_badge = ft.Text(
                "Connecting...", size=12, color=ft.Colors.AMBER_300
            )

    elif item.status == TransferStatus.REJECTED:
        status_badge = ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.CANCEL_ROUNDED,
                    size=16,
                    color=ft.Colors.ORANGE_400,
                ),
                ft.Text("Declined", size=12, color=ft.Colors.ORANGE_400),
            ],
            spacing=4,
        )

    else:
        status_badge = ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.ERROR_OUTLINE_ROUNDED,
                    size=16,
                    color=ft.Colors.RED_400,
                ),
                ft.Text(
                    item.error_message or "Failed",
                    size=12,
                    color=ft.Colors.RED_400,
                ),
            ],
            spacing=4,
        )

    # Progress bar displayed when active
    progress_bar = (
        ft.ProgressBar(
            value=item.progress,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            color=ft.Colors.PRIMARY,
            height=4,
            border_radius=2,
        )
        if item.status == TransferStatus.TRANSFERRING
        else ft.Container(height=0)
    )

    direction_label = "To" if is_send else "From"

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Icon(icon, size=24, color=icon_color),
                            padding=8,
                            border_radius=8,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    item.file_name,
                                    size=14,
                                    weight=ft.FontWeight.W_600,
                                    color=ft.Colors.ON_SURFACE,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    max_lines=1,
                                ),
                                ft.Text(
                                    f"{item.formatted_size}  •  "
                                    f"{direction_label} {item.peer_alias}",
                                    size=12,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        status_badge,
                        ft.Row(controls=action_controls, spacing=4),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                progress_bar,
            ],
            spacing=8,
        ),
        padding=12,
        border_radius=10,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
    )
