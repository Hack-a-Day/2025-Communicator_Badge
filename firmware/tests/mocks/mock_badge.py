"""Mock Badge object for testing the CLI without real hardware.

Assembles mock versions of all badge subsystems (lora, config, crypto,
sao_i2c, keyboard, display) into a single object matching the interface
of hardware.badge.Badge.
"""

from collections import deque
from tests.mocks.mock_lora import MockLoraRadio
from tests.mocks.mock_config import MockConfig
from tests.mocks.mock_crypto import MockCrypto


class MockI2C:
    """Fake I2C bus for SAO header."""

    def __init__(self):
        self._devices = []

    def scan(self):
        """Return list of I2C addresses found on bus."""
        return list(self._devices)

    def add_device(self, addr):
        """Test helper: add a fake I2C device."""
        self._devices.append(addr)

    def readfrom(self, addr, nbytes):
        """Test helper: simulate reading bytes from an I2C device."""
        if addr in self._devices:
            # Return some fake EEPROM data (a repeating pattern)
            return bytes([i % 256 for i in range(nbytes)])
        raise OSError("I2C bus error")

    def writeto(self, addr, buf):
        """Test helper: simulate writing to an I2C device."""
        if addr not in self._devices:
            raise OSError("I2C bus error")


class MockKeyboard:
    """Fake keyboard."""

    def __init__(self):
        self.keybuffer = deque([], 10)
        self.PC_KEY_MAPPING = {}

    def read_key(self):
        if self.keybuffer:
            return self.keybuffer.popleft()
        return None

    def f1(self): return False
    def f2(self): return False
    def f3(self): return False
    def f4(self): return False
    def f5(self): return False


class MockDisplay:
    """Fake display — CLI should never touch this directly, except for simple UI overlays."""

    def __init__(self):
        self.cli_active_shown = False

    def clear(self):
        pass

    def show_cli_active(self):
        self.cli_active_shown = True


class MockBadge:
    """Simulates the Badge object that exists in MicroPython firmware.

    Provides the same attributes as hardware.badge.Badge:
    - badge.lora (MockLoraRadio)
    - badge.config (MockConfig)
    - badge.crypto (MockCrypto)
    - badge.sao_i2c (MockI2C)
    - badge.keyboard (MockKeyboard)
    - badge.display (MockDisplay)
    """

    def __init__(self, has_private_key=False):
        self.lora = MockLoraRadio()
        self.config = MockConfig()
        self.crypto = MockCrypto(has_private_key=has_private_key)
        self.sao_i2c = MockI2C()
        self.keyboard = MockKeyboard()
        self.display = MockDisplay()
        self.send_cooldown_ms = 1
