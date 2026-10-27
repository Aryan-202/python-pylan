"""Core networking, framing, and discovery primitives for PyLan.

This package provides low-level network abstractions, binary framing
protocols, peer discovery mechanisms, and device state management for local
area network coordination and file transfer.

Modules:
    discovery: UDP multicast announcements, TCP probing, and subnet sweeps.
    handshake: Synchronous length-prefixed socket handshake manager.
    models: Data models representing network channels, devices, and stores.
    net: Network adapter inspection and ARP neighbor table queries.
    protocol: Fixed-header binary message framing and serialization.
"""

from pylan.core.discovery import (
    DEFAULT_DISCOVERY_TIMEOUT,
    DEFAULT_MULTICAST_GROUP,
    DEFAULT_MULTICAST_PORT,
    DiscoveryEngine,
    DiscoveryProtocol,
)
from pylan.core.handshake import (
    DEFAULT_MAX_PAYLOAD_SIZE,
    HandshakeManager,
)
from pylan.core.models import (
    DeviceStore,
    DiscoveredDevice,
    HttpChannel,
    ProtocolType,
    StatefulDevice,
)
from pylan.core.net import (
    get_active_interface_details,
    get_arp_neighbors,
    get_default_interface_ip,
)
from pylan.core.protocol import (
    HEADER_FORMAT,
    HEADER_SIZE,
    MSG_TYPE_TRANSFER_ACCEPT,
    MSG_TYPE_TRANSFER_CHUNK,
    MSG_TYPE_TRANSFER_COMPLETE,
    MSG_TYPE_TRANSFER_REJECT,
    MSG_TYPE_TRANSFER_REQUEST,
    pack_message,
    unpack_header,
)

__all__: list[str] = [
    "DEFAULT_DISCOVERY_TIMEOUT",
    "DEFAULT_MAX_PAYLOAD_SIZE",
    "DEFAULT_MULTICAST_GROUP",
    "DEFAULT_MULTICAST_PORT",
    "DeviceStore",
    "DiscoveredDevice",
    "DiscoveryEngine",
    "DiscoveryProtocol",
    "HEADER_FORMAT",
    "HEADER_SIZE",
    "HandshakeManager",
    "HttpChannel",
    "MSG_TYPE_TRANSFER_ACCEPT",
    "MSG_TYPE_TRANSFER_CHUNK",
    "MSG_TYPE_TRANSFER_COMPLETE",
    "MSG_TYPE_TRANSFER_REJECT",
    "MSG_TYPE_TRANSFER_REQUEST",
    "ProtocolType",
    "StatefulDevice",
    "get_active_interface_details",
    "get_arp_neighbors",
    "get_default_interface_ip",
    "pack_message",
    "unpack_header",
]
