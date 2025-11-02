"""Hardware Monitor app - displays system information across multiple pages."""

import lvgl
import gc
import machine
import micropython
import sys
from apps.base_app import BaseApp
from ui import styles

try:
    import esp32
    HAS_ESP32 = True
except ImportError:
    HAS_ESP32 = False

try:
    import os
    HAS_OS = True
except ImportError:
    HAS_OS = False


class HardwareMonitor(BaseApp):
    """Multi-page hardware monitor showing system info."""

    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.foreground_sleep_ms = 50  # Fast response for buttons

        self.pages = [
            "System",
            "Memory",
            "Display",
            "LoRa",
            "I2C/GPIO",
            "Config"
        ]
        self.current_page = 0
        self.scroll_offset = 0  # For scrolling within a page
        self.max_visible_lines = 9  # Number of lines that fit on screen
        self.update_counter = 0
        self.update_interval = 20  # Redraw every 20 iterations (1 second)

        # LVGL objects
        self.title_label = None
        self.info_labels = []
        self.scroll_indicator = None
        self.current_lines = []  # Store current page lines for scrolling

    def switch_to_foreground(self):
        """Set up the monitor screen."""
        super().switch_to_foreground()
        self.badge.display.clear()
        self.badge.display.screen.set_style_bg_color(lvgl.color_hex(0x000000), 0)

        # Set up function key labels
        self.badge.display.f1("Prev", styles.hackaday_yellow)
        self.badge.display.f2("Next", styles.hackaday_yellow)
        self.badge.display.f5("Exit", styles.hackaday_yellow)

        # Create title label
        self.title_label = lvgl.label(self.badge.display.screen)
        self.title_label.set_style_text_color(styles.hackaday_yellow, 0)
        self.title_label.set_pos(10, 2)

        # Draw initial page
        self.draw_page()

    def draw_page(self):
        """Draw the current page."""
        # Clear old labels
        for label in self.info_labels:
            try:
                label.delete()
            except:
                pass
        self.info_labels = []

        # Clear scroll indicator
        if self.scroll_indicator:
            try:
                self.scroll_indicator.delete()
            except:
                pass
            self.scroll_indicator = None

        # Update title
        if self.title_label:
            self.title_label.set_text(f"HW Monitor - {self.pages[self.current_page]}")

        # Get page data
        if self.current_page == 0:
            self.current_lines = self.get_system_info()
        elif self.current_page == 1:
            self.current_lines = self.get_memory_info()
        elif self.current_page == 2:
            self.current_lines = self.get_display_info()
        elif self.current_page == 3:
            self.current_lines = self.get_lora_info()
        elif self.current_page == 4:
            self.current_lines = self.get_gpio_info()
        elif self.current_page == 5:
            self.current_lines = self.get_config_info()
        else:
            self.current_lines = ["Unknown page"]

        # Constrain scroll offset
        max_scroll = max(0, len(self.current_lines) - self.max_visible_lines)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        # Draw visible lines based on scroll offset
        y_pos = 18
        visible_lines = self.current_lines[self.scroll_offset:self.scroll_offset + self.max_visible_lines]

        for line in visible_lines:
            label = lvgl.label(self.badge.display.screen)
            label.set_text(line)
            label.set_style_text_color(lvgl.color_hex(0xFFFFFF), 0)  # White text
            label.set_style_text_font(lvgl.font_montserrat_12, 0)
            label.set_pos(5, y_pos)
            self.info_labels.append(label)
            y_pos += 13

        # Add scroll indicator if there are more lines
        if len(self.current_lines) > self.max_visible_lines:
            self.scroll_indicator = lvgl.label(self.badge.display.screen)
            scroll_text = f"{self.scroll_offset + 1}-{min(self.scroll_offset + self.max_visible_lines, len(self.current_lines))}/{len(self.current_lines)}"
            self.scroll_indicator.set_text(scroll_text)
            self.scroll_indicator.set_style_text_color(styles.hackaday_yellow, 0)
            self.scroll_indicator.set_style_text_font(lvgl.font_montserrat_12, 0)
            self.scroll_indicator.set_pos(380, 2)

    def get_system_info(self):
        """Get system information."""
        lines = []

        # CPU frequency
        freq_hz = machine.freq()
        lines.append(f"CPU Freq: {freq_hz / 1_000_000:.0f} MHz")

        # ESP32 chip info
        if HAS_ESP32:
            try:
                temp = esp32.raw_temperature()
                lines.append(f"Chip Temp: {temp}F (raw)")
            except:
                pass

            try:
                hall = esp32.hall_sensor()
                lines.append(f"Hall Sensor: {hall}")
            except:
                pass

        # Flash size
        try:
            import flashbdev
            flash_size = flashbdev.bdev.size
            lines.append(f"Flash: {flash_size / 1024 / 1024:.1f} MB")
        except:
            pass

        # Python version
        lines.append(f"Python: {sys.version.split()[0]}")
        lines.append(f"Platform: {sys.platform}")

        # Uptime (approximate from gc stats)
        try:
            import time
            uptime = time.ticks_ms() // 1000
            mins = uptime // 60
            secs = uptime % 60
            lines.append(f"Uptime: {mins}m {secs}s")
        except:
            pass

        return lines

    def get_memory_info(self):
        """Get memory information."""
        lines = []

        # Force garbage collection first
        gc.collect()

        # Memory stats
        free = gc.mem_free()
        alloc = gc.mem_alloc()
        total = free + alloc

        lines.append(f"RAM Total: {total / 1024:.1f} KB")
        lines.append(f"RAM Used:  {alloc / 1024:.1f} KB")
        lines.append(f"RAM Free:  {free / 1024:.1f} KB")
        lines.append(f"RAM Use %: {alloc * 100 / total:.1f}%")

        # GC threshold
        try:
            threshold = gc.threshold()
            lines.append(f"GC Threshold: {threshold}")
        except:
            pass

        # Heap info (if available)
        try:
            import micropython
            # Get stack and heap info
            lines.append("")
            lines.append("Memory Stats:")
            # This will crash but let's try to get some info
        except:
            pass

        return lines

    def get_display_info(self):
        """Get display information."""
        lines = []

        lines.append("Display: NV3007 TFT")
        lines.append("Resolution: 428x142")
        lines.append("Rotation: 270deg")
        lines.append("Color: 16-bit RGB565")

        # Backlight duty cycle
        try:
            duty = self.badge.display.backlight.duty()
            lines.append(f"Backlight: {duty}/1023")
        except:
            pass

        # LVGL version
        try:
            lines.append(f"LVGL: v{lvgl.version_major()}.{lvgl.version_minor()}.{lvgl.version_patch()}")
        except:
            lines.append("LVGL: (version N/A)")

        return lines

    def get_lora_info(self):
        """Get LoRa radio information."""
        lines = []

        try:
            lora = self.badge.lora

            lines.append("Radio: SX1262")
            lines.append(f"Freq: {lora.frequency} MHz")
            lines.append(f"Freq Slot: {lora.freq_slot}")
            lines.append(f"TX Power: {lora.tx_power} dBm")
            lines.append(f"Power Level: {lora.power_level}")
            lines.append(f"Bandwidth: {lora.bandwidth} kHz")
            lines.append(f"Spread Factor: {lora.spreading_factor}")
            lines.append(f"Coding Rate: 4/{lora.coding_rate}")
            lines.append(f"Preamble: {lora.preamble_length}")
            lines.append(f"Sync Word: 0x{lora.sync_word:02X}")
            lines.append(f"CRC: {lora.crc}")
            lines.append(f"Last SNR: {lora.last_snr:.1f} dB")
            lines.append(f"Last RSSI: {lora.last_rssi:.1f} dBm")
        except Exception as e:
            lines.append(f"Error: {str(e)[:30]}")

        return lines

    def get_gpio_info(self):
        """Get GPIO and I2C information."""
        lines = []

        # I2C info
        try:
            lines.append("SAO I2C (bus 0):")
            devices = self.badge.sao_i2c.scan()
            if devices:
                for addr in devices:
                    lines.append(f"  Device: 0x{addr:02X}")
            else:
                lines.append("  No devices found")
        except Exception as e:
            lines.append(f"SAO I2C Error: {str(e)[:20]}")

        lines.append("")

        # Keyboard I2C
        try:
            lines.append("Keyboard: I2C bus 1")
            lines.append("Display: I2C bus 2")
        except:
            pass

        # Pin info
        lines.append("")
        lines.append("Pins:")
        lines.append("  Debug LED: GPIO 1")
        lines.append("  LCD BL: GPIO 2")
        lines.append("  SAO: GPIO 4-7")

        return lines

    def get_config_info(self):
        """Get badge configuration."""
        lines = []

        try:
            config = self.badge.config

            # Get config values
            alias = config.get("alias")
            if alias:
                lines.append(f"Alias: {alias[:20]}")

            nametag = config.get("nametag")
            if nametag:
                lines.append(f"Name: {nametag[:20]}")

            tx_power = config.get("radio_tx_power")
            if tx_power:
                lines.append(f"Radio TX: {tx_power} dBm")

            ttl = config.get("chat_ttl")
            if ttl:
                lines.append(f"Chat TTL: {ttl}")

            cooldown = config.get("send_cooldown_ms")
            if cooldown:
                lines.append(f"TX Cooldown: {cooldown} ms")

            show_img = config.get("nametag_show_image")
            if show_img:
                lines.append(f"Show Image: {show_img}")

            img_path = config.get("nametag_image")
            if img_path:
                lines.append(f"Image: {img_path[:25]}")
        except Exception as e:
            lines.append(f"Error: {str(e)[:30]}")

        return lines

    def run_foreground(self):
        """Main loop - handle navigation."""
        # Check for scrolling with arrow keys
        from hardware.keyboard import Keyboard
        key = self.badge.keyboard.read_key()

        if key == Keyboard.UP:
            # Scroll up
            if self.scroll_offset > 0:
                self.scroll_offset -= 1
                self.draw_page()
            return

        if key == Keyboard.DOWN:
            # Scroll down
            max_scroll = max(0, len(self.current_lines) - self.max_visible_lines)
            if self.scroll_offset < max_scroll:
                self.scroll_offset += 1
                self.draw_page()
            return

        # Check for page navigation
        if self.badge.keyboard.f1():
            # Previous page
            self.current_page = (self.current_page - 1) % len(self.pages)
            self.scroll_offset = 0  # Reset scroll when changing pages
            self.update_counter = 0  # Force immediate redraw
            self.draw_page()
            return

        if self.badge.keyboard.f2():
            # Next page
            self.current_page = (self.current_page + 1) % len(self.pages)
            self.scroll_offset = 0  # Reset scroll when changing pages
            self.update_counter = 0  # Force immediate redraw
            self.draw_page()
            return

        # Check for exit
        if self.badge.keyboard.f5():
            self.switch_to_background()
            return

        # Only update periodically (not every iteration)
        self.update_counter += 1
        if self.update_counter >= self.update_interval:
            self.update_counter = 0
            self.draw_page()

    def switch_to_background(self):
        """Clean up when going to background."""
        super().switch_to_background()

        # Clear all labels
        for label in self.info_labels:
            try:
                label.delete()
            except:
                pass
        self.info_labels = []

        # Delete title
        if self.title_label:
            try:
                self.title_label.delete()
            except:
                pass
            self.title_label = None

        # Delete scroll indicator
        if self.scroll_indicator:
            try:
                self.scroll_indicator.delete()
            except:
                pass
            self.scroll_indicator = None

        # Clear display
        try:
            self.badge.display.clear()
        except:
            pass


# Export the app class
App = HardwareMonitor
