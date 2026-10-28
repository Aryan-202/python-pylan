"""Flet desktop application entrypoint and main window setup for PyLan."""

from pathlib import Path

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
        if current == "send":
            top_bar_container.content = create_top_bar(
                state=state,
                on_scan_click=state.trigger_discovery,
                on_settings_click=go_settings,
                on_back_click=go_home,
                title="Send Files",
            )
            content_area.content = create_send_view(
                state=state,
                picker_component=file_picker_comp,
                on_back_click=go_home,
            )
        elif current == "receive":
            top_bar_container.content = create_top_bar(
                state=state,
                on_scan_click=state.trigger_discovery,
                on_settings_click=go_settings,
                on_back_click=go_home,
                title="Receive Files",
            )
            content_area.content = create_receive_view(
                state=state,
                on_back_click=go_home,
            )
        elif current == "settings":
            top_bar_container.content = create_top_bar(
                state=state,
                on_scan_click=state.trigger_discovery,
                on_settings_click=go_home,
                on_back_click=go_home,
                title="Settings",
            )
            content_area.content = create_settings_view(
                state=state,
                folder_picker=folder_picker,
                on_back_click=go_home,
            )
        else:
            top_bar_container.content = create_top_bar(
                state=state,
                on_scan_click=state.trigger_discovery,
                on_settings_click=go_settings,
            )
            content_area.content = create_home_view(
                state=state,
                on_send_click=go_send,
                on_receive_click=go_receive,
                on_quick_send=switch_to_send_with_peer,
            )

    def handle_state_change() -> None:
        render_current_view()
        try:
            page.update()
        except Exception:
            pass

    state.add_listener(handle_state_change)

    render_current_view()

    layout = ft.Column(
        controls=[
            top_bar_container,
            content_area,
        ],
        expand=True,
        spacing=0,
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
