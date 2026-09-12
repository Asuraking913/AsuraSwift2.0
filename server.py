"""Receiving end of an AsuraSwift transfer.

The listener binds once with SO_REUSEADDR and keeps the accepted connection for
the whole session, so there is no longer a window between messages where the
sender can connect into a dying backlog and lose data silently.

Binding to 0.0.0.0 means the machine's own address never has to be typed or
guessed -- it accepts on whichever interface the peer can actually reach.
"""
import os
import socket

from protocol import (CHUNK, MAGIC, DEFAULT_PORT, recv_exactly, recv_header,
                      safe_join, send_header)


def listen(port=DEFAULT_PORT, host="", backlog=1):
    """Open a listening socket on every interface.

    SO_REUSEADDR matters: without it a rebind while a previous connection sits
    in TIME_WAIT fails, and the old code swallowed that error and then let
    listen() pick a random port nobody was dialling.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(backlog)
    return server


def receive_session(dest, server=None, port=DEFAULT_PORT, on_progress=None,
                    on_status=None, on_peer=None, cancel=None, timeout=None):
    """Accept one transfer and write it beneath `dest`.

    Pass an existing `server` socket to reuse a listener across transfers.
    on_progress(received_bytes, total_bytes, current_name) reports movement.
    Returns (files_received, bytes_received).
    """
    owns_server = server is None
    if owns_server:
        server = listen(port)
    if timeout is not None:
        server.settimeout(timeout)

    if on_status:
        on_status("Waiting for a sender…")

    conn, addr = server.accept()
    conn.settimeout(60.0)
    received = 0
    count = 0
    try:
        if on_peer:
            on_peer(addr[0])
        if on_status:
            on_status(f"Connected to {addr[0]}")

        if recv_exactly(conn, len(MAGIC)) != MAGIC:
            raise ConnectionError("peer is not speaking the AsuraSwift protocol")

        manifest = recv_header(conn)
        if manifest.get("type") != "manifest":
            raise ConnectionError(f"expected a manifest, got {manifest}")

        total = int(manifest.get("total_bytes", 0))
        expected = int(manifest.get("total_files", 0))

        # Build the whole tree up front. No round trip per folder, so no race.
        os.makedirs(dest, exist_ok=True)
        for rel in manifest.get("dirs", []):
            os.makedirs(safe_join(dest, rel), exist_ok=True)

        send_header(conn, {"type": "ready"})
        if on_status:
            on_status(f"Receiving {expected} file(s)…")
        if on_progress:
            on_progress(0, total, "")

        while True:
            if cancel is not None and cancel.is_set():
                raise InterruptedError("transfer cancelled")

            header = recv_header(conn)
            kind = header.get("type")

            if kind == "done":
                send_header(conn, {"type": "complete", "files": count})
                break
            if kind == "abort":
                raise InterruptedError("sender cancelled the transfer")
            if kind != "file":
                raise ConnectionError(f"unexpected message: {header}")

            target = safe_join(dest, header["path"])
            os.makedirs(os.path.dirname(target), exist_ok=True)
            remaining = int(header["size"])
            with open(target, "wb") as handle:
                while remaining:
                    block = recv_exactly(conn, min(CHUNK, remaining))
                    handle.write(block)
                    remaining -= len(block)
                    received += len(block)
                    if on_progress:
                        on_progress(received, total, header["path"])
            count += 1
    finally:
        conn.close()
        if owns_server:
            server.close()

    if on_status:
        on_status(f"Received {count} file(s).")
    return count, received
