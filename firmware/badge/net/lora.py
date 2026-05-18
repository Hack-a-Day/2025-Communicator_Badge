import asyncio
import binascii
import collections
import random
import sys

from net.sx1262 import SX1262, CHANNEL_FREE, LORA_DETECTED, ERR_UNKNOWN
from hardware import board



class LoraRadio:
    def __init__(self, tx_led=None, tx_power=9):
        # Settings
        # https://meshtastic.org/docs/overview/radio-settings/
        self.freq_slot = 1
        self.frequency = 869.525  # MHz: Only one slot in EU

        self.bandwidth = 250.0  # 250000  # kHz: 31000, 125000, or 250000
        self.coding_rate = (
            5  # 4/x bit redundancy, increases reliability but decreases datarate: 5 - 8
        )
        self.spreading_factor = (
            7  # 1<<x num chirps per symbol, each step doubles airtime, adds 2.5dB: 7-12
        )
        self.preamble_length = 16
        self.crc = True
        self.tx_power = tx_power
        self.sync_word = 0x12
        self.rf_power_levels = {"max": [4, 0, 7], "middle": [2, 0, 2], "low": [1, 0, 1]}
        self.power_level = "low"  # RF amp power, for power saving

        self.last_snr: float = 0.0
        self.last_rssi: float = 0.0
        self._message_ready = asyncio.ThreadSafeFlag()  # type: ignore
        self._ready_for_tx = asyncio.ThreadSafeFlag()  # type: ignore
        self._rx_queue: collections.deque = collections.deque([], 30)
        self.tx_led = tx_led

        try:
            print("Initializing SX1262...")
            self.radio = SX1262(
                spi_host=2, sck=8, mosi=3, miso=9, cs=17, irq=16, rst=18, gpio=15
            )
            self.rf_sw = board.RF_SW
            self.radio.begin(
                freq=self.frequency,
                bw=self.bandwidth,
                sf=self.spreading_factor,
                cr=self.coding_rate,
                syncWord=self.sync_word,
                power=self.tx_power,
                currentLimit=60,
                preambleLength=self.preamble_length,
                implicit=False,
                implicitLen=0xFF,
                crcOn=self.crc,
                txIq=False,
                rxIq=False,
                tcxoVoltage=1.7,
                useRegulatorLDO=False,
                blocking=True,
            )
            self.radio.setPaConfig(
                *self.rf_power_levels[self.power_level]
            )  ## datasheet p. 76
            self.radio.setBlockingCallback(False, self._handle_events)
        except Exception as ex:
            print(f"Failed to configure radio: {ex}")
            sys.print_exception(ex)
            self.radio = None
            self.fake_rx_buffer = collections.deque([], 3)

    def _handle_events(self, events):
        if events & SX1262.RX_DONE:
            msg, err = self.radio.recv()
            self._ready_for_tx.set()  # Done with an Rx operations, so allow Tx
            error = SX1262.STATUS[err]
            if error != "ERR_NONE":
                # print(f"Lora Error: {error}")
                return
            self.last_rssi = self.radio.getRSSI()
            self.last_snr = self.radio.getSNR()
            self._rx_queue.append(msg)
            self._message_ready.set()
        elif events & SX1262.TX_DONE:
            if self.tx_led:
                self.tx_led.value(0)
            self._rf_sw_rx()
            self._ready_for_tx.clear()

    async def recv(self) -> bytes | None:
        if self.radio:
            await self._message_ready.wait()
            data = self._rx_queue.popleft()
            # print(f"RX:<{binascii.b2a_base64(data, newline=False).decode()}>")
            return data
        return None

    async def send(self, packet: bytes):
        # print(f"TX:<{binascii.b2a_base64(packet, newline=False).decode()}>")
        if self.radio:
            # Detect a free RF channel before transmitting
            channel_status = LORA_DETECTED
            while channel_status != CHANNEL_FREE:
                # try:
                #     # Don't interrupt Rx
                #     await asyncio.wait_for(self._ready_for_tx.wait(), 2)
                # except asyncio.TimeoutError:
                #     # Unless nothing is being received, then go ahead and Tx
                #     pass
                channel_status = self.radio.scanChannel()
                if channel_status == ERR_UNKNOWN:
                    print("SX126X error scanning channel")
                if channel_status == LORA_DETECTED:
                    print(".", end="")
                else:
                    # If busy, sleep a random 0-10ms
                    await asyncio.sleep(random.random() / 100)
                # channel_status = CHANNEL_FREE
            print(">", end="")
            self._rf_sw_tx()
            if self.tx_led:
                self.tx_led.value(1)
            self.radio.send(packet)
        return None

    def get_rssi(self) -> float:
        if self.radio:
            return self.last_rssi
        return float("-inf")

    def get_snr(self) -> float:
        if self.radio:
            return self.last_snr
        return float("-inf")

    def _rf_sw_tx(self):
        self.rf_sw.value(0)

    def _rf_sw_rx(self):
        self.rf_sw.value(1)

    def set_freq_slot(self, slot):
        if slot < 1 or slot > 52: # or slot in (2, 7, 10, 23, 26, 34, 38, 50):
            raise ValueError(
                "Invalid frequency slot. Must be in [1, 52] and not [2, 7, 10, 23, 26, 34, 38, 50] (Meshtastic defaults)"
            )
        freq_mhz = 902.250 + (slot - 1) * 0.5
        print(f"Trying to set radio to slot {slot} at {freq_mhz} MHz")
        self.radio.setFrequency(freq_mhz)
        self.freq_slot = slot
        self.frequency = freq_mhz
        return self.frequency
