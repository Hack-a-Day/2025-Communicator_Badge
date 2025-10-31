"""Menu system"""

import lvgl
from ui import styles
from ui import graphics
from ui.page import Page
from apps.base_app import BaseApp
# from ui.pages import Splashscreen

# For logo random
import random

class AppMenu(BaseApp):
    def __init__(self, name: str, badge, apps: list[BaseApp | None], main: bool):
        super().__init__(name, badge)
        self.apps = apps
        self.background_sleep_ms = 200
        self.heartbeat_print_counter = 0
        self.main: bool = main
        print("Preparing AppMenu Splashscreen")
        self.name_list = []
        for app in self.apps:
            if app:
                self.name_list.append(app.name)
            else:
                self.name_list.append("")
        if not self.main:  # For secondary menu
            self.name_list.append("Home")
        self.page = None

    def add_logo(self, logo_filename):
        self.logo = graphics.create_image(logo_filename, self.page.content)
        self.logo.align(lvgl.ALIGN.TOP_LEFT, 5, 5)
        self.logo.set_scale(200)

    def add_message(self, message):
        self.welcome = lvgl.label(self.page.content)
        self.welcome.align(lvgl.ALIGN.TOP_LEFT, 120, 20)
        self.welcome.set_style_text_font(lvgl.font_montserrat_16, 0)
        self.welcome.set_text(message)

    def switch_to_foreground(self):
        super().switch_to_foreground()
        self.badge.display.clear()
        self.page = Page()
        self.page.create_content()

        # Load random logo
        self.add_logo("images/logos/" + str(random.randrange(1, 102)) + ".png")

        # Header message
        self.add_message("SUPERCON 2025\nPasadena, CA")
        self.page.create_menubar(self.name_list)
        self.page.replace_screen()

    def switch_to_background(self):
        self.page = None
        return super().switch_to_background()

    def run_foreground(self):
        app_to_run = None
        if self.badge.keyboard.f1():
            app_to_run = self.apps[0]
        if self.badge.keyboard.f2():
            app_to_run = self.apps[1]
        if self.badge.keyboard.f3():
            app_to_run = self.apps[2]
        if self.badge.keyboard.f4():
            app_to_run = self.apps[3]
        if self.badge.keyboard.f5():
            if self.main:
                app_to_run = self.apps[4]
            else:  # Secondary menu, go back home
                self.switch_to_background()
        if app_to_run is not None:
            # self.menu.clear()
            self.badge.display.clear()
            self.switch_to_background()
            app_to_run.switch_to_foreground()

    def run_background(self):
        if not self.main:
            return
        foreground_apps = [
            app for app in self.all_apps if app and app.active_foreground
        ]
        if len(foreground_apps) == 0:
            self.switch_to_foreground()
        else:
            if self.heartbeat_print_counter & 0x0F == 0:
                print(
                    f"Menu heartbeat --^v--^v--. Current foreground app: {foreground_apps[0].name}"
                )
                self.heartbeat_print_counter = self.heartbeat_print_counter >> 4  #
            self.heartbeat_print_counter += 1
