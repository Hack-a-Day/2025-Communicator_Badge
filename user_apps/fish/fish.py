"""Template app for badge applications. Copy this file and update to implement your own app."""

import uasyncio as aio  # type: ignore

from apps.base_app import BaseApp
from net.net import register_receiver, send, BROADCAST_ADDRESS
from net.protocols import Protocol, NetworkFrame
from ui.page import Page
import ui.styles as styles
import lvgl
import random

"""
All protocols must be defined in their apps with unique ports. Ports must fit in uint8.
Try to pick a protocol ID that isn't in use yet; good luck.
Structdef is the struct library format string. This is a subset of cpython struct.
https://docs.micropython.org/en/latest/library/struct.html
"""
# NEW_PROTOCOL = Protocol(port=<PORT>, name="<NAME>", structdef="!")

SCREEN_WIDTH = 428
SCREEN_HEIGHT = 142
GROUND_HEIGHT = 25  # Height of the sand/gravel layer


def sign(x):
    if x > 0: return 1
    elif x < 0: return -1
    else: return 0

class Bubble:
    def __init__(self, lv_obj):
        self.lv_obj = lv_obj
        self.lv_obj.set_text('o')
        self.x = random.randint(0, SCREEN_WIDTH)
        self.dx = random.uniform(-2, 2)
        self.y = SCREEN_HEIGHT
        self.dy = -random.uniform(1, 4)

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.dx = random.uniform(-2, 2)

        self.lv_obj.set_pos(int(self.x), int(self.y))


class Fish:
    fish_text = {
        -1: "<°)))><",
        0: "<°)))><",
        #0: " }('_'){",
        1: "><(((°>",
    }

    def __init__(self, lv_obj, x, y, dx, dy):
        self.lv_obj = lv_obj
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy

        txt = self.fish_text[sign(self.dx)]
        self.lv_obj.set_text(txt)
        self.update()

    def update(self):
        self.x += self.dx
        self.y += self.dy

        # Bounce off walls
        if self.x <= 0 or self.x >= SCREEN_WIDTH - self.lv_obj.get_width():
            self.dx *= -1
            txt = self.fish_text[sign(self.dx)]
            self.lv_obj.set_text(txt)

        if self.y <= 0 or self.y >= SCREEN_HEIGHT - self.lv_obj.get_height():
            self.dy *= -1

        self.lv_obj.set_pos(int(self.x), int(self.y))


class App(BaseApp):
    """Define a new app to run on the badge."""

    def __init__(self, name: str, badge):
        """ Define any attributes of the class in here, after super().__init__() is called.
            self.badge will be available in the rest of the class methods for accessing the badge hardware.
            If you don't have anything else to add, you can delete this method.
        """
        super().__init__(name, badge)
        self.foreground_sleep_ms = 50  # Update rate for animation
        self.p = None
        self.fishes = set()
        self.bubbles = set()
        self.num_fishes = 10
        self.bubble_timer = 0

    def start(self):
        """ Register the app with the system.
            This is where to register any functions to be called when a message of that protocol is received.
            The app will start running in the background.
            If you don't have anything else to add, you can delete this method.
        """
        super().start()
        # register_receiver(NEW_PROTOCOL, self.receive_message)

    def run_foreground(self):
        """ Run one pass of the app's behavior when it is in the foreground (has keyboard input and control of the screen).
            You do not need to loop here, and the app will sleep for at least self.foreground_sleep_ms milliseconds between calls.
            Don't block in this function, for it will block reading the radio and keyboard.
            If the app only runs in the background, you can delete this method.
        """
        # Exit on any key press
        if self.badge.keyboard.read_key() is not None:
            self.switch_to_background()
            return

        remove_bubbles = [b for b in self.bubbles if b.y <= 2]
        for bubble in remove_bubbles:
            bubble.lv_obj.delete()
            self.bubbles.remove(bubble)

        for fish in self.fishes:
            fish.update()
        for bubble in self.bubbles:
            bubble.update()

        self.bubble_timer += 1
        if self.bubble_timer % 10 == 0:
            bubble_obj = lvgl.label(self.p.scr)
            bubble_obj.set_style_text_color(lvgl.color_hex(0xFFFFFF), 0)
            self.bubbles.add(Bubble(bubble_obj))

    def run_background(self):
        """ App behavior when running in the background.
            You do not need to loop here, and the app will sleep for at least self.background_sleep_ms milliseconds between calls.
            Don't block in this function, for it will block reading the radio and keyboard.
            If the app only does things when running in the foreground, you can delete this method.
        """
        super().run_background()

    def switch_to_foreground(self):
        """ Set the app as the active foreground app.
            This will be called by the Menu when the app is selected.
            Any one-time logic to run when the app comes to the foreground (such as setting up the screen) should go here.
            If you don't have special transition logic, you can delete this method.
        """
        super().switch_to_foreground()
        self.p = Page() # We'll draw on p.scr

        # Style for the water (Blue gradient background)
        water_style = lvgl.style_t()
        water_style.init()
        water_style.set_bg_opa(lvgl.OPA.COVER)
        water_style.set_bg_grad_dir(lvgl.GRAD_DIR.VER)
        # Darker blue at the bottom, lighter blue at the top
        water_style.set_bg_color(lvgl.color_make(0x66, 0xCC, 0xFF))
        water_style.set_bg_grad_color(lvgl.color_make(0x01, 0x50, 0x80))

        water = lvgl.obj(self.p.scr)
        water.add_style(water_style, 0)
        water.set_size(SCREEN_WIDTH, SCREEN_HEIGHT)
        water.align(lvgl.ALIGN.TOP_MID, 0, 0)
        
        # Style for the sand/gravel (Brown/Gold)
        style_ground = lvgl.style_t()
        style_ground.init()
        style_ground.set_bg_opa(lvgl.OPA.COVER)
        style_ground.set_bg_color(lvgl.color_make(0xB8, 0x86, 0x0B)) # Gold/Brown color
        style_ground.set_radius(0)

        # --- 2. Create Ground (Sand/Gravel) ---
        ground = lvgl.obj(self.p.scr)
        ground.remove_style_all()
        ground.add_style(style_ground, 0)
        ground.set_size(SCREEN_WIDTH, GROUND_HEIGHT)
        ground.align(lvgl.ALIGN.BOTTOM_MID, 0, 0)

        self.fishes = []
        for _ in range(self.num_fishes):
            fish_obj = lvgl.label(self.p.scr)
            fish_obj.set_style_text_color(lvgl.color_hex(random.randint(0, 0xFFFFFF)), 0)
            
            # Ensure fish are moving
            dx = 0
            while -0.5 < dx < 0.5:
                dx = random.uniform(-2, 2)

            x = random.randint(0, SCREEN_WIDTH - 50)
            y = random.randint(0, SCREEN_HEIGHT - 10)
            dy = random.uniform(-1, 1)
            
            self.fishes.append(Fish(fish_obj, float(x), float(y), dx, dy))

        self.p.replace_screen()

    def switch_to_background(self):
        """ Set the app as a background app.
            This will be called when the app is first started in the background and when it stops being in the foreground.
            If you don't have special transition logic, you can delete this method.
        """
        self.fishes = set()
        self.bubbles = set()
        self.p = None
        super().switch_to_background()
