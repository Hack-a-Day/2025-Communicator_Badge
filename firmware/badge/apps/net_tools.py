"""Tools for debugging the badge network, like ping."""

from collections import deque
import time

from apps.base_app import BaseApp
from net.net import register_receiver, send, MY_ADDRESS, BROADCAST_ADDRESS
from net.protocols import NetworkFrame, Protocol


PING = Protocol(port=1, name="PING", structdef="!IB")  # Test connection to a node
PONG = Protocol(port=2, name="PONG", structdef="!IBBff")  # Response to PING


class NetTools(BaseApp):
    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.receive_queue = deque([], 10)
        self.last_ping_time = time.time()
        self.last_rssi = 0
        self.last_snr = 0
        self.last_ping_sender = 0
        self.foreground_sleep_ms = 500
        self.background_sleep_ms = 500
        self.last_ping_responder = 0
        self.last_pings_ttl = 0
        self.last_pings_rssi = 0
        self.last_pings_snr = 0
        self.last_pong_rssi = 0
        self.last_pong_snr = 0
        self.ping_counter = 0
        self.pings = {}

    def start(self):
        """Register the app with the system."""
        super().start()
        # Registery any ports the app should receive messages from.
        # By default, these will get pushed into self.receive_queue.
        register_receiver(PING, self.receive_queue.append)
        register_receiver(PONG, self.receive_queue.append)

    def process_receive_queue(self):
        while self.receive_queue:
            message = self.receive_queue.popleft()
            if message.port == PING.port and message.payload:
                self.last_ping_sender = message.source
                # print(
                #     f"Received PING from {message.source:x} to {message.destination:x}: {message.payload}"
                # )
                self.last_rssi = self.badge.lora.get_rssi()
                self.last_snr = self.badge.lora.get_snr()
                # Respond with PONG
                send(
                    NetworkFrame().set_fields(
                        protocol=PONG,
                        destination=message.payload[0],
                        ttl=7,
                        payload=(MY_ADDRESS, message.ttl, message.payload[1], self.last_rssi, self.last_snr),
                    )
                )
            elif message.port == PONG.port:
                self.last_ping_responder, self.last_pings_ttl, self.pong_counter, self.last_pings_rssi, self.last_pings_snr = message.payload
                self.last_pong_rssi = self.badge.lora.get_rssi()
                self.last_pong_snr = self.badge.lora.get_snr()
                self.pings[self.pong_counter] = True
                # print(f"Received PONG from {pinged_address:x} via {message.source}.")
                # print(f"PING arrived with TTL {ping_arrival_ttl} RSSI: {ping_arrival_rssi} SNR: {ping_arrival_snr}")
                # print(f"PONG RSSI: {self.badge.lora.get_rssi()}  SNR: {self.badge.lora.get_snr()}")

    def run_background(self):
        self.process_receive_queue()
        # self.send_ping()

    def run_foreground(self):
        self.process_receive_queue()
        if self.badge.keyboard.f5():  # Go back to Main Menu
            self.switch_to_background()
        if self.badge.keyboard.f1() or time.time() - self.last_ping_time > 1.0:
            self.send_ping()
        if self.badge.keyboard.f5():
            self.switch_to_background()
        if len(self.pings):
            num_success = sum([1 for ping in self.pings.values() if ping])
            num_tries = len(self.pings)
            success_perc = int((num_success / num_tries) * 100)
            self.title_label.set_text(f"Net Tools     My Address: {MY_ADDRESS:x}     Success: {num_success}/{num_tries}  {success_perc}%")
        self.addr_label.set_text(f"Last Ping Source: {self.last_ping_sender:x}")
        self.rssi_label.set_text(f"Last Ping RSSI: {self.last_rssi}")
        self.snr_label.set_text(f"Last Ping SNR: {self.last_snr}")
        self.last_ping_responder_label.set_text(f"Last Ping Responder: {self.last_ping_responder:x}")
        self.last_pings_ttl_label.set_text(f"Last Sent Ping Received TTL: {self.last_pings_ttl}")
        self.last_pings_rssi_label.set_text(f"Last Sent Ping Received RSSI: {self.last_pings_rssi}")
        self.last_pings_snr_label.set_text(f"Last Sent Ping Recevied SNR: {self.last_pings_snr}")
        self.last_pong_rssi_label.set_text(f"Last Ping Response RSSI: {self.last_pong_rssi}")
        self.last_pong_snr_label.set_text(f"Last Ping Response SNR: {self.last_pong_snr}")

    def send_ping(self):
        # print("Sending a ping...")
        send(
            NetworkFrame().set_fields(
                protocol=PING,
                destination=BROADCAST_ADDRESS,
                ttl=7,
                payload=(MY_ADDRESS, self.ping_counter),
            )
        )
        self.pings[self.ping_counter] = False
        self.ping_counter = (self.ping_counter + 1) & 0xFF
        self.last_ping_time = time.time()

    def switch_to_foreground(self):
        self.title_label = self.badge.display.text(0, 0, f"Net Tools     My Address: {MY_ADDRESS:x}     Succes: 0/0  0%")
        self.badge.display.f1("Ping")
        self.badge.display.f5("Home")
        self.addr_label = self.badge.display.text(self.badge.display.CHAR_HEIGHT, 0, "Last Ping Source:")
        self.rssi_label = self.badge.display.text(self.badge.display.CHAR_HEIGHT * 2, 0, "Last Ping RSSI:")
        self.snr_label = self.badge.display.text(self.badge.display.CHAR_HEIGHT * 3, 0, "Last Ping SNR:")
        self.last_ping_responder_label = self.badge.display.text(self.badge.display.CHAR_HEIGHT * 4, 0, "Last Ping Responder:")
        self.last_pings_ttl_label = self.badge.display.text(self.badge.display.CHAR_HEIGHT * 5, 0, "Last Sent Ping Received TTL:")
        self.last_pings_rssi_label = self.badge.display.text(self.badge.display.CHAR_HEIGHT * 6, 0, "Last Sent Ping Received RSSI:")
        self.last_pings_snr_label = self.badge.display.text(self.badge.display.CHAR_HEIGHT * 7, 0, "Last Sent Ping Recevied SNR:")
        self.last_pong_rssi_label = self.badge.display.text(self.badge.display.CHAR_HEIGHT * 8, 0, "Last Ping Response RSSI:")
        self.last_pong_snr_label = self.badge.display.text(self.badge.display.CHAR_HEIGHT * 9, 0, "Last Ping Response SNR:")
        return super().switch_to_foreground()