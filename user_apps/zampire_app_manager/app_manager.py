"""Menu system"""

import lvgl
import os
import sys
from ui import styles
from ui import graphics
from ui.page import Page
from apps.base_app import BaseApp
# from ui.pages import Splashscreen

# For logo random
import random

APPMOD_DENYLIST = {
    "__init__",
    "app_manager",
    "app_menu",
    "badgeshark",
    "base_app",
    "chat",
    "config_manager",
    "demo",
    "nametag",
    "net_tools",
    "talks",
    "template_app",
    "usb_debug",
}

class AppManager(BaseApp):
    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.background_sleep_ms = 200
        self.heartbeat_print_counter = 0

        self.apps = []
        self.apps_offset = 0
        print("Finding application modules...")
        app_mods = []
        for filename, filetype, _, size in os.ilistdir("/apps"):
            if not filename.endswith(".py") or filename.startswith("_"):
                continue
            app_modname = filename.split('.')[0]
            print(f"Checking if {app_modname} is in deny list: {APPMOD_DENYLIST}")
            if not app_modname in APPMOD_DENYLIST:
                app_mods.append(app_modname)
        if app_mods:
            print(f"Found app mods: {app_mods}")
            with open("/data/user_apps.py", "w") as out:
                out.write(f"from apps import {', '.join(app_mods)}\n")

        import data.user_apps as apps

        apps_list = dir(apps)
        print(f"Applications list: {apps_list}")
        for appmod_name in apps_list:
            if appmod_name.startswith('_') or appmod_name in APPMOD_DENYLIST:
                continue
            appmod = getattr(apps, appmod_name)
            try:
                print(f"Checking app module: {appmod}")
                if (
                    hasattr(appmod, "APP_NAME") and (
                        hasattr(appmod, "APP_CLASS") or
                        hasattr(appmod, "App")
                )):
                    app_name = appmod.APP_NAME
                    app_class = getattr(appmod, "APP_CLASS", None) or getattr(appmod, "App")
                    app = app_class(app_name, badge)
                    self.apps.append(app)
                    print(f"Added app: {app_name}")

            except Exception as exc:
                print(f"Failed to load app module: {appmod}")
                sys.print_exception(exc)
        
        self.prepare_menu()
        
    def prepare_menu(self):
        print("Preparing AppManager Menu")
        self.name_list = []
        self.has_prev = False
        self.has_next = False
        max_apps = 4
        if self.apps_offset > 0:
            self.name_list.append("Prev")
            self.has_prev = True
            max_apps = 3
        for appmod in self.apps[self.apps_offset:self.apps_offset+max_apps]:
            self.name_list.append(appmod.name)
        for _ in range(len(self.name_list), 4):
            self.name_list.append("")
        if self.apps_offset + max_apps >= len(self.apps):
            self.name_list.append("Home")
        else:
            self.name_list.append("Next")
            self.has_next = True
        self.page = None
    
    def start(self):
        super().start()
        for app in self.apps:
            app.start()

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

    def hasapp(self, app_index: int):
        return app_index < len(self.apps)

    def key2app(self, key_index: int):
        if self.apps_offset < 4:
            assert key_index >= 0 and key_index < 4
            app_index = key_index
        else:
            assert key_index >= 1 and key_index < 4
            app_index = self.apps_offset + key_index - 1
        if self.hasapp(app_index):
            return self.apps[app_index]
        else:
            return None

    def run_foreground(self):
        app_to_run = None
        if self.badge.keyboard.f1():
            if self.has_prev:
                if self.apps_offset <= 4:
                    self.apps_offset = 0
                else:
                    self.apps_offset -= 3
                self.prepare_menu()
                self.switch_to_foreground()
            else:
                app_to_run = self.key2app(0)
        if self.badge.keyboard.f2():
            app_to_run = self.key2app(1)
        if self.badge.keyboard.f3():
            app_to_run = self.key2app(2)
        if self.badge.keyboard.f4():
            app_to_run = self.key2app(3)
        if self.badge.keyboard.f5():
            if self.has_next:
                if self.apps_offset == 0:
                    self.apps_offset += 4
                else:
                    self.apps_offset += 3
                self.prepare_menu()
                self.switch_to_foreground()
            else:
                self.switch_to_background()
        if app_to_run is not None:
            # self.menu.clear()
            self.badge.display.clear()
            self.switch_to_background()
            app_to_run.switch_to_foreground()

    def run_background(self):
        pass
