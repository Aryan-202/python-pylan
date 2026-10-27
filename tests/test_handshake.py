"""Unit tests for the synchronous HandshakeManager framing protocol.

This module validates that HandshakeManager correctly frames and serializes
JSON payloads over stream sockets, handles fragmented chunk reception,
validates payload boundaries against untrusted input, and handles error paths
such as premature socket closure.
"""

import json
import struct
import unittest
from unittest.mock import Mock

from pylan.core.handshake import (
    DEFAULT_MAX_PAYLOAD_SIZE,
    HandshakeManager,
)


class TestHandshakeManager(unittest.TestCase):
    """Test suite targeting synchronous length-prefixed handshake framing."""

    def setUp(self) -> None:
        """Create a mock socket and handshake manager for each test."""
        self.mock_sock = Mock()
        self.manager = HandshakeManager(self.mock_sock)

    def test_send_handshake_success(self) -> None:
        """Verify that a valid dictionary is serialized and sent with header.
        """
        payload = {"device_id": "test-device", "version": "1.0"}
        expected_json = json.dumps(payload).encode("utf-8")
        expected_header = struct.pack(">I", len(expected_json))
        expected_frame = expected_header + expected_json

        self.manager.send_handshake(payload)

        self.mock_sock.sendall.assert_called_once_with(expected_frame)

    def test_send_handshake_invalid_type_raises_type_error(self) -> None:
        """Verify that non-dictionary payloads raise a TypeError."""
        with self.assertRaises(TypeError):
            self.manager.send_handshake(["not", "a", "dict"])  # type: ignore

        with self.assertRaises(TypeError):
            self.manager.send_handshake("string_payload")  # type: ignore

        self.mock_sock.sendall.assert_not_called()

    def test_receive_handshake_success(self) -> None:
        """Verify reading a complete framed JSON handshake."""
        payload = {"status": "ready", "port": 44000}
        raw_body = json.dumps(payload).encode("utf-8")
        header = struct.pack(">I", len(raw_body))

        self.mock_sock.recv.side_effect = [header, raw_body]

        result = self.manager.receive_handshake()

        self.assertEqual(result, payload)

    def test_receive_handshake_fragmented_chunks(self) -> None:
        """Verify reading a payload that arrives across multiple TCP chunks."""
        payload = {"data": "A" * 100}
        raw_body = json.dumps(payload).encode("utf-8")
        header = struct.pack(">I", len(raw_body))

        chunks = [
            header[:2],
            header[2:],
            raw_body[:20],
            raw_body[20:50],
            raw_body[50:],
        ]
        self.mock_sock.recv.side_effect = chunks

        result = self.manager.receive_handshake()

        self.assertEqual(result, payload)

    def test_receive_handshake_premature_close_in_header(self) -> None:
        """Verify ConnectionResetError when connection closes during header."""
        self.mock_sock.recv.return_value = b""

        with self.assertRaises(ConnectionResetError):
            self.manager.receive_handshake()

    def test_receive_handshake_premature_close_in_body(self) -> None:
        """Verify ConnectionResetError when connection closes during body."""
        header = struct.pack(">I", 50)
        self.mock_sock.recv.side_effect = [header, b"1234567890", b""]

        with self.assertRaises(ConnectionResetError):
            self.manager.receive_handshake()

    def test_receive_handshake_exceeds_max_payload_size(self) -> None:
        """Verify ValueError when declared payload exceeds maximum bound."""
        oversized = DEFAULT_MAX_PAYLOAD_SIZE + 1
        header = struct.pack(">I", oversized)
        self.mock_sock.recv.return_value = header

        with self.assertRaises(ValueError) as ctx:
            self.manager.receive_handshake()

        self.assertIn("exceeds maximum allowed size", str(ctx.exception))

    def test_receive_handshake_zero_length_raises_value_error(self) -> None:
        """Verify ValueError when declared payload length is zero."""
        header = struct.pack(">I", 0)
        self.mock_sock.recv.return_value = header

        with self.assertRaises(ValueError):
            self.manager.receive_handshake()

    def test_receive_handshake_non_dict_json_raises_value_error(self) -> None:
        """Verify ValueError when decoded JSON is not a dictionary."""
        raw_body = json.dumps(["element1", "element2"]).encode("utf-8")
        header = struct.pack(">I", len(raw_body))
        self.mock_sock.recv.side_effect = [header, raw_body]

        with self.assertRaises(ValueError) as ctx:
            self.manager.receive_handshake()

        self.assertIn("Expected JSON object", str(ctx.exception))

    def test_recv_exact_zero_bytes(self) -> None:
        """Verify that requesting zero bytes returns empty bytes."""
        result = self.manager._recv_exact(0)
        self.assertEqual(result, b"")
        self.mock_sock.recv.assert_not_called()

    def test_recv_exact_negative_bytes_raises_value_error(self) -> None:
        """Verify that negative byte requests raise ValueError."""
        with self.assertRaises(ValueError):
            self.manager._recv_exact(-5)

    def test_init_invalid_max_payload_size_raises_value_error(self) -> None:
        """Verify ValueError when max_payload_size is non-positive."""
        with self.assertRaises(ValueError):
            HandshakeManager(self.mock_sock, max_payload_size=0)

        with self.assertRaises(ValueError):
            HandshakeManager(self.mock_sock, max_payload_size=-100)


if __name__ == "__main__":
    unittest.main()
