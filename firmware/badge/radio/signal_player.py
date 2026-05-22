"""Replay recorded Sub-GHz packets preserving timing offsets."""

import time

from radio.sub_file import SubFile


class SignalPlayer:
    """Player for Sub-GHz capture files."""

    def __init__(self, lora):
        self.lora = lora

    def _sleep_ms(self, value):
        if value <= 0:
            return
        try:
            time.sleep_ms(value)
        except AttributeError:
            time.sleep(value / 1000.0)

    def replay(self, path, repeat=1, frequency_mhz=None):
        capture = SubFile.read(path)
        packets = capture["packets"]
        freq = frequency_mhz if frequency_mhz is not None else capture["frequency_mhz"]
        if freq is None:
            raise ValueError("Capture file missing frequency and no override provided")

        sent = 0
        for _ in range(repeat):
            prev_ts = 0
            for pkt in packets:
                ts_ms = int(pkt.get("ts_ms", 0))
                delay = ts_ms - prev_ts
                self._sleep_ms(delay)
                self.lora.tx_ook(freq, pkt["data"])
                prev_ts = ts_ms
                sent += 1
        return sent
