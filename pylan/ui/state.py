"""Reactive application state management for PyLan UI.

This module encapsulates discovery state, transfer queues, settings, and
background networking services (discovery scanner, TCP receiver daemon, and
file transmission worker) into a decoupled thread-safe state store.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from pylan.core.discovery import (
    DiscoveryEngine,
    MSG_TYPE_PROBE_REQUEST,
    MSG_TYPE_PROBE_RESPONSE,
)
from pylan.core.models import StatefulDevice
from pylan.core.net import (
    get_active_interface_details,
    get_default_interface_ip,
)
from pylan.core.protocol import (
    HEADER_SIZE,
    MSG_TYPE_TRANSFER_ACCEPT,
    MSG_TYPE_TRANSFER_CHUNK,
    MSG_TYPE_TRANSFER_COMPLETE,
    MSG_TYPE_TRANSFER_REJECT,
    MSG_TYPE_TRANSFER_REQUEST,
    pack_message,
    unpack_header,
)

logger = logging.getLogger(__name__)

CHUNK_SIZE: int = 64 * 1024
DEFAULT_TCP_PORT: int = 44000
DEFAULT_TIMEOUT: float = 3.0


def format_bytes(num_bytes: int) -> str:
    """Format a byte count into a human-readable representation.

    Args:
        num_bytes: Total number of bytes.

    Returns:
        Formatted string (e.g., '14.2 MB').
    """
    if num_bytes < 0:
        return "0 B"
    if num_bytes < 1024:
        return f"{num_bytes} B"
    val = float(num_bytes)
    for unit in ["KB", "MB", "GB", "TB"]:
        val /= 1024.0
        if val < 1024.0 or unit == "TB":
            return f"{val:.1f} {unit}"
    return f"{val:.1f} TB"


class TransferDirection(str, Enum):
    """Directionality of a file transfer operation."""

    SEND = "send"
    RECEIVE = "receive"


class TransferStatus(str, Enum):
    """Lifecycle phase of a file transfer task."""

    PENDING = "pending"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass
class TransferItem:
    """Represents a discrete file transfer session in the UI transfer queue.

    Attributes:
        id: Unique hexadecimal identifier for tracking this session.
        direction: TransferDirection indicating upload or download.
        file_name: Base name of the file being transferred.
        file_path: Local filesystem path where the file is stored or read.
        file_size: Declared total length of the file in bytes.
        transferred_bytes: Accumulated count of transmitted payload bytes.
        peer_alias: Hostname or display alias of the remote participant.
        peer_address: Network socket address of the remote participant.
        status: Current lifecycle state of the transfer.
        error_message: Explanatory error details if status is FAILED.
        speed_bps: Instantaneous transmission rate in bytes per second.
        created_at: Timestamp when the session was instantiated.
    """

    id: str
    direction: TransferDirection
    file_name: str
    file_path: str
    file_size: int
    transferred_bytes: int = 0
    peer_alias: str = "Unknown"
    peer_address: str = "127.0.0.1:44000"
    status: TransferStatus = TransferStatus.PENDING
    error_message: Optional[str] = None
    speed_bps: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def progress(self) -> float:
        """Fraction of transfer completion ranging between 0.0 and 1.0."""
        if self.file_size <= 0:
            return 1.0 if self.status == TransferStatus.COMPLETED else 0.0
        return min(1.0, max(0.0, self.transferred_bytes / self.file_size))

    @property
    def formatted_size(self) -> str:
        """Human-readable size format."""
        return format_bytes(self.file_size)

    @property
    def formatted_speed(self) -> str:
        """Human-readable transmission rate format."""
        return f"{format_bytes(int(self.speed_bps))}/s"


@dataclass
class AppSettings:
    """Local configuration preferences for the PyLan application.

    Attributes:
        device_alias: Advertised display name for this node.
        device_model: Descriptive hardware model or platform tag.
        tcp_port: Local TCP port used for incoming connections.
        download_dir: Filesystem path configured for incoming downloads.
        auto_accept: Whether to automatically accept incoming transfers.
        discovery_timeout: Seconds to wait during peer discovery sweeps.
    """

    device_alias: str = field(default_factory=socket.gethostname)
    device_model: str = "PyLan Desktop"
    tcp_port: int = DEFAULT_TCP_PORT
    download_dir: str = field(
        default_factory=lambda: str(Path.home() / "Downloads" / "PyLan")
    )
    auto_accept: bool = False
    discovery_timeout: float = DEFAULT_TIMEOUT


class AppState:
    """Reactive state container and service coordinator for PyLan UI.

    Maintains thread-safe collections for discovered peers, transfer history,
    and user settings. Manages background worker threads and asynchronous
    networking services to ensure the UI event loop remains responsive.
    """

    def __init__(self, settings: Optional[AppSettings] = None) -> None:
        """Initialize the application state manager.

        Args:
            settings: Optional custom application settings instance.
        """
        self._lock = threading.RLock()
        self.settings: AppSettings = settings or AppSettings()

        self.devices: list[StatefulDevice] = []
        self.selected_device: Optional[StatefulDevice] = None
        self.selected_files: list[str] = []
        self.transfers: list[TransferItem] = []

        self.is_scanning: bool = False
        self.is_receiver_running: bool = False
        self.active_interface_ip: str = get_default_interface_ip()

        self._listeners: list[Callable[[], None]] = []

        # Background async worker loop and daemon thread
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Engine and server handles
        self.engine: Optional[DiscoveryEngine] = None
        self._server: Optional[asyncio.Server] = None
        self._mc_transport: Optional[asyncio.DatagramTransport] = None
        self._announce_task: Optional[asyncio.Task[None]] = None

        # Incoming transfer approval coordination
        self._incoming_decisions: dict[str, asyncio.Event] = {}
        self._incoming_results: dict[str, bool] = {}

    def add_listener(self, listener: Callable[[], None]) -> None:
        """Register an observer callback to be notified on state updates.

        Args:
            listener: Zero-argument callable triggered on state change.
        """
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        """Unregister a previously attached observer callback.

        Args:
            listener: The callable to detach.
        """
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def notify(self) -> None:
        """Invoke all registered listener callbacks."""
        with self._lock:
            callbacks = list(self._listeners)
        for cb in callbacks:
            try:
                cb()
            except Exception as exc:
                logger.debug(
                    "Error during state listener notification: %s", exc
                )

    def update_settings(
        self,
        alias: Optional[str] = None,
        device_model: Optional[str] = None,
        port: Optional[int] = None,
        download_dir: Optional[str] = None,
        auto_accept: Optional[bool] = None,
        discovery_timeout: Optional[float] = None,
    ) -> None:
        """Update user preferences and notify observers.

        Args:
            alias: Updated local peer display alias.
            device_model: Updated device description string.
            port: Updated TCP receiver port.
            download_dir: Updated directory path for storing transfers.
            auto_accept: Updated automatic transfer acceptance toggle.
            discovery_timeout: Updated seconds for discovery sweep.
        """
        with self._lock:
            if alias is not None and alias.strip():
                self.settings.device_alias = alias.strip()
            if device_model is not None:
                self.settings.device_model = device_model.strip()
            if port is not None and 1024 <= port <= 65535:
                self.settings.tcp_port = port
            if download_dir is not None:
                self.settings.download_dir = download_dir.strip()
            if auto_accept is not None:
                self.settings.auto_accept = auto_accept
            if discovery_timeout is not None and discovery_timeout > 0:
                self.settings.discovery_timeout = discovery_timeout
        self.notify()

    def select_device(self, device: Optional[StatefulDevice]) -> None:
        """Set the target peer device for outbound operations.

        Args:
            device: Discovered device instance to select, or None to clear.
        """
        with self._lock:
            self.selected_device = device
        self.notify()

    def set_selected_files(self, file_paths: list[str]) -> None:
        """Set the file paths queued for outbound transmission.

        Args:
            file_paths: List of absolute local file paths.
        """
        with self._lock:
            self.selected_files = [p for p in file_paths if os.path.isfile(p)]
        self.notify()

    def clear_completed_transfers(self) -> None:
        """Remove completed, rejected, and cancelled transfers from history."""
        with self._lock:
            self.transfers = [
                item
                for item in self.transfers
                if item.status
                in (TransferStatus.PENDING, TransferStatus.TRANSFERRING)
            ]
        self.notify()

    def start_services(self) -> None:
        """Start the background async event loop and receiver services."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_background_loop,
                name="PyLanStateWorker",
                daemon=True,
            )
            self._thread.start()

    def stop_services(self) -> None:
        """Gracefully terminate background services and async worker loop."""
        self._stop_event.set()
        loop = self._loop
        if loop is not None and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                self._stop_receiver_coro(), loop
            )
            try:
                future.result(timeout=3.0)
            except Exception:
                pass
            loop.call_soon_threadsafe(loop.stop)
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
        with self._lock:
            self.is_receiver_running = False
            self.is_scanning = False
        self.notify()

    def _run_background_loop(self) -> None:
        """Worker thread entrypoint establishing an asyncio event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop

        # Start initial receiver daemon inside the worker loop
        loop.run_until_complete(self._start_receiver_coro())

        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(self._stop_receiver_coro())
            loop.close()
            self._loop = None

    async def _start_receiver_coro(self) -> None:
        """Coroutine initializing discovery engine and TCP receiver server."""
        try:
            ip, _ = get_active_interface_details()
            self.active_interface_ip = ip
        except Exception:
            self.active_interface_ip = "127.0.0.1"

        fingerprint = uuid.uuid4().hex[:12]
        self.engine = DiscoveryEngine(
            alias=self.settings.device_alias,
            fingerprint=fingerprint,
            tcp_port=self.settings.tcp_port,
            device_model=self.settings.device_model,
        )

        try:
            self._mc_transport = await self.engine.start_multicast_listener()
        except Exception as exc:
            logger.debug("Failed initializing multicast listener: %s", exc)

        try:
            self._server = await asyncio.start_server(
                self._handle_client_connection,
                host="0.0.0.0",
                port=self.settings.tcp_port,
            )
            with self._lock:
                self.is_receiver_running = True
        except Exception as exc:
            logger.error("Failed binding TCP server on port %d: %s",
                         self.settings.tcp_port, exc)
            with self._lock:
                self.is_receiver_running = False

        self._announce_task = asyncio.create_task(
            self._periodic_announce_task()
        )
        self.notify()

    async def _stop_receiver_coro(self) -> None:
        """Coroutine shutting down server, listeners, and announcements."""
        if self._announce_task is not None:
            self._announce_task.cancel()
            try:
                await self._announce_task
            except asyncio.CancelledError:
                pass
            self._announce_task = None

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        if self._mc_transport is not None:
            self._mc_transport.close()
            self._mc_transport = None

        with self._lock:
            self.is_receiver_running = False

    async def _periodic_announce_task(self) -> None:
        """Periodically broadcast multicast presence announcements."""
        while not self._stop_event.is_set():
            if self.engine is not None:
                try:
                    await self.engine.announce()
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.debug("Multicast announce error: %s", exc)
            try:
                await asyncio.sleep(2.0)
            except asyncio.CancelledError:
                break

    def trigger_discovery(self) -> None:
        """Initiate an asynchronous peer discovery sweep in the background."""
        loop = self._loop
        if loop is None or not loop.is_running():
            return
        with self._lock:
            if self.is_scanning:
                return
            self.is_scanning = True
        self.notify()
        asyncio.run_coroutine_threadsafe(self._discover_coro(), loop)

    async def _discover_coro(self) -> None:
        """Coroutine executing staged multicast and subnet discovery."""
        try:
            engine = self.engine or DiscoveryEngine(
                alias=self.settings.device_alias,
                fingerprint=uuid.uuid4().hex[:12],
                tcp_port=self.settings.tcp_port,
                device_model=self.settings.device_model,
            )
            devices = await engine.discover_staged(
                interface_ips=[self.active_interface_ip],
                grace_period=self.settings.discovery_timeout,
            )
            with self._lock:
                self.devices = list(devices)
        except Exception as exc:
            logger.debug("Discovery sweep encountered error: %s", exc)
        finally:
            with self._lock:
                self.is_scanning = False
            self.notify()

    async def _handle_client_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming TCP framed connection for discovery or transfer."""
        peer_name = "Unknown"
        try:
            peer_info = writer.get_extra_info("peername")
            if peer_info:
                peer_name = f"{peer_info[0]}:{peer_info[1]}"
        except Exception:
            pass

        try:
            header_bytes = await reader.readexactly(HEADER_SIZE)
            msg_type, length = unpack_header(header_bytes)
            body = await reader.readexactly(length)

            if msg_type == MSG_TYPE_PROBE_REQUEST:
                engine = self.engine or DiscoveryEngine(
                    alias=self.settings.device_alias,
                    fingerprint="receiver",
                    tcp_port=self.settings.tcp_port,
                )
                reply = pack_message(
                    MSG_TYPE_PROBE_RESPONSE, engine.get_announcement_payload()
                )
                writer.write(reply)
                await writer.drain()

            elif msg_type == MSG_TYPE_TRANSFER_REQUEST:
                await self._process_incoming_transfer(
                    reader, writer, body, peer_name
                )
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        except Exception as exc:
            logger.debug("Error handling client stream: %s", exc)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _process_incoming_transfer(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        initial_body: bytes,
        peer_address: str,
    ) -> None:
        """Negotiate and stream incoming file chunks with UI state updates."""
        import json

        meta: dict[str, Any] = {}
        try:
            meta = json.loads(initial_body.decode("utf-8"))
        except Exception:
            writer.write(
                pack_message(
                    MSG_TYPE_TRANSFER_REJECT, {"reason": "Malformed JSON"}
                )
            )
            await writer.drain()
            return

        raw_name = str(meta.get("file_name", "downloaded_file"))
        file_name = Path(raw_name).name
        file_size = int(meta.get("file_size", 0))
        sender_alias = str(meta.get("alias", peer_address))

        transfer_id = uuid.uuid4().hex[:8]
        out_dir = Path(self.settings.download_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        target_path = str(out_dir / file_name)

        item = TransferItem(
            id=transfer_id,
            direction=TransferDirection.RECEIVE,
            file_name=file_name,
            file_path=target_path,
            file_size=file_size,
            peer_alias=sender_alias,
            peer_address=peer_address,
            status=TransferStatus.PENDING,
        )

        with self._lock:
            self.transfers.insert(0, item)
        self.notify()

        # Approval handling
        accepted = False
        if self.settings.auto_accept:
            accepted = True
        else:
            decision_event = asyncio.Event()
            self._incoming_decisions[transfer_id] = decision_event
            try:
                await asyncio.wait_for(decision_event.wait(), timeout=60.0)
                accepted = self._incoming_results.pop(transfer_id, False)
            except asyncio.TimeoutError:
                accepted = False
            finally:
                self._incoming_decisions.pop(transfer_id, None)

        if not accepted:
            with self._lock:
                item.status = TransferStatus.REJECTED
                item.error_message = "Declined by user"
            self.notify()
            writer.write(
                pack_message(
                    MSG_TYPE_TRANSFER_REJECT,
                    {"reason": "Declined by receiver"},
                )
            )
            await writer.drain()
            return

        # Accepted - begin reception
        with self._lock:
            item.status = TransferStatus.TRANSFERRING
        self.notify()

        writer.write(pack_message(MSG_TYPE_TRANSFER_ACCEPT, {}))
        await writer.drain()

        received_bytes = 0
        last_time = time.time()
        last_bytes = 0

        try:
            with open(target_path, "wb") as f:
                while True:
                    h_bytes = await reader.readexactly(HEADER_SIZE)
                    m_type, l_len = unpack_header(h_bytes)
                    chunk_body = await reader.readexactly(l_len)

                    if m_type == MSG_TYPE_TRANSFER_CHUNK:
                        f.write(chunk_body)
                        received_bytes += len(chunk_body)
                        now = time.time()
                        dt = now - last_time
                        if dt >= 0.25:
                            speed = (received_bytes - last_bytes) / dt
                            with self._lock:
                                item.transferred_bytes = received_bytes
                                item.speed_bps = speed
                            self.notify()
                            last_time = now
                            last_bytes = received_bytes

                    elif m_type == MSG_TYPE_TRANSFER_COMPLETE:
                        break
                    else:
                        break

            with self._lock:
                item.transferred_bytes = received_bytes
                item.status = TransferStatus.COMPLETED
                item.speed_bps = 0.0
            self.notify()

        except Exception as exc:
            with self._lock:
                item.status = TransferStatus.FAILED
                item.error_message = str(exc)
            self.notify()

    def accept_incoming(self, transfer_id: str) -> None:
        """Signal acceptance of an incoming transfer awaiting approval.

        Args:
            transfer_id: Session identifier of the pending transfer.
        """
        loop = self._loop
        if loop is None:
            return
        self._incoming_results[transfer_id] = True
        evt = self._incoming_decisions.get(transfer_id)
        if evt:
            loop.call_soon_threadsafe(evt.set)

    def reject_incoming(self, transfer_id: str) -> None:
        """Signal rejection of an incoming transfer awaiting approval.

        Args:
            transfer_id: Session identifier of the pending transfer.
        """
        loop = self._loop
        if loop is None:
            return
        self._incoming_results[transfer_id] = False
        evt = self._incoming_decisions.get(transfer_id)
        if evt:
            loop.call_soon_threadsafe(evt.set)

    def queue_send(
        self,
        file_paths: list[str],
        target_device: Optional[StatefulDevice] = None,
        manual_target: Optional[str] = None,
    ) -> list[TransferItem]:
        """Queue and initiate outbound transfers to a target peer.

        Args:
            file_paths: Local files to transmit.
            target_device: Optional discovered device target.
            manual_target: Optional 'HOST:PORT' or 'HOST' fallback address.

        Returns:
            List of generated TransferItem objects.
        """
        host = "127.0.0.1"
        port = DEFAULT_TCP_PORT
        alias = "Peer"

        if target_device is not None:
            alias = getattr(target_device.device, "alias", "Peer")
            channel = getattr(target_device.device, "channel", None)
            if channel is not None:
                host = channel.host
                port = channel.port
        elif manual_target:
            if ":" in manual_target:
                parts = manual_target.split(":", 1)
                host = parts[0]
                try:
                    port = int(parts[1])
                except ValueError:
                    port = DEFAULT_TCP_PORT
            else:
                host = manual_target
            alias = host

        items: list[TransferItem] = []
        for path in file_paths:
            if not os.path.isfile(path):
                continue
            item = TransferItem(
                id=uuid.uuid4().hex[:8],
                direction=TransferDirection.SEND,
                file_name=os.path.basename(path),
                file_path=path,
                file_size=os.path.getsize(path),
                peer_alias=alias,
                peer_address=f"{host}:{port}",
                status=TransferStatus.PENDING,
            )
            items.append(item)
            with self._lock:
                self.transfers.insert(0, item)

        self.notify()

        loop = self._loop
        if loop is not None and loop.is_running():
            for item in items:
                asyncio.run_coroutine_threadsafe(
                    self._send_file_coro(item, host, port), loop
                )

        return items

    async def _send_file_coro(
        self, item: TransferItem, host: str, port: int
    ) -> None:
        """Transmit a file over TCP with live progress reporting."""
        with self._lock:
            item.status = TransferStatus.TRANSFERRING
        self.notify()

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=8.0
            )
        except Exception as exc:
            with self._lock:
                item.status = TransferStatus.FAILED
                item.error_message = f"Connection failed: {exc}"
            self.notify()
            return

        try:
            req = {
                "file_name": item.file_name,
                "file_size": item.file_size,
                "alias": self.settings.device_alias,
            }
            writer.write(pack_message(MSG_TYPE_TRANSFER_REQUEST, req))
            await writer.drain()

            h_bytes = await asyncio.wait_for(
                reader.readexactly(HEADER_SIZE), timeout=15.0
            )
            m_type, l_len = unpack_header(h_bytes)
            resp_body = await asyncio.wait_for(
                reader.readexactly(l_len), timeout=15.0
            )

            if m_type != MSG_TYPE_TRANSFER_ACCEPT:
                reason = "Rejected by recipient"
                if m_type == MSG_TYPE_TRANSFER_REJECT:
                    try:
                        import json

                        resp = json.loads(resp_body.decode("utf-8"))
                        reason = resp.get("reason", reason)
                    except Exception:
                        pass
                with self._lock:
                    item.status = TransferStatus.REJECTED
                    item.error_message = reason
                self.notify()
                return

            sent_bytes = 0
            last_time = time.time()
            last_bytes = 0

            with open(item.file_path, "rb") as f:
                while chunk := f.read(CHUNK_SIZE):
                    writer.write(pack_message(MSG_TYPE_TRANSFER_CHUNK, chunk))
                    await writer.drain()
                    sent_bytes += len(chunk)

                    now = time.time()
                    dt = now - last_time
                    if dt >= 0.25:
                        speed = (sent_bytes - last_bytes) / dt
                        with self._lock:
                            item.transferred_bytes = sent_bytes
                            item.speed_bps = speed
                        self.notify()
                        last_time = now
                        last_bytes = sent_bytes

            writer.write(pack_message(MSG_TYPE_TRANSFER_COMPLETE, {}))
            await writer.drain()

            with self._lock:
                item.transferred_bytes = item.file_size
                item.status = TransferStatus.COMPLETED
                item.speed_bps = 0.0
            self.notify()

        except Exception as exc:
            with self._lock:
                item.status = TransferStatus.FAILED
                item.error_message = str(exc)
            self.notify()
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
