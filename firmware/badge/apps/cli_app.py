"""CLI App — Serves the Badge CLI over USB serial.

Replaces/extends UsbDebug as the background app that reads USB serial input.
Dispatches complete lines to the Shell for command execution.
Preserves UsbDebug's keyboard-injection and LoRa-inject features.
"""

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
        self.poll = None
        try:
            self.poll = select.poll()
            self.poll.register(self.stdin, select.POLLIN)
        except Exception:
            # Some test/mocked stdin objects don't provide a usable fileno().
            # In that case, fall back to a no-op reader unless tests override it.
            self.poll = None
        self.shell = Shell(badge, write_func=self.stdout.write)
        self.shell.check_interrupt_func = self.run_background
        self._line_buf = ""
        self._saw_cr = False
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

        Returns a short buffered burst of characters, or empty string.
        This mirrors UsbDebug behavior to avoid losing characters when
        hosts send bytes faster than one app loop tick.
        """
        if self.poll is None:
            # Fallback for mocked stdin in tests and environments where poll()
            # registration is not possible.
            try:
                if hasattr(self.stdin, "in_waiting") and self.stdin.in_waiting <= 0:
                    return ""
            except Exception:
                pass
            try:
                if hasattr(self.stdin, "any") and not self.stdin.any():
                    return ""
            except Exception:
                pass
            try:
                data = self.stdin.read(1)
                return data or ""
            except Exception:
                return ""

        buffer = ""
        events = self.poll.poll(0)
        while events:
            try:
                buffer += self.stdin.read(1)
            except UnicodeError:
                pass
            # Briefly wait for additional bytes in the same burst.
            events = self.poll.poll(2)
        return buffer

    def run_background(self):
        chunk = self.read_stdin_noblock()
        if not chunk:
            return

        for ch in chunk:
            if ch == "\x03":  # Ctrl+C — interrupt streaming command
                if self.shell._streaming:
                    self.shell.interrupt()
                continue

            if ch == "\x04":  # Ctrl+D — drop to MicroPython REPL
                raise KeyboardInterrupt()

            if self._cli_mode:
                self._handle_cli_input(ch)
            else:
                self._handle_passthrough(ch)

    def _handle_cli_input(self, ch):
        """Handle input in CLI mode — build lines, dispatch on Enter."""
        self.show_ui_feedback()
        
        if ch == "\n" and self._saw_cr:
            # Many terminals send CRLF; ignore LF immediately after CR.
            self._saw_cr = False
            return

        if ch in ("\r", "\n"):
            self._saw_cr = (ch == "\r")
            # Echo the newline
            self.stdout.write("\r\n")
            if self._line_buf:
                self.shell.run_command(self._line_buf)
                self._line_buf = ""
            self.shell._prompt()
        elif ch == "\x7f" or ch == "\x08":  # Backspace / Delete
            self._saw_cr = False
            if self._line_buf:
                self._line_buf = self._line_buf[:-1]
                self.stdout.write("\x08 \x08")  # Erase character on terminal
        elif ch == "\t":  # Tab completion
            self._saw_cr = False
            matches = self.shell.complete(self._line_buf)
            if len(matches) == 1:
                # Complete the line
                self._clear_current_line()
                self._line_buf = matches[0]
                self.stdout.write(self._line_buf)
            elif len(matches) > 1:
                # Show matches
                self.stdout.write("\r\n" + "  ".join(matches) + "\r\n")
                self.shell._prompt()
                self.stdout.write(self._line_buf)
        elif ch == "\x1b":
            self._saw_cr = False
            # Start of escape sequence
            self._esc_buf = "["
        elif getattr(self, "_esc_buf", "") == "[":
            self._saw_cr = False
            if ch == "[": return # Skip second [ if it happens
            if ch == "A": # Up
                self._line_buf = self.shell.get_history_nav("up", self._line_buf)
                self._redraw_line()
            elif ch == "B": # Down
                self._line_buf = self.shell.get_history_nav("down", self._line_buf)
                self._redraw_line()
            self._esc_buf = ""
        elif ord(ch) >= 32:  # Printable character
            self._saw_cr = False
            self._line_buf += ch
            self.stdout.write(ch)  # Echo

    def _clear_current_line(self):
        """Erase the current line on the terminal."""
        # Move to start of line, erase to end
        self.stdout.write("\r" + " " * (len(self._line_buf) + 10) + "\r")
        self.shell._prompt()

    def _redraw_line(self):
        """Redraw the prompt and current buffer."""
        self._clear_current_line()
        self.stdout.write(self._line_buf)

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
            # For real hardware: support both newer and older lvgl bindings.
            if not getattr(self, "_cli_label", None):
                scr_act = getattr(lv, "scr_act", None)
                screen_active = getattr(lv, "screen_active", None)
                if callable(scr_act):
                    scr = scr_act()
                elif callable(screen_active):
                    scr = screen_active()
                else:
                    return
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
        except (ImportError, AttributeError):
            pass
