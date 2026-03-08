"""Tests for AuditDaemon subprocess lifecycle manager."""

import os
import socket

import pytest

from argus.security.audit.daemon import AuditDaemon
from argus.security.exceptions import AuditUnavailableError


@pytest.fixture
def daemon_paths(tmp_path):
    """Return (socket_path, log_path) under /tmp to avoid macOS 104-byte limit."""
    sock = f"/tmp/argus-daemon-test-{os.getpid()}.sock"
    log = str(tmp_path / "audit.jsonl")
    yield sock, log
    # Cleanup stale socket if test forgot to stop daemon
    try:
        os.unlink(sock)
    except FileNotFoundError:
        pass


class TestStartCreatesConnectableSocket:
    def test_socket_is_connectable_after_start(self, daemon_paths):
        sock_path, log_path = daemon_paths
        daemon = AuditDaemon(socket_path=sock_path, log_path=log_path)
        daemon.start()
        try:
            # Verify the socket is actually connectable
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(sock_path)
            s.close()
        finally:
            daemon.stop()

    def test_process_is_alive_after_start(self, daemon_paths):
        sock_path, log_path = daemon_paths
        daemon = AuditDaemon(socket_path=sock_path, log_path=log_path)
        daemon.start()
        try:
            assert daemon.is_alive() is True
            assert daemon.pid is not None
        finally:
            daemon.stop()


class TestStopTerminatesProcess:
    def test_stop_kills_process(self, daemon_paths):
        sock_path, log_path = daemon_paths
        daemon = AuditDaemon(socket_path=sock_path, log_path=log_path)
        daemon.start()
        assert daemon.pid is not None
        daemon.stop()
        assert daemon.is_alive() is False
        assert daemon.pid is None

    def test_socket_file_cleaned_up_after_stop(self, daemon_paths):
        sock_path, log_path = daemon_paths
        daemon = AuditDaemon(socket_path=sock_path, log_path=log_path)
        daemon.start()
        daemon.stop()
        assert not os.path.exists(sock_path)


class TestTimeoutRaisesError:
    def test_bogus_socket_path_raises(self, tmp_path):
        """A daemon that fails to start within timeout raises AuditUnavailableError."""
        # Use a socket path inside a non-existent directory so the process fails
        bad_sock = str(tmp_path / "no_such_dir" / "audit.sock")
        log_path = str(tmp_path / "audit.jsonl")
        daemon = AuditDaemon(socket_path=bad_sock, log_path=log_path, timeout_s=1.0)
        with pytest.raises(AuditUnavailableError):
            daemon.start()


class TestContextManager:
    def test_context_manager_starts_and_stops(self, daemon_paths):
        sock_path, log_path = daemon_paths
        with AuditDaemon(socket_path=sock_path, log_path=log_path) as daemon:
            assert daemon.is_alive() is True
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s.connect(sock_path)
            s.close()
        # After exiting context, process should be dead
        assert daemon.is_alive() is False


class TestStopIsIdempotent:
    def test_double_stop_does_not_raise(self, daemon_paths):
        sock_path, log_path = daemon_paths
        daemon = AuditDaemon(socket_path=sock_path, log_path=log_path)
        daemon.start()
        daemon.stop()
        daemon.stop()  # Second stop should not raise

    def test_stop_without_start_does_not_raise(self, daemon_paths):
        sock_path, log_path = daemon_paths
        daemon = AuditDaemon(socket_path=sock_path, log_path=log_path)
        daemon.stop()  # Never started — should not raise
