"""Manage badge config file."""

from apps.base_app import BaseApp

from net.net import register_receiver
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

    def _override_config_value(self, message: NetworkFrame):
        signature, key, value = message.payload
        kv_bytes = key + value
        signed = self.badge.crypto.verify(kv_bytes, signature)
        print(f"Got config override message: {key}:{value} Signed: {signed}")
        if not signed:
            return
        key_stripped = key.strip(b"\0").decode()
        val_stripped = value.strip(b"\0")
        self.badge.config, set(key_stripped, val_stripped)
        self.badge.config.flush()
        self._reload_config()

    def start(self):
        register_receiver(CONFIG_OVERRIDE, self._override_config_value)
        return super().start()

    def _reload_config(self):
        self.config = [
            (key.decode(), value.decode())
            for key, value in self.badge.config.db.items()
        ]
        self.config.sort()

    def run_foreground(self):
        if self.badge.keyboard.f5():
            self.switch_to_background()
        if self.edit_active:
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
                self.config[self.cursor_pos] = (self.config[self.cursor_pos][0], new_value)
                configs = [(key, f"   {value}") for key, value in self.config]
                self.page.populate_message_rows(configs)
                self.page.message_rows.set_cell_value(
                    self.cursor_pos, 1, f"> {self.config[self.cursor_pos][1]}"
                )
                self.page.infobar_right.set_text("Go Home to Save, Reboot to Load")
                self.edit_active = False 
        else:
            key = self.badge.keyboard.read_key()
            if key == self.badge.keyboard.UP:
                self.page.message_rows.set_cell_value(
                    self.cursor_pos, 1, f"   {self.config[self.cursor_pos][1]}"
                )
                self.cursor_pos = max(0, self.cursor_pos - 1)
                self.page.message_rows.set_cell_value(
                    self.cursor_pos, 1, f"> {self.config[self.cursor_pos][1]}"
                )
            elif key == self.badge.keyboard.DOWN:
                self.page.message_rows.set_cell_value(
                    self.cursor_pos, 1, f"   {self.config[self.cursor_pos][1]}"
                )
                self.cursor_pos = min(len(self.config) - 1, self.cursor_pos + 1)
                self.page.message_rows.set_cell_value(
                    self.cursor_pos, 1, f"> {self.config[self.cursor_pos][1]}"
                )
            if self.badge.keyboard.f1():
                try:
                    int(self.config[self.cursor_pos][1])
                    print("Not allowed to edit numeric configs, sorry")
                except ValueError:
                    self.page.create_text_box(
                        self.config[self.cursor_pos][1],
                        one_line=True,
                    )
                    self.edit_active = True

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

        self.page.create_menubar(["Edit", "DON'T", "CHANGE", "NUMBERS", "Home"])
        self.page.replace_screen()
        super().switch_to_foreground()

    def switch_to_background(self):
        """Save configs to flash and go back to main menu"""
        for key, value in self.config:
            self.badge.config.set(key, value)
        self.badge.config.flush()
        self.page = None
        super().switch_to_background()
