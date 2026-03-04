import pytest


def test_hash_chain_integrity(tmp_path):
    from argus.security.audit.chain import build_entry, GENESIS_HASH
    event1 = {"type": "tool_call", "tool": "read_file"}
    event2 = {"type": "tool_output", "tool": "read_file"}
    line1, hash1 = build_entry(event1, GENESIS_HASH)
    line2, hash2 = build_entry(event2, hash1)
    assert hash1 != GENESIS_HASH
    assert hash2 != hash1
    assert len(hash1) == 64  # SHA-256 hex digest


def test_tamper_detection(tmp_path):
    from argus.security.audit.chain import build_entry, verify_chain, GENESIS_HASH
    log_file = tmp_path / "audit.jsonl"
    event = {"type": "tool_call", "tool": "read_file"}
    event2 = {"type": "tool_output", "tool": "read_file"}
    line1, hash1 = build_entry(event, GENESIS_HASH)
    line2, hash2 = build_entry(event2, hash1)
    # Write a valid two-entry chain
    log_file.write_text(line1 + "\n" + line2 + "\n")
    # Tamper: replace first entry content (but keep prev_hash=GENESIS_HASH)
    tampered_line1 = '{"prev_hash":"' + "0" * 64 + '","type":"tampered","tool":"write_file"}'
    log_file.write_text(tampered_line1 + "\n" + line2 + "\n")
    broken = verify_chain(str(log_file))
    assert len(broken) > 0


def test_fail_closed(tmp_socket_path):
    from argus.security.audit.logger import AuditLogger
    from argus.security.exceptions import AuditUnavailableError
    logger = AuditLogger(socket_path="/tmp/argus-nonexistent-99999.sock")
    with pytest.raises(AuditUnavailableError):
        logger.send({"type": "test"})


@pytest.mark.asyncio
async def test_separate_process(tmp_socket_path, tmp_path):
    import subprocess
    import sys
    import time
    from argus.security.audit.logger import AuditLogger
    log_file = str(tmp_path / "audit.jsonl")
    proc = subprocess.Popen(
        [sys.executable, "-m", "argus.security.audit.log_process", tmp_socket_path, log_file],
        env={"PATH": "/usr/bin:/bin", "HOME": "/tmp", "PYTHONPATH": str(__import__("pathlib").Path.cwd())}
    )
    try:
        AuditLogger.wait_for_socket(tmp_socket_path, timeout_s=3.0)
        logger = AuditLogger(tmp_socket_path)
        logger.send({"type": "test_event", "value": "hello"})
        time.sleep(0.1)
        content = __import__("pathlib").Path(log_file).read_text()
        assert "test_event" in content
    finally:
        proc.terminate()
        proc.wait()
