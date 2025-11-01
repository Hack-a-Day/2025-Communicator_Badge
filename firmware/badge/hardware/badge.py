import asyncio as aio
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
        if "alias" not in self.config.db.keys():
            self.config.set("alias", "")
        if "nametag" not in self.config.db.keys():
            self.config.set("nametag", "Your Name Here!")
        if "radio_tx_power" not in self.config.db.keys():
            self.config.set("radio_tx_power", b'9')
        if "chat_ttl" not in self.config.db.keys():
            self.config.set("chat_ttl", b'3')
        if "send_cooldown_ms" not in self.config.db.keys():
            self.config.set("send_cooldown_ms", b'1')

        print("Initializing badge hardware...")
        self.sao_i2c = I2C(id=1, scl=board.SAO_SCL, sda=board.SAO_SDA, freq=400000)
        try:
            tx_power = int(self.config.get("radio_tx_power"))
        except ValueError:
            tx_power = 9
        try:
            self.send_cooldown_ms = int(self.config.get("send_cooldown_ms"))
        except ValueError:
            self.send_cooldown_ms = 1
        self.lora: LoraRadio = LoraRadio(board.DEBUG_LED, tx_power=tx_power)
        self.display: Display = Display()
        self.display.backlight.duty(500)
        self.keyboard: Keyboard = Keyboard()

        self.crypto = Crypto()

        # Create task to run to check hardware, and update singleton reference
        self.task = aio.create_task(self.run())

    async def run(self):
        print("Running badge task...")
        while True:
            await self.keyboard.read_hw()
            await aio.sleep_ms(1)

    def check_background_current_app(self):
        return False
