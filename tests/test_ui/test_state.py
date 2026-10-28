"""Unit tests for PyLan reactive state management and transfer models."""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

from pylan.core.models import (
    DiscoveredDevice,
    HttpChannel,
    StatefulDevice,
)
from pylan.ui.components import (
    FilePickerComponent,
    create_navigation_rail,
    create_peer_tile,
    create_top_bar,
    create_transfer_row,
)
from pylan.ui.state import (
    AppSettings,
    AppState,
    TransferDirection,
    TransferItem,
    TransferStatus,
    format_bytes,
)
from pylan.ui.views import (
    create_home_view,
    create_receive_view,
    create_send_view,
    create_settings_view,
)


class TestFormatBytes(unittest.TestCase):
    """Test format_bytes utility function."""

    def test_negative_and_zero(self) -> None:
        """Verify handling of zero and negative values."""
        self.assertEqual(format_bytes(-10), "0 B")
        self.assertEqual(format_bytes(0), "0 B")

    def test_bytes_range(self) -> None:
        """Verify formatting below 1 KB."""
        self.assertEqual(format_bytes(512), "512 B")
        self.assertEqual(format_bytes(1023), "1023 B")

    def test_kilobytes_and_megabytes(self) -> None:
        """Verify scaling to KB and MB."""
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(1536), "1.5 KB")
        self.assertEqual(format_bytes(1024 * 1024 * 5), "5.0 MB")

    def test_gigabytes_and_terabytes(self) -> None:
        """Verify scaling to GB and TB."""
        self.assertEqual(format_bytes(1024 * 1024 * 1024 * 2), "2.0 GB")
        self.assertEqual(
            format_bytes(1024 * 1024 * 1024 * 1024 * 3), "3.0 TB"
        )


class TestTransferItem(unittest.TestCase):
    """Test TransferItem model and calculated properties."""

    def test_progress_calculation(self) -> None:
        """Verify progress percentage calculations."""
        item = TransferItem(
            id="t1",
            direction=TransferDirection.SEND,
            file_name="test.txt",
            file_path="/path/test.txt",
            file_size=1000,
            transferred_bytes=500,
        )
        self.assertEqual(item.progress, 0.5)

        item.transferred_bytes = 1000
        self.assertEqual(item.progress, 1.0)

    def test_zero_size_file_progress(self) -> None:
        """Verify progress for zero-byte file."""
        item = TransferItem(
            id="t2",
            direction=TransferDirection.RECEIVE,
            file_name="empty.txt",
            file_path="/path/empty.txt",
            file_size=0,
            status=TransferStatus.PENDING,
        )
        self.assertEqual(item.progress, 0.0)

        item.status = TransferStatus.COMPLETED
        self.assertEqual(item.progress, 1.0)

    def test_formatted_properties(self) -> None:
        """Verify formatted size and speed strings."""
        item = TransferItem(
            id="t3",
            direction=TransferDirection.SEND,
            file_name="doc.pdf",
            file_path="/path/doc.pdf",
            file_size=2048,
            speed_bps=10240,
        )
        self.assertEqual(item.formatted_size, "2.0 KB")
        self.assertEqual(item.formatted_speed, "10.0 KB/s")


