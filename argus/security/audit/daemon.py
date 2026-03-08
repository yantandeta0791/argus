"""
AuditDaemon — subprocess lifecycle manager for the audit log process.

Spawns ``python -m argus.security.audit.log_process`` as a child process,
waits until the Unix socket is connectable, and provides clean shutdown.

Uses subprocess.Popen (NOT multiprocessing.Process) because fork breaks asyncio.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from typing import Self

from argus.security.exceptions import AuditUnavailableError


class AuditDaemon:
    """Manage the audit log subprocess lifecycle."""

    def __init__(
        self,
        socket_path: str,
        log_path: str,
        timeout_s: float = 5.0,
    ) -> None:
        self._socket_path = socket_path
        self._log_path = log_path
        self._timeout_s = timeout_s
        self._proc: subprocess.Popen | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Spawn the audit log process and block until the socket is connectable."""
        self._proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "argus.security.audit.log_process",
                self._socket_path,
                self._log_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._wait_for_socket_ready()

    def stop(self) -> None:
        """Terminate the audit process. Idempotent — safe to call multiple times."""
        if self._proc is None:
            return
        try:
            self._proc.terminate()
            self._proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=2)
        except OSError:
            pass  # already dead
        finally:
            self._proc = None
            # Clean up stale socket file
            try:
                os.unlink(self._socket_path)
            except FileNotFoundError:
                pass

    def is_alive(self) -> bool:
        """Return True if the subprocess is still running."""
        if self._proc is None:
            return False
        return self._proc.poll() is None

    @property
    def pid(self) -> int | None:
        """Return the PID of the subprocess, or None if not running."""
        if self._proc is None:
            return None
        return self._proc.pid

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        self.stop()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _wait_for_socket_ready(self) -> None:
        """Poll with socket.connect() until the daemon socket is accepting connections.

        Uses an actual connection probe rather than os.path.exists() to avoid
        a race condition where the file exists but the server is not yet
        listening.
        """
        deadline = time.monotonic() + self._timeout_s
        while time.monotonic() < deadline:
            # If the child died, fail immediately instead of waiting.
            if self._proc is not None and self._proc.poll() is not None:
                raise AuditUnavailableError(
                    f"Audit process exited with code {self._proc.returncode} "
                    f"before socket was ready at {self._socket_path}"
                )
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(self._socket_path)
                sock.close()
                return
            except (ConnectionRefusedError, FileNotFoundError, OSError):
                time.sleep(0.05)
        raise AuditUnavailableError(
            f"Audit socket not ready after {self._timeout_s}s at {self._socket_path}"
        )
