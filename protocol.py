"""Wire protocol shared by the sending and receiving ends of AsuraSwift.

One TCP connection carries an entire transfer session. Every message on that
connection is a 4-byte big-endian length followed by a JSON header; a header of
type "file" is followed by exactly `size` raw bytes of payload.

This replaces the old one-connection-per-message scheme, where the sender could
connect into a listener's backlog and have send() report success for bytes the
receiver tore down before ever accepting.
"""
import json
import os
import struct

MAGIC = b"ASWIFT01"
CHUNK = 64 * 1024
DEFAULT_PORT = 9999


def recv_exactly(sock, n):
    """Read exactly n bytes, or raise ConnectionError if the peer hangs up."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(min(CHUNK, n - len(buf)))
        if not chunk:
            raise ConnectionError(f"peer closed after {len(buf)} of {n} bytes")
        buf += chunk
    return bytes(buf)


def send_header(sock, header):
    raw = json.dumps(header).encode()
    sock.sendall(struct.pack("!I", len(raw)) + raw)


def recv_header(sock):
    (length,) = struct.unpack("!I", recv_exactly(sock, 4))
    return json.loads(recv_exactly(sock, length).decode())


def safe_join(dest_root, relative_path):
    """Resolve relative_path beneath dest_root, refusing anything that escapes.

    The receiver writes paths chosen by whoever is on the other end of the
    socket, so a header carrying '../../.bashrc' must not be honoured.
    """
    root = os.path.abspath(dest_root)
    target = os.path.abspath(os.path.join(root, relative_path))
    if target != root and not target.startswith(root + os.sep):
        raise ValueError(f"unsafe path in transfer: {relative_path!r}")
    return target


def build_manifest(paths):
    """Describe the selection as (dirs, files, total_bytes).

    `paths` is a list of absolute file or folder paths. Every entry is named
    relative to its own basename, so sending /home/me/Photos recreates
    Photos/... at the destination rather than the whole absolute path.
    Returned file entries carry "src" for local use; strip it before sending.
    """
    dirs, files, total = [], [], 0
    seen_dirs = set()

    def add_dir(rel):
        if rel and rel not in seen_dirs:
            seen_dirs.add(rel)
            dirs.append(rel)

    for path in paths:
        path = os.path.abspath(path.rstrip(os.sep))
        base = os.path.basename(path)
        if os.path.isfile(path):
            size = os.path.getsize(path)
            files.append({"path": base, "size": size, "src": path})
            total += size
            continue
        for walk_root, walk_dirs, walk_files in os.walk(path):
            rel_dir = os.path.relpath(walk_root, os.path.dirname(path))
            add_dir(rel_dir.replace(os.sep, "/"))
            for name in walk_files:
                src = os.path.join(walk_root, name)
                if not os.path.isfile(src):  # skip sockets, broken symlinks
                    continue
                size = os.path.getsize(src)
                rel = os.path.join(rel_dir, name).replace(os.sep, "/")
                files.append({"path": rel, "size": size, "src": src})
                total += size

    return dirs, files, total


def human_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def human_time(seconds):
    if seconds < 0 or seconds != seconds or seconds == float("inf"):
        return "--"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
