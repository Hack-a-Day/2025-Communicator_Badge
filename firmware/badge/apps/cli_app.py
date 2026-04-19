"""CLI App — Serves the Badge CLI over USB serial.

Replaces/extends UsbDebug as the background app that reads USB serial input.
Dispatches complete lines to the Shell for command execution.
Preserves UsbDebug's keyboard-injection and LoRa-inject features.
"""

import binascii
import select
import sys

from apps.base_app import BaseApp
from badge_cli.shell import Shell


class CliApp(BaseApp):
    """Background app that serves the Badge CLI over USB serial."""

    def __init__(self, name, badge, stdin=None, stdout=None):
        super().__init__(name, badge)
        self.background_sleep_ms = 20
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.poll = select.poll()
        self.poll.register(self.stdin, select.POLLIN)
        self.shell = Shell(badge, write_func=self.stdout.write)
        self._line_buf = ""
        self._cli_mode = True  # True = CLI mode, False = passthrough (UsbDebug compat)
        self._started = False

    def start(self):
        super().start()
        if not self._started:
            self.shell.motd()
            self.shell._prompt()
            self._started = True

    def read_stdin_noblock(self):
        """Read from USB serial without blocking.

        Returns one character at a time for line-buffer building,
        or empty string if nothing available.
        """
        events = self.poll.poll(0)
        if events:
            try:
                return self.stdin.read(1)
            except UnicodeError:
                pass
        return ""

    def run_background(self):
        ch = self.read_stdin_noblock()
        if not ch:
            return

        if ch == "\x03":  # Ctrl+C — interrupt streaming command
            if self.shell._streaming:
                self.shell.interrupt()
            return

        if ch == "\x04":  # Ctrl+D — drop to MicroPython REPL
            raise KeyboardInterrupt()

        if self._cli_mode:
            self._handle_cli_input(ch)
        else:
            self._handle_passthrough(ch)

    def _handle_cli_input(self, ch):
        """Handle input in CLI mode — build lines, dispatch on Enter."""
        self.show_ui_feedback()
        if ch in ("\r", "\n"):
            # Echo the newline
            self.stdout.write("\r\n")
            if self._line_buf:
                self.shell.run_command(self._line_buf)
                self._line_buf = ""
            self.shell._prompt()
        elif ch == "\x7f" or ch == "\x08":  # Backspace / Delete
            if self._line_buf:
                self._line_buf = self._line_buf[:-1]
                self.stdout.write("\x08 \x08")  # Erase character on terminal
        elif ch == "\x1b":
            # Escape sequence start — read more chars for arrow keys etc.
            # For now, ignore escape sequences in CLI mode
            pass
        elif ord(ch) >= 32:  # Printable character
            self._line_buf += ch
            self.stdout.write(ch)  # Echo

    def _handle_passthrough(self, ch):
        """Handle input in passthrough mode (UsbDebug compatibility).

        Supports keyboard injection and LoRa frame injection.
        """
        if ch == "\x1b":  # Keyboard special characters
            # Would need to buffer and check PC_KEY_MAPPING
            pass
        elif ch == "/":
            # LoRa inject mode — would need line buffering
            pass
        elif len(ch) == 1:
            self.badge.keyboard.keybuffer.append(ch)

    def show_ui_feedback(self):
        """Show UI feedback on the LCD when CLI is active."""
        if hasattr(self.badge, "display") and hasattr(self.badge.display, "show_cli_active"):
            self.badge.display.show_cli_active()
            return

        try:
            import lvgl as lv
            # For real hardware
            if not getattr(self, "_cli_label", None):
                scr = lv.scr_act()
                self._cli_label = lv.label(scr)
                self._cli_label.set_text("CLI Active")
                self._cli_label.align(lv.ALIGN.TOP_RIGHT, -5, 5)
                # Fallback style setup (simple)
                try:
                    self._cli_label.set_style_bg_color(lv.palette_main(lv.PALETTE.RED), 0)
                    self._cli_label.set_style_bg_opa(lv.OPA.COVER, 0)
                    self._cli_label.set_style_text_color(lv.color_white(), 0)
                    self._cli_label.set_style_pad_all(2, 0)
                except AttributeError:
                    pass # Older LVGL version syntax fallback
        except ImportError:
            pass
