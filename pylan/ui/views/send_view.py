"""Send view for queuing files, picking nearby devices, and transferring."""

from typing import Any, Callable, Optional

import flet as ft

from pylan.ui.components.file_picker import FilePickerComponent
from pylan.ui.components.transfer_row import create_transfer_row
from pylan.ui.state import AppState, TransferDirection


def show_notice(page: Any, text: str) -> None:
    """Display an informational notification bar.

    Args:
        page: Flet Page instance.
        text: Message string to present.
    """
    if page is None:
        return
    snack = ft.SnackBar(content=ft.Text(text))
    if hasattr(page, "show_dialog"):
        page.show_dialog(snack)
    elif hasattr(page, "show_snack_bar"):
        page.show_snack_bar(snack)


def create_send_view(
    state: AppState,
    picker_component: FilePickerComponent,
    on_back_click: Optional[Callable[[], None]] = None,
    on_transfer_started: Optional[Callable[[], None]] = None,
    page_width: Optional[float] = None,
) -> ft.Control:
    """Construct the Send Files view.

    Args:
        state: Reactive application state store.
        picker_component: Shared FilePickerComponent instance.
        on_back_click: Optional callback to return to the home screen.
        on_transfer_started: Optional event handler on transfer dispatch.
        page_width: Optional viewport width for responsive layout adjustments.

    Returns:
        A Flet Control rendering the file sending workspace.
    """
    _ = on_back_click
    is_mobile = page_width is not None and page_width < 500
    manual_ip_field = ft.TextField(
        label="Or enter device address directly",
        hint_text="e.g. 192.168.1.50:44000",
        prefix_icon=ft.Icons.ROUTER_ROUNDED,
        dense=True,
        expand=True,
        border=ft.OutlineInputBorder(border_radius=8),
    )

    peer_options = [
        ft.dropdown.Option(
            key=dev.device.fingerprint,
            text=(
                f"{dev.device.alias} "
                f"({dev.device.channel.host}:{dev.device.channel.port})"
            ),
        )
        for dev in state.devices
    ]

    selected_key: Optional[str] = (
        state.selected_device.device.fingerprint
        if state.selected_device
        else (peer_options[0].key if peer_options else None)
    )

    def handle_peer_dropdown_change(e: Any = None) -> None:
        key = getattr(getattr(e, "control", None), "value", None)
        matched = next(
            (d for d in state.devices if d.device.fingerprint == key), None
        )
        state.select_device(matched)

    peer_dropdown = ft.Dropdown(
        label="Select nearby device",
        options=peer_options,
        value=selected_key,
        dense=True,
        expand=True,
        border=ft.OutlineInputBorder(border_radius=8),
    )
    peer_dropdown.on_select = handle_peer_dropdown_change

    def handle_send_click(e: Any = None) -> None:
        page = getattr(getattr(e, "control", None), "page", None)
        files = picker_component.selected_paths
        if not files:
            show_notice(page, "Please select at least one file to send.")
            return

        manual_val = (manual_ip_field.value or "").strip()
        target_dev = state.selected_device

        if not target_dev and not manual_val:
            show_notice(page, "Please choose a recipient device or address.")
            return

        state.queue_send(
            file_paths=files,
            target_device=target_dev,
            manual_target=manual_val if not target_dev else None,
        )

        picker_component.clear_files()
        show_notice(page, f"Queued {len(files)} file(s) for transmission.")
        if on_transfer_started is not None:
            on_transfer_started()

    send_button = ft.FilledButton(
        "Send Files",
        icon=ft.Icons.SEND_ROUNDED,
        height=42,
        on_click=handle_send_click,
    )

    recipient_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    "Recipient",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.ON_SURFACE,
                ),
                peer_dropdown
                if peer_options
                else ft.Text(
                    "No nearby devices detected yet. "
                    "Enter device address manually:",
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                manual_ip_field,
                ft.Row(
                    controls=[send_button],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=10,
        ),
        padding=12 if is_mobile else 16,
        border_radius=12,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
    )

    # Outgoing transfers list
    outgoing_transfers = [
        t for t in state.transfers if t.direction == TransferDirection.SEND
    ]
    outgoing_rows: list[ft.Control] = []
    transfers_section: ft.Control
    if outgoing_transfers:
        for t in outgoing_transfers:
            outgoing_rows.append(create_transfer_row(item=t))
        transfers_section = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "Outgoing Transfers",
                            size=15,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.ON_SURFACE,
                        ),
                        ft.TextButton(
                            "Clear completed",
                            icon=ft.Icons.CLEAR_ALL_ROUNDED,
                            on_click=lambda _: (
                                state.clear_completed_transfers()
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Column(controls=outgoing_rows, spacing=8),
            ],
            spacing=10,
        )
    else:
        transfers_section = ft.Container(height=0)

    return ft.ListView(
        controls=[
            picker_component.build(),
            recipient_card,
            transfers_section,
        ],
        spacing=12 if is_mobile else 16,
        padding=12 if is_mobile else 20,
        expand=True,
    )
