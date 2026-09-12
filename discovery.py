"""Zero-configuration peer discovery over UDP broadcast.

The receiver runs a Beacon announcing "I am <name>, listening on <port>".
The sender runs a Browser that collects those announcements; the peer's address
comes from the UDP packet itself, so neither end ever types an IP.

On a hotspot LAN this is the same trick ShareIt and friends use. If the access
point has client isolation enabled, broadcast is blocked and nothing will be
found -- the UI keeps a manual-address escape hatch for that case.
"""
import json
import socket
import threading
import time

DISCOVERY_PORT = 50505
APP_ID = "AsuraSwift"
BEACON_INTERVAL = 1.0
PEER_TIMEOUT = 5.0


def local_ip():
    """Best guess at this machine's LAN address.

    socket.gethostbyname(socket.gethostname()) returns 127.0.1.1 on Debian and
    is useless here. Opening a UDP socket toward an off-link address makes the
    kernel pick the outbound interface without sending a single packet, so this
    works on a hotspot with no internet behind it.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def _broadcast_addresses(ip):
    """255.255.255.255 plus the /24 directed broadcast, which some APs prefer."""
    addrs = ["255.255.255.255"]
    parts = ip.split(".")
    if len(parts) == 4 and ip != "127.0.0.1":
        addrs.append(".".join(parts[:3] + ["255"]))
    return addrs


class Beacon(threading.Thread):
    """Announces this machine on the LAN until stop() is called."""

    def __init__(self, name=None, port=9999):
        super().__init__(daemon=True)
        self.name = name or socket.gethostname()
        self.port = port
        self._stop = threading.Event()

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        payload = json.dumps(
            {"app": APP_ID, "name": self.name, "port": self.port}
        ).encode()
        try:
            while not self._stop.is_set():
                for dest in _broadcast_addresses(local_ip()):
                    try:
                        sock.sendto(payload, (dest, DISCOVERY_PORT))
                    except OSError:
                        pass  # interface down or broadcast filtered; keep trying
                self._stop.wait(BEACON_INTERVAL)
        finally:
            sock.close()

    def stop(self):
        self._stop.set()


class Browser(threading.Thread):
    """Collects beacons. peers() returns the currently visible devices."""

    def __init__(self):
        super().__init__(daemon=True)
        self._peers = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", DISCOVERY_PORT))
        except OSError:
            sock.close()
            return
        sock.settimeout(0.5)
        mine = local_ip()
        try:
            while not self._stop.is_set():
                try:
                    data, addr = sock.recvfrom(1024)
                except socket.timeout:
                    continue
                except OSError:
                    break
                try:
                    msg = json.loads(data.decode())
                except (ValueError, UnicodeDecodeError):
                    continue
                if msg.get("app") != APP_ID or addr[0] == mine:
                    continue
                with self._lock:
                    self._peers[addr[0]] = {
                        "name": msg.get("name", addr[0]),
                        "ip": addr[0],
                        "port": int(msg.get("port", 9999)),
                        "seen": time.time(),
                    }
        finally:
            sock.close()

    def peers(self):
        """Devices heard from recently, newest announcements kept, sorted by name."""
        cutoff = time.time() - PEER_TIMEOUT
        with self._lock:
            live = [p for p in self._peers.values() if p["seen"] >= cutoff]
            self._peers = {p["ip"]: p for p in live}
        return sorted(live, key=lambda p: p["name"].lower())

    def stop(self):
        self._stop.set()
