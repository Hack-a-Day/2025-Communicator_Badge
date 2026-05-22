"""Capture raw Sub-GHz packets with relative timestamps."""

import time

from radio.sub_file import SubFile


class SignalRecorder:
    """Recorder for OOK packet captures using badge.lora helpers."""

    def __init__(self, lora):
        self.lora = lora

    def _ticks_ms(self):
        try:
            return time.ticks_ms()
        except AttributeError:
            return int(time.time() * 1000)

    def _ticks_diff(self, now, start):
        try:
            return time.ticks_diff(now, start)
        except AttributeError:
            return now - start

    def record(self, frequency_mhz, duration_s, path, check_interrupt=None):
        start = self._ticks_ms()
        packets = []

        while True:
            now = self._ticks_ms()
            elapsed = self._ticks_diff(now, start)
            if elapsed >= int(duration_s * 1000):
                break

            data = self.lora.rx_ook(frequency_mhz, timeout_ms=100)
            if data:
                packets.append({"ts_ms": elapsed, "data": data})

            if check_interrupt:
                check_interrupt()

        SubFile.write(path, frequency_mhz, "OOK", packets)
        return len(packets)
