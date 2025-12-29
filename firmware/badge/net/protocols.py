"""Everything for Encoding and Decoding badgenet network frames and protocols.

Important Note: Everything in this file needs to be usable by both micropython (on the badge)
and CPython (for testing on a host computer). Only import libraries that exist in both Pythons.
"""

from collections import namedtuple
import struct
import time

from libs.crc import Calculator, Crc16

crc_calculator = Calculator(Crc16.xmodem)
# On micropython, switch to the viper implementation for faster execution
try:
    from libs.crc import Opt_viper
except (ImportError, NameError):
    pass

Protocol = namedtuple("Protocol", ("port", "name", "structdef"))

# Packet Structure
# Network (Big) endian
#
# Idx: Count: Field
#  0: 2 bytes: Header 0x07E9 (2025)
#  2: 2 bytes: Checksum (everything in packet after TTL field)
#  4: 1 byte: Flags and TTL
## bits 7-4: Reserved
## bits 3-0: TTL
#  5: 1 byte: Packet length [16-250]
#  6: 4 bytes: Destination Address
# 10: 4 bytes: Source Address
# 14: 1 byte: Port (Packet type, protocol ID)
# 15: 1 byte: Seq num
# 16: n bytes: Payload
SYNCWORD = b"\x07\xe9"
FRAME_STRUCTURE = "!BBIIBB"  # Doesn't include syncword or checksum at front
HEADER_LEN = struct.calcsize(FRAME_STRUCTURE) + 4
assert HEADER_LEN == 16, "Packet Header struct incorrect size"
MAX_FRAME_LEN = 250
CHECKSUM_OFFSET = 2

NULL_PROTO = Protocol(0, "UNKNOWN_PROTOCOL", f"!{MAX_FRAME_LEN - HEADER_LEN}s")

global_sequence: int = 0


