"""
Network blocker module with the aim to implement a complete
restriction in network access across the entire project, modules
and all dependencies.

IMPORTANT: Must be imported and enabled BEFORE ANY IMPORTS that use networking.

Ideally, this is placed as one of the first things to run in
the project's entry point.
"""

import logging
import socket
import sys

_original_socket = socket.socket
_original_create_connection = socket.create_connection
_network_blocked = False

log = logging.getLogger("NETBLOCK")


class NetworkBlockedError(RuntimeError):
    """
    Raised when network access is attempted while blocking is in effect.
    """

    def __init__(self, operation="socket"):
        super().__init__(f"Network access is disabled (--no-conn flag is active). " f"Attempted operation: {operation}")


class BlockedSocket:
    """
    Replacement for socket.socket that raises an error on instantiation
    MUST be a class (not a function) so ssl.SSLSocket can inherit from it
    """

    def __init__(self, *args, **kwargs):
        raise NetworkBlockedError("socket.socket")

    def __call__(self, *args, **kwargs):
        raise NetworkBlockedError("socket.socket")

    # Seems needed so ssl module doesn't break in import
    def __getattr__(self, name):
        raise NetworkBlockedError(f"socket.socket.{name}")


def _block_operation(operation_name):
    """Factory function to create blocking functions for various operations"""

    def blocker(*args, **kwargs):
        log.error(f"Blocked: {operation_name}")
        raise NetworkBlockedError(operation_name)

    return blocker


def enable_network_blocking():
    """
    Enable comprehensive network blocking by monkey-patching the socket
    module.

    Must be called before any networking library is imported.
    """

    global _network_blocked

    if _network_blocked:
        return  # Already blocked

    # Block basic connections
    socket.socket = BlockedSocket

    # Block getaddrinfo (DNS lookups)
    socket.create_connection = _block_operation("socket.create_connection")
    socket.getaddrinfo = _block_operation("socket.getaddrinfo")
    socket.gethostbyname = _block_operation("socket.gethostbyname")
    socket.gethostbyaddr = _block_operation("socket.gethostbyaddr")

    _network_blocked = True
    log.info(f"Network access has been disabled.", file=sys.stderr)


def disable_network_blocking():
    """
    Restore normal network access
    """

    global _network_blocked

    if not _network_blocked:
        return

    socket.socket = _original_socket
    socket.create_connection = _original_create_connection

    _network_blocked = False
    log.info(f"Network access has been restored.", file=sys.stderr)


def is_blocked():
    return _network_blocked


def block_imported_modules():
    """
    Attempt to block network access in already imported modules.

    This should be called after imports.
    """

    # Block urllib
    if "urllib.request" in sys.modules:
        import urllib.request

        urllib.request.urlopen = _block_operation("urllib.request.urlopen")

    # Block http.client
    if "http.client" in sys.modules:
        import http.client

        http.client.HTTPConnection = _block_operation("http.client.HTTPConnection")
        http.client.HTTPSConnection = _block_operation("http.client.HTTPSConnection")

    # Block requests if already imported
    if "requests" in sys.modules:
        import requests

        requests.get = _block_operation("requests.get")
        requests.post = _block_operation("requests.post")
        requests.put = _block_operation("requests.put")
        requests.delete = _block_operation("requests.delete")
        requests.patch = _block_operation("requests.patch")
        requests.head = _block_operation("requests.head")
        requests.options = _block_operation("requests.options")
        requests.request = _block_operation("requests.request")

    # Block ssl if already imported
    if "ssl" in sys.modules:
        import ssl

        _original_wrap_socket = ssl.SSLContext.wrap_socket
        ssl.SSLContext.wrap_socket = _block_operation("ssl.SSLContext.wrap_socket")
