"""
Standalone audit logger process.
Usage: python -m argus.security.audit.log_process <socket_path> <log_file>

Spawned automatically by Argus at run start.
Runs until the parent process terminates (SIGTERM or SIGINT).
"""
import asyncio
import json
import os
import sys
from argus.security.audit.chain import build_entry, GENESIS_HASH


async def handle_client(reader, writer, log_file: str, state: dict) -> None:
    try:
        data = await reader.readline()
        if data:
            event = json.loads(data.decode("utf-8"))
            line, new_hash = build_entry(event, state["prev_hash"])
            state["prev_hash"] = new_hash
            with open(log_file, "a") as f:
                f.write(line + "\n")
                f.flush()  # ensure data is written to disk immediately
    except Exception:
        pass  # Logger must never crash on malformed input
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def run_logger(socket_path: str, log_file: str) -> None:
    # Remove stale socket file from prior crash before binding
    if os.path.exists(socket_path):
        os.unlink(socket_path)

    state = {"prev_hash": GENESIS_HASH}
    server = await asyncio.start_unix_server(
        lambda r, w: handle_client(r, w, log_file, state),
        path=socket_path,
    )
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <socket_path> <log_file>", file=sys.stderr)
        sys.exit(1)
    socket_path, log_file = sys.argv[1], sys.argv[2]
    asyncio.run(run_logger(socket_path, log_file))
