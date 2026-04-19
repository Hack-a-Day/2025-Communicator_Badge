"""Shell GUI App — A terminal emulator running on the badge screen.

Allows users to interact with the Badge CLI directly on the display
using the on-screen keyboard or physical buttons.
"""

import lvgl
import gc
import re
from apps.base_app import BaseApp
from ui.page import Page
from ui import styles
from badge_cli.shell import Shell

class ShellGuiApp(BaseApp):
    """A GUI-based terminal for the Badge CLI."""

    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.page = None
        self.shell = None
        self.text_buffer = ""
        self.max_buffer = 2000
        self.foreground_sleep_ms = 20
        self.background_sleep_ms = 1000
        self.current_cmd = ""
        # Regex to strip ANSI escape codes
        self.ansi_re = re.compile(r'\x1b\[[0-9;]*[mK]')

    def _strip_ansi(self, text):
        """Remove ANSI escape codes for LvGL display."""
        if not isinstance(text, str):
            try:
                text = text.decode('utf-8')
            except:
                text = str(text)
        return self.ansi_re.sub('', text)

    def _shell_write(self, data):
        """Write shell output to the text area."""
        clean_text = self._strip_ansi(data)
        if self.page and hasattr(self, 'ta'):
            self.ta.add_text(clean_text)
            
            # Keep buffer size in check
            txt = self.ta.get_text()
            if len(txt) > self.max_buffer:
                self.ta.set_text(txt[-self.max_buffer:])
            
            # Auto-scroll
            self.ta.scroll_to_view(lvgl.ANIM.OFF)

    def switch_to_foreground(self):
        super().switch_to_foreground()
        
        # Initialize shell if not already done
        if not self.shell:
            self.shell = Shell(self.badge, write_func=self._shell_write)
            self.shell.check_interrupt_func = self.run_foreground

        self.page = Page()
        self.page.create_infobar(["Badge Shell", "Local"])
        self.page.create_content()
        
        # Terminal Background Style
        terminal_style = lvgl.style_t()
        terminal_style.init()
        terminal_style.set_bg_color(lvgl.palette_main(lvgl.PALETTE.GREY))
        terminal_style.set_text_color(lvgl.color_white())
        terminal_style.set_radius(0)

        # Text Area for Output
        self.ta = lvgl.textarea(self.page.content)
        self.ta.set_size(440, 110)
        self.ta.align(lvgl.ALIGN.TOP_MID, 0, 0)
        self.ta.set_text("")
        self.ta.set_cursor_click_pos(False)
        self.ta.add_style(terminal_style, 0)
        self.ta.set_style_text_font(lvgl.font_montserrat_14, 0)
        
        # Input Field (hidden or small, or just use TA directly)
        # For simplicity, we'll just use the Keyboard and append to a string
        
        self.page.create_menubar(["Exit", "Clear", "Help", "Top", ""])
        self.page.replace_screen()
        
        # Show MOTD and Prompt
        self.shell.motd()
        self.shell._prompt()

    def run_foreground(self):
        if not self.page:
            return

        # Handle Keyboard Input
        key = self.badge.keyboard.read_key()
        if key:
            if len(key) == 1:
                # Echo the key and add to command
                self.current_cmd += key
                self._shell_write(key)
            elif key == self.badge.keyboard.ENTER:
                self._shell_write("\r\n")
                if self.current_cmd.strip():
                    self.shell.run_command(self.current_cmd)
                    self.current_cmd = ""
                self.shell._prompt()
            elif key == self.badge.keyboard.BACKSPACE:
                if self.current_cmd:
                    self.current_cmd = self.current_cmd[:-1]
                    # LvGL textarea backspace logic
                    self._shell_write("\x08 \x08") # This might not work in TA, let's just edit current line
                    # Better: delete the last character in TA
                    self.ta.del_char()

        # Menu Buttons
        if self.badge.keyboard.f1(): # Exit
            self.switch_to_background()
            self.badge.display.clear()
            return
            
        if self.badge.keyboard.f2(): # Clear
            self.ta.set_text("")
            self.shell._prompt()
            
        if self.badge.keyboard.f3(): # Help
            self.shell.run_command("help")
            self.shell._prompt()

        if self.badge.keyboard.f4(): # System Top
            self.shell.run_command("info top")
            self.shell._prompt()

    def switch_to_background(self):
        super().switch_to_background()
        self.page = None
        gc.collect()

    def run_background(self):
        pass
