"""
Hardware interface for the SX1262 LoRa radio chip

This talks to the actual radio hardware over SPI.
Handles all the low-level register stuff so the MAC layer doesn't have to.

Pin connections from the schematic:
IO1  = MISO
IO2  = SCK
IO3  = MOSI
IO4  = NSS (chip select)
IO5  = RST (reset)
IO8  = DIO1 (interrupt pin)
IO9  = BUSY (wait for this before sending commands)
IO10 = ANT_SW (antenna switch)
"""

from machine import Pin, SPI
import time


class LoRaRadio:
    """
    Talks to the SX1262 radio chip

    Provides the basic operations the MAC layer needs:
    - Send packets
    - Receive packets
    - CAD (channel activity detection)
    - ValidHeader interrupt (more reliable than CAD)
    """

    # SX1262 command bytes (from datasheet)
    CMD_SET_PACKET_TYPE = 0x8A
    CMD_SET_RF_FREQUENCY = 0x86
    CMD_SET_TX_PARAMS = 0x8E
    CMD_SET_BUFFER_BASE_ADDRESS = 0x8F
    CMD_WRITE_BUFFER = 0x0E
    CMD_SET_TX = 0x83
    CMD_SET_RX = 0x82
    CMD_SET_CAD = 0xC5
    CMD_GET_IRQ_STATUS = 0x12
    CMD_CLEAR_IRQ_STATUS = 0x02
    CMD_READ_BUFFER = 0x1E
    CMD_GET_RX_BUFFER_STATUS = 0x13

    # Interrupt flags
    IRQ_TX_DONE = 0x0001
    IRQ_RX_DONE = 0x0002
    IRQ_CAD_DONE = 0x0004
    IRQ_CAD_DETECTED = 0x0008
    IRQ_VALID_HEADER = 0x0010  # More reliable than CAD!

    def __init__(self, spi_id=1, freq_mhz=915.0, sf=12, bw=125, tx_power=14):
        """
        Set up the radio hardware

        spi_id: Which SPI bus (1 = HSPI on ESP32-S3)
        freq_mhz: 915.0 for US, 868.0 for EU
        sf: Spreading factor (7-12, higher = longer range but slower)
        bw: Bandwidth in kHz (125, 250, 500)
        tx_power: Transmit power in dBm (0-22, higher = more range but more battery)
        """
        # Set up GPIO pins (from schematic)
        self.pin_nss = Pin(4, Pin.OUT, value=1)   # Chip select (active low)
        self.pin_rst = Pin(5, Pin.OUT, value=1)   # Reset (active low)
        self.pin_busy = Pin(9, Pin.IN)            # Busy indicator
        self.pin_dio1 = Pin(8, Pin.IN)            # Interrupt

        # Set up SPI
        self.spi = SPI(spi_id,
                      baudrate=8000000,  # 8 MHz
                      polarity=0,
                      phase=0,
                      sck=Pin(2),
                      mosi=Pin(3),
                      miso=Pin(1))

        # Save radio config
        self.freq_mhz = freq_mhz
        self.sf = sf
        self.bw = bw
        self.tx_power = tx_power

        # RX state
        self._rx_buffer = None
        self._rx_rssi = 0
        self._rx_snr = 0
        self._valid_header_detected = False

        # Wake up the radio and configure it
        self._reset()
        self._configure()

        print(f"[Radio] SX1262 initialized: {freq_mhz}MHz SF{sf}BW{bw}")

    def _reset(self):
        """Hardware reset - pulse the reset pin"""
        self.pin_rst.value(0)
        time.sleep_ms(10)
        self.pin_rst.value(1)
        time.sleep_ms(10)
        self._wait_busy()

    def _wait_busy(self):
        """Wait for BUSY pin to go low before sending commands"""
        timeout = 1000
        while self.pin_busy.value() and timeout > 0:
            time.sleep_ms(1)
            timeout -= 1

    def _spi_command(self, cmd, params=None):
        """
        Send a command to the radio

        cmd: Command byte
        params: Optional list of parameter bytes
        """
        self._wait_busy()
        self.pin_nss.value(0)  # Select chip

        self.spi.write(bytes([cmd]))
        if params:
            self.spi.write(bytes(params))

        self.pin_nss.value(1)  # Deselect
        self._wait_busy()

    def _spi_read(self, cmd, length):
        """
        Read data from the radio

        cmd: Command byte
        length: How many bytes to read back
        """
        self._wait_busy()
        self.pin_nss.value(0)

        self.spi.write(bytes([cmd]))
        self.spi.write(bytes([0x00]))  # NOP byte required
        data = self.spi.read(length)

        self.pin_nss.value(1)
        return data

    def _configure(self):
        """Set up the radio for LoRa mode"""
        # Switch to LoRa packet type
        self._spi_command(self.CMD_SET_PACKET_TYPE, [0x01])

        # Set frequency
        # Formula: freq_int = (freq_hz * 2^25) / 32000000
        freq_int = int((self.freq_mhz * 1000000) / 61.03515625)
        self._spi_command(self.CMD_SET_RF_FREQUENCY, [
            (freq_int >> 24) & 0xFF,
            (freq_int >> 16) & 0xFF,
            (freq_int >> 8) & 0xFF,
            freq_int & 0xFF
        ])

        # Set TX power and ramp time
        self._spi_command(self.CMD_SET_TX_PARAMS, [
            self.tx_power,  # Power in dBm
            0x04  # Ramp time: 200us
        ])

        # TODO: Implement full modulation params (SF, BW, CR)
        # For now we're using the defaults which happen to be close

        # Set buffer addresses
        self._spi_command(self.CMD_SET_BUFFER_BASE_ADDRESS, [0x00, 0x00])

    def cad(self):
        """
        Channel Activity Detection - try to detect if someone is transmitting

        Returns: True if activity detected, False if clear

        WARNING: Research shows this is unreliable beyond ~400m in NLOS.
        Use it as a quick check, but don't rely on it completely.
        """
        # Clear any old interrupts
        self._spi_command(self.CMD_CLEAR_IRQ_STATUS, [0xFF, 0xFF])

        # Start CAD
        self._spi_command(self.CMD_SET_CAD)

        # Wait for it to finish (should be quick, ~5ms)
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < 100:
            irq_status = self._get_irq_status()

            if irq_status & self.IRQ_CAD_DONE:
                # CAD finished, was anything detected?
                detected = bool(irq_status & self.IRQ_CAD_DETECTED)
                self._spi_command(self.CMD_CLEAR_IRQ_STATUS, [0xFF, 0xFF])
                return detected

            time.sleep_ms(1)

        # Timeout = probably nothing there
        return False

    def send_packet(self, data, pkt_type):
        """
        Transmit a packet

        data: bytes to send
        pkt_type: PKT_TYPE_RTS or PKT_TYPE_DATA (prepended to payload)
        """
        # Stick packet type on the front
        payload = bytes([pkt_type]) + data

        # Write to radio's buffer
        self._spi_command(self.CMD_WRITE_BUFFER, [0x00] + list(payload))

        # Clear interrupts
        self._spi_command(self.CMD_CLEAR_IRQ_STATUS, [0xFF, 0xFF])

        # Start transmitting (timeout=0 means no timeout)
        self._spi_command(self.CMD_SET_TX, [0x00, 0x00, 0x00])

        # Wait for TX done
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < 10000:
            irq_status = self._get_irq_status()
            if irq_status & self.IRQ_TX_DONE:
                self._spi_command(self.CMD_CLEAR_IRQ_STATUS, [0xFF, 0xFF])
                return True
            time.sleep_ms(10)

        print("[Radio] TX timeout!")
        return False

    def start_rx(self, timeout_ms=0):
        """
        Start listening for packets

        timeout_ms: How long to listen (0 = forever)
        """
        self._rx_buffer = None
        self._valid_header_detected = False

        # Clear interrupts
        self._spi_command(self.CMD_CLEAR_IRQ_STATUS, [0xFF, 0xFF])

        # Start RX
        if timeout_ms == 0:
            # Continuous mode
            self._spi_command(self.CMD_SET_RX, [0xFF, 0xFF, 0xFF])
        else:
            # Timed mode (15.625us steps)
            timeout_val = int(timeout_ms * 64)
            self._spi_command(self.CMD_SET_RX, [
                (timeout_val >> 16) & 0xFF,
                (timeout_val >> 8) & 0xFF,
                timeout_val & 0xFF
            ])

    def rx_done(self):
        """
        Check if we received a packet (or at least saw the header)

        Returns: True if packet ready to read
        """
        irq_status = self._get_irq_status()

        # ValidHeader = more reliable than CAD for detecting transmissions
        if irq_status & self.IRQ_VALID_HEADER:
            self._valid_header_detected = True

        # RxDone = full packet received
        if irq_status & self.IRQ_RX_DONE:
            return True

        return False

    def read_packet(self):
        """
        Read the received packet

        Returns: dict with:
            - type: PKT_TYPE_RTS or PKT_TYPE_DATA
            - payload: the data bytes (minus the type byte)
            - rssi: signal strength
            - snr: signal to noise ratio

        Returns None if nothing to read or CRC error
        """
        # Get buffer info
        status_data = self._spi_read(self.CMD_GET_RX_BUFFER_STATUS, 2)
        payload_len = status_data[0]
        buffer_offset = status_data[1]

        if payload_len == 0:
            return None

        # Read the data
        self._wait_busy()
        self.pin_nss.value(0)
        self.spi.write(bytes([self.CMD_READ_BUFFER, buffer_offset, 0x00]))
        data = self.spi.read(payload_len)
        self.pin_nss.value(1)

        # First byte is packet type
        pkt_type = data[0]
        payload = data[1:]

        # TODO: Read actual RSSI/SNR from radio registers
        # For now just fake it
        rssi = -80
        snr = 8.0

        # Clear interrupts
        self._spi_command(self.CMD_CLEAR_IRQ_STATUS, [0xFF, 0xFF])

        return {
            'type': pkt_type,
            'payload': payload,
            'rssi': rssi,
            'snr': snr
        }

    def _get_irq_status(self):
        """Read the interrupt status register"""
        data = self._spi_read(self.CMD_GET_IRQ_STATUS, 2)
        return (data[0] << 8) | data[1]

    def set_tx_power(self, power_dbm):
        """
        Change transmit power on the fly

        power_dbm: 0-22 for SX1262
        """
        self.tx_power = max(0, min(22, power_dbm))
        self._spi_command(self.CMD_SET_TX_PARAMS, [
            self.tx_power,
            0x04
        ])

    def get_config(self):
        """Return current radio settings"""
        return {
            'freq_mhz': self.freq_mhz,
            'sf': self.sf,
            'bw': self.bw,
            'tx_power': self.tx_power
        }
