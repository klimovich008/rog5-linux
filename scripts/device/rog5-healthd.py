#!/usr/bin/env python3
"""Minimal credential-free health endpoint for the ROG5 server MVP."""

from __future__ import annotations

import argparse
import http.server
import ipaddress
import socket
import threading


HEALTH_BODY = b'{"service":"rog5-healthd","status":"ok","version":1}\n'
NOT_FOUND_BODY = b"not found\n"


class HealthHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "rog5-healthd/1"
    sys_version = ""
    # StreamRequestHandler applies this to accepted sockets, including header
    # reads. This is an idle I/O limit, not a total request-duration deadline.
    timeout = 1.0

    def setup(self) -> None:
        super().setup()
        self._expired = False
        # An idle socket timeout alone is renewed by every trickled byte.
        # Bound the whole request, not just idle gaps between bytes.
        self._deadline = threading.Timer(self.timeout, self._expire_request)
        self._deadline.daemon = True
        self._deadline.start()

    def _expire_request(self) -> None:
        self._expired = True
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def finish(self) -> None:
        try:
            super().finish()
        finally:
            self._deadline.cancel()

    def do_GET(self) -> None:  # noqa: N802 - HTTP method name
        if self.path != "/healthz":
            self._reply(404, NOT_FOUND_BODY, "text/plain; charset=utf-8")
            return
        self._reply(200, HEALTH_BODY, "application/json")

    def _reply(self, status: int, body: bytes, content_type: str) -> None:
        if self._expired:
            self.close_connection = True
            return
        # This tiny endpoint has no reason to retain connections.
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


class HealthServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True
    request_queue_size = 16
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        self._clients = threading.BoundedSemaphore(4)
        super().__init__(*args, **kwargs)

    def process_request(self, request, address):
        if not self._clients.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self._clients.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self._clients.release()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8787)
    arguments = parser.parse_args()
    try:
        ipaddress.IPv4Address(arguments.bind)
    except ipaddress.AddressValueError as error:
        parser.error(f"invalid IPv4 bind address: {error}")
    if not 0 <= arguments.port <= 65535:
        parser.error("port must be between 0 and 65535")
    return arguments


def main() -> None:
    arguments = parse_arguments()
    with HealthServer((arguments.bind, arguments.port), HealthHandler) as server:
        actual_port = int(server.server_address[1])
        print(f"READY bind={arguments.bind} port={actual_port}", flush=True)
        server.serve_forever(poll_interval=0.5)


if __name__ == "__main__":
    main()
