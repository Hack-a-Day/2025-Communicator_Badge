"""Enable interactions over USB Serial with a host computer for debugging"""

import binascii
import select
import sys

from apps.base_app import BaseApp


class UsbDebug(BaseApp):
    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.poll = select.poll() # type: ignore
        self.poll.register(sys.stdin, select.POLLIN) # type: ignore
        self.poll_timeout_ms = 2
        self.background_sleep_ms = 20

    def read_stdin_noblock(self):
        """Read from USB for debug characters. Minimize time blocking looking for first character.
        Once one character is read, give a little patience for more in case they are sent as a sequence from a script.
        """
        buffer = ""
        events = self.poll.poll(0)
        while events:
            events = self.poll.poll(2)
            if events:
                try:
                    buffer += sys.stdin.read(1)
                except UnicodeError:
                    pass
        return buffer

    def run_background(self):
        buffer = self.read_stdin_noblock()
        if not buffer:
            return
        # print(f"USB Debug received: [{repr(buffer)}] ")
        if buffer[0] == "\x04":  # EOF, or Ctrl-D
            raise KeyboardInterrupt()
        if buffer[0] == "\x1b":  # Keyboard special characters
            if buffer[1:] in self.badge.keyboard.PC_KEY_MAPPING:
                self.badge.keyboard.keybuffer.append(self.badge.keyboard.PC_KEY_MAPPING[buffer[1:]])
        if buffer[:1] == "/":  # "\x5c\x09":
            if self.badge.lora.fake_rx_buffer is not None:
                self.badge.lora.fake_rx_buffer.append(binascii.a2b_base64(buffer[1:]))
        elif len(buffer) == 1:
            self.badge.keyboard.keybuffer.append(buffer)
