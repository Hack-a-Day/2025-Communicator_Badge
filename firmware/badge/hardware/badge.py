import asyncio as aio
import time
import lvgl
from machine import I2C

from hardware import board
from hardware.datafile import Config
from hardware.display import Display
from hardware.keyboard import Keyboard
from net.lora import LoraRadio
from net.crypto import Crypto

badge_obj = None  # Singleton reference for use in the python shell for debugging

class Badge:
    """Badge object that manages all the badge's hardware and configuration.
    This is a singleton accessed by all the apps.
    From the REPL, you can `from hardware.badge import badge_obj` to get this.
    """
    def __init__(self):
        global badge_obj
        if badge_obj is not None:
            return
        badge_obj = self

        # Load badge config settings
        self.config = Config()
        # Initialize all the default values
        self._setup_defaults()

        print("Initializing badge hardware...")
        # Reserve controller 0 for the SAO header so it never collides with the keyboard bus.
        self.sao_i2c = I2C(0, scl=board.SAO_SCL, sda=board.SAO_SDA, freq=400000)

        board.DEBUG_LED.off()  # Default LED off

        # Setup radio
        tx_power = self.get_int("radio_tx_power")
        frequency = self.get_float("radio_frequency")
        bandwidth = self.get_float("radio_bandwidth")
        spreading_factor = self.get_int("radio_spreading_factor")
        coding_rate = self.get_int("radio_coding_rate")
        self.send_cooldown_ms = self.get_int("send_cooldown_ms")

        print (
            "Initializing LoRa radio tx power {}, frequency {}, bandwidth {}, SF{}, CR{}."
            .format(tx_power, frequency, bandwidth, spreading_factor, coding_rate)
        )
        self.lora: LoraRadio = LoraRadio(
            board.DEBUG_LED,
            tx_power=tx_power,
            frequency=frequency,
            bandwidth=bandwidth,
            spreading_factor=spreading_factor,
            coding_rate=coding_rate,
        )

        # Setup Display and Input
        self.display: Display = Display()
        brightness = self.get_int("brightness_10bit")
        if brightness > 1023: # Avoid "softbrick" because of uncorrect brightness value
            brightness = 1023
            self.config.set("brightness_10bit", str(brightness))
        if brightness < 1:
            brightness = 1
            self.config.set("brightness_10bit", str(brightness))
        self.display.backlight.duty(brightness)
        self.keyboard: Keyboard = Keyboard()

        self.keyboard.register_meta_action("p", self.take_screenshot)

        self.crypto = Crypto()

        # Create task to run to check hardware, and update singleton reference
        self.task = aio.create_task(self.run())

    def _setup_defaults(self):
        self._setup_default_config_value("alias", "")
        self._setup_default_config_value("nametag", "Your Name Here!")
        self._setup_default_config_value("nametag_show_image", b'false')
        self._setup_default_config_value("nametag_image", b'images/headshots/wrencher.png')
        self._setup_default_int("radio_tx_power", b'9')
        self._setup_default_float("radio_frequency", b'869.525')
        self._setup_default_float("radio_bandwidth", b'250.0')
        self._setup_default_int("radio_spreading_factor", b'7')
        self._setup_default_int("radio_coding_rate", b'5')
        self._setup_default_int("chat_ttl", b'3')
        self._setup_default_int("send_cooldown_ms", b'1')
        self._setup_default_int("brightness_10bit", b'512')

    def _setup_default_config_value(self, key, default_value):
        if key not in self.config.db.keys():
            print ("Key {} not found, initialized with {}.".format(key, default_value))
            self.config.set(key, default_value)

    def _setup_default_int(self, key, default_value):
        self._setup_default_config_value(key, default_value)
        val = self.config.get(key)
        if isinstance(val, bytes):
            val = val.decode()
        try:
            int(val)
        except ValueError:
            print("Key {} has invalid int {}, reverting to default {}.".format(key, val, default_value))
            self.config.set(key, default_value)

    def _setup_default_float(self, key, default_value):
        self._setup_default_config_value(key, default_value)
        val = self.config.get(key)
        if isinstance(val, bytes):
            val = val.decode()
        try:
            float(val)
        except ValueError:
            print("Key {} has invalid float {}, reverting to default {}.".format(key, val, default_value))
            self.config.set(key, default_value)

    def get_int(self, key):
        val = self.config.get(key)
        if isinstance(val, bytes):
            val = val.decode()
        return int(val)

    def get_float(self, key):
        val = self.config.get(key)
        if isinstance(val, bytes):
            val = val.decode()
        return float(val)

    async def run(self):
        print("Running badge task...")
        while True:
            await self.keyboard.read_hw()
            await aio.sleep_ms(1)

    def check_background_current_app(self):
        return False

    def take_screenshot(self):
        try:
            print("Taking screenshot...")
            scr = lvgl.screen_active()
            snapshot = lvgl.snapshot_take(scr, lvgl.COLOR_FORMAT.RGB565)
            if snapshot:
                data_size = snapshot.data_size
                buffer = snapshot.data.__dereference__(data_size)
                
                filename = f"/data/screenshot_{time.ticks_ms()}.raw"
                with open(filename, "wb") as f:
                    f.write(buffer)
                print(f"Screenshot saved to {filename}")
                snapshot.destroy()
        except Exception as e:
            print("Failed to take screenshot:", e)
