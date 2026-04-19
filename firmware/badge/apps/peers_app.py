"""Peer tracking app.

Tracks seen badges from network traffic (PING/PONG, beacons, etc.)
and maintains a peer table with RSSI history and last-seen timestamps.

This is a proper app that runs independently; the CLI
wraps it via peers_cmd.py.
"""

import time
from collections import deque

try:
    import uasyncio as aio  # type: ignore
except ImportError:
    aio = None

try:
    from apps.base_app import BaseApp
    from net.net import badgenet
    _HAS_FIRMWARE = True
except ImportError:
    _HAS_FIRMWARE = False


class PeersApp:
    """Tracks peers seen on the LoRa network.

    Works as standalone class for test compatibility.
    """

    all_apps = []

    def __init__(self, name, badge):
        self.name = name
        self.badge = badge
        self.active_foreground = False
        self.active_background = True
        self.foreground_sleep_ms = 100
        self.background_sleep_ms = 5000
        self.task = None

        # Peers: {address_int: {"rssi": float, "snr": float, "last_seen": float, "count": int}}
        self._peers = {}

    def start(self):
        if self not in self.all_apps:
            self.all_apps.append(self)

    def stop(self):
        self.active_foreground = False
        self.active_background = False

    def update_peer(self, address, rssi=-80.0, snr=0.0):
        """Record that a peer has been seen."""
        if address in self._peers:
            peer = self._peers[address]
            peer["rssi"] = rssi
            peer["snr"] = snr
            peer["last_seen"] = time.time()
            peer["count"] += 1
        else:
            self._peers[address] = {
                "rssi": rssi,
                "snr": snr,
                "last_seen": time.time(),
                "count": 1,
            }

    def get_peers(self):
        """Return dict of all known peers."""
        return dict(self._peers)

    def nearest_peer(self):
        """Return the address of the peer with the strongest RSSI."""
        if not self._peers:
            return None
        return max(self._peers.items(), key=lambda item: item[1]["rssi"])[0]

    def clear(self):
        """Forget all peers."""
        self._peers.clear()

    def run_background(self):
        """Sync with badgenet.seen_nodes if available."""
        if _HAS_FIRMWARE:
            try:
                for addr in badgenet.seen_nodes:
                    if addr not in self._peers:
                        self.update_peer(addr)
            except Exception:
                pass

    def run_foreground(self):
        self.run_background()

    def switch_to_foreground(self):
        self.active_foreground = True
        self.active_background = False

    def switch_to_background(self):
        self.active_background = True
        self.active_foreground = False
