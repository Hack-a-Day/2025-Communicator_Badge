"""Screensaver app with multiple visual effects."""

import lvgl
import random
import time
from apps.base_app import BaseApp
from ui import styles


class ScreensaverApp(BaseApp):
    """Screensaver app with multiple animated effects."""

    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.foreground_sleep_ms = 20  # Faster loop = more responsive buttons

        # Available screensavers
        self.screensavers = [
            "Starfield",
            "Matrix Rain",
            "Bouncing Balls",
            "DVD Logo",
            "SMPTE Bars",
            "Plasma",  # Moved to end - heavy rendering
        ]
        self.current_saver = 0

        # SMPTE color bars state
        self.smpte_offset = 0
        self.smpte_bars = []

        # Starfield state
        self.stars = []
        self.star_objects = []

        # Matrix rain state
        self.matrix_columns = []
        self.matrix_labels = []

        # Bouncing balls state
        self.balls = []
        self.ball_objects = []

        # Plasma state
        self.plasma_time = 0
        self.plasma_pixels = []

        # DVD logo state
        self.dvd_x = 100
        self.dvd_y = 50
        self.dvd_dx = 2
        self.dvd_dy = 2
        self.dvd_color = 0xFF0000
        self.dvd_object = None

        # UI elements
        self.title_label = None

    def init_starfield(self):
        """Initialize starfield effect."""
        self.stars = []
        for _ in range(25):  # Reduced from 50 for better performance
            self.stars.append({
                'x': random.randint(0, 428),
                'y': random.randint(0, 142),
                'speed': random.randint(1, 4),
                'size': random.randint(1, 3)
            })

    def update_starfield(self):
        """Update starfield animation."""
        # Clear old stars
        for obj in self.star_objects:
            if obj:
                obj.delete()
        self.star_objects = []

        # Update and draw stars
        for star in self.stars:
            star['x'] -= star['speed']
            if star['x'] < 0:
                star['x'] = 428
                star['y'] = random.randint(0, 142)

            # Draw star
            obj = lvgl.obj(self.badge.display.screen)
            obj.set_size(star['size'], star['size'])
            obj.set_pos(int(star['x']), int(star['y']))
            obj.set_style_bg_color(lvgl.color_hex(0xFFFFFF), 0)
            obj.set_style_border_width(0, 0)
            self.star_objects.append(obj)

    def init_matrix_rain(self):
        """Initialize Matrix-style rain effect."""
        self.matrix_columns = []
        num_columns = 15  # Reduced from 30 to avoid memory issues
        for i in range(num_columns):
            self.matrix_columns.append({
                'x': i * (428 // num_columns),
                'y': random.randint(-50, 0),
                'speed': random.randint(2, 6),
                'chars': [chr(random.randint(33, 126)) for _ in range(5)]  # Reduced from 8
            })

    def update_matrix_rain(self):
        """Update Matrix rain animation."""
        try:
            # Clear old labels
            for lbl in self.matrix_labels:
                if lbl:
                    try:
                        lbl.delete()
                    except:
                        pass
            self.matrix_labels = []

            # Update and draw columns
            for col_idx, col in enumerate(self.matrix_columns):
                # Check keyboard every few columns
                if col_idx % 5 == 0:
                    if self.badge.keyboard.f1() or self.badge.keyboard.f2() or self.badge.keyboard.f5():
                        return True  # Signal button was pressed

                col['y'] += col['speed']
                if col['y'] > 150:
                    col['y'] = random.randint(-50, -10)
                    col['chars'] = [chr(random.randint(33, 126)) for _ in range(5)]

                # Draw characters in column
                for idx, char in enumerate(col['chars']):
                    y_pos = int(col['y'] + idx * 15)
                    if 0 <= y_pos < 142:
                        label = lvgl.label(self.badge.display.screen)
                        label.set_text(char)
                        # Fade from bright green to dark
                        brightness = max(0, 255 - idx * 40)
                        color = (brightness << 8)  # Green channel
                        label.set_style_text_color(lvgl.color_hex(color), 0)
                        label.set_pos(col['x'], y_pos)
                        self.matrix_labels.append(label)
            return False
        except Exception as e:
            print(f"Matrix rain error: {e}")
            return False

    def init_bouncing_balls(self):
        """Initialize bouncing balls effect."""
        self.balls = []
        for _ in range(5):  # Reduced from 8 for better performance
            self.balls.append({
                'x': random.randint(10, 400),
                'y': random.randint(10, 120),
                'dx': random.randint(-3, 3),
                'dy': random.randint(-3, 3),
                'color': random.randint(0, 0xFFFFFF),
                'size': random.randint(10, 20)
            })

    def update_bouncing_balls(self):
        """Update bouncing balls animation."""
        # Clear old balls
        for obj in self.ball_objects:
            if obj:
                obj.delete()
        self.ball_objects = []

        # Update and draw balls
        for ball in self.balls:
            # Update position
            ball['x'] += ball['dx']
            ball['y'] += ball['dy']

            # Bounce off walls
            if ball['x'] <= 0 or ball['x'] >= 428 - ball['size']:
                ball['dx'] = -ball['dx']
                ball['color'] = random.randint(0, 0xFFFFFF)
            if ball['y'] <= 0 or ball['y'] >= 142 - ball['size']:
                ball['dy'] = -ball['dy']
                ball['color'] = random.randint(0, 0xFFFFFF)

            # Draw ball
            obj = lvgl.obj(self.badge.display.screen)
            obj.set_size(ball['size'], ball['size'])
            obj.set_pos(int(ball['x']), int(ball['y']))
            obj.set_style_bg_color(lvgl.color_hex(ball['color']), 0)
            obj.set_style_border_width(0, 0)
            obj.set_style_radius(ball['size'] // 2, 0)
            self.ball_objects.append(obj)

    def init_plasma(self):
        """Initialize plasma effect."""
        self.plasma_time = 0
        self.plasma_pixels = []

    def update_plasma(self):
        """Update plasma animation."""
        # Clear old pixels
        for obj in self.plasma_pixels:
            if obj:
                obj.delete()
        self.plasma_pixels = []

        # Draw plasma (HEAVILY simplified for performance - larger blocks)
        self.plasma_time += 0.1
        pixel_count = 0
        for x in range(0, 428, 32):  # Changed to 32x32 blocks for better performance
            for y in range(0, 142, 32):  # ~70 objects per frame vs ~240 at 16x16
                # Check keyboard every 5 pixels to allow interruption
                pixel_count += 1
                if pixel_count % 5 == 0:
                    if self.badge.keyboard.f1() or self.badge.keyboard.f2() or self.badge.keyboard.f5():
                        # Button pressed during rendering, return early
                        return True

                # Simple plasma calculation
                value = abs(int(128 + 128 * ((x / 50) + (y / 50) + self.plasma_time)))
                color = ((value & 0xFF) << 16) | ((255 - value) << 8) | 128

                obj = lvgl.obj(self.badge.display.screen)
                obj.set_size(32, 32)  # 32x32 blocks for much better performance
                obj.set_pos(x, y)
                obj.set_style_bg_color(lvgl.color_hex(color), 0)
                obj.set_style_border_width(0, 0)
                self.plasma_pixels.append(obj)
        return False  # No button pressed

    def init_dvd_logo(self):
        """Initialize DVD logo bouncing effect."""
        self.dvd_x = 214  # Center
        self.dvd_y = 71
        self.dvd_dx = 3
        self.dvd_dy = 2
        self.dvd_color = 0xFF0000

    def init_smpte_bars(self):
        """Initialize SMPTE color bars."""
        self.smpte_offset = 0
        self.smpte_bars = []

    def update_smpte_bars(self):
        """Update SMPTE color bars with scrolling effect."""
        # Clear old bars
        for obj in self.smpte_bars:
            if obj:
                try:
                    obj.delete()
                except:
                    pass
        self.smpte_bars = []

        # SMPTE color bar pattern (standard test pattern colors)
        # Top section: 75% color bars
        top_colors = [
            0xC0C0C0,  # White (75%)
            0xC0C000,  # Yellow
            0x00C0C0,  # Cyan
            0x00C000,  # Green
            0xC000C0,  # Magenta
            0xC00000,  # Red
            0x0000C0,  # Blue
        ]

        # Middle section: reverse bars
        mid_colors = [
            0x0000C0,  # Blue
            0x000000,  # Black
            0xC000C0,  # Magenta
            0x000000,  # Black
            0x00C0C0,  # Cyan
            0x000000,  # Black
            0xC0C0C0,  # White
        ]

        # Bottom section: PLUGE pattern
        bottom_colors = [
            0x0D0D61,  # Dark blue
            0xFFFFFF,  # White
            0x350566,  # Purple
            0x000000,  # Black
            0x000000,  # Black (slightly different)
            0x1D1D1D,  # Dark grey
            0x000000,  # Black
        ]

        bar_width = 428 // 7

        # Scroll offset
        self.smpte_offset = (self.smpte_offset + 2) % 428

        # Draw top section (60% of height)
        for i, color in enumerate(top_colors):
            x = (i * bar_width - self.smpte_offset) % 428
            obj = lvgl.obj(self.badge.display.screen)
            obj.set_size(bar_width + 2, 85)  # +2 for overlap
            obj.set_pos(x, 20)
            obj.set_style_bg_color(lvgl.color_hex(color), 0)
            obj.set_style_border_width(0, 0)
            self.smpte_bars.append(obj)

            # Draw second copy for seamless scrolling
            if x > 428 - bar_width:
                obj2 = lvgl.obj(self.badge.display.screen)
                obj2.set_size(bar_width + 2, 85)
                obj2.set_pos(x - 428, 20)
                obj2.set_style_bg_color(lvgl.color_hex(color), 0)
                obj2.set_style_border_width(0, 0)
                self.smpte_bars.append(obj2)

        # Draw middle section (25% of height)
        for i, color in enumerate(mid_colors):
            x = (i * bar_width - self.smpte_offset) % 428
            obj = lvgl.obj(self.badge.display.screen)
            obj.set_size(bar_width + 2, 30)
            obj.set_pos(x, 105)
            obj.set_style_bg_color(lvgl.color_hex(color), 0)
            obj.set_style_border_width(0, 0)
            self.smpte_bars.append(obj)

            if x > 428 - bar_width:
                obj2 = lvgl.obj(self.badge.display.screen)
                obj2.set_size(bar_width + 2, 30)
                obj2.set_pos(x - 428, 105)
                obj2.set_style_bg_color(lvgl.color_hex(color), 0)
                obj2.set_style_border_width(0, 0)
                self.smpte_bars.append(obj2)

        # Draw bottom section (15% of height)
        for i, color in enumerate(bottom_colors):
            x = (i * bar_width - self.smpte_offset) % 428
            obj = lvgl.obj(self.badge.display.screen)
            obj.set_size(bar_width + 2, 7)
            obj.set_pos(x, 135)
            obj.set_style_bg_color(lvgl.color_hex(color), 0)
            obj.set_style_border_width(0, 0)
            self.smpte_bars.append(obj)

            if x > 428 - bar_width:
                obj2 = lvgl.obj(self.badge.display.screen)
                obj2.set_size(bar_width + 2, 7)
                obj2.set_pos(x - 428, 135)
                obj2.set_style_bg_color(lvgl.color_hex(color), 0)
                obj2.set_style_border_width(0, 0)
                self.smpte_bars.append(obj2)

    def update_dvd_logo(self):
        """Update DVD logo animation."""
        # Clear old logo
        if self.dvd_object:
            self.dvd_object.delete()

        # Update position
        self.dvd_x += self.dvd_dx
        self.dvd_y += self.dvd_dy

        # Bounce and change color
        if self.dvd_x <= 0 or self.dvd_x >= 428 - 60:
            self.dvd_dx = -self.dvd_dx
            self.dvd_color = random.randint(0, 0xFFFFFF)
        if self.dvd_y <= 20 or self.dvd_y >= 142 - 40:
            self.dvd_dy = -self.dvd_dy
            self.dvd_color = random.randint(0, 0xFFFFFF)

        # Draw logo (simple box with "DVD" text)
        self.dvd_object = lvgl.label(self.badge.display.screen)
        self.dvd_object.set_text("DVD")
        self.dvd_object.set_style_text_color(lvgl.color_hex(self.dvd_color), 0)
        self.dvd_object.set_style_text_font(lvgl.font_montserrat_28, 0)
        self.dvd_object.set_pos(int(self.dvd_x), int(self.dvd_y))

    def switch_screensaver(self, direction=1):
        """Switch to next/previous screensaver."""
        # Clean up current screensaver
        self.clear_current()

        # Move to next/previous
        self.current_saver = (self.current_saver + direction) % len(self.screensavers)

        # Initialize new screensaver
        self.init_current()

        # Update title
        if self.title_label:
            try:
                self.title_label.set_text(self.screensavers[self.current_saver])
            except:
                # If title label is invalid, recreate it
                self.title_label = lvgl.label(self.badge.display.screen)
                self.title_label.set_text(self.screensavers[self.current_saver])
                self.title_label.set_style_text_color(styles.hackaday_yellow, 0)
                self.title_label.set_pos(214 - 40, 2)  # Approximately centered

    def init_current(self):
        """Initialize the current screensaver."""
        saver_name = self.screensavers[self.current_saver]
        if saver_name == "Starfield":
            self.init_starfield()
        elif saver_name == "Matrix Rain":
            self.init_matrix_rain()
        elif saver_name == "Bouncing Balls":
            self.init_bouncing_balls()
        elif saver_name == "Plasma":
            self.init_plasma()
        elif saver_name == "DVD Logo":
            self.init_dvd_logo()
        elif saver_name == "SMPTE Bars":
            self.init_smpte_bars()

    def update_current(self):
        """Update the current screensaver. Returns True if a button was pressed during update."""
        saver_name = self.screensavers[self.current_saver]
        button_pressed = False

        if saver_name == "Starfield":
            self.update_starfield()
        elif saver_name == "Matrix Rain":
            button_pressed = self.update_matrix_rain()
        elif saver_name == "Bouncing Balls":
            self.update_bouncing_balls()
        elif saver_name == "Plasma":
            button_pressed = self.update_plasma()
        elif saver_name == "DVD Logo":
            self.update_dvd_logo()
        elif saver_name == "SMPTE Bars":
            self.update_smpte_bars()

        return button_pressed

    def clear_current(self):
        """Clear current screensaver objects."""
        try:
            for obj in self.star_objects:
                if obj:
                    try:
                        obj.delete()
                    except:
                        pass
            for obj in self.matrix_labels:
                if obj:
                    try:
                        obj.delete()
                    except:
                        pass
            for obj in self.ball_objects:
                if obj:
                    try:
                        obj.delete()
                    except:
                        pass
            for obj in self.plasma_pixels:
                if obj:
                    try:
                        obj.delete()
                    except:
                        pass
            for obj in self.smpte_bars:
                if obj:
                    try:
                        obj.delete()
                    except:
                        pass
            if self.dvd_object:
                try:
                    self.dvd_object.delete()
                except:
                    pass
        except Exception as e:
            print(f"Clear error: {e}")
        finally:
            self.star_objects = []
            self.matrix_labels = []
            self.ball_objects = []
            self.plasma_pixels = []
            self.smpte_bars = []
            self.dvd_object = None

    def switch_to_foreground(self):
        """Set up the screensaver screen."""
        super().switch_to_foreground()
        self.badge.display.clear()

        # Set background to black
        self.badge.display.screen.set_style_bg_color(lvgl.color_hex(0x000000), 0)

        # Set up function key labels
        self.badge.display.f1("Prev", styles.hackaday_yellow)
        self.badge.display.f2("Next", styles.hackaday_yellow)
        self.badge.display.f5("Exit", styles.hackaday_yellow)

        # Create title label
        self.title_label = lvgl.label(self.badge.display.screen)
        self.title_label.set_text(self.screensavers[self.current_saver])
        self.title_label.set_style_text_color(styles.hackaday_yellow, 0)
        # Position at top center manually (TOP_CENTER doesn't exist in this LVGL version)
        self.title_label.set_pos(214 - 40, 2)  # Approximately centered

        # Initialize current screensaver
        self.init_current()

    def run_foreground(self):
        """Main screensaver loop."""
        try:
            # Check for exit first
            if self.badge.keyboard.f5():
                self.switch_to_background()
                return

            # Check for screensaver change
            if self.badge.keyboard.f1():
                self.switch_screensaver(-1)
                return

            if self.badge.keyboard.f2():
                self.switch_screensaver(1)
                return

            # Update current screensaver - it may return True if button was pressed during update
            button_pressed = self.update_current()

            # If button was pressed during animation, handle it on next loop
            if button_pressed:
                # Check which button and handle accordingly
                if self.badge.keyboard.f5():
                    self.switch_to_background()
                elif self.badge.keyboard.f1():
                    self.switch_screensaver(-1)
                elif self.badge.keyboard.f2():
                    self.switch_screensaver(1)
        except Exception as e:
            print(f"Screensaver error: {e}")
            # Try to recover by clearing and reinitializing
            try:
                self.clear_current()
                self.init_current()
            except:
                # If recovery fails, just exit
                self.switch_to_background()

    def switch_to_background(self):
        """Clean up when going to background."""
        super().switch_to_background()

        # Clear all screensaver objects
        self.clear_current()

        # Delete title label
        if self.title_label:
            try:
                self.title_label.delete()
            except:
                pass
            self.title_label = None

        # Clear the entire display (this cleans up function key labels too)
        try:
            self.badge.display.clear()
        except:
            pass

        # Reset background color to default
        try:
            self.badge.display.screen.set_style_bg_color(styles.hackaday_grey, 0)
        except:
            pass
