# TODO.md — Things need to be fixed for PyLan v0.0.3

## High Priority

- [ ] **Package & Dependency Decoupling (`pyproject.toml`)**
  - [ ] Strip GUI (`flet`) and CLI (`click`, `rich`) dependencies out of core runtime requirements.
  - [ ] Set up optional installation targets:
    - [ ] `pip install pylan` (Core engine + lightweight SDK only)
    - [ ] `pip install "pylan[cli]"` (Command-line tool)
    - [ ] `pip install "pylan[ui]"` (Desktop graphical interface)
    - [ ] `pip install "pylan[all]"` (Full bundle)
  - [ ] Implement graceful import guards in entrypoints that suggest the missing extra if uninstalled.

- [ ] **Core Independence & Callback Extraction**
  - [ ] Remove all UI and CLI imports from `pylan/core/`.
  - [ ] Abstract progress tracking into standard callback protocols (`Callable[[int, int], None]`) instead of coupling to Rich or Flet UI widgets.
  - [ ] Decouple `pylan/cli/` and `pylan/ui/` so both act purely as independent presentation layers consuming the public SDK.

---

## Exception Hierarchy (`pylan/errors/`)

- [ ] **Define Base Exception**
  - [ ] `base.py`: Root exception for all PyLan-related failures.

- [ ] **Discovery Exceptions (`pylan/errors/discovery.py`)**
  - [ ] `DiscoveryError`: Base class for peer discovery failures.
  - [ ] `PeerNotFoundError`: Raised when the target peer name or ID cannot be discovered on the subnet.
  - [ ] `DiscoveryTimeoutError`: Raised when discovery scan expires without finding devices.
  - [ ] `NetworkInterfaceError`: Raised when bound interface or multicast socket is unavailable.
  - [ ] `InvalidServiceRecordError`: Raised when mDNS/multicast packet contains malformed peer payload.

- [ ] **Connection & Handshake Exceptions (`pylan/errors/connection.py`)**
  - [ ] `PylanConnectionError`: Base class for transport connection errors.
  - [ ] `PeerUnreachableError`: Raised when the target IP/port is unreachable or drops socket connection.
  - [ ] `HandshakeError`: Base class for handshake phase errors.
  - [ ] `HandshakeRejectedError`: Raised when the receiver explicitly declines incoming transfer.
  - [ ] `HandshakeTimeoutError`: Raised when peer does not respond to the handshake proposal within timeout.
  - [ ] `ProtocolVersionMismatchError`: Raised when client and peer use incompatible protocol versions.
  - [ ] `AuthenticationFailedError`: Raised if pre-shared key, PIN, or peer token validation fails.

- [ ] **Transfer & Payload Exceptions (`pylan/errors/transfer.py`)**
  - [ ] `TransferError`: Base class for file streaming errors.
  - [ ] `TransferFailedError`: Generic failure during chunk streaming or socket writing.
  - [ ] `TransferAbortedError`: Raised when transfer is aborted mid-stream by peer or local user.
  - [ ] `TransferTimeoutError`: Raised when data stream stalls past read/write timeout.
  - [ ] `ChecksumMismatchError`: Raised when file integrity check fails after transfer completes.
  - [ ] `InsufficientStorageError`: Raised by receiver if target disk has inadequate free space.
  - [ ] `FileAccessError`: Base class for local file system permission or path errors.
  - [ ] `TransportFileNotFoundError`: Raised when requested payload does not exist on disk.
  - [ ] `FileReadError`: Raised when local sender fails to read chunks from disk.
  - [ ] `FileWriteError`: Raised when receiver fails to write chunks to disk.

- [ ] **Protocol & Framing Exceptions (`pylan/errors/protocol.py`)**
  - [ ] `ProtocolError`: Base class for packet serialization and framing errors.
  - [ ] `InvalidPacketError`: Raised when receiving corrupted or malformed packet header/body.
  - [ ] `PacketHeaderTooShortError`: Raised when socket read delivers incomplete struct header.
  - [ ] `MagicBytesMismatchError`: Raised when packet header magic header does not match expected signature.
  - [ ] `PayloadTooLargeError`: Raised when incoming frame size exceeds protocol buffer limit.

- [ ] **Integrate Exceptions Across Modules**
  - [ ] Export all exception classes through `pylan/errors/__init__.py`.
  - [ ] Re-export top-level exceptions in `pylan/__init__.py` for public SDK consumption.
  - [ ] Audit `pylan/core/discovery.py`, `pylan/core/handshake.py`, and `pylan/core/protocol.py` to replace generic exceptions with domain-specific classes.

---

## Public Client API

- [ ] **Design High-Level Interface (`pylan/client.py` & `pylan/__init__.py`)**
  - [ ] Implement sync wrapper methods:
    - [ ] `pylan.send_file(file_path: Path | str, peer_name: str | None = None, peer_ip: str | None = None, port: int = ..., timeout: float = 30.0, on_progress: Callable | None = None) -> TransferResult`
    - [ ] `pylan.receive_file(save_dir: Path | str = "./downloads", accept_all: bool = False, timeout: float | None = None, on_progress: Callable | None = None) -> TransferResult`
    - [ ] `pylan.scan(timeout: float = 3.0) -> list[Peer]`
  - [ ] Implement object-oriented client class:
    - [ ] `PyLanClient` (Context manager supporting `.scan()`, `.connect()`, `.send()`, `.receive()`).
    - [ ] Event callbacks: `on_peer_found`, `on_handshake_request`, `on_progress`, `on_complete`.
  - [ ] Implement async equivalents (`AsyncPyLanClient`) for event loops, UI runtimes, and web services.

---

## Verification & Tests

- [ ] Add isolated unit tests in `tests/test_errors.py` ensuring all custom exceptions inherit from `PyLanError`.
- [ ] Add packaging tests in `tests/test_packaging.py` validating `import pylan` runs in headless environments without `flet` or `click`.
- [ ] Add integration tests in `tests/test_public_api.py` validating `pylan.send_file` and `pylan.scan` error states.
