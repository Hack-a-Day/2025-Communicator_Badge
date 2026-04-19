"""Mock LoRa radio for testing without SX1262 hardware."""

from collections import deque


class MockLoraRadio:
    """Fake LoraRadio that simulates badge.lora without SX1262 hardware.

    Provides the same attributes and methods as net.lora.LoraRadio
    but operates entirely in memory.
    """

    def __init__(self):
        self.freq_slot = 9
        self.frequency = 904.250
        self.bandwidth = 500.0
        self.coding_rate = 5
        self.spreading_factor = 7
        self.preamble_length = 16
        self.crc = True
        self.tx_power = 9
        self.sync_word = 0x12

        self.last_rssi = -80.0
        self.last_snr = 8.5
        self._rx_queue = deque([], 30)
        self._tx_log = []  # Record sent packets for test assertions
        self.radio = None  # No real radio hardware
        self.fake_rx_buffer = deque([], 3)

    def get_rssi(self):
        return self.last_rssi

    def get_snr(self):
        return self.last_snr

    async def recv(self):
        if self._rx_queue:
            return self._rx_queue.popleft()
        return None

    async def send(self, packet):
        self._tx_log.append(packet)

    def set_freq_slot(self, slot):
        if slot < 1 or slot > 52:
            raise ValueError(
                "Invalid frequency slot. Must be in [1, 52]"
            )
        self.freq_slot = slot
        self.frequency = 902.250 + (slot - 1) * 0.5
        return self.frequency

    def inject_rx(self, frame_bytes, rssi=-70.0, snr=9.0):
        """Test helper: simulate receiving a frame."""
        self._rx_queue.append(frame_bytes)
        self.last_rssi = rssi
        self.last_snr = snr

    def rx_ook(self, freq, timeout_ms=1000):
        """Simulate receiving OOK data."""
        import time
        if hasattr(self, "_ook_rx_queue") and self._ook_rx_queue:
            return self._ook_rx_queue.popleft()
        time.sleep(timeout_ms / 1000.0)
        return None

    def tx_ook(self, freq, data):
        """Simulate transmitting OOK data."""
        if not hasattr(self, "_ook_tx_log"):
            self._ook_tx_log = []
        self._ook_tx_log.append((freq, data))
