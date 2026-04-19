"""Capture-the-Flag (CTF) hot/cold game over LoRa.

One badge hosts a flag by periodically sending a beacon.
Other badges scan for the beacon and track whether they're
getting warmer or colder based on RSSI.

This is a proper BaseApp that runs independently; the CLI
wraps it via ctf_cmd.py.
"""

from collections import deque

try:
    import uasyncio as aio  # type: ignore
except ImportError:
    aio = None

try:
    from apps.base_app import BaseApp
    from net.net import register_receiver, send, MY_ADDRESS, BROADCAST_ADDRESS
    from net.protocols import NetworkFrame, Protocol
    _HAS_FIRMWARE = True
except ImportError:
    _HAS_FIRMWARE = False


# CTF protocol: beacon contains the host's address
CTF_BEACON = None
if _HAS_FIRMWARE:
    CTF_BEACON = Protocol(port=20, name="CTF_BEACON", structdef="!I")


class CTFApp:
    """Capture-the-flag hot/cold game.

    When running on real firmware, inherits from BaseApp.
    When running in tests, works as a standalone class.
    """

    # Class-level list for test compatibility (BaseApp has all_apps)
    all_apps = []

    def __init__(self, name, badge):
        self.name = name
        self.badge = badge
        self.active_foreground = False
        self.active_background = True
        self.foreground_sleep_ms = 100
        self.background_sleep_ms = 2000
        self.task = None

        # CTF state
        self.hosting = False
        self.last_rssi = None
        self.beacon_count = 0
        self.scan_history = []  # List of (rssi, trend) tuples
        self.max_history = 50
        self._receive_queue = deque([], 10)

    def start(self):
        """Register CTF protocol and add to app list."""
        if self not in self.all_apps:
            self.all_apps.append(self)
        if _HAS_FIRMWARE and CTF_BEACON:
            register_receiver(CTF_BEACON, self._receive_queue.append)

    def stop(self):
        self.hosting = False
        self.active_foreground = False
        self.active_background = False

    def host_flag(self):
        """Start hosting a CTF flag beacon."""
        self.hosting = True
        self.beacon_count = 0

    def stop_flag(self):
        """Stop hosting the flag."""
        self.hosting = False

    def scan(self, rssi):
        """Update scan with a new RSSI reading.

        Returns a trend string: 'start', 'warmer', 'colder', or 'same'.
        """
        if self.last_rssi is None:
            trend = "start"
        elif rssi > self.last_rssi:
            trend = "warmer"
        elif rssi < self.last_rssi:
            trend = "colder"
        else:
            trend = "same"

        self.last_rssi = rssi
        self.scan_history.append((rssi, trend))
        if len(self.scan_history) > self.max_history:
            self.scan_history.pop(0)
        return trend

    def reset_scan(self):
        """Reset scanning state."""
        self.last_rssi = None
        self.scan_history.clear()

    def run_background(self):
        """Send beacon if hosting."""
        if self.hosting and _HAS_FIRMWARE:
            try:
                send(
                    NetworkFrame().set_fields(
                        protocol=CTF_BEACON,
                        destination=BROADCAST_ADDRESS,
                        ttl=7,
                        payload=(MY_ADDRESS,),
                    )
                )
                self.beacon_count += 1
            except Exception:
                pass

        # Process received beacons
        while self._receive_queue:
            message = self._receive_queue.popleft()
            if hasattr(message, 'payload') and message.payload:
                rssi = self.badge.lora.get_rssi()
                self.scan(rssi)

    def run_foreground(self):
        self.run_background()

    def switch_to_foreground(self):
        self.active_foreground = True
        self.active_background = False

    def switch_to_background(self):
        self.active_background = True
        self.active_foreground = False
