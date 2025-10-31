# Display manager and helpers

import lvgl
from hardware import lvgl_setup

from hardware import board
from ui import styles


class Display:
    def __init__(self):
        # NV3007 TFT LCD 2.79"
        self._screen = lvgl_setup.lcd_init()
        self.backlight = board.LCD_BACKLIGHT
        self.backlight.duty(500)  ## PWM: 0-1023

        self.default_color = 0x0000
        self.max_width = 428
        self.max_height = 142
        self.CHAR_HEIGHT = 12
        self.CHAR_WIDTH = 12
        self.screen.set_style_bg_color(styles.hackaday_grey, 0)
        print("Display initialized")

    @property
    def screen(self):
        return lvgl.screen_active()

    def _fn_label(self, text: str, y: int, color=None):
        if color is None:
            color = styles.hackaday_yellow
        label = lvgl.label(self.screen)
        label.set_text(text)
        label.set_style_text_color(color, 0)
        label.set_style_text_font(lvgl.font_montserrat_16, 0)
        label.set_style_bg_color(styles.hackaday_grey, 0)
        label.set_style_text_color(color, 0)
        label.align(lvgl.ALIGN.BOTTOM_LEFT, int(y), 0)

    def f1(self, text, color=None):
        self._fn_label(text, 0, color)

    def f2(self, text, color=None):
        self._fn_label(text, 110 - len(text) * self.CHAR_WIDTH / 2, color)

    def f3(self, text, color=None):
        self._fn_label(text, 214 - len(text) * self.CHAR_WIDTH / 2, color)

    def f4(self, text, color=None):
        self._fn_label(text, 310 - len(text) * self.CHAR_WIDTH / 2, color)

    def f5(self, text, color=None):
        self._fn_label(text, 428 - len(text) * self.CHAR_WIDTH, color)

    def text(self, x, y, text, color=0xFFFFFF):
        """Draw text on the screen.
        Use badge.display.CHAR_WIDTH and badge.display.CHAR_HEIGHT for calculating (x, y) offsets.
        Args:
            x: Row of top of character, in pixels from top of screen.
            y: Col of left of first character, in pixels from left of screen.
            text: ASCII Text to draw.
            color: Color to set text to. Encoding: RRGGBB
        """
        line = lvgl.label(self.screen)
        line.set_style_text_color(lvgl.color_hex(color), 0)
        line.align(lvgl.ALIGN.TOP_LEFT, y, x)
        line.set_text(text)
        # lvgl.screen_load(self.display)
        return line

    def clear(self):
        """Clear the entire display."""
        for i in range(self.screen.get_child_count()):
            self.screen.get_child(0).delete()

    def image(self, x: int, y: int, filename: str):
        image = lvgl.image(self.screen)
        with open(filename, "rb") as f:
            image_data = f.read()
        image_dsc = lvgl.image_dsc_t({"data_size": len(image_data), "data": image_data})
        image.set_src(image_dsc)
        image.align(lvgl.ALIGN.CENTER, y, x)
        return image
