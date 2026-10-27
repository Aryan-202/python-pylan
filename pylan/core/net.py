"""Low-level network adapter inspection and ARP neighbor discovery."""

import ipaddress
import logging
import os
import re
import socket
import subprocess

import psutil

logger = logging.getLogger(__name__)


def get_default_interface_ip() -> str:
    """Find the primary outbound local IPv4 address."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def get_active_interface_details() -> tuple[str, str]:
    """Retrieve the primary active local IPv4 address and its netmask.

    Returns:
        A tuple of (ip_address, netmask_str). Falls back to /24 if the netmask
        cannot be determined from psutil interface records.
    """
    default_ip = get_default_interface_ip()
    if default_ip == "127.0.0.1":
        return "127.0.0.1", "255.255.255.0"

    try:
        interfaces = psutil.net_if_addrs()
        for _iface, addrs in interfaces.items():
            for addr in addrs:
                if (
                    addr.family == socket.AF_INET
                    and addr.address == default_ip
                ):
                    netmask = addr.netmask or "255.255.255.0"
                    return addr.address, netmask
    except Exception as exc:
        logger.debug("Failed querying psutil network interfaces: %s", exc)

    return default_ip, "255.255.255.0"


def get_arp_neighbors() -> set[str]:
    """Extract cached IPv4 addresses from the local OS ARP table."""
    neighbors: set[str] = set()
    ip_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

    try:
        if os.name == "nt":
            output = subprocess.check_output(
                ["arp", "-a"], stderr=subprocess.DEVNULL
            ).decode(errors="ignore")
        else:
            try:
                output = subprocess.check_output(
                    ["ip", "neighbor", "show"], stderr=subprocess.DEVNULL
                ).decode(errors="ignore")
            except Exception:
                output = subprocess.check_output(
                    ["arp", "-an"], stderr=subprocess.DEVNULL
                ).decode(errors="ignore")

        for match in ip_pattern.findall(output):
            try:
                ip_obj = ipaddress.ip_address(match)
                if not (
                    ip_obj.is_multicast
                    or ip_obj.is_loopback
                    or ip_obj.is_reserved
                ):
                    neighbors.add(str(ip_obj))
            except ValueError:
                continue
    except Exception as exc:
        logger.debug("Failed reading system ARP cache: %s", exc)

    return neighbors
