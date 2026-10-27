"""Synchronous length-prefixed JSON handshake framing manager.

This module provides the :class:`HandshakeManager` for transmitting and
receiving length-prefixed JSON payloads over synchronous TCP sockets.
Messages are framed using a fixed 4-byte big-endian unsigned integer header
that specifies the length of the upcoming UTF-8 encoded JSON body.
"""

import json
import socket
import struct
from typing import Any

DEFAULT_MAX_PAYLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB limit


class HandshakeManager:
    """Manages synchronous JSON message exchanges over a stream socket.

    Frames outgoing messages with a 4-byte big-endian length prefix and
    reads framed responses from incoming socket streams with explicit buffer
    bounds to prevent unbounded memory allocation from untrusted input.

    Attributes:
        sock: The underlying connected stream socket.
        max_payload_size: Maximum acceptable payload size in bytes.
    """

    HEADER_STRUCT: str = ">I"

    def __init__(
        self,
        sock: socket.socket,
        max_payload_size: int = DEFAULT_MAX_PAYLOAD_SIZE,
    ) -> None:
        """Initialize the handshake manager with an active socket.

        Args:
            sock: A connected :class:`socket.socket` instance.
            max_payload_size: Maximum incoming payload size in bytes.
                Defaults to 10 MB.

        Raises:
            ValueError: If `max_payload_size` is not positive.
        """
        if max_payload_size <= 0:
            raise ValueError("max_payload_size must be positive.")
        self.sock = sock
        self.max_payload_size = max_payload_size

    def send_handshake(self, payload: dict[str, Any]) -> None:
        """Serialize and send a JSON payload with a length prefix.

        Encodes the dictionary to UTF-8 JSON, prepends a 4-byte big-endian
        length header, and transmits the entire frame via the socket.

        Args:
            payload: A JSON-serializable dictionary to transmit.

        Raises:
            TypeError: If `payload` is not a dictionary.
            OSError: If a network transmission error occurs.
        """
        if not isinstance(payload, dict):
            raise TypeError(
                f"Payload must be a dict, got {type(payload).__name__}"
            )
        raw_data = json.dumps(payload).encode("utf-8")
        header = struct.pack(self.HEADER_STRUCT, len(raw_data))
        self.sock.sendall(header + raw_data)

    def receive_handshake(self) -> dict[str, Any]:
        """Receive and decode a length-prefixed JSON payload.

        Reads the exact 4-byte length prefix, verifies that the payload
        size does not exceed `max_payload_size`, collects the declared byte
        count, and deserializes the JSON body into a dictionary.

        Returns:
            The parsed JSON dictionary received from the remote peer.

        Raises:
            ConnectionResetError: If the connection is closed prematurely.
            ValueError: If the declared payload size is invalid, exceeds
                `max_payload_size`, or the decoded JSON is not a dictionary.
            UnicodeDecodeError: If payload bytes are not valid UTF-8.
            json.JSONDecodeError: If payload bytes cannot be parsed as JSON.
            OSError: If a network read error occurs.
        """
        header_size = struct.calcsize(self.HEADER_STRUCT)
        raw_length = self._recv_exact(header_size)
        length = struct.unpack(self.HEADER_STRUCT, raw_length)[0]

        if length <= 0:
            raise ValueError("Handshake payload length must be positive.")

        if length > self.max_payload_size:
            raise ValueError(
                f"Payload length {length} exceeds maximum allowed size "
                f"({self.max_payload_size} bytes)."
            )

        raw_data = self._recv_exact(length)
        parsed: Any = json.loads(raw_data.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError(
                f"Expected JSON object (dict), got {type(parsed).__name__}"
            )
        return parsed

    def _recv_exact(self, num_bytes: int) -> bytes:
        """Read an exact number of bytes from the underlying socket.

        Loops until all requested bytes are gathered in chunks or raises
        an error if the peer terminates the connection before completion.

        Args:
            num_bytes: The exact number of bytes to receive.

        Returns:
            A bytes object of exact length `num_bytes`.

        Raises:
            ValueError: If `num_bytes` is negative.
            ConnectionResetError: If the socket closes before `num_bytes`
                are read.
            OSError: If a network error occurs during socket read.
        """
        if num_bytes < 0:
            raise ValueError("num_bytes cannot be negative.")
        if num_bytes == 0:
            return b""

        chunks: list[bytes] = []
        bytes_left = num_bytes
        while bytes_left > 0:
            chunk = self.sock.recv(min(bytes_left, 4096))
            if not chunk:
                raise ConnectionResetError(
                    "Connection closed before reading complete "
                    "handshake frame."
                )
            chunks.append(chunk)
            bytes_left -= len(chunk)
        return b"".join(chunks)