class TestAppState(unittest.TestCase):
    """Test AppState management, observers, and transfer operations."""

    def setUp(self) -> None:
        """Initialize a fresh AppState instance with mock settings."""
        self.settings = AppSettings(
            device_alias="TestNode",
            device_model="TestPlatform",
            tcp_port=44100,
            download_dir="/tmp/pylan_test",
            auto_accept=False,
            discovery_timeout=2.0,
        )
        self.state = AppState(settings=self.settings)

    def test_initial_state(self) -> None:
        """Verify baseline state configuration."""
        self.assertEqual(self.state.settings.device_alias, "TestNode")
        self.assertEqual(self.state.settings.tcp_port, 44100)
        self.assertFalse(self.state.settings.auto_accept)
        self.assertEqual(len(self.state.devices), 0)
        self.assertEqual(len(self.state.transfers), 0)
        self.assertIsNone(self.state.selected_device)

    def test_listener_notification(self) -> None:
        """Verify observer callbacks receive updates."""
        mock_cb = MagicMock()
        self.state.add_listener(mock_cb)

        self.state.update_settings(alias="NewAlias")
        self.assertEqual(self.state.settings.device_alias, "NewAlias")
        mock_cb.assert_called_once()

        self.state.remove_listener(mock_cb)
        self.state.update_settings(alias="AnotherAlias")
        self.assertEqual(mock_cb.call_count, 1)

    def test_listener_exception_resilience(self) -> None:
        """Verify failing listener does not prevent other callbacks."""
        failing_cb = MagicMock(side_effect=RuntimeError("Test error"))
        success_cb = MagicMock()

        self.state.add_listener(failing_cb)
        self.state.add_listener(success_cb)

        self.state.notify()
        failing_cb.assert_called_once()
        success_cb.assert_called_once()

    def test_select_device(self) -> None:
        """Verify device target selection and clearing."""
        channel = HttpChannel(host="192.168.1.10", port=44000)
        discovered = DiscoveredDevice(
            alias="Peer1",
            version="0.0.2",
            device_model="Linux Box",
            device_type="desktop",
            fingerprint="fp123",
            channel=channel,
        )
        now = datetime.now()
        dev = StatefulDevice(
            device=discovered,
            first_seen=now,
            last_seen=now,
            channels=[channel],
        )

        self.state.select_device(dev)
        self.assertEqual(self.state.selected_device, dev)

        self.state.select_device(None)
        self.assertIsNone(self.state.selected_device)

    def test_set_selected_files(self) -> None:
        """Verify setting file queues filters non-existent paths."""
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"content")
            valid_path = tf.name

        try:
            self.state.set_selected_files(
                [valid_path, "/nonexistent/fake.file"]
            )
            self.assertEqual(self.state.selected_files, [valid_path])
        finally:
            if os.path.exists(valid_path):
                os.remove(valid_path)

    def test_queue_send_creates_transfers(self) -> None:
        """Verify queue_send instantiates TransferItems."""
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"data-packet")
            file_path = tf.name

        try:
            items = self.state.queue_send(
                file_paths=[file_path], manual_target="192.168.1.99:44000"
            )
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].file_name, os.path.basename(file_path))
            self.assertEqual(items[0].peer_address, "192.168.1.99:44000")
            self.assertEqual(items[0].direction, TransferDirection.SEND)
            self.assertEqual(len(self.state.transfers), 1)
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    def test_clear_completed_transfers(self) -> None:
        """Verify clearing transfers preserves pending and active items."""
        item_done = TransferItem(
            id="t1",
            direction=TransferDirection.SEND,
            file_name="done.txt",
            file_path="/done.txt",
            file_size=10,
            status=TransferStatus.COMPLETED,
        )
        item_active = TransferItem(
            id="t2",
            direction=TransferDirection.SEND,
            file_name="active.txt",
            file_path="/active.txt",
            file_size=10,
            status=TransferStatus.TRANSFERRING,
        )
        item_pending = TransferItem(
            id="t3",
            direction=TransferDirection.RECEIVE,
            file_name="pending.txt",
            file_path="/pending.txt",
            file_size=10,
            status=TransferStatus.PENDING,
        )
        item_failed = TransferItem(
            id="t4",
            direction=TransferDirection.SEND,
            file_name="failed.txt",
            file_path="/failed.txt",
            file_size=10,
            status=TransferStatus.FAILED,
        )

        self.state.transfers = [
            item_done,
            item_active,
            item_pending,
            item_failed,
        ]
        self.state.clear_completed_transfers()

        self.assertIn(item_active, self.state.transfers)
        self.assertIn(item_pending, self.state.transfers)
        self.assertNotIn(item_done, self.state.transfers)
        self.assertNotIn(item_failed, self.state.transfers)

    def test_start_receiver_port_fallback(self) -> None:
        """Verify fallback to alternate port when preferred port is in use."""
        import asyncio

        state = AppState()
        mock_server = MagicMock()
        calls: list[int] = []

        async def fake_start_server(*args: Any, **kwargs: Any) -> Any:
            p = kwargs.get("port", 0)
            calls.append(p)
            if p == 44000:
                raise OSError("Port busy")
            return mock_server

        with patch("asyncio.start_server", side_effect=fake_start_server):
            asyncio.run(state._start_receiver_coro())
            self.assertTrue(state.is_receiver_running)
            self.assertEqual(state.settings.tcp_port, 44001)
            self.assertEqual(calls, [44000, 44001])


class TestUIComponentRendering(unittest.TestCase):
    """Test that all UI components and views instantiate correctly."""

    def setUp(self) -> None:
        """Create sample state and device fixture."""
        self.state = AppState()
        channel = HttpChannel(host="192.168.1.15", port=44000)
        discovered = DiscoveredDevice(
            alias="LaptopPeer",
            version="0.0.2",
            device_model="MacBook",
            device_type="laptop",
            fingerprint="abc123456789",
            channel=channel,
        )
        now = datetime.now()
        self.device = StatefulDevice(
            device=discovered,
            first_seen=now,
            last_seen=now,
            channels=[channel],
        )

    def test_create_peer_tile(self) -> None:
        """Verify peer tile creation."""
        tile = create_peer_tile(device=self.device, is_selected=True)
        self.assertIsNotNone(tile)

    def test_create_transfer_row(self) -> None:
        """Verify transfer row creation."""
        item = TransferItem(
            id="t1",
            direction=TransferDirection.RECEIVE,
            file_name="incoming.png",
            file_path="/downloads/incoming.png",
            file_size=5000,
            status=TransferStatus.PENDING,
        )
        row = create_transfer_row(item=item)
        self.assertIsNotNone(row)

    def test_create_navigation_rail_and_top_bar(self) -> None:
        """Verify top bar and navigation rail generation."""
        top_bar = create_top_bar(state=self.state)
        nav_rail = create_navigation_rail(
            selected_index=0, on_change=lambda _: None
        )
        self.assertIsNotNone(top_bar)
        self.assertIsNotNone(nav_rail)

    def test_create_views(self) -> None:
        """Verify all full-screen views construct without exceptions."""
        picker_comp = FilePickerComponent()
        home = create_home_view(state=self.state)
        send = create_send_view(
            state=self.state, picker_component=picker_comp
        )
        receive = create_receive_view(state=self.state)
        settings = create_settings_view(state=self.state)

        self.assertIsNotNone(home)
        self.assertIsNotNone(send)
        self.assertIsNotNone(receive)
        self.assertIsNotNone(settings)


class TestMainDispatch(unittest.TestCase):
    """Test package execution dispatch between CLI and GUI."""

    def test_cli_dispatch_when_no_gui_arg(self) -> None:
        """Verify execution delegates to CLI when gui flag is omitted."""
        from pylan.__main__ import main

        with patch.object(sys, "argv", ["pylan", "scan"]), patch(
            "pylan.cli.cli.cli"
        ) as mock_cli:
            main()
            mock_cli.assert_called_once()

    def test_gui_dispatch_when_gui_arg_passed(self) -> None:
        """Verify execution delegates to Flet run when gui flag is passed."""
        from pylan.__main__ import main

        with patch.object(sys, "argv", ["pylan", "gui"]), patch(
            "flet.run"
        ) as mock_run:
            main()
            mock_run.assert_called_once()
