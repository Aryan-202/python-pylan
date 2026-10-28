"""Top app bar and navigation controls for PyLan UI."""

from typing import Any, Callable, Optional

import flet as ft

from pylan.ui.state import AppState


def create_top_bar(
    state: AppState,
    on_scan_click: Optional[Callable[[], None]] = None,
    on_settings_click: Optional[Callable[[], None]] = None,
    on_back_click: Optional[Callable[[], None]] = None,
    title: Optional[str] = None,
    page_width: Optional[float] = None,
) -> ft.Container:
    """Create a styled top application header bar.

    Args:
        state: Application state instance providing node identity and status.
        on_scan_click: Callback fired when clicking the search/scan button.
        on_settings_click: Callback fired when clicking the settings icon.
        on_back_click: Optional callback for returning to the home screen.
        title: Optional custom header title string.
        page_width: Optional current viewport width for responsive sizing.

    Returns:
        A Flet Container styled as an application header bar.
    """
    settings = state.settings
    alias = settings.device_alias
    is_compact = page_width is not None and page_width < 500

    status_color = (
        ft.Colors.GREEN_ACCENT_400
        if state.is_receiver_running
        else ft.Colors.ORANGE_400
    )
    status_text = (
        "Ready to share" if state.is_receiver_running else "Offline"
    )

    scan_button = (
        ft.ProgressRing(width=16, height=16, stroke_width=2)
        if state.is_scanning
        else ft.IconButton(
            icon=ft.Icons.REFRESH_ROUNDED,
            tooltip="Find devices",
            icon_color=ft.Colors.PRIMARY,
            on_click=lambda _: on_scan_click() if on_scan_click else None,
        )
    )

    settings_button = ft.IconButton(
        icon=ft.Icons.SETTINGS_ROUNDED,
        tooltip="Settings",
        icon_color=ft.Colors.ON_SURFACE_VARIANT,
        on_click=lambda _: (
            on_settings_click() if on_settings_click else None
        ),
    )

    if on_back_click is not None:
        leading_area = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.Icons.ARROW_BACK_ROUNDED,
                    tooltip="Back to Home",
                    icon_color=ft.Colors.ON_SURFACE,
                    on_click=lambda _: on_back_click(),
                ),
                ft.Text(
                    title or "pylan",
                    size=16 if is_compact else 18,
                    weight=ft.FontWeight.W_700,
                    color=ft.Colors.ON_SURFACE,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1,
                ),
            ],
            spacing=2 if is_compact else 4,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
    else:
        leading_area = ft.Row(
            controls=[
                ft.Image(
                    src="icon.png",
                    width=24 if is_compact else 26,
                    height=24 if is_compact else 26,
                    fit=ft.BoxFit.CONTAIN,
                    error_content=ft.Icon(
                        ft.Icons.SHARE_ROUNDED,
                        size=24 if is_compact else 26,
                        color=ft.Colors.PRIMARY,
                    ),
                ),
                ft.Text(
                    "pylan",
                    size=18 if is_compact else 20,
                    weight=ft.FontWeight.W_800,
                    color=ft.Colors.ON_SURFACE,
                ),
            ],
            spacing=6 if is_compact else 8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # Responsive status indicator
    if page_width is not None and page_width < 380:
        status_pill_content = ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.CIRCLE,
                    size=8,
                    color=status_color,
                ),
            ],
            spacing=0,
            tight=True,
        )
        status_padding = ft.Padding.all(8)
    elif is_compact:
        status_pill_content = ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.CIRCLE,
                    size=8,
                    color=status_color,
                ),
                ft.Text(
                    status_text,
                    size=11,
                    weight=ft.FontWeight.W_500,
                    color=ft.Colors.ON_SURFACE,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1,
                ),
            ],
            spacing=4,
            tight=True,
        )
        status_padding = ft.Padding.symmetric(horizontal=8, vertical=4)
    else:
        status_pill_content = ft.Row(
            controls=[
                ft.Icon(
                    ft.Icons.CIRCLE,
                    size=8,
                    color=status_color,
                ),
                ft.Text(
                    f"{alias} • {status_text}",
                    size=12,
                    weight=ft.FontWeight.W_500,
                    color=ft.Colors.ON_SURFACE,
                    overflow=ft.TextOverflow.ELLIPSIS,
                    max_lines=1,
                ),
            ],
            spacing=6,
            tight=True,
        )
        status_padding = ft.Padding.symmetric(horizontal=12, vertical=6)

    status_pill = ft.Container(
        content=status_pill_content,
        padding=status_padding,
        border_radius=20,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
        tooltip=f"{alias} • {status_text}",
    )

    return ft.Container(
        content=ft.Row(
            controls=[
                leading_area,
                ft.Row(
                    controls=[
                        status_pill,
                        scan_button,
                        settings_button,
                    ],
                    spacing=4 if is_compact else 8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=ft.Padding.symmetric(
            horizontal=12 if is_compact else 16,
            vertical=8 if is_compact else 10,
        ),
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        border=ft.Border(
            bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)
        ),
    )


def create_navigation_rail(
    selected_index: int,
    on_change: Callable[[int], None],
) -> ft.NavigationRail:
    """Create a vertical sidebar navigation rail for main views.

    Args:
        selected_index: Index of currently active page.
        on_change: Callback fired when user selects a different destination.

    Returns:
        A configured Flet NavigationRail control.
    """

    def handle_change(e: Any = None) -> None:
        idx = getattr(e.control, "selected_index", 0) if e else 0
        on_change(int(idx))

    return ft.NavigationRail(
        selected_index=selected_index,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=72,
        min_extended_width=160,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        on_change=handle_change,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.DASHBOARD_OUTLINED,
                selected_icon=ft.Icons.DASHBOARD_ROUNDED,
                label="Home",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SEND_OUTLINED,
                selected_icon=ft.Icons.SEND_ROUNDED,
                label="Send",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DOWNLOAD_OUTLINED,
                selected_icon=ft.Icons.DOWNLOAD_ROUNDED,
                label="Receive",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS_ROUNDED,
                label="Settings",
            ),
        ],
    )