class NetworkFrame:
    def __init__(self):
        self.protocol: Protocol
        self.source: int = 0
        self.destination: int = 0
        self.port: int = 0
        self.seq_num: int = 0
        self.payload: tuple | list = []
        self.payload_bytes: bytes = b""
        self.ttl: int = 0
        self.checksum: int = 0
        self.frame: bytes = b""
        self.timestamp: int = 0
        self.validated_frame: bool = False
        self.fields_set: bool = False

    def __repr__(self):
        if self.fields_set:
            if self.payload:
                payload = repr(self.payload)
            else:
                payload = repr(self.payload_bytes)
            if self.protocol is not None:
                return f"NetworkFrame({self.protocol.name}, dst:{self.destination:x}, src:{self.source:x}, ttl:{self.ttl} {payload}"
            return f"NetworkFrame([Unknown port [{self.port}]]), dst:{self.destination:x}, src:{self.source:x}, ttl:{self.ttl} {payload}"
        elif self.frame:
            return f"NetworkFrame(frame_bytes:{repr(self.frame)})"

    def set_fields(
        self,
        protocol: Protocol,
        destination: int,
        payload: bytes | tuple | list,
        source: int = 0,
        ttl: int = 0,
    ):
        self.protocol = protocol
        self.port = protocol.port
        self.source = source
        self.destination = destination
        if isinstance(payload, bytes):
            self.payload_bytes = payload
        elif isinstance(payload, (tuple, list)):
            self.payload = payload
        else:
            raise ValueError(
                f"payload needs to be a tuple/list of arguments or the byte array. Got {type(payload)}: [{repr(payload)}]"
            )
        self.ttl = ttl if 0 <= ttl < 15 else 0
        if not self.timestamp:
            self.timestamp = time.time() # type: ignore
        self.fields_set = True
        global global_sequence
        self.seq_num = global_sequence
        global_sequence = (global_sequence + 1) & 0xFF
        return self

    def set_frame(self, frame):
        self.frame = frame
        self.ttl = frame[4] & 0x0F
        self.destination = int.from_bytes(frame[6:10], "big")
        self.source = int.from_bytes(frame[10:14], "big")
        self.port = frame[14]
        self.seq_num = frame[15]
        self.validated_frame = False
        if not self.timestamp:
            self.timestamp = time.time() # type: ignore
        return self

    def validate_frame(self):
        if self.validated_frame:
            return self
        frame = self.frame
        frame_actual_len = len(frame)
        if frame_actual_len < HEADER_LEN:
            raise ValueError(
                f"Frame shorter [{len(frame)}] than required header [{HEADER_LEN}], Invalid."
            )
        elif frame_actual_len > MAX_FRAME_LEN:
            raise ValueError(
                f"Frame too long [{frame_actual_len}] for LoRa [{MAX_FRAME_LEN}]. Invalid."
            )
        if frame[:2] != SYNCWORD:
            raise ValueError(
                f"Frame does not start [{repr(frame[:2])}] with expected syncword [{repr(SYNCWORD)}]. Invalid."
            )
        frame_claimed_len = int(frame[5])
        # frame_theoretical_len = HEADER_LEN + struct.calcsize(self.protocol.structdef)
        # However, the protocol may not be known by this badge, so it can't be calculated reliably
        if frame_claimed_len < HEADER_LEN or frame_claimed_len > MAX_FRAME_LEN:
            raise ValueError(
                f"Frame claims to be illegal length {frame_claimed_len}: [{HEADER_LEN}, {MAX_FRAME_LEN}]. Invalid."
            )
        if frame_actual_len < frame_claimed_len:
            raise ValueError(
                f"Frame only {frame_actual_len} long but claims to be {frame_claimed_len} long. Invalid."
            )
        elif frame_actual_len > frame_claimed_len:
            frame = frame[:frame_claimed_len]
            self.frame = frame
            print(
                f"Warning: frame truncated due to being longer [{frame_actual_len}] than reported length [{frame_claimed_len}]."
            )
        claimed_checksum = frame[2:4]
        calced_checksum = crc_calculator.checksum(frame[5:]).to_bytes(2, "big")
        self.validated_frame = claimed_checksum == calced_checksum
        return self

    def serialize(self) -> bytes:
        if self.frame:
            return self.frame
        flags_ttl = 0 | self.ttl
        if isinstance(self.payload, (tuple, list)) and self.payload:
            payload = struct.pack(self.protocol.structdef, *self.payload)
        elif isinstance(self.payload_bytes, bytes):
            payload_max_len = struct.calcsize(self.protocol.structdef)
            payload_len = len(self.payload_bytes)
            if payload_len > payload_max_len:
                raise ValueError(
                    f"Payload too long for protocol {self.protocol.name}: [{repr(self.payload_bytes)}]"
                )
            elif payload_len < payload_max_len:
                payload = self.payload_bytes + (b"\0" * (payload_max_len - payload_len))
            else:
                payload = self.payload_bytes
        else:
            raise ValueError(
                f"Unknown payload for protocol {self.protocol.name}: [{self.payload}][{self.payload_bytes}]"
            )
        frame_length = len(payload) + HEADER_LEN
        try:
            frame = (
                struct.pack(
                    FRAME_STRUCTURE,
                    flags_ttl,
                    frame_length,
                    self.destination,
                    self.source,
                    self.protocol.port,
                    self.seq_num & 0xFF,
                )
                + payload
            )
        except Exception as err:
            print(f"Serialization failed for message: {err}")
            print(
                f"flags_ttl: {flags_ttl} frame_length: {frame_length} dst: {self.destination} src: {self.source} port: {self.protocol.port}, payload: {repr(payload)}"
            )
            raise
        try:
            self.checksum = crc_calculator.checksum(frame[1:]) # start from frame_length byte
        except Exception as err:
            print(f"Checksumming failed for message: {err}")
            raise
        self.frame = struct.pack(f"!2sH{len(frame)}s", SYNCWORD, self.checksum, frame)
        # Debug: Check that the frame was valid after serialization
        self.validate_frame()
        return frame

    def deserialize(self, protocols: dict[int, Protocol]):
        # If already deserialized, return.
        if self.fields_set:
            return self
        # Validate if not done yet.
        if self.validated_frame:
            frame = self.frame
        else:
            try:
                frame = self.validate_frame()
            except ValueError as err:
                print(f"Validation failed, could not deserialze: {err}")
                raise
        frame = self.frame
        self.ttl = frame[4] & 0x0F
        self.destination = int.from_bytes(frame[6:10], "big")
        self.source = int.from_bytes(frame[10:14], "big")
        self.port = frame[14]
        self.seq_num = frame[15]
        self.payload_bytes = frame[HEADER_LEN:]
        try:
            self.protocol = protocols[self.port]
            try:
                self.payload = struct.unpack_from(
                    self.protocol.structdef, frame, HEADER_LEN
                )
            except ValueError as err:
                print(
                    f"Unable to decode payload for protocol {self.protocol.name}: {repr(self.payload_bytes)}: {err}"
                )
                self.payload = []
        except KeyError as err:
            # print(f"Unknown protocol on port {err}, can't decode payload.")
            self.protocol = None
            self.payload = []
        self.fields_set = True
        return self

    def check_for_retransmit(self, exclude_destination: int):
        """Checks if a message should be retransmitted.
        Don't retransmit if: this is the expected destination or the TTL has reached 0.
        Returns a new message with decremented TTL or None if it shouldn't be retransmitted.
        """
        destination = int.from_bytes(self.frame[6:10], "big")
        if destination == exclude_destination:
            return None
        ttl = self.frame[4] & 0x0F
        if 0 < ttl < 16:
            # Only 4 bytes allowed for TTL, so check it's positive and hasn't overflowed.
            new_ttl_byte = self.frame[4] & 0xF0 | (ttl - 1)
            new_frame = self.frame[:4] + new_ttl_byte.to_bytes() + self.frame[5:]
            # checksum = struct.unpack(
            #     "!H", new_frame[CHECKSUM_OFFSET : CHECKSUM_OFFSET + 2]
            # )[0]
            # print(f"Queueing {repr(new_frame)} for retransmit. TTL was {ttl} is {new_ttl_byte}. Checksum: {checksum:x}")
            return NetworkFrame().set_frame(new_frame)
        return None

    def check_for_me(self, my_address: int, broadcast_address: int):
        """Checks a frame before its been deserialzed if it is meant for this badge."""
        destination = int.from_bytes(self.frame[6:10], "big")
        source = int.from_bytes(self.frame[10:14], "big")
        # print(f"dest:{destination:x} me:{my_address:x} brd:{broadcast_address:x} from {source:x}")
        return (destination in (my_address, broadcast_address)) and source != my_address
