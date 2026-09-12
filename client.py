"""Sending end of an AsuraSwift transfer.

A whole selection (files, folders, or both) travels over a single connection
that stays open for the entire session. The manifest goes first so the receiver
can build the directory tree in one step and both ends know the byte total up
front, which is what makes an honest progress bar possible.
"""
import os
import socket
import time

from protocol import (CHUNK, MAGIC, build_manifest, recv_header, send_header)


def connect(host, port, timeout=20.0, on_status=None):
    """Dial the receiver, retrying until `timeout` elapses.

    The old code looped on connect() forever with no way out; here a refused
    connection is retried briefly and then reported honestly.
    """
    deadline = time.time() + timeout
    attempt = 0
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect((host, port))
            return sock
        except OSError as exc:
            sock.close()
            attempt += 1
            if time.time() >= deadline:
                raise ConnectionError(
                    f"could not reach {host}:{port} after {attempt} attempts ({exc})"
                ) from exc
            if on_status:
                on_status(f"Connecting to {host}… (attempt {attempt})")
            time.sleep(1.0)


def send_session(host, port, paths, on_progress=None, on_status=None, cancel=None):
    """Send `paths` to a waiting receiver.

    on_progress(sent_bytes, total_bytes, current_name) is called as data moves.
    cancel is an optional threading.Event; setting it aborts the transfer.
    Returns (files_sent, bytes_sent).
    """
    dirs, files, total = build_manifest(paths)
    if not files and not dirs:
        raise ValueError("nothing selected to send")

    if on_status:
        on_status("Connecting…")
    sock = connect(host, port, on_status=on_status)
    sent = 0
    try:
        sock.sendall(MAGIC)
        send_header(sock, {
            "type": "manifest",
            "dirs": dirs,
            "files": [{"path": f["path"], "size": f["size"]} for f in files],
            "total_bytes": total,
            "total_files": len(files),
        })

        reply = recv_header(sock)
        if reply.get("type") != "ready":
            raise ConnectionError(f"receiver refused transfer: {reply}")

        if on_status:
            on_status(f"Sending {len(files)} file(s)…")
        if on_progress:
            on_progress(0, total, "")

        for entry in files:
            if cancel is not None and cancel.is_set():
                send_header(sock, {"type": "abort"})
                raise InterruptedError("transfer cancelled")

            send_header(sock, {
                "type": "file",
                "path": entry["path"],
                "size": entry["size"],
            })
            with open(entry["src"], "rb") as handle:
                remaining = entry["size"]
                while remaining:
                    block = handle.read(min(CHUNK, remaining))
                    if not block:
                        # File shrank mid-transfer; pad so the framing stays honest.
                        block = b"\0" * remaining
                    sock.sendall(block)
                    remaining -= len(block)
                    sent += len(block)
                    if on_progress:
                        on_progress(sent, total, entry["path"])

        send_header(sock, {"type": "done"})
        final = recv_header(sock)
        if final.get("type") != "complete":
            raise ConnectionError(f"receiver did not confirm: {final}")
    finally:
        sock.close()

    if on_status:
        on_status(f"Sent {len(files)} file(s).")
    return len(files), sent


def send_paths(host, port, paths, **kwargs):
    """Convenience wrapper accepting a single path or a list of them."""
    if isinstance(paths, (str, os.PathLike)):
        paths = [str(paths)]
    return send_session(host, port, list(paths), **kwargs)
