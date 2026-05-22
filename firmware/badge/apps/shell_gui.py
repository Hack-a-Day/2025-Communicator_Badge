"""Shell GUI App — A terminal emulator running on the badge screen.

Allows users to interact with the Badge CLI directly on the display
using the on-screen keyboard or physical buttons.
"""

import lvgl
import gc
import re
from apps.base_app import BaseApp
from ui.page import Page, SCREEN_WIDTH, SCREEN_HEIGHT, MENU_HEIGHT
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
        self.cursor_pos = 0
        self.cmd_view_offset = 0
        self.cmd_view_chars = 46
        self.viewport_lines = 12
        self.scrollback_lines = 0
        self._defer_render = False
        self._render_dirty = False
        self.busy_label = None
        self._anim_tick = 0
        self._blink_prev = None
        # Regex to strip ANSI escape codes
        self.ansi_re = re.compile(r'\x1b\[[0-9;]*[mK]')

    def _blink_on(self):
        # 20ms frame -> 25 ticks ~= 500ms blink period.
        return (self._anim_tick // 25) % 2 == 0

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
        clean_text = clean_text.replace("\r", "")
        self._append_output(clean_text)

    def _append_output(self, text):
        self.text_buffer += text
        if len(self.text_buffer) > self.max_buffer:
            self.text_buffer = self.text_buffer[-self.max_buffer:]
        if self._defer_render:
            self._render_dirty = True
        else:
            self._render_terminal()

    def _run_shell_command(self, cmd):
        """Run shell command while deferring intermediate GUI renders."""
        self._set_busy(True)
        self._defer_render = True
        self._render_dirty = False
        try:
            self.shell.run_command(cmd)
        finally:
            self._defer_render = False
            if self._render_dirty:
                self._render_terminal()
            self._set_busy(False)

    def _set_busy(self, on):
        if not self.page:
            return

        if on:
            if not self.busy_label:
                self.busy_label = lvgl.label(self.page.content)
                self.busy_label.set_style_text_color(lvgl.color_hex(0x00FF66), 0)
                self.busy_label.set_style_bg_color(lvgl.color_hex(0x000000), 0)
                self.busy_label.set_style_bg_opa(lvgl.OPA.COVER, 0)
                self.busy_label.set_style_pad_all(1, 0)
                self.busy_label.align(lvgl.ALIGN.TOP_RIGHT, -4, 2)
            self.busy_label.set_text("working...")
        else:
            if self.busy_label:
                self.busy_label.set_text("")

    def _prompt_text(self):
        cwd = "/"
        if self.shell and hasattr(self.shell, "cwd"):
            cwd = self.shell.cwd
        return "badge [" + str(cwd) + "] >: "

    def _ensure_cursor_visible(self):
        if self.cursor_pos < self.cmd_view_offset:
            self.cmd_view_offset = self.cursor_pos
        elif self.cursor_pos > self.cmd_view_offset + self.cmd_view_chars:
            self.cmd_view_offset = self.cursor_pos - self.cmd_view_chars

        if self.cmd_view_offset < 0:
            self.cmd_view_offset = 0

    def _visible_cmd(self):
        self._ensure_cursor_visible()
        start = self.cmd_view_offset
        end = start + self.cmd_view_chars
        visible = self.current_cmd[start:end]

        # In-place shell row animation: blinking caret on active command line.
        if self.scrollback_lines == 0:
            rel = self.cursor_pos - start
            if rel < 0:
                rel = 0
            if rel > len(visible):
                rel = len(visible)
            caret = "|" if self._blink_on() else " "
            visible = visible[:rel] + caret + visible[rel:]

        return visible

    def _render_terminal(self):
        if not (self.page and hasattr(self, "ta")):
            return

        prompt = self._prompt_text()
        cmd_view = self._visible_cmd()
        full_text = self.text_buffer + prompt + cmd_view

        if self.scrollback_lines > 0:
            lines = full_text.split("\n")
            total = len(lines)
            end = max(0, total - self.scrollback_lines)
            start = max(0, end - self.viewport_lines)
            rendered = "[SCROLL x" + str(self.scrollback_lines) + "]\n" + "\n".join(lines[start:end])
        else:
            rendered = full_text

        self.ta.set_text(rendered)
        try:
            self.ta.set_cursor_pos(lvgl.TEXTAREA.CURSOR_LAST)
        except AttributeError:
            pass

    def switch_to_foreground(self):
        super().switch_to_foreground()
        
        # Initialize shell if not already done
        if not self.shell:
            self.shell = Shell(self.badge, write_func=self._shell_write)
            self.shell.check_interrupt_func = self.run_foreground

        self.page = Page()
        # Keep only the bottom menubar and use all remaining space for terminal output.
        self.page.create_content()

        # Matrix terminal style: black background, green text.
        terminal_style = lvgl.style_t()
        terminal_style.init()
        terminal_style.set_bg_color(lvgl.color_hex(0x000000))
        terminal_style.set_text_color(lvgl.color_hex(0x00FF66))
        terminal_style.set_radius(0)
        try:
            terminal_style.set_border_width(0)
            terminal_style.set_pad_all(2)
        except AttributeError:
            pass

        # Also enforce the content panel theme so there is no gray framing.
        try:
            self.page.content.set_style_bg_color(lvgl.color_hex(0x000000), 0)
            self.page.content.set_style_border_width(0, 0)
            self.page.content.set_style_pad_all(0, 0)
            self.page.content.set_style_margin_all(0, 0)
        except AttributeError:
            pass

        # Text Area for Output
        self.ta = lvgl.textarea(self.page.content)
        self.ta.set_size(SCREEN_WIDTH, SCREEN_HEIGHT - MENU_HEIGHT)
        self.ta.align(lvgl.ALIGN.TOP_LEFT, 0, 0)
        self.ta.set_text("")
        self.ta.set_cursor_click_pos(False)
        self.ta.set_scrollbar_mode(lvgl.SCROLLBAR_MODE.OFF)
        self.ta.add_style(terminal_style, 0)
        try:
            self.ta.set_style_bg_color(lvgl.color_hex(0x000000), lvgl.PART.MAIN)
            self.ta.set_style_text_color(lvgl.color_hex(0x00FF66), lvgl.PART.MAIN)
            self.ta.set_style_border_width(0, lvgl.PART.MAIN)
            self.ta.set_style_pad_all(2, lvgl.PART.MAIN)
        except AttributeError:
            pass
        self.ta.set_style_text_font(lvgl.font_montserrat_14, 0)
        
        # Input Field (hidden or small, or just use TA directly)
        # For simplicity, we'll just use the Keyboard and append to a string
        
        self.page.create_menubar(["Exit", "Clear", "Help", "Top", "REPL"])
        try:
            # Avoid a light seam between content and menu bar.
            self.page.menubar.set_style_border_width(0, 0)
            self.page.menubar.set_style_pad_all(0, 0)
            self.page.menubar.set_style_margin_all(0, 0)
        except AttributeError:
            pass
        self.page.replace_screen()

        self.text_buffer = ""
        self.current_cmd = ""
        self.cursor_pos = 0
        self.cmd_view_offset = 0
        self.scrollback_lines = 0
        
        # Show MOTD
        self.shell.motd()
        self._render_terminal()

    def _set_cmd(self, cmd):
        self.current_cmd = cmd
        self.cursor_pos = len(self.current_cmd)
        self.scrollback_lines = 0
        self._ensure_cursor_visible()
        self._render_terminal()

    def _handle_enter(self):
        cmd = self.current_cmd
        self.scrollback_lines = 0
        self._append_output(self._prompt_text() + cmd + "\n")
        if cmd.strip():
            parts = cmd.strip().split()
            if len(parts) == 2 and parts[0] == "help":
                # Convenience for on-device keyboard: allow 'help <group>'
                # instead of requiring '<group> ?'.
                self._run_shell_command(parts[1] + " ?")
            else:
                self._run_shell_command(cmd)
        self.current_cmd = ""
        self.cursor_pos = 0
        self.cmd_view_offset = 0
        self._render_terminal()

    def run_foreground(self):
        if not self.page:
            return

        # Advance animation clock and redraw on blink edge.
        self._anim_tick += 1
        blink_now = self._blink_on()
        if self._blink_prev is None:
            self._blink_prev = blink_now
        elif blink_now != self._blink_prev and self.scrollback_lines == 0:
            self._blink_prev = blink_now
            self._render_terminal()

        delete_key = getattr(self.badge.keyboard, "DEL", "\x7f")
        left_key = getattr(self.badge.keyboard, "LEFT", "`h")
        right_key = getattr(self.badge.keyboard, "RIGHT", "`l")
        up_key = getattr(self.badge.keyboard, "UP", "`j")
        down_key = getattr(self.badge.keyboard, "DOWN", "`k")
        tab_key = getattr(self.badge.keyboard, "TAB", "\t")
        enter_key = getattr(self.badge.keyboard, "ENTER", "\n")
        shift_pressed = bool(getattr(self.badge.keyboard, "shift_pressed", False))

        # Handle all queued keyboard input this frame to avoid dropped chars.
        while True:
            key = self.badge.keyboard.read_key()
            if key is None:
                break

            if not isinstance(key, str):
                try:
                    key = key.decode("utf-8")
                except Exception:
                    key = str(key)

            if self.cursor_pos > len(self.current_cmd):
                self.cursor_pos = len(self.current_cmd)
            if self.cursor_pos == 0 and self.current_cmd:
                self.cursor_pos = len(self.current_cmd)

            if key in (enter_key, "\r", "\n"):
                self._handle_enter()
            elif key in (self.badge.keyboard.BS, delete_key):
                if self.cursor_pos > 0:
                    self.current_cmd = (
                        self.current_cmd[: self.cursor_pos - 1]
                        + self.current_cmd[self.cursor_pos :]
                    )
                    self.cursor_pos -= 1
                    try:
                        self.ta.del_char()
                    except Exception:
                        pass
                    self._render_terminal()
            elif key == left_key:
                self.scrollback_lines = 0
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
                    self._render_terminal()
            elif key == right_key:
                self.scrollback_lines = 0
                if self.cursor_pos < len(self.current_cmd):
                    self.cursor_pos += 1
                    self._render_terminal()
            elif key == up_key:
                if shift_pressed:
                    self.scrollback_lines += 1
                    self._render_terminal()
                else:
                    self._set_cmd(self.shell.get_history_nav("up", self.current_cmd))
            elif key == down_key:
                if shift_pressed:
                    if self.scrollback_lines > 0:
                        self.scrollback_lines -= 1
                    self._render_terminal()
                else:
                    self._set_cmd(self.shell.get_history_nav("down", self.current_cmd))
            elif key == tab_key:
                self.scrollback_lines = 0
                matches = self.shell.complete(self.current_cmd)
                if len(matches) == 1:
                    self._set_cmd(matches[0])
                elif len(matches) > 1:
                    self._append_output("\n" + "  ".join(matches) + "\n")
                    self._render_terminal()
            elif len(key) == 1:
                self.scrollback_lines = 0
                # Insert at cursor and advance.
                self.current_cmd = (
                    self.current_cmd[: self.cursor_pos]
                    + key
                    + self.current_cmd[self.cursor_pos :]
                )
                self.cursor_pos += 1
                self._render_terminal()

        # Menu Buttons
        if self.badge.keyboard.f1(): # Exit
            self.switch_to_background()
            self.badge.display.clear()
            return
            
        if self.badge.keyboard.f2(): # Clear
            self.text_buffer = ""
            self.scrollback_lines = 0
            self._render_terminal()
            
        if self.badge.keyboard.f3(): # Help
            self._run_shell_command("help")
            self._append_output("\nTip: use 'help <group>' (example: help net)\n")
            self._render_terminal()

        if self.badge.keyboard.f4(): # System Top
            self._run_shell_command("info top")
            self._render_terminal()

        if self.badge.keyboard.f5(): # Drop to MicroPython REPL
            self._append_output("\nEntering REPL...\n")
            self._run_shell_command("exit")

    def switch_to_background(self):
        super().switch_to_background()
        self.page = None
        gc.collect()

    def run_background(self):
        pass
