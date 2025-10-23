"""
LoRa MAC Layer - Stops 500 badges from screaming over each other

This is the collision avoidance magic from that research paper.
Gets you from 5% to 95% success rate in dense deployments.

The basic idea:
- Most badges listen before talking
- Random backoffs spread things out
- NAV tells everyone when to chill
- No reliance on broken CAD
"""

import time
import urandom
from micropython import const

# What kind of packet is this?
PKT_TYPE_RTS = const(0x01)   # "I'm about to talk"
PKT_TYPE_DATA = const(0x02)  # Actual message

# Where are we in the protocol?
PHASE_IDLE = const(0)
PHASE_1_LISTEN = const(1)
PHASE_2_RTS = const(2)
PHASE_3_DATA = const(3)
PHASE_NAV = const(4)  # Waiting politely

# Prime offsets to prevent stampede synchronization
PRIME_OFFSETS = [5, 7, 11, 13, 17]


class LoRaMAC:
    """
    The MAC layer that makes dense deployment actually work

    How it works:
    1. Quick CAD check (if it sees activity, bail immediately)
    2. Coin flip: listen first (90%) or claim channel (10%)
    3. If you claimed it, send your data
    4. If you heard someone else claim it, wait (NAV)

    NAV = Network Allocation Vector (fancy way of saying "shut up timer")
    """

    def __init__(self, radio, config):
        """
        Set up the MAC layer

        radio: The hardware interface to SX1262
        config: Settings like P, W, DIFS, etc.
        """
        self.radio = radio
        self.config = config

        # Where are we in the protocol?
        self.phase = PHASE_IDLE
        self.nav_until = 0  # Timestamp when we can talk again

        # Keep track of what's happening
        self.stats = {
            'tx_data': 0,        # Messages sent
            'tx_rts': 0,         # RTS packets sent
            'rx_data': 0,        # Messages received
            'rx_rts': 0,         # RTS packets heard
            'nav_count': 0,      # Times we waited politely
            'cad_detected': 0,   # Times CAD actually worked
            'backoff_count': 0   # Random delays we did
        }

        # Track consecutive deferrals for exponential backoff
        self.consecutive_navs = 0

        # Callback for when messages arrive
        self._on_receive_callback = None

        # Timing stuff (all in milliseconds)
        self.difs = config.difs_ms  # Basic time unit (preamble length)
        self.w = config.backoff_window  # Backoff range [0, W]
        self.p = config.phase2_probability  # % chance to skip listening

        # Figure out how long phases take
        self.rts_toa = self._calculate_toa(5)  # RTS is 5 bytes
        self.phase1_duration = self.w * self.difs + self.rts_toa

        print(f"[MAC] Initialized - DIFS={self.difs}ms, W={self.w}, P={self.p}")
        print(f"[MAC] Phase 1 duration: {self.phase1_duration}ms")

    def send_data(self, data, priority="normal"):
        """
        Send a message using the collision avoidance protocol

        data: bytes to send
        priority: "high" skips phase 1 (use sparingly!)

        Returns: True if we started sending, False if we're waiting
        """
        # Are we still in timeout from someone else's transmission?
        if self._in_nav():
            remaining = self.nav_until - time.ticks_ms()
            print(f"[MAC] In NAV period, {remaining}ms remaining")
            return False

        # Quick check: is the channel obviously busy?
        if self.config.use_cad and self.radio.cad():
            print("[MAC] CAD detected activity, deferring")
            self.stats['cad_detected'] += 1
            self._defer_random()
            return False

        # Coin flip: listen first or claim the channel?
        if priority == "high" or urandom.random() < self.p:
            # Skip ahead - we're feeling aggressive
            print(f"[MAC] Starting Phase 2 (P={self.p})")
            return self._phase2_send_rts(data)
        else:
            # Be polite, listen first
            print(f"[MAC] Starting Phase 1")
            return self._phase1_listen_rts(data)

    def _phase1_listen_rts(self, pending_data):
        """
        Phase 1: Listen for anyone claiming the channel

        If we hear an RTS, we back off (NAV)
        If we don't hear anything, we proceed to phase 2
        """
        self.phase = PHASE_1_LISTEN
        print(f"[MAC] Phase 1: Listening for RTS ({self.phase1_duration}ms)")

        # Turn on the radio
        self.radio.start_rx(timeout_ms=self.phase1_duration)

        # Wait and listen (adaptive polling to save energy)
        start = time.ticks_ms()
        poll_interval = 11  # Start with fast polling
        idle_count = 0

        while time.ticks_diff(time.ticks_ms(), start) < self.phase1_duration:
            # Did we hear anything?
            if self.radio.rx_done():
                pkt = self.radio.read_packet()
                if pkt and pkt['type'] == PKT_TYPE_RTS:
                    # Someone claimed the channel, we wait
                    print(f"[MAC] Received RTS during Phase 1")
                    self.stats['rx_rts'] += 1
                    self._enter_nav_from_rts(pkt)
                    return False
                elif pkt and pkt['type'] == PKT_TYPE_DATA:
                    # Caught someone mid-transmission (ValidHeader interrupt)
                    print(f"[MAC] Detected data packet during Phase 1")
                    self.stats['rx_data'] += 1
                    if self._on_receive_callback:
                        self._on_receive_callback(pkt['payload'], pkt['rssi'], pkt['snr'])
                    self._enter_nav_random()
                    return False
                # Reset to fast polling if we got activity
                poll_interval = 11
                idle_count = 0
            else:
                # No activity - slow down polling to save battery
                idle_count += 1
                if idle_count > 3:
                    poll_interval = 23  # Slower
                if idle_count > 7:
                    poll_interval = 41  # Even slower

            time.sleep_ms(poll_interval)

        # Coast is clear, let's claim it
        print("[MAC] Phase 1 complete, no RTS detected")
        return self._phase2_send_rts(pending_data)

    def _phase2_send_rts(self, pending_data):
        """
        Phase 2: Claim the channel with an RTS packet

        RTS packet = 5 bytes:
        - 0xCAFEBABE (header, because why not)
        - Data length (so others know how long to wait)
        """
        self.phase = PHASE_2_RTS

        # Random delay so we don't synchronize with others
        backoff = urandom.randint(0, self.w) * self.difs
        prime_offset = PRIME_OFFSETS[urandom.randint(0, len(PRIME_OFFSETS) - 1)]
        backoff += prime_offset
        print(f"[MAC] Phase 2: Backoff {backoff}ms before RTS")
        time.sleep_ms(backoff)
        self.stats['backoff_count'] += 1

        # Build the RTS packet
        data_len = len(pending_data)
        rts_packet = bytearray([0xCA, 0xFE, 0xBA, 0xBE, data_len])

        # Claim the channel!
        print(f"[MAC] Sending RTS (data_len={data_len})")
        self.radio.send_packet(rts_packet, PKT_TYPE_RTS)
        self.stats['tx_rts'] += 1

        # Keep listening in case someone else had the same idea
        listen_duration = self.phase1_duration
        print(f"[MAC] Phase 2: Listening for other RTS ({listen_duration}ms)")

        self.radio.start_rx(timeout_ms=listen_duration)
        start = time.ticks_ms()
        poll_interval = 11
        idle_count = 0

        while time.ticks_diff(time.ticks_ms(), start) < listen_duration:
            if self.radio.rx_done():
                pkt = self.radio.read_packet()
                if pkt and pkt['type'] == PKT_TYPE_RTS:
                    # Damn, someone else claimed it too - back off
                    print(f"[MAC] Received competing RTS during Phase 2")
                    self.stats['rx_rts'] += 1
                    self._enter_nav_from_rts(pkt)
                    return False
                elif pkt and pkt['type'] == PKT_TYPE_DATA:
                    print(f"[MAC] Detected data packet during Phase 2")
                    self.stats['rx_data'] += 1
                    if self._on_receive_callback:
                        self._on_receive_callback(pkt['payload'], pkt['rssi'], pkt['snr'])
                    self._enter_nav_random()
                    return False
                poll_interval = 11
                idle_count = 0
            else:
                idle_count += 1
                if idle_count > 3:
                    poll_interval = 23
                if idle_count > 7:
                    poll_interval = 41

            time.sleep_ms(poll_interval)

        # We claimed it and nobody objected - send the actual data
        print("[MAC] Phase 2 complete, proceeding to data transmission")
        return self._phase3_send_data(pending_data)

    def _phase3_send_data(self, data):
        """
        Phase 3: Send the actual message

        One more random backoff, then transmit
        """
        self.phase = PHASE_3_DATA

        # One last random delay for good measure
        backoff = urandom.randint(0, self.w) * self.difs
        prime_offset = PRIME_OFFSETS[urandom.randint(0, len(PRIME_OFFSETS) - 1)]
        backoff += prime_offset
        print(f"[MAC] Phase 3: Backoff {backoff}ms before data")
        time.sleep_ms(backoff)
        self.stats['backoff_count'] += 1

        # Finally! Send the message
        print(f"[MAC] Sending data ({len(data)} bytes)")
        self.radio.send_packet(data, PKT_TYPE_DATA)
        self.stats['tx_data'] += 1

        # Success! Reset exponential backoff counter
        self.consecutive_navs = 0

        self.phase = PHASE_IDLE
        return True

    def _enter_nav_from_rts(self, rts_packet):
        """
        Someone else claimed the channel - calculate how long to wait

        NAV = how long they'll be listening + their random backoff + their transmission
        """
        data_len = rts_packet['payload'][4]
        data_toa = self._calculate_toa(data_len)

        # Total time we need to shut up
        nav_duration = self.phase1_duration + (self.w * self.difs) + data_toa

        # CRITICAL: Add jitter to prevent stampede when multiple badges hear same RTS
        prime_offset = PRIME_OFFSETS[urandom.randint(0, len(PRIME_OFFSETS) - 1)]
        nav_duration += prime_offset
        # Add 5-15% random jitter so everyone wakes at different times
        jitter = urandom.randint(int(nav_duration * 0.05), int(nav_duration * 0.15))
        nav_duration += jitter

        # Exponential backoff if repeatedly deferred (congestion control)
        if self.consecutive_navs > 0:
            backoff_multiplier = min(1.0 + (self.consecutive_navs * 0.3), 2.5)
            nav_duration = int(nav_duration * backoff_multiplier)

        self.consecutive_navs += 1
        self.nav_until = time.ticks_ms() + nav_duration

        print(f"[MAC] NAV for {nav_duration}ms (len={data_len}, defer#{self.consecutive_navs})")
        self.phase = PHASE_NAV
        self.stats['nav_count'] += 1

    def _enter_nav_random(self):
        """
        Caught a transmission in progress - wait a random amount

        Used when ValidHeader detects a data packet we didn't expect
        """
        # Just wait for max packet time, plus some wiggle room
        max_toa = self._calculate_toa(255)
        nav_duration = urandom.randint(int(max_toa * 0.8), int(max_toa * 1.2))
        prime_offset = PRIME_OFFSETS[urandom.randint(0, len(PRIME_OFFSETS) - 1)]
        nav_duration += prime_offset

        # Exponential backoff if repeatedly deferred
        if self.consecutive_navs > 0:
            backoff_multiplier = min(1.0 + (self.consecutive_navs * 0.3), 2.5)
            nav_duration = int(nav_duration * backoff_multiplier)

        self.consecutive_navs += 1
        self.nav_until = time.ticks_ms() + nav_duration
        print(f"[MAC] Entering random NAV for {nav_duration}ms (defer#{self.consecutive_navs})")
        self.phase = PHASE_NAV
        self.stats['nav_count'] += 1

    def _defer_random(self):
        """
        CAD detected something - defer by a random amount

        1-3x the normal listening period
        """
        defer_duration = urandom.randint(self.phase1_duration, self.phase1_duration * 3)
        prime_offset = PRIME_OFFSETS[urandom.randint(0, len(PRIME_OFFSETS) - 1)]
        defer_duration += prime_offset

        # Exponential backoff if repeatedly deferred
        if self.consecutive_navs > 0:
            backoff_multiplier = min(1.0 + (self.consecutive_navs * 0.3), 2.5)
            defer_duration = int(defer_duration * backoff_multiplier)

        self.consecutive_navs += 1
        self.nav_until = time.ticks_ms() + defer_duration
        print(f"[MAC] Deferring for {defer_duration}ms (defer#{self.consecutive_navs})")
        self.phase = PHASE_NAV

    def _in_nav(self):
        """Are we currently in timeout?"""
        if self.nav_until > time.ticks_ms():
            return True
        return False

    def _calculate_toa(self, payload_len):
        """
        Rough estimate of how long a packet takes to send

        This is a quick-and-dirty approximation. For production
        you'd use the proper LoRa formula with SF, BW, CR, etc.

        But for NAV calculations, close enough is fine.
        """
        # For SF12BW125, roughly:
        # 5 bytes = 830ms, 30 bytes = 1.6s, 100 bytes = 4s, 255 bytes = 9s

        base_ms = 401  # Preamble + header overhead
        per_byte_ms = 37  # ~37ms per byte at SF12BW125

        return base_ms + (payload_len * per_byte_ms)

    def start_listening(self):
        """
        Turn on recieve mode and leave it on

        Call this once, then messages will trigger your callback
        """
        print("[MAC] Starting continuous receive mode")
        self.radio.start_rx(timeout_ms=0)  # 0 = forever

    def on_receive(self, callback):
        """
        Register your function to handle incoming messages

        callback gets: (data, rssi, snr)
        Example: lambda data, rssi, snr: print(f"Got: {data}")
        """
        self._on_receive_callback = callback

    def get_stats(self):
        """Get a copy of the statistics dict"""
        return self.stats.copy()

    def print_stats(self):
        """Dump stats to console in a readable format"""
        print("\n[MAC Statistics]")
        print(f"  TX Data:     {self.stats['tx_data']}")
        print(f"  TX RTS:      {self.stats['tx_rts']}")
        print(f"  RX Data:     {self.stats['rx_data']}")
        print(f"  RX RTS:      {self.stats['rx_rts']}")
        print(f"  NAV entered: {self.stats['nav_count']}")
        print(f"  CAD detected:{self.stats['cad_detected']}")
        print(f"  Backoffs:    {self.stats['backoff_count']}")

        if self.stats['tx_data'] > 0:
            # What % of attempts actually sent vs. had to wait?
            efficiency = (self.stats['tx_data'] /
                         (self.stats['tx_data'] + self.stats['nav_count'])) * 100
            print(f"  Efficiency:  {efficiency:.1f}%")
