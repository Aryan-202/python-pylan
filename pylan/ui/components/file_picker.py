"""Custom file selector and drag-and-drop drop zone widget for PyLan."""

import inspect
import logging
import os
from typing import Any, Callable, Optional

import flet as ft

from pylan.ui.state import format_bytes

logger = logging.getLogger(__name__)


class FilePickerComponent:
    """Component for picking, queuing, and managing local files to transmit.

    Integrates with Flet's FilePicker service and renders a dashed drop
    zone container alongside a list of selected files and removal controls.
    """

    def __init__(
        self,
        on_files_changed: Optional[Callable[[list[str]], None]] = None,
    ) -> None:
        """Initialize the file picker component.

        Args:
            on_files_changed: Optional callback fired when file queue changes.
        """
        self.selected_paths: list[str] = []
        self.on_files_changed = on_files_changed

        self.picker = ft.FilePicker(on_result=self._handle_picker_result)
        self._files_list_view = ft.Column(spacing=6)
        self._summary_text = ft.Text(
            "No files selected",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        self._clear_btn = ft.TextButton(
            "Clear all",
            icon=ft.Icons.CLEAR_ALL_ROUNDED,
            visible=False,
            on_click=lambda _: self.clear_files(),
        )

    def attach_to_page(self, page: ft.Page) -> None:
        """Register the underlying FilePicker service with page services.

        Args:
            page: Active Flet Page instance.
        """
        if hasattr(page, "services") and self.picker not in page.services:
            page.services.append(self.picker)

    async def open_picker(self, _: Any = None) -> None:
        """Open the native file selection dialog."""
        try:
            res = self.picker.pick_files(allow_multiple=True)
            files = await res if inspect.isawaitable(res) else res
            if files:
                for f in files:
                    p = getattr(f, "path", None)
                    if (
                        p
                        and os.path.exists(p)
                        and p not in self.selected_paths
                    ):
                        self.selected_paths.append(p)
                self._update_ui()
                if self.on_files_changed:
                    self.on_files_changed(list(self.selected_paths))
        except Exception as exc:
            logger.debug("Error during pick_files: %s", exc)

    def _handle_picker_result(self, e: Any = None) -> None:
        """Callback processing selected files from OS dialog."""
        files = getattr(e, "files", None)
        if files:
            new_paths = [
                f.path
                for f in files
                if getattr(f, "path", None) and os.path.exists(f.path)
            ]
            for path in new_paths:
                if path not in self.selected_paths:
                    self.selected_paths.append(path)
            self._update_ui()
            if self.on_files_changed:
                self.on_files_changed(list(self.selected_paths))

    def remove_file(self, path: str) -> None:
        """Remove a single file path from the queued list.

        Args:
            path: Local file path to remove.
        """
        if path in self.selected_paths:
            self.selected_paths.remove(path)
            self._update_ui()
            if self.on_files_changed:
                self.on_files_changed(list(self.selected_paths))

    def clear_files(self) -> None:
        """Remove all files from the queue."""
        self.selected_paths.clear()
        self._update_ui()
        if self.on_files_changed:
            self.on_files_changed([])

    def _update_ui(self) -> None:
        """Re-render the list items and summary information."""
        self._files_list_view.controls.clear()

        total_bytes = 0
        for path in self.selected_paths:
            try:
                size = os.path.getsize(path)
                total_bytes += size
                size_str = format_bytes(size)
            except OSError:
                size_str = "Unknown size"

            file_name = os.path.basename(path)
            row = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.INSERT_DRIVE_FILE_ROUNDED,
                            size=20,
                            color=ft.Colors.PRIMARY,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    file_name,
                                    size=13,
                                    weight=ft.FontWeight.W_500,
                                    color=ft.Colors.ON_SURFACE,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    max_lines=1,
                                ),
                                ft.Text(
                                    f"{size_str}  •  {path}",
                                    size=11,
                                    color=ft.Colors.ON_SURFACE_VARIANT,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                    max_lines=1,
                                ),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE_ROUNDED,
                            icon_size=18,
                            tooltip="Remove file",
                            on_click=lambda _, p=path: self.remove_file(p),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                border_radius=8,
                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
            )
            self._files_list_view.controls.append(row)

        count = len(self.selected_paths)
        if count == 0:
            self._summary_text.value = "No files selected"
            self._clear_btn.visible = False
        else:
            total_str = format_bytes(total_bytes)
            plural = "s" if count > 1 else ""
            self._summary_text.value = (
                f"{count} file{plural} selected ({total_str} total)"
            )
            self._clear_btn.visible = True

        page = getattr(self._files_list_view, "page", None)
        if page:
            self._files_list_view.update()
            self._summary_text.update()
            self._clear_btn.update()

    def build(self) -> ft.Control:
        """Construct the visual Flet control for the file selector.

        Returns:
            A Flet Container displaying drop zone and queued files.
        """
        drop_zone = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.CLOUD_UPLOAD_ROUNDED,
                        size=48,
                        color=ft.Colors.PRIMARY,
                    ),
                    ft.Text(
                        "Select Files to Transfer",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE,
                    ),
                    ft.Text(
                        "Browse or select multiple files from your system",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Container(height=6),
                    ft.FilledButton(
                        "Browse Files",
                        icon=ft.Icons.FOLDER_OPEN_ROUNDED,
                        on_click=self.open_picker,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=24,
            border_radius=12,
            border=ft.Border.all(1.5, ft.Colors.PRIMARY),
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            alignment=ft.Alignment.CENTER,
        )

        return ft.Column(
            controls=[
                drop_zone,
                ft.Row(
                    controls=[self._summary_text, self._clear_btn],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                self._files_list_view,
            ],
            spacing=10,
        )
