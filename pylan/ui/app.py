"""Flet desktop application entrypoint and main window setup for PyLan."""

from pathlib import Path
from typing import Any

import flet as ft

from pylan.core.models import StatefulDevice
from pylan.ui.components.file_picker import FilePickerComponent
from pylan.ui.components.navbar import create_top_bar
from pylan.ui.state import AppState
from pylan.ui.views.home_view import create_home_view
from pylan.ui.views.receive_view import create_receive_view
from pylan.ui.views.send_view import create_send_view
from pylan.ui.views.settings_view import create_settings_view


def main(page: ft.Page) -> None:
    """Initialize and run the PyLan Flet user interface.

    Args:
        page: Active root Page provided by the Flet runtime.
    """
    page.title = "pylan"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.Colors.SURFACE_CONTAINER
    page.padding = 0

    assets_dir = Path(__file__).parent / "assets"
    ico_file = assets_dir / "icon.ico"
    png_file = assets_dir / "icon.png"

    if hasattr(page, "window"):
        page.window.width = 900
        page.window.height = 680
        page.window.min_width = 650
        page.window.min_height = 540
        if ico_file.exists():
            page.window.icon = str(ico_file)
        elif png_file.exists():
            page.window.icon = str(png_file)

    state = AppState()

    file_picker_comp = FilePickerComponent()
    file_picker_comp.attach_to_page(page)

    folder_picker = ft.FilePicker()
    if hasattr(page, "services") and folder_picker not in page.services:
        page.services.append(folder_picker)

    active_page: list[str] = ["home"]
    content_area = ft.Container(expand=True)
    top_bar_container = ft.Container()

    def go_home() -> None:
        active_page[0] = "home"
        render_current_view()
        page.update()

    def go_send() -> None:
        active_page[0] = "send"
        render_current_view()
        page.update()

    def go_receive() -> None:
        active_page[0] = "receive"
        render_current_view()
        page.update()

    def go_settings() -> None:
        active_page[0] = "settings"
        render_current_view()
        page.update()

    def switch_to_send_with_peer(device: StatefulDevice) -> None:
        state.select_device(device)
        go_send()

    def render_current_view() -> None:
        current = active_page[0]
        cur_width = page.width
        if current == "send":
            top_bar_container.content = create_top_bar(
                state=state,
                on_scan_click=state.trigger_discovery,
                on_settings_click=go_settings,
                on_back_click=go_home,
                title="Send Files",
                page_width=cur_width,
            )
            content_area.content = create_send_view(
                state=state,
                picker_component=file_picker_comp,
                on_back_click=go_home,
                page_width=cur_width,
            )
        elif current == "receive":
            top_bar_container.content = create_top_bar(
                state=state,
                on_scan_click=state.trigger_discovery,
                on_settings_click=go_settings,
                on_back_click=go_home,
                title="Receive Files",
                page_width=cur_width,
            )
            content_area.content = create_receive_view(
                state=state,
                on_back_click=go_home,
                page_width=cur_width,
            )
        elif current == "settings":
            top_bar_container.content = create_top_bar(
                state=state,
                on_scan_click=state.trigger_discovery,
                on_settings_click=go_home,
                on_back_click=go_home,
                title="Settings",
                page_width=cur_width,
            )
            content_area.content = create_settings_view(
                state=state,
                folder_picker=folder_picker,
                on_back_click=go_home,
                page_width=cur_width,
            )
        else:
            top_bar_container.content = create_top_bar(
                state=state,
                on_scan_click=state.trigger_discovery,
                on_settings_click=go_settings,
                page_width=cur_width,
            )
            content_area.content = create_home_view(
                state=state,
                on_send_click=go_send,
                on_receive_click=go_receive,
                on_quick_send=switch_to_send_with_peer,
                page_width=cur_width,
            )

    def handle_state_change() -> None:
        render_current_view()
        try:
            page.update()
        except Exception:
            pass

    def handle_resize(_: Any = None) -> None:
        render_current_view()
        try:
            page.update()
        except Exception:
            pass

    page.on_resize = handle_resize
    state.add_listener(handle_state_change)

    render_current_view()

    layout = ft.SafeArea(
        content=ft.Column(
            controls=[
                top_bar_container,
                content_area,
            ],
            expand=True,
            spacing=0,
        ),
        expand=True,
    )

    page.add(layout)

    # Lifecycle management
    state.start_services()
    state.trigger_discovery()

    def cleanup() -> None:
        state.remove_listener(handle_state_change)
        state.stop_services()

    page.on_disconnect = lambda _: cleanup()


if __name__ == "__main__":
    assets_path = str(Path(__file__).parent / "assets")
    ft.run(main, assets_dir=assets_path)
