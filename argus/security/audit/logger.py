import socket
import json
import os
import time
from argus.security.exceptions import AuditUnavailableError


class AuditLogger:
    """
    Fail-closed Unix socket client.
    Raises AuditUnavailableError (subclass of ArgusSecurityError) if socket unreachable.
    One connection per send() — no persistent connection pooling needed for audit event volume.
    """

    def __init__(self, socket_path: str):
        self._path = socket_path

    def send(self, event: dict) -> None:
        line = json.dumps(event) + "\n"
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self._path)
            sock.sendall(line.encode("utf-8"))
            sock.close()
        except (ConnectionRefusedError, FileNotFoundError, OSError) as exc:
            raise AuditUnavailableError(
                f"Audit logger socket unavailable at {self._path}"
            ) from exc

    @staticmethod
    def wait_for_socket(path: str, timeout_s: float = 2.0) -> None:
        """Poll until the socket file exists. Raises AuditUnavailableError on timeout."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if os.path.exists(path):
                return
            time.sleep(0.05)
        raise AuditUnavailableError(f"Logger socket never appeared at {path}")
