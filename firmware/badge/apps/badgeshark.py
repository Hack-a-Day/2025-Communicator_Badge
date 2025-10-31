"""Wireshark, but for BadgeNet."""

from collections import deque
import gc
import uasyncio as aio  # type: ignore

from apps.base_app import BaseApp
from net.protocols import NetworkFrame, Protocol
from net.net import capture_all_packets, badgenet


class BadgeShark(BaseApp):
    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.capture_list: list[NetworkFrame] = []
        self.capture_list_max_len: int = 20
        self.display_list: list[NetworkFrame] = []
        self.display_list_max_len: int = 10
        self.capture_accept_filters: dict[Protocol | str, bool | int] = {}
        self.capture_reject_filters: dict[Protocol | str, bool | int] = {}
        self.display_accept_filters: dict[Protocol | str, bool | int] = {}
        self.display_reject_filters: dict[Protocol | str, bool | int] = {}
        self.foreground_sleep_ms = 5000

    def retrieve_captured_packets(self):
        while badgenet.promiscuous_queue:
            message = badgenet.promiscuous_queue.popleft()
            if self.filter(
                message, self.capture_accept_filters, self.capture_reject_filters
            ):
                self.capture_list.append(message)
            if len(self.capture_list) > self.capture_list_max_len:
                self.capture_list.pop(0)

    def run_foreground(self):
        self.badge.np[4] = (0, 0, 50)
        self.badge.np.write()
        self.retrieve_captured_packets()
        for message in self.capture_list:
            message.deserialize(badgenet.protocols)
            if self.filter(
                message, self.display_accept_filters, self.display_reject_filters
            ):
                self.display_list.append(message)
            if len(self.display_list) > self.display_list_max_len:
                self.display_list.pop(0)
        self.capture_list = []
        for idx, message in enumerate(self.display_list):
            if isinstance(message, NetworkFrame):
                if message.fields_set:
                    print(
                        f"{idx}: {message.timestamp}: [{message.seq_num:x}] From {message.source:x} to {message.destination:x}:{message.port}[{message.protocol.name}]: {message.payload} {message.checksum:04x}"
                    )
                elif message.frame:
                    print(f"{idx}: Undecoded {repr(message.frame)}")
            # elif isinstance(message, TransmitMessage):
            #     print(f"{message.timestamp}: Transmitted to {message.destination}: {message.payload.hex()}")
            self.badge.np[4] = (0, 50, 0)
            self.badge.np.write()

    def run_background(self):
        # Clear out the queue
        while badgenet.promiscuous_queue:
            badgenet.promiscuous_queue.popleft()
        gc.collect()

    def switch_to_foreground(self):
        capture_all_packets(True)
        return super().switch_to_foreground()

    def switch_to_background(self):
        capture_all_packets(False)
        return super().switch_to_background()

    def stop(self):
        capture_all_packets(False)
        super().stop()

    def filter(
        self,
        message: NetworkFrame,
        accept_filters: dict[Protocol | str, bool | int],
        reject_filters: dict[Protocol | str, bool | int],
    ) -> bool:
        return True
