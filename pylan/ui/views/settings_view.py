"""Settings view for configuring device identity, networking, and storage."""

import inspect
from typing import Any, Callable, Optional

import flet as ft

from pylan.ui.state import AppState


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


def create_settings_view(
    state: AppState,
    folder_picker: Optional[ft.FilePicker] = None,
    on_back_click: Optional[Callable[[], None]] = None,
    page_width: Optional[float] = None,
) -> ft.Control:
    """Construct the Settings configuration view.

    Args:
        state: Reactive application state store.
        folder_picker: Optional FilePicker instance for directory selection.
        on_back_click: Optional callback to return to the home screen.
        page_width: Optional viewport width for responsive layout adjustments.

    Returns:
        A Flet Control containing the application settings form.
    """
    settings = state.settings

    _ = on_back_click
    is_mobile = page_width is not None and page_width < 500
    alias_field = ft.TextField(
        label="Device Name",
        value=settings.device_alias,
        prefix_icon=ft.Icons.BADGE_ROUNDED,
        dense=True,
        border=ft.OutlineInputBorder(border_radius=8),
    )

    model_field = ft.TextField(
        label="Device Model",
        value=settings.device_model,
        prefix_icon=ft.Icons.LAPTOP_ROUNDED,
        dense=True,
        border=ft.OutlineInputBorder(border_radius=8),
    )

    port_field = ft.TextField(
        label="Connection Port",
        value=str(settings.tcp_port),
        prefix_icon=ft.Icons.LAN_ROUNDED,
        dense=True,
        border=ft.OutlineInputBorder(border_radius=8),
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    download_dir_field = ft.TextField(
        label="Save Location",
        value=settings.download_dir,
        prefix_icon=ft.Icons.FOLDER_ROUNDED,
        dense=True,
        expand=True,
        border=ft.OutlineInputBorder(border_radius=8),
    )

    async def handle_browse_folder(_: Any = None) -> None:
        if folder_picker is not None:
            try:
                res = folder_picker.get_directory_path()
                path = await res if inspect.isawaitable(res) else res
                if path:
                    download_dir_field.value = str(path)
                    if (
                        hasattr(download_dir_field, "page")
                        and download_dir_field.page
                    ):
                        download_dir_field.update()
            except Exception:
                pass

    browse_folder_btn = ft.FilledTonalButton(
        "Browse",
        icon=ft.Icons.FOLDER_OPEN_ROUNDED,
        height=40,
        on_click=handle_browse_folder,
    )

    auto_accept_switch = ft.Switch(
        label="Automatically accept files from nearby devices",
        value=settings.auto_accept,
    )

    timeout_field = ft.TextField(
        label="Device Search Timeout (seconds)",
        value=str(settings.discovery_timeout),
        prefix_icon=ft.Icons.TIMER_ROUNDED,
        dense=True,
        border=ft.OutlineInputBorder(border_radius=8),
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    def handle_save(e: Any = None) -> None:
        page = getattr(getattr(e, "control", None), "page", None)
        new_alias = (alias_field.value or "").strip()
        new_model = (model_field.value or "").strip()
        new_dir = (download_dir_field.value or "").strip()

        try:
            new_port = int(port_field.value or "44000")
            if not (1024 <= new_port <= 65535):
                raise ValueError("Port must be between 1024 and 65535")
        except ValueError:
            show_notice(
                page, "Invalid port: enter a number (1024-65535)"
            )
            return

        try:
            new_timeout = float(timeout_field.value or "3.0")
            if new_timeout <= 0:
                raise ValueError()
        except ValueError:
            new_timeout = 3.0

        state.update_settings(
            alias=new_alias,
            device_model=new_model,
            port=new_port,
            download_dir=new_dir,
            auto_accept=bool(auto_accept_switch.value),
            discovery_timeout=new_timeout,
        )

        show_notice(page, "Settings saved successfully.")

    def create_section(
        title: str, icon: Any, controls: list[ft.Control]
    ) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Icon(icon, size=20, color=ft.Colors.PRIMARY),
                            ft.Text(
                                title,
                                size=15,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.ON_SURFACE,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT),
                    *controls,
                ],
                spacing=12,
            ),
            padding=12 if is_mobile else 16,
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
        )

    identity_section = create_section(
        "Device Identity",
        ft.Icons.PERSON_ROUNDED,
        [alias_field, model_field],
    )

    network_section = create_section(
        "Network Preferences",
        ft.Icons.WIFI_ROUNDED,
        [
            port_field,
            timeout_field,
        ],
    )

    storage_section = create_section(
        "Storage Preferences",
        ft.Icons.SAVE_ROUNDED,
        [
            ft.Row(
                controls=[download_dir_field, browse_folder_btn],
                spacing=8,
            ),
            auto_accept_switch,
        ],
    )

    save_btn = ft.FilledButton(
        "Save Settings",
        icon=ft.Icons.CHECK_ROUNDED,
        height=42,
        expand=True if is_mobile else False,
        on_click=handle_save,
    )

    return ft.ListView(
        controls=[
            identity_section,
            network_section,
            storage_section,
            ft.Row(
                controls=[save_btn],
                alignment=(
                    ft.MainAxisAlignment.CENTER
                    if is_mobile
                    else ft.MainAxisAlignment.END
                ),
            ),
        ],
        spacing=12 if is_mobile else 16,
        padding=12 if is_mobile else 20,
        expand=True,
    )
