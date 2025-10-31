# BadgeNet Protocol

from collections import deque
import machine  # type: ignore
import struct
import sys
import time
import asyncio as aio  # type: ignore

from net.protocols import (
    Protocol,
    NetworkFrame,
    HEADER_LEN,
    MAX_FRAME_LEN,
    NULL_PROTO,
    CHECKSUM_OFFSET,
)

# For an event the size of supercon, there's ~50% chance of address collision with a 2-byte address. 4 is virtually 0.
MY_ADDRESS = int.from_bytes(machine.unique_id()[2:6], "big")
BROADCAST_ADDRESS = 0xFFFFFFFF  # Broadcast address for all nodes
RECENT_MESSAGE_EXPIRATION_S = 6000


class BadgeNet:
    """Badge Network Stack"""

    def __init__(self):
        self.transmit_queue_max_len = 20
        self.transmit_queue: deque[NetworkFrame] = deque([], self.transmit_queue_max_len)
        self.receive_callbacks: dict[int, list] = {}
        self.protocols: dict[int, Protocol] = {0: NULL_PROTO}
        self.seen_nodes: dict[int, str] = {}
        self.capture_all_packets: bool = False
        self.promiscuous_queue: deque[NetworkFrame] = deque([], 100)
        self.last_tx_time = 0
        self.transmit_cooldown_s = 0.1
        self.recently_seen_messages: dict[
            int, tuple[int, int]
        ] = {}  # checksum: (count, timestamp)
        self.lora_rx_task: aio.Task
        self.lora_tx_task: aio.Task
        self.send_cooldown_s: float = 0.001
        self.flush_recently_seen_cache_task: aio.Task

    def init(self, badge):
        self.badge = badge
        self.send_cooldown_s = self.badge.send_cooldown_ms / 1000
        self.lora_rx_task = aio.create_task(self.recv_all())
        self.lora_tx_task = aio.create_task(self.send_all())
        self.flush_recently_seen_cache_task = aio.create_task(
            self.flush_recently_seen()
        )

    def register_protocol(self, protocol: Protocol):
        """Register a protocol to be known by the network stack for debug decoding.
        Not required if registering the protocol with a callback function, this will happen automatically."""
        port = protocol.port
        if port not in self.protocols:
            self.protocols[port] = protocol
            try:
                payload_len = struct.calcsize(protocol.structdef)
                max_payload_len = MAX_FRAME_LEN - HEADER_LEN
                if payload_len > max_payload_len:
                    raise ValueError(
                        f"Protocol {protocol.name} payload length is too large: {payload_len} bytes vs max of {max_payload_len} bytes."
                    )
            except ValueError as err:
                raise ValueError(
                    f"Unable to use protocol {protocol.name}, illegal structdef: {err}"
                )
        else:
            if (
                protocol.name != self.protocols[port].name
                or protocol.structdef != self.protocols[port].structdef
                or protocol.port != self.protocols[port].port
            ):
                print("Registered protocols:")
                for proto in self.protocols.values():
                    print(f"{proto.port}: {proto.name}")
                raise ValueError(
                    f"Redefining protocol at port {port} from {self.protocols[port]} to {protocol}."
                )

    def register_receiver(self, protocol: Protocol, callback=None):
        """Registers a function to be called when a message is received for this badge in the specified protocol."""
        port = protocol.port
        if callback is not None:
            if port not in self.receive_callbacks:
                self.receive_callbacks[port] = []
            self.receive_callbacks[port].append(callback)
        self.register_protocol(protocol)

    async def recv_all(self):
        while True:
            try:
                frame = await self.badge.lora.recv()
                if frame is not None and len(frame) > 0:
                    # print("frame: ", repr(frame))
                    # rssi = self.badge.lora.get_rssi()
                    # snr = self.badge.lora.get_snr()
                    # print("rssi: ", rssi)
                    # print("snr: ", snr)
                    try:
                        message = NetworkFrame().set_frame(frame).validate_frame()
                        # print(f"Received frame {repr(message)}")
                    except ValueError as err:
                        print(f"Failed validation {repr(frame)}: {err}")
                        continue

                    if self.capture_all_packets and len(message.frame):
                        self.promiscuous_queue.append(message)
                    # Check if messages haven't been seen before and add them to the transmit queue for repeating
                    seen_checksum = struct.unpack(
                        "!H", message.frame[CHECKSUM_OFFSET : CHECKSUM_OFFSET + 2]
                    )[0]
                    seen_count, seen_timestamp = self.recently_seen_messages.get(seen_checksum, (0, 0))
                    self.recently_seen_messages[seen_checksum] = (seen_count + 1, seen_timestamp)
                    if seen_count == 0:
                        # Check how many times this has been recently seen, and if not, add it to the tx queue
                        retransmit_message = message.check_for_retransmit(MY_ADDRESS)
                        if retransmit_message and len(self.transmit_queue) < self.transmit_queue_max_len // 2:
                            # Decrement TTL and re-transmit if not expired (done in check_for_retransmit)
                            self.transmit_queue.append(retransmit_message)
                    else:
                        # This message has been seen before, no need to reprocess it
                        continue
                    message.deserialize(self.protocols)
                    # print(f"Decoded frame {repr(message)}")
                    if message.check_for_me(MY_ADDRESS, BROADCAST_ADDRESS):
                        if message.port in self.receive_callbacks and len(
                            message.payload_bytes
                        ) == struct.calcsize(message.protocol.structdef):
                            # If multiple protocols are defined on the same port by different badges, only
                            # send the message to the app if it matches the app's protocol definition for this port.
                            for callback in self.receive_callbacks[message.port]:
                                try:
                                    callback(message)
                                except Exception as ex:
                                    print(f"Exception in callback for message in protocol {message.protocol.name}")
                                    sys.print_exception(ex)
            except Exception as exc:
                print("Recv error:", exc)
                raise
            await aio.sleep(0.001)

    async def send_all(self):
        while True:
            if self.transmit_queue:
                try:
                    # print(f"Tx queue len: {len(self.transmit_queue)}")
                    message = None
                    while message is None:
                        message = self.transmit_queue.popleft()
                        if message.source == 0:  # Not set yet
                            message.source = MY_ADDRESS
                        message.serialize()
                        checksum = struct.unpack(
                            "!H", message.frame[CHECKSUM_OFFSET : CHECKSUM_OFFSET + 2]
                        )[0]
                        if self.recently_seen_messages.get(checksum, (0, 0))[0] > 1:
                            # If a message has been seen never or once, send it.
                            # print(
                            #     f"Dropping recently repeated message with checksum {checksum:x} before transmit."
                            # )
                            # print(self.recently_seen_messages)
                            continue
                        # else:
                        #     print(f"New message from {message.source:x} with checksum {checksum:x}")
                        # recent_checksums = [f"{cs:x}" for cs in self.recently_seen_messages]
                        # print(f"{recent_checksums}")
                        # Check if the Tx queue is too full, and if it is, stop relaying messages in favor of local messages
                        # Throw out the relayed messages until the queue is more empty
                        if len(self.transmit_queue) > self.transmit_queue_max_len // 2 and message.source != MY_ADDRESS:
                            message = None
                            continue
                    time_since_last_tx = time.time() - self.last_tx_time
                    if time_since_last_tx < self.transmit_cooldown_s:
                        await aio.sleep(self.transmit_cooldown_s - time_since_last_tx)
                    try:
                        await self.badge.lora.send(message.frame)
                    except Exception as err:
                        print(f"Failed sending: {err}")
                        continue
                    self.last_tx_time = time.time()
                    if self.capture_all_packets:
                        self.promiscuous_queue.append(message)
                    self.recently_seen_messages[message.checksum] = (
                        2,
                        self.last_tx_time,
                    )  # type: ignore
                except IndexError:
                    await aio.sleep(1)
                    continue
                await aio.sleep(self.send_cooldown_s)
            else:
                await aio.sleep(1)

    async def flush_recently_seen(self):
        while True:
            # print(
            #     f"Badgenet: Purging messages from recently seen cache, initial len {len(self.recently_seen_messages)}"
            # )
            now = time.time()
            self.recently_seen_messages = {
                checksum: count_time_seen
                for checksum, count_time_seen in self.recently_seen_messages.items()
                if now - count_time_seen[1] < RECENT_MESSAGE_EXPIRATION_S
            }
            await aio.sleep(1)


# Network Stack singleton
badgenet = BadgeNet()


def register_receiver(protocol: Protocol, callback=None):
    """Register a callback for incoming messages on a specific port."""
    badgenet.register_receiver(protocol, callback)


def register_protocol(protocol: Protocol):
    """Register a protocol for debug decoding.
    Only needed for protocols transmitted, not needed if register_receiver is used."""
    badgenet.register_protocol(protocol)


def send(message: NetworkFrame):
    """Send a message to the network"""
    badgenet.transmit_queue.append(message)


def capture_all_packets(enabled: bool):
    """Enables collecting traffic for the badgeshark app."""
    badgenet.capture_all_packets = enabled
