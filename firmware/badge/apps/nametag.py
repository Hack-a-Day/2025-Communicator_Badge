"""Template app for badge applications. Copy this file and update to implement your own app."""

import uasyncio as aio  # type: ignore

from apps.base_app import BaseApp
from net.net import register_receiver, send, BROADCAST_ADDRESS
from net.protocols import Protocol, NetworkFrame
from ui.page import Page
import ui.styles as styles
import lvgl
import os
from ui import graphics

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
        # Nametag image configuration
        try:
            self.show_image = self.badge.config.get("nametag_show_image").decode().strip() in ("1", "true", "True")
        except Exception:
            self.show_image = False
        try:
            self.image_path = self.badge.config.get("nametag_image").decode().strip()
        except Exception:
            self.image_path = "images/headshots/wrencher.png"
        self.font = (
            lvgl.font_montserrat_42
        )  ## LVGL font object -- get more below or define your own
        self.all_fonts = {
            "Monserrat 48": lvgl.font_montserrat_48,
            "Monserrat ": lvgl.font_montserrat_42,
            "Monserrat 28": lvgl.font_montserrat_28,
        }
        # Image picker state
        self.image_dir = "images/headshots"
        self.headshot_files = []
        self.headshot_index = 0
        self.picker_image = None
        self.picker_label = None
        ## Small state machine to handle button presses in the app
        self.app_states = [
            "default",
            "enter_add_username",
            "in_add_username",
            "enter_fullscreen",
            "in_fullscreen",
            "enter_pick_font",
            "in_pick_font",
            "enter_pick_image",
            "in_pick_image",
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
                self.app_state = self.app_states.index("enter_pick_image")
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
            self.p.set_menubar_button_label(4, "Done")

        if self.app_states[self.app_state] == "in_add_username":
            key, text = self.p.text_box_type(self.badge.keyboard)

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

            # Build fullscreen content: image on the left, name on the right (no scaling)
            fs_headshot = None
            if self.show_image and self.image_path:
                try:
                    fs_headshot = graphics.create_image(self.image_path, self.fullscreen)
                    fs_headshot.set_style_radius(40, 0)
                    fs_headshot.align(lvgl.ALIGN.LEFT_MID, 10, 0)
                except Exception as e:
                    print("Nametag FS image load failed:", e)
                    fs_headshot = None

            fs_label = lvgl.label(self.fullscreen)
            fs_label.set_style_text_font(self.font, lvgl.STATE.DEFAULT)
            if fs_headshot:
                fs_label.align_to(fs_headshot, lvgl.ALIGN.OUT_RIGHT_MID, 10, 0)
            else:
                fs_label.align(lvgl.ALIGN.CENTER, 0, 0)
            fs_label.set_text(self.username)

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

        # Enter image picker: list images/headshots/*.png and show preview with filename
        if self.app_states[self.app_state] == "enter_pick_image":
            try:
                files = []
                for fname in os.listdir(self.image_dir):
                    fn_lower = fname.lower()
                    if fn_lower.endswith(".png"):
                        files.append(fname)
                files.sort()
                self.headshot_files = files
            except Exception as e:
                print("Nametag: listdir failed:", e)
                self.headshot_files = []

            if not self.headshot_files:
                # No images found, notify and return
                try:
                    self.p.infobar_left.set_text("No headshots in images/headshots/")
                except Exception:
                    pass
                self.app_state = self.app_states.index("default")
            else:
                # Start at current selection if present
                try:
                    current_basename = self.image_path.split("/")[-1]
                    if current_basename in self.headshot_files:
                        self.headshot_index = self.headshot_files.index(current_basename)
                    else:
                        self.headshot_index = 0
                except Exception:
                    self.headshot_index = 0

                # Clear current content widgets
                try:
                    if self.headshot:
                        self.headshot.delete()
                        self.headshot = None
                except Exception:
                    pass
                try:
                    if self.name_label:
                        self.name_label.delete()
                        self.name_label = None
                except Exception:
                    pass

                # Build picker preview
                try:
                    fullpath = self.image_dir + "/" + self.headshot_files[self.headshot_index]
                    self.picker_image = graphics.create_image(fullpath, self.p.content)
                    self.picker_image.set_style_radius(40, 0)
                    self.picker_image.align(lvgl.ALIGN.LEFT_MID, 10, 0)
                except Exception as e:
                    print("Nametag: picker image load failed:", e)
                    self.picker_image = None

                self.picker_label = lvgl.label(self.p.content)
                label_text = self.headshot_files[self.headshot_index]
                if self.picker_image:
                    self.picker_label.align_to(self.picker_image, lvgl.ALIGN.OUT_RIGHT_MID, 10, 0)
                else:
                    self.picker_label.align(lvgl.ALIGN.CENTER, 0, 0)
                self.picker_label.set_text(label_text)

                # Update menubar for picker controls: F1 Select, F3 Prev, F4 Next, F5 Cancel
                try:
                    self.p.set_menubar_button_label(0, "Select")
                    self.p.set_menubar_button_label(1, "")
                    self.p.set_menubar_button_label(2, "Prev")
                    self.p.set_menubar_button_label(3, "Next")
                    self.p.set_menubar_button_label(4, "Cancel")
                except Exception:
                    pass
                self.app_state = self.app_states.index("in_pick_image")

        # Handle image picker navigation and selection
        if self.app_states[self.app_state] == "in_pick_image":
            # Prev (F3)
            if self.badge.keyboard.f3():
                if self.headshot_files:
                    self.headshot_index = (self.headshot_index - 1) % len(self.headshot_files)
                    # Refresh preview
                    try:
                        if self.picker_image:
                            self.picker_image.delete()
                    except Exception:
                        pass
                    fullpath = self.image_dir + "/" + self.headshot_files[self.headshot_index]
                    try:
                        self.picker_image = graphics.create_image(fullpath, self.p.content)
                        self.picker_image.set_style_radius(40, 0)
                        self.picker_image.align(lvgl.ALIGN.LEFT_MID, 10, 0)
                    except Exception as e:
                        print("Nametag: picker image load failed:", e)
                        self.picker_image = None
                    try:
                        if self.picker_label:
                            self.picker_label.delete()
                    except Exception:
                        pass
                    self.picker_label = lvgl.label(self.p.content)
                    if self.picker_image:
                        self.picker_label.align_to(self.picker_image, lvgl.ALIGN.OUT_RIGHT_MID, 10, 0)
                    else:
                        self.picker_label.align(lvgl.ALIGN.CENTER, 0, 0)
                    self.picker_label.set_text(self.headshot_files[self.headshot_index])

            # Next (F4)
            if self.badge.keyboard.f4():
                if self.headshot_files:
                    self.headshot_index = (self.headshot_index + 1) % len(self.headshot_files)
                    # Refresh preview
                    try:
                        if self.picker_image:
                            self.picker_image.delete()
                    except Exception:
                        pass
                    fullpath = self.image_dir + "/" + self.headshot_files[self.headshot_index]
                    try:
                        self.picker_image = graphics.create_image(fullpath, self.p.content)
                        self.picker_image.set_style_radius(40, 0)
                        self.picker_image.align(lvgl.ALIGN.LEFT_MID, 10, 0)
                    except Exception as e:
                        print("Nametag: picker image load failed:", e)
                        self.picker_image = None
                    try:
                        if self.picker_label:
                            self.picker_label.delete()
                    except Exception:
                        pass
                    self.picker_label = lvgl.label(self.p.content)
                    if self.picker_image:
                        self.picker_label.align_to(self.picker_image, lvgl.ALIGN.OUT_RIGHT_MID, 10, 0)
                    else:
                        self.picker_label.align(lvgl.ALIGN.CENTER, 0, 0)
                    self.picker_label.set_text(self.headshot_files[self.headshot_index])

            # Select (F1)
            if self.badge.keyboard.f1():
                if self.headshot_files:
                    chosen = self.image_dir + "/" + self.headshot_files[self.headshot_index]
                    try:
                        self.badge.config.set("nametag_image", chosen)
                        self.badge.config.set("nametag_show_image", b"1")
                        self.badge.config.flush()
                    except Exception as e:
                        print("Nametag: failed to save config:", e)
                    # Small confirmation
                    try:
                        self.p.infobar_left.set_text("Headshot set: " + self.headshot_files[self.headshot_index])
                    except Exception:
                        pass
                # Exit picker and rebuild main view
                try:
                    if self.picker_image:
                        self.picker_image.delete()
                        self.picker_image = None
                    if self.picker_label:
                        self.picker_label.delete()
                        self.picker_label = None
                except Exception:
                    pass
                # Re-render the whole screen to reflect change
                self.app_state = self.app_states.index("default")
                self.switch_to_foreground()
                return

            # Cancel/Back (F5)
            if self.badge.keyboard.f5():
                try:
                    if self.picker_image:
                        self.picker_image.delete()
                        self.picker_image = None
                    if self.picker_label:
                        self.picker_label.delete()
                        self.picker_label = None
                except Exception:
                    pass
                # Restore default labels
                try:
                    self.p.set_menubar_button_label(0, "Name")
                    self.p.set_menubar_button_label(1, "Pick Img")
                    self.p.set_menubar_button_label(2, "Fullscreen")
                    self.p.set_menubar_button_label(3, "")
                    self.p.set_menubar_button_label(4, "Home")
                except Exception:
                    pass
                self.app_state = self.app_states.index("default")
                # Rebuild main content
                self.switch_to_foreground()
                return

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
        # Refresh image config on entry
        try:
            self.show_image = self.badge.config.get("nametag_show_image").decode().strip() in ("1", "true", "True")
        except Exception:
            self.show_image = False
        try:
            self.image_path = self.badge.config.get("nametag_image").decode().strip()
        except Exception:
            self.image_path = "images/headshots/wrencher.png"
        self.p.create_infobar([f"Hello, My Name Is: {self.username}", "Nametag App"])
        self.p.create_content()
        self.p.create_menubar(["Name", "Pick Img", "Fullscreen", "", "Home"])
        # Build content: image on the left (rounded), name label to the right. No scaling.
        self.name_label = None
        self.headshot = None
        try:
            if self.show_image and self.image_path:
                self.headshot = graphics.create_image(self.image_path, self.p.content)
                # Mimic Talks app styling: rounded corners (circle at 100x100)
                self.headshot.set_style_radius(40, 0)
                self.headshot.align(lvgl.ALIGN.LEFT_MID, 10, 0)
        except Exception as e:
            # If image cannot be loaded, fall back to text-only
            print("Nametag image load failed:", e)
            self.headshot = None
        # Create the name label
        self.name_label = lvgl.label(self.p.content)
        self.name_label.set_style_text_font(self.font, lvgl.STATE.DEFAULT)
        if self.headshot:
            # Place the text to the right of the image, vertically centered
            self.name_label.align_to(self.headshot, lvgl.ALIGN.OUT_RIGHT_MID, 10, 0)
        else:
            # Center text if no image
            self.name_label.align(lvgl.ALIGN.CENTER, 0, 0)
        self.name_label.set_text(self.username)
        self.p.replace_screen()

    def switch_to_background(self):
        """Set the app as a background app.
        This will be called when the app is first started in the background and when it stops being in the foreground.
        If you don't have special transition logic, you can delete this method.
        """
        self.p = None  ## remove the screen
        super().switch_to_background()
