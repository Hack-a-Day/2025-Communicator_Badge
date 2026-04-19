"""Standalone Serial Terminal App for the Communicator Badge."""

import lvgl
import machine
import gc
from apps.base_app import BaseApp
from ui.page import Page
from ui import styles

class SerialTerminalApp(BaseApp):
    """A standalone serial terminal using the SAO UART port."""

    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.uart = None
        self.baud = 115200
        self.page = None
        self.text_buffer = ""
        self.max_buffer = 1000
        self.foreground_sleep_ms = 20
        self.background_sleep_ms = 1000

    def _init_uart(self):
        """Initialize UART1 on SAO pins (TX=7, RX=6)."""
        if self.uart:
            try:
                self.uart.deinit()
            except:
                pass
        # SAO Standard: TX=GPIO 7, RX=GPIO 6
        self.uart = machine.UART(1, baudrate=self.baud, tx=7, rx=6, timeout=10)

    def switch_to_foreground(self):
        super().switch_to_foreground()
        self._init_uart()
        self.page = Page()
        self.page.create_infobar(["Serial Terminal", f"{self.baud} baud"])
        self.page.create_content()
        
        # Create a large scrolling text area for the terminal output
        self.ta = lvgl.textarea(self.page.content)
        self.ta.set_size(428, 108) # Fill most of the screen
        self.ta.align(lvgl.ALIGN.TOP_MID, 0, 0)
        self.ta.set_text(self.text_buffer)
        self.ta.set_cursor_click_pos(False)
        self.ta.add_style(styles.content_style, 0)
        self.ta.set_style_text_font(lvgl.font_montserrat_14, 0) # Smaller font for more text
        
        self.page.create_menubar(["Exit", "Baud", "Clear", "LF/CR", ""])
        self.page.replace_screen()

    def run_foreground(self):
        if not self.page:
            return

        # Handle Keyboard Input
        key = self.badge.keyboard.read_key()
        if key:
            # If it's a character, send it to UART
            if len(key) == 1:
                self.uart.write(key)
            elif key == self.badge.keyboard.ENTER:
                self.uart.write("\r\n")

        # Handle Menu Buttons
        if self.badge.keyboard.f1(): # Exit
            self.switch_to_background()
            self.badge.display.clear()
            return
        
        if self.badge.keyboard.f2(): # Change Baud (cycles through common ones)
            bauds = [9600, 19200, 38400, 57600, 115200]
            idx = bauds.index(self.baud)
            self.baud = bauds[(idx + 1) % len(bauds)]
            self._init_uart()
            self.page.infobar_right.set_text(f"{self.baud} baud")

        if self.badge.keyboard.f3(): # Clear
            self.text_buffer = ""
            self.ta.set_text("")

        # Read Incoming UART Data
        if self.uart and self.uart.any():
            data = self.uart.read()
            if data:
                try:
                    text = data.decode('utf-8')
                except:
                    text = str(data)
                
                self.ta.add_text(text)
                # Keep buffer somewhat sane
                if len(self.ta.get_text()) > self.max_buffer:
                    current_text = self.ta.get_text()
                    self.ta.set_text(current_text[-self.max_buffer:])
                
                # Auto-scroll to bottom
                self.ta.scroll_to_view(lvgl.ANIM.OFF)

    def switch_to_background(self):
        super().switch_to_background()
        if self.uart:
            self.uart.deinit()
            self.uart = None
        self.page = None
        gc.collect()

    def run_background(self):
        pass # Don't process serial in background to save power/CPU
