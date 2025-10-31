"""Template app for badge applications. Copy this file and update to implement your own app."""

import uasyncio as aio  # type: ignore

from apps.base_app import BaseApp
from net.net import register_receiver, send, BROADCAST_ADDRESS
from net.protocols import Protocol, NetworkFrame
from ui.page import Page
import ui.styles as styles
import lvgl

"""
All protocols must be defined in their apps with unique ports. Ports must fit in uint8.
Try to pick a protocol ID that isn't in use yet; good luck.
Structdef is the struct library format string. This is a subset of cpython struct.
https://docs.micropython.org/en/latest/library/struct.html
"""
# NEW_PROTOCOL = Protocol(port=<PORT>, name="<NAME>", structdef="!")


class App(BaseApp):
    """Define a new app to run on the badge."""

    def __init__(self, name: str, badge):
        """Define any attributes of the class in here, after super().__init__() is called.
        self.badge will be available in the rest of the class methods for accessing the badge hardware.
        If you don't have anything else to add, you can delete this method.
        """
        super().__init__(name, badge)
        # You can also set the sleep time when running in the foreground or background. Uncomment and update.
        # Remember to make background sleep longer so this app doesn't interrupt other processing.
        # self.foreground_sleep_ms = 10
        # self.background_sleep_ms = 1000
        self.username = self.badge.config.get("nametag").decode().strip()
        self.font = (
            lvgl.font_montserrat_42
        )  ## LVGL font object -- get more below or define your own
        self.all_fonts = {
            "Monserrat 48": lvgl.font_montserrat_48,
            "Monserrat ": lvgl.font_montserrat_42,
            "Monserrat 28": lvgl.font_montserrat_28,
        }
        ## Small state machine to handle button presses in the app
        self.app_states = [
            "default",
            "enter_add_username",
            "in_add_username",
            "enter_fullscreen",
            "in_fullscreen",
            "enter_pick_font",
            "in_pick_font",
        ]
        self.app_state = 0

    def start(self):
        """Register the app with the system.
        This is where to register any functions to be called when a message of that protocol is received.
        The app will start running in the background.
        If you don't have anything else to add, you can delete this method.
        """
        super().start()
        # register_receiver(NEW_PROTOCOL, self.receive_message)

    def run_foreground(self):
        """Run one pass of the app's behavior when it is in the foreground (has keyboard input and control of the screen).
        You do not need to loop here, and the app will sleep for at least self.foreground_sleep_ms milliseconds between calls.
        Don't block in this function, for it will block reading the radio and keyboard.
        If the app only runs in the background, you can delete this method.
        """

        if self.app_states[self.app_state] == "default":
            print("default mode")
            if self.badge.keyboard.f1():
                self.app_state = self.app_states.index("enter_add_username")
            if self.badge.keyboard.f2():
                self.app_state = self.app_states.index("enter_pick_font")
            if self.badge.keyboard.f3():
                self.app_state = self.app_states.index("enter_fullscreen")
            if self.badge.keyboard.f4():
                pass
            if self.badge.keyboard.f5():
                self.badge.display.clear()
                self.switch_to_background()

        if self.app_states[self.app_state] == "enter_add_username":
            print("enter username")
            self.p.create_text_box(self.username)
            self.app_state = self.app_states.index("in_add_username")

        if self.app_states[self.app_state] == "in_add_username":
            key, text = self.p.text_box_type(self.badge.keyboard)

            self.p.set_menubar_button_label(4, "Done")
            if self.badge.keyboard.f5() or self.badge.keyboard.f1():
                self.username = self.p.text_box.get_text().strip()
                self.badge.config.set("nametag", self.username)
                self.badge.config.flush()
                self.p.infobar_left.set_text(f"Hello, My Name Is: {self.username}")
                self.p.close_text_box()
                self.p.set_menubar_button_label(4, "Home")
                self.app_state = self.app_states.index("default")

        if self.app_states[self.app_state] == "enter_fullscreen":
            ## overlay
            print("enter fullscreen")
            ## This screen overlays the previous screen.
            ## If you want a custom background, colors, whatever... this is where you break things.
            self.fullscreen = lvgl.obj(lvgl.screen_active())
            self.fullscreen.add_style(styles.base_style, lvgl.STATE.DEFAULT)
            self.fullscreen.set_width(lvgl.pct(100))
            self.fullscreen.set_height(lvgl.pct(100))
            nametag = lvgl.label(self.fullscreen)
            nametag.set_style_text_font(self.font, lvgl.STATE.DEFAULT)
            nametag.align(lvgl.ALIGN.CENTER, 0, 0)
            nametag.set_text(self.username)

            self.app_state = self.app_states.index("in_fullscreen")

        if self.app_states[self.app_state] == "in_fullscreen":
            if (
                self.badge.keyboard.f1()
                or self.badge.keyboard.f2()
                or self.badge.keyboard.f3()
                or self.badge.keyboard.f4()
                or self.badge.keyboard.f5()
            ):
                self.fullscreen.delete()
                self.app_state = self.app_states.index("default")

        ## Scaffolding here for changing fonts on the fly. Check out the git repo for updates.
        ## Amaze your friends and confound your enemies!
        if self.app_states[self.app_state] == "enter_pick_font":
            print("enter pick_font")
            """pull up a scroller menu to pick fonts from"""
            self.app_state = self.app_states.index("in_pick_font")

        if self.app_states[self.app_state] == "in_pick_font":
            """keys up down enter, any fn key"""
            self.app_state = self.app_states.index("default")

    def run_background(self):
        """App behavior when running in the background.
        You do not need to loop here, and the app will sleep for at least self.background_sleep_ms milliseconds between calls.
        Don't block in this function, for it will block reading the radio and keyboard.
        If the app only does things when running in the foreground, you can delete this method.
        """
        super().run_background()

    def switch_to_foreground(self):
        """Set the app as the active foreground app.
        This will be called by the Menu when the app is selected.
        Any one-time logic to run when the app comes to the foreground (such as setting up the screen) should go here.
        If you don't have special transition logic, you can delete this method.
        """
        super().switch_to_foreground()
        self.p = Page()
        ## Note this order is important: it renders top to bottom that the "content" section expands to fill empty space
        ## If you want to go fully clean-slate, you can draw straight onto the p.scr object, which should fit the full screen.
        self.username = self.badge.config.get("nametag").decode().strip()
        self.p.create_infobar([f"Hello, My Name Is: {self.username}", "Nametag App"])
        self.p.create_content()
        self.p.create_menubar(["Name", "", "Fullscreen", "", "Home"])
        self.p.replace_screen()

    def switch_to_background(self):
        """Set the app as a background app.
        This will be called when the app is first started in the background and when it stops being in the foreground.
        If you don't have special transition logic, you can delete this method.
        """
        self.p = None  ## remove the screen
        super().switch_to_background()
