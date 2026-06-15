"""Manage badge config file."""

import struct
import machine
import lvgl
from ui import styles
from apps.base_app import BaseApp

from net.net import register_receiver, send, BROADCAST_ADDRESS
from net.protocols import NetworkFrame, Protocol
from ui.page import Page

CONFIG_OVERRIDE = Protocol(port=4, name="CONFIG_OVERRIDE", structdef="!128s20s80s")

class ConfigManager(BaseApp):
    """View and edit badge config file."""

    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.foreground_sleep_ms = 100
        self.background_sleep_ms = 100
        self.config = []
        self._reload_config()
        self.cursor_pos: int = 0
        self.edit_active = False
        self.datetime_edit_active = False
        self.dt_text_boxes = []
        self.dt_focus_idx = 0
        self.dt_container = None

    def _override_config_value(self, message: NetworkFrame):
        signature, key, value = message.payload
        kv_bytes = key + value
        signed = self.badge.crypto.verify(kv_bytes, signature)
        print(f"Got config override message: {key}:{value} Signed: {signed}")
        if not signed:
            return
        key_stripped = key.strip(b"\0").decode()
        val_stripped = value.strip(b"\0")
        self.badge.config.set(key_stripped, val_stripped)
        self.badge.config.flush()
        self._reload_config()

    def _send_override(self, key, value):
        kv_bytes = struct.pack("!20s80s", key, value)
        signature = self.badge.crypto.sign(kv_bytes)
        check = self.badge.crypto.verify(kv_bytes, signature)
        print(f"Sending signed message: {key}:{value} Sig-okay: {check}")
        if check:
            send(
                NetworkFrame().set_fields(
                    protocol=CONFIG_OVERRIDE,
                    destination=BROADCAST_ADDRESS,
                    ttl=15,
                    payload=(signature, key, value),
                )
            )

    def start(self):
        register_receiver(CONFIG_OVERRIDE, self._override_config_value)
        return super().start()

    def _reload_config(self):
        self.config = [
            (key.decode(), value.decode())
            for key, value in self.badge.config.db.items()
        ]
        self.config.sort()

    def _open_datetime_edit(self):
        self.datetime_edit_active = True
        
        self.dt_container = lvgl.obj(self.page.content)
        self.dt_container.set_size(lvgl.pct(100), lvgl.pct(100))
        self.dt_container.add_style(styles.content_style, 0)
        self.dt_container.set_scrollbar_mode(0)
        self.dt_container.move_foreground()
        
        title = lvgl.label(self.dt_container)
        title.set_text("Set Date/Time")
        title.align(lvgl.ALIGN.TOP_MID, 0, 0)
        
        self.dt_error_label = lvgl.label(self.dt_container)
        self.dt_error_label.set_text("")
        self.dt_error_label.set_style_text_color(styles.lvg_color_red, 0)
        self.dt_error_label.align(lvgl.ALIGN.TOP_RIGHT, -5, 0)
        
        self.dt_text_boxes = []
        labels = ["Y:", "M:", "D:", "h:", "m:", "s:"]
        
        rtc = machine.RTC()
        dt = rtc.datetime()  # (year, month, day, weekday, hours, minutes, seconds, subseconds)
        values = [f"{dt[0]:04d}", f"{dt[1]:02d}", f"{dt[2]:02d}", f"{dt[4]:02d}", f"{dt[5]:02d}", f"{dt[6]:02d}"]
        
        start_x = 25
        box_width = 35
        pad_x = 10
        
        for i in range(6):
            # first box is larger because 4 digits (yyyy)
            if i == 0:
                bw = 55
            else:
                bw = box_width
                
            lbl = lvgl.label(self.dt_container)
            lbl.set_text(labels[i])
            lbl.align(lvgl.ALIGN.LEFT_MID, start_x, 15)
            
            tb = lvgl.textarea(self.dt_container)
            tb.set_size(bw, 40) 
            tb.align(lvgl.ALIGN.LEFT_MID, start_x + 15, 15)
            tb.add_style(styles.infobar_style, 0)
            tb.set_style_border_width(2, 0)
            tb.set_text(values[i])
            tb.set_one_line(True)
            tb.set_style_border_color(styles.lcd_color_fg, lvgl.PART.CURSOR | lvgl.STATE.FOCUSED)
            tb.set_style_text_align(lvgl.TEXT_ALIGN.CENTER, lvgl.PART.MAIN)
            
            self.dt_text_boxes.append(tb)
            start_x += bw + pad_x + 15
            
        self.dt_focus_idx = 0
        self.dt_text_boxes[self.dt_focus_idx].add_state(lvgl.STATE.FOCUSED)
        
        self.page.set_menubar_button_label(0, "Save")
        self.page.set_menubar_button_label(1, "Prev")
        self.page.set_menubar_button_label(2, "Next")
        self.page.set_menubar_button_label(3, "")
        self.page.set_menubar_button_label(4, "Cancel")

    def _close_datetime_edit(self):
        if self.dt_container:
            self.dt_container.delete()
            self.dt_container = None
        self.dt_text_boxes = []
        self.datetime_edit_active = False
        
        self.page.set_menubar_button_label(0, "Edit")
        self.page.set_menubar_button_label(1, "Set Time")
        self.page.set_menubar_button_label(2, "Up")
        self.page.set_menubar_button_label(3, "Down")
        self.page.set_menubar_button_label(4, "Home")

    def _save_datetime(self):
        try:
            y = int(self.dt_text_boxes[0].get_text().strip() or 0)
            m = int(self.dt_text_boxes[1].get_text().strip() or 0)
            d = int(self.dt_text_boxes[2].get_text().strip() or 0)
            h = int(self.dt_text_boxes[3].get_text().strip() or 0)
            mi = int(self.dt_text_boxes[4].get_text().strip() or 0)
            s = int(self.dt_text_boxes[5].get_text().strip() or 0)
            
            if not (2000 <= y <= 2100): raise ValueError("Year out of bounds")
            if not (1 <= m <= 12): raise ValueError("Month out of bounds")
            if not (1 <= d <= 31): raise ValueError("Day out of bounds")
            if not (0 <= h <= 23): raise ValueError("Hour out of bounds")
            if not (0 <= mi <= 59): raise ValueError("Minute out of bounds")
            if not (0 <= s <= 59): raise ValueError("Second out of bounds")
            
            machine.RTC().datetime((y, m, d, 0, h, mi, s, 0))
            print(f"RTC updated to {y}-{m}-{d} {h}:{mi}:{s}")
        except Exception as e:
            print(f"Failed to set RTC: {e}")
            self.dt_error_label.set_text("Invalid Date/Time!")
            return
        
        self._close_datetime_edit()

    def _increment_dt_field(self, tb, idx, direction):
        try:
            val = int(tb.get_text().strip() or 0)
        except ValueError:
            val = 0
            
        limits = [(2000, 2100), (1, 12), (1, 31), (0, 23), (0, 59), (0, 59)]
        min_val, max_val = limits[idx]
        
        val += direction
        if val > max_val:
            val = min_val
        elif val < min_val:
            val = max_val
            
        fmt = "{:04d}" if idx == 0 else "{:02d}"
        tb.set_text(fmt.format(val))

    def _handle_datetime_input(self):
        tb = self.dt_text_boxes[self.dt_focus_idx]
        
        if self.badge.keyboard.escape_pressed or self.badge.keyboard.f5():
            self._close_datetime_edit()
            return

        if self.badge.keyboard.f1():
            self._save_datetime()
            return
            
        if self.badge.keyboard.f2():
            tb.remove_state(lvgl.STATE.FOCUSED)
            self.dt_focus_idx = (self.dt_focus_idx - 1) % 6
            self.dt_text_boxes[self.dt_focus_idx].add_state(lvgl.STATE.FOCUSED)
            return
            
        if self.badge.keyboard.f3():
            tb.remove_state(lvgl.STATE.FOCUSED)
            self.dt_focus_idx = (self.dt_focus_idx + 1) % 6
            self.dt_text_boxes[self.dt_focus_idx].add_state(lvgl.STATE.FOCUSED)
            return

        key = self.badge.keyboard.read_key()
        if key is None:
            return

        if key == self.badge.keyboard.TAB:
            tb.remove_state(lvgl.STATE.FOCUSED)
            self.dt_focus_idx = (self.dt_focus_idx + 1) % 6
            self.dt_text_boxes[self.dt_focus_idx].add_state(lvgl.STATE.FOCUSED)
            return

        if key == self.badge.keyboard.ENTER:
            self._save_datetime()
            return
            
        if key == self.badge.keyboard.LEFT:
            tb.cursor_left()
        elif key == self.badge.keyboard.RIGHT:
            tb.cursor_right()
        elif key == self.badge.keyboard.UP:
            self._increment_dt_field(tb, self.dt_focus_idx, 1)
        elif key == self.badge.keyboard.DOWN:
            self._increment_dt_field(tb, self.dt_focus_idx, -1)
        elif key == self.badge.keyboard.BS:
            tb.delete_char()
        elif key == self.badge.keyboard.DEL:
            tb.delete_char_forward()
        else:
            if key in "0123456789":
                tb.add_text(key)

    def run_foreground(self):
        if self.datetime_edit_active:
            self._handle_datetime_input()
        elif self.badge.keyboard.f5():
            self.switch_to_background()
        elif self.edit_active:
            key, text = self.page.text_box_type(self.badge.keyboard)
            if self.config[self.cursor_pos][0] == "alias":
                self.page.infobar_right.set_text(f"{len(text)}/10  F1 to set")
            if self.badge.keyboard.escape_pressed:
                self.page.close_text_box()
                self.page.infobar_right.set_text("Go Home to Save, Reboot to Load")
                self.edit_active = False
            if key == self.badge.keyboard.ENTER or self.badge.keyboard.f1():
                new_value = self.page.close_text_box()
                if self.config[self.cursor_pos][0] == "alias":
                    new_value = new_value[:10]
                self.config[self.cursor_pos] = (
                    self.config[self.cursor_pos][0],
                    new_value,
                )
                configs = [(key, f"   {value}") for key, value in self.config]
                self.page.populate_message_rows(configs)
                self.page.message_rows.set_cell_value(
                    self.cursor_pos, 1, f"> {self.config[self.cursor_pos][1]}"
                )
                self.page.infobar_right.set_text("Go Home to Save, Reboot to Load")
                self.edit_active = False
            # if self.badge.keyboard.f3() and self.badge.crypto.private_key is not None:  # Send override
            #     key = self.config[self.cursor_pos][0]
            #     value = self.page.close_text_box()
            #     self._send_override(key, value)
            #     self.page.infobar_right.set_text("Go Home to Save, Reboot to Load")
            #     self.edit_active = False
        else:
            key = self.badge.keyboard.read_key()
            if key == self.badge.keyboard.UP:
                if self.badge.keyboard.shift_pressed:
                    self.page.scroll_up(16)
                else:
                    self.page.message_rows.set_cell_value(
                        self.cursor_pos, 1, f"   {self.config[self.cursor_pos][1]}"
                    )
                    self.cursor_pos = max(0, self.cursor_pos - 1)
                    self.page.message_rows.set_cell_value(
                        self.cursor_pos, 1, f"> {self.config[self.cursor_pos][1]}"
                    )
            elif key == self.badge.keyboard.DOWN:
                if self.badge.keyboard.shift_pressed:
                    self.page.scroll_down(16)
                else:
                    self.page.message_rows.set_cell_value(
                        self.cursor_pos, 1, f"   {self.config[self.cursor_pos][1]}"
                    )
                    self.cursor_pos = min(len(self.config) - 1, self.cursor_pos + 1)
                    self.page.message_rows.set_cell_value(
                        self.cursor_pos, 1, f"> {self.config[self.cursor_pos][1]}"
                    )
            if self.badge.keyboard.f1():
                self.page.create_text_box(
                    self.config[self.cursor_pos][1],
                    one_line=True,
                )
                self.edit_active = True
            if self.badge.keyboard.f2():
                self._open_datetime_edit()
            if self.badge.keyboard.f3():
                self.page.scroll_up(16)
                self.page.message_rows.set_cell_value(
                    self.cursor_pos, 1, f"   {self.config[self.cursor_pos][1]}"
                )
                self.cursor_pos = max(0, self.cursor_pos - 1)
                self.page.message_rows.set_cell_value(
                    self.cursor_pos, 1, f"> {self.config[self.cursor_pos][1]}"
                )
            if self.badge.keyboard.f4():
                self.page.scroll_down(16)
                self.page.message_rows.set_cell_value(
                    self.cursor_pos, 1, f"   {self.config[self.cursor_pos][1]}"
                )
                self.cursor_pos = min(len(self.config) - 1, self.cursor_pos + 1)
                self.page.message_rows.set_cell_value(
                    self.cursor_pos, 1, f"> {self.config[self.cursor_pos][1]}"
                )

    def switch_to_foreground(self):
        self._reload_config()
        self.page = Page()
        self.page.create_infobar(("Config Manager", "Go Home to Save, Reboot to Load"))
        self.page.create_content()
        self.page.add_message_rows(len(self.config), 150)
        configs = [(key, f"   {value}") for key, value in self.config]
        self.page.populate_message_rows(configs)
        self.page.message_rows.set_cell_value(
            self.cursor_pos, 1, f"> {self.config[self.cursor_pos][1]}"
        )

        self.page.create_menubar(["Edit", "Set Time", "Up", "Down", "Home"])
        self.page.replace_screen()
        super().switch_to_foreground()

    def switch_to_background(self):
        """Save configs to flash and go back to main menu"""
        for key, value in self.config:
            self.badge.config.set(key, value.encode())
        self.badge.config.flush()
        self.page = None
        super().switch_to_background()
