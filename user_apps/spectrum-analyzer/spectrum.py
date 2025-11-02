"""Spectrum Analyzer app - displays RF spectrum activity."""

import lvgl
import gc
from apps.base_app import BaseApp
from ui import styles
from net._sx126x import SX126X_CMD_GET_RSSI_INST


class SpectrumAnalyzer(BaseApp):
    """RF spectrum analyzer using the SX1262 LoRa radio."""

    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.foreground_sleep_ms = 1  # Minimal sleep - each channel scan takes ~4ms anyway

        # Spectrum settings for 915 MHz ISM band
        self.start_freq = 902.0  # MHz
        self.end_freq = 928.0    # MHz
        self.num_channels = 52   # Number of frequency steps (0.5 MHz apart)
        self.channel_width = (self.end_freq - self.start_freq) / self.num_channels

        # Display settings
        self.graph_x_offset = 35  # Left margin for dBm scale
        self.bar_width = 7  # Width of each frequency bar (52 × 7 = 364 pixels)
        self.graph_height = 80  # Height of the spectrum graph
        self.graph_y_offset = 30  # Y position where graph starts

        # RSSI history for each channel (for averaging/smoothing)
        self.rssi_history = [[-120.0] * 3 for _ in range(self.num_channels)]
        self.current_channel = 0

        # Adaptive baseline tracking
        self.baseline_rssi = -120.0  # Noise floor
        self.max_rssi = -40.0  # Strongest signal seen
        self.baseline_samples = 0
        self.baseline_calibrated = False

        # Peak tracking
        self.peak_rssi = -120.0
        self.peak_channel = 0

        # LVGL objects
        self.title_label = None
        self.status_label = None
        self.info_label = None
        self.freq_labels = []
        self.scale_labels = []
        self.grid_lines = []
        self.spectrum_bars = []

        # Radio state
        self.original_freq = None
        self.scanning_active = False

        # Display mode (spectrum or waterfall)
        self.display_mode = "spectrum"  # "spectrum" or "waterfall"

        # Waterfall data storage (rows x channels)
        self.waterfall_rows = 40  # Number of scans to store (each scan = 2 pixels tall)
        self.waterfall_data = []  # List of lists: each inner list is one scan (52 RSSI values)
        self.waterfall_pixels = []  # LVGL objects for waterfall display (fixed positions)
        self.waterfall_row_height = 2  # Pixels per waterfall row
        self.waterfall_next_row = 0  # Circular buffer index: which row to overwrite next

    def switch_to_foreground(self):
        """Set up the spectrum analyzer screen."""
        super().switch_to_foreground()
        self.badge.display.clear()
        self.badge.display.screen.set_style_bg_color(lvgl.color_hex(0x000000), 0)

        # Set up function key labels
        self.badge.display.f1("Hold", styles.hackaday_yellow)
        self.badge.display.f3("Recal", styles.hackaday_yellow)
        self.badge.display.f4("Mode", styles.hackaday_yellow)
        self.badge.display.f5("Exit", styles.hackaday_yellow)

        # Create title label
        self.title_label = lvgl.label(self.badge.display.screen)
        self.update_title()
        self.title_label.set_style_text_color(styles.hackaday_yellow, 0)
        self.title_label.set_style_text_font(lvgl.font_montserrat_12, 0)
        self.title_label.set_pos(10, 2)

        # Create status label
        self.status_label = lvgl.label(self.badge.display.screen)
        self.status_label.set_text("Scanning...")
        self.status_label.set_style_text_color(lvgl.color_hex(0x00FF00), 0)
        self.status_label.set_style_text_font(lvgl.font_montserrat_12, 0)
        self.status_label.set_pos(360, 2)

        # Create info label (shows peak and current info)
        self.info_label = lvgl.label(self.badge.display.screen)
        self.info_label.set_text("Peak: --- dBm")
        self.info_label.set_style_text_color(lvgl.color_hex(0xFFFFFF), 0)
        self.info_label.set_style_text_font(lvgl.font_montserrat_12, 0)
        self.info_label.set_pos(10, 16)

        # Draw frequency labels at bottom
        self.draw_freq_labels()

        # Create spectrum bars
        for i in range(self.num_channels):
            bar = lvgl.obj(self.badge.display.screen)
            bar.set_size(self.bar_width - 1, 1)  # Start with minimal height
            bar.set_pos(self.graph_x_offset + i * self.bar_width, self.graph_y_offset + self.graph_height)
            bar.set_style_bg_color(lvgl.color_hex(0x00FF00), 0)
            bar.set_style_border_width(0, 0)
            self.spectrum_bars.append(bar)

        # Save original radio frequency
        try:
            self.original_freq = self.badge.lora.frequency
            self.scanning_active = True
        except:
            pass

    def update_title(self):
        """Update title based on current display mode."""
        if self.title_label:
            if self.display_mode == "spectrum":
                self.title_label.set_text("Spectrum - 902-928 MHz")
            else:
                self.title_label.set_text("Waterfall - 902-928 MHz")

    def draw_freq_labels(self):
        """Draw frequency labels and grid lines."""
        # Draw vertical grid lines and labels every 5 MHz
        # 902, 905, 910, 915, 920, 925 MHz
        grid_freqs = [902, 905, 910, 915, 920, 925, 928]

        for freq in grid_freqs:
            # Calculate channel position for this frequency
            ch = int((freq - self.start_freq) / self.channel_width)
            if ch < 0 or ch >= self.num_channels:
                continue

            x_pos = self.graph_x_offset + ch * self.bar_width

            # Draw vertical grid line (subtle, behind the bars)
            line = lvgl.obj(self.badge.display.screen)
            line.set_size(1, self.graph_height)
            line.set_pos(x_pos, self.graph_y_offset)
            line.set_style_bg_color(lvgl.color_hex(0x333333), 0)  # Dark gray
            line.set_style_border_width(0, 0)
            self.grid_lines.append(line)

            # Draw frequency label at bottom
            label = lvgl.label(self.badge.display.screen)
            label.set_text(f"{freq}")
            label.set_style_text_color(lvgl.color_hex(0xAAAAAA), 0)  # Light gray
            label.set_style_text_font(lvgl.font_montserrat_12, 0)
            label.set_pos(x_pos - 10, 113)  # Position below graph with margin
            self.freq_labels.append(label)

    def draw_scale_labels(self):
        """Draw dBm or time scale on the left side."""
        # Clear old scale labels
        for label in self.scale_labels:
            try:
                label.delete()
            except:
                pass
        self.scale_labels = []

        if self.display_mode == "spectrum":
            # Draw dBm scale for spectrum mode
            scale_values = [
                (f"{self.max_rssi:.0f}", self.graph_y_offset),  # Top
                (f"{(self.baseline_rssi + self.max_rssi) / 2:.0f}", self.graph_y_offset + self.graph_height // 2),  # Middle
                (f"{self.baseline_rssi:.0f}", self.graph_y_offset + self.graph_height - 10),  # Bottom
            ]
        else:
            # Draw time scale for waterfall mode
            # Approximate scan rate: ~1-2 scans/sec, 40 rows total
            total_time = self.waterfall_rows  # Rough seconds estimate
            scale_values = [
                ("Now", self.graph_y_offset + self.graph_height - 10),  # Bottom (newest)
                (f"{total_time//2}s", self.graph_y_offset + self.graph_height // 2),  # Middle
                (f"{total_time}s", self.graph_y_offset),  # Top (oldest)
            ]

        for text, y_pos in scale_values:
            label = lvgl.label(self.badge.display.screen)
            label.set_text(text)
            label.set_style_text_color(lvgl.color_hex(0x888888), 0)
            label.set_style_text_font(lvgl.font_montserrat_12, 0)
            label.set_pos(2, y_pos)
            self.scale_labels.append(label)

    def get_color_for_rssi(self, rssi):
        """Get color for RSSI value based on adaptive baseline."""
        if not self.baseline_calibrated:
            return 0x0088FF  # Blue during calibration

        dynamic_range = max(20, self.max_rssi - self.baseline_rssi)
        rssi_above_baseline = rssi - self.baseline_rssi

        if rssi_above_baseline > dynamic_range * 0.8:
            return 0xFF0000  # Red - very strong (top 20%)
        elif rssi_above_baseline > dynamic_range * 0.6:
            return 0xFF8000  # Orange - strong (60-80%)
        elif rssi_above_baseline > dynamic_range * 0.4:
            return 0xFFFF00  # Yellow - moderate (40-60%)
        elif rssi_above_baseline > dynamic_range * 0.2:
            return 0x00FF00  # Green - weak signal (20-40%)
        else:
            return 0x0088FF  # Blue - near baseline (bottom 20%)

    def add_waterfall_row(self, scan_data):
        """Add a new row to waterfall - circular buffer, pixels stay at fixed positions."""
        import time
        start_time = time.ticks_ms()

        # Don't draw if we haven't started collecting data yet
        if len(self.waterfall_data) == 0:
            return

        print(f"[WATERFALL] Adding row, current pixel rows: {len(self.waterfall_pixels)}, next_row: {self.waterfall_next_row}")

        # If not at full capacity yet, create new row at next position
        if len(self.waterfall_pixels) < self.waterfall_rows:
            row_idx = len(self.waterfall_pixels)
            y_pos = self.graph_y_offset + (row_idx * self.waterfall_row_height)
            print(f"[WATERFALL] Creating new row {row_idx} at y={y_pos}")

            row_pixels = []
            for ch_idx, rssi in enumerate(scan_data):
                x_pos = self.graph_x_offset + ch_idx * self.bar_width
                color = self.get_color_for_rssi(rssi)

                pixel = lvgl.obj(self.badge.display.screen)
                pixel.set_size(self.bar_width - 1, self.waterfall_row_height)
                pixel.set_pos(x_pos, y_pos)
                pixel.set_style_bg_color(lvgl.color_hex(color), 0)
                pixel.set_style_border_width(0, 0)
                row_pixels.append(pixel)

            self.waterfall_pixels.append(row_pixels)
            draw_time = time.ticks_diff(time.ticks_ms(), start_time)
            print(f"[WATERFALL] Create took {draw_time}ms, rows now: {len(self.waterfall_pixels)}")

        else:
            # At full capacity - reuse row at waterfall_next_row index (circular buffer)
            # This row stays at its fixed Y position, we just update the colors
            row = self.waterfall_pixels[self.waterfall_next_row]
            print(f"[WATERFALL] Reusing row {self.waterfall_next_row} (pixels stay in place)")

            # Update colors for all pixels in this row
            for ch_idx, pixel in enumerate(row):
                try:
                    color = self.get_color_for_rssi(scan_data[ch_idx])
                    pixel.set_style_bg_color(lvgl.color_hex(color), 0)
                except:
                    pass

            # Advance to next row in circular buffer
            self.waterfall_next_row = (self.waterfall_next_row + 1) % self.waterfall_rows

            update_time = time.ticks_diff(time.ticks_ms(), start_time)
            print(f"[WATERFALL] Update took {update_time}ms, next_row now: {self.waterfall_next_row}")

        # Check buttons after updating
        if self.check_buttons():
            return

    def toggle_display_mode(self):
        """Toggle between spectrum and waterfall display modes."""
        if self.display_mode == "spectrum":
            self.display_mode = "waterfall"
            # Hide spectrum bars instantly
            for bar in self.spectrum_bars:
                try:
                    bar.add_flag(lvgl.obj.FLAG.HIDDEN)
                except:
                    pass

            # Draw existing waterfall data if we have any (draw all rows we have)
            if len(self.waterfall_data) > 0:
                # Draw all cached rows to show full history
                for row_idx, scan_data in enumerate(self.waterfall_data):
                    y_pos = self.graph_y_offset + row_idx * self.waterfall_row_height
                    row_pixels = []
                    for ch_idx, rssi in enumerate(scan_data):
                        x_pos = self.graph_x_offset + ch_idx * self.bar_width
                        color = self.get_color_for_rssi(rssi)
                        pixel = lvgl.obj(self.badge.display.screen)
                        pixel.set_size(self.bar_width - 1, self.waterfall_row_height)
                        pixel.set_pos(x_pos, y_pos)
                        pixel.set_style_bg_color(lvgl.color_hex(color), 0)
                        pixel.set_style_border_width(0, 0)
                        row_pixels.append(pixel)
                    self.waterfall_pixels.append(row_pixels)

                # Set next_row to start of buffer if full, otherwise next available position
                if len(self.waterfall_pixels) >= self.waterfall_rows:
                    self.waterfall_next_row = 0  # Circular buffer will overwrite from start
                else:
                    self.waterfall_next_row = len(self.waterfall_pixels)
        else:
            self.display_mode = "spectrum"

            # Hide waterfall pixels instantly
            for row in self.waterfall_pixels:
                for pixel in row:
                    try:
                        pixel.add_flag(lvgl.obj.FLAG.HIDDEN)
                    except:
                        pass

            # Delete old spectrum bars and recreate them with current data
            for bar in self.spectrum_bars:
                try:
                    bar.delete()
                except:
                    pass
            self.spectrum_bars = []

            # Recreate all bars with current RSSI data
            for idx in range(self.num_channels):
                try:
                    # Calculate bar properties from current RSSI
                    avg_rssi = sum(self.rssi_history[idx]) / len(self.rssi_history[idx])
                    dynamic_range = max(20, self.max_rssi - self.baseline_rssi)
                    rssi_clamped = max(self.baseline_rssi, min(self.max_rssi, avg_rssi))
                    bar_height = int((rssi_clamped - self.baseline_rssi) * self.graph_height / dynamic_range)
                    bar_height = max(2, min(self.graph_height, bar_height))
                    color = self.get_color_for_rssi(avg_rssi)

                    # Create new bar
                    bar = lvgl.obj(self.badge.display.screen)
                    bar.set_size(self.bar_width - 1, bar_height)
                    bar.set_pos(self.graph_x_offset + idx * self.bar_width,
                               self.graph_y_offset + self.graph_height - bar_height)
                    bar.set_style_bg_color(lvgl.color_hex(color), 0)
                    bar.set_style_border_width(0, 0)
                    self.spectrum_bars.append(bar)
                except:
                    pass

        # Update title and scale labels
        self.update_title()
        self.draw_scale_labels()

    def recalibrate(self):
        """Reset calibration to start fresh."""
        self.baseline_rssi = -120.0
        self.max_rssi = -40.0
        self.baseline_samples = 0
        self.baseline_calibrated = False
        self.peak_rssi = -120.0
        self.peak_channel = 0
        # Clear RSSI history
        self.rssi_history = [[-120.0] * 3 for _ in range(self.num_channels)]
        # Clear scale labels (will be redrawn after recalibration)
        for label in self.scale_labels:
            try:
                label.delete()
            except:
                pass
        self.scale_labels = []
        # Clear waterfall data
        self.waterfall_data = []
        # Clear waterfall pixels
        for row in self.waterfall_pixels:
            for pixel in row:
                try:
                    pixel.delete()
                except:
                    pass
        self.waterfall_pixels = []
        self.waterfall_next_row = 0  # Reset circular buffer index

    def get_instantaneous_rssi(self):
        """Get instantaneous RSSI from the radio."""
        try:
            # Call the low-level command to get instantaneous RSSI
            rssi_buf = bytearray(1)
            rssi_buf_mv = memoryview(rssi_buf)

            # Send GET_RSSI_INST command
            self.badge.lora.radio.SPIreadCommand([SX126X_CMD_GET_RSSI_INST], 1, rssi_buf_mv, 1)

            # Convert to dBm (same formula as packet RSSI)
            rssi_raw = rssi_buf[0]
            rssi_dbm = -1.0 * rssi_raw / 2.0

            return rssi_dbm
        except Exception as e:
            # If we can't get RSSI, return a very low value
            return -120.0

    def scan_spectrum(self):
        """Scan one channel and update the display."""
        if not self.scanning_active:
            return

        try:
            import time

            # Calculate frequency for current channel
            freq = self.start_freq + (self.current_channel * self.channel_width)

            # Set radio to this frequency and let it settle
            self.badge.lora.radio.setFrequency(freq)
            self.badge.lora.radio.standby()
            time.sleep_ms(3)  # Let frequency settle (reduced from 5ms)

            # Put radio in RX mode briefly to measure RSSI
            self.badge.lora.radio.setRx(0)  # Continuous RX
            time.sleep_ms(1)  # Brief delay to start receiving (reduced from 2ms)

            # Get instantaneous RSSI
            rssi = self.get_instantaneous_rssi()

            # Return to standby
            self.badge.lora.radio.standby()

            # Add to history and average
            self.rssi_history[self.current_channel].pop(0)
            self.rssi_history[self.current_channel].append(rssi)
            avg_rssi = sum(self.rssi_history[self.current_channel]) / len(self.rssi_history[self.current_channel])

            # Auto-calibrate baseline during first few scans
            if self.baseline_samples < 200:  # Calibrate over ~4 full scans
                if self.baseline_samples == 0:
                    self.baseline_rssi = avg_rssi
                    self.max_rssi = avg_rssi
                else:
                    # Track minimum (noise floor) and maximum
                    self.baseline_rssi = min(self.baseline_rssi, avg_rssi)
                    self.max_rssi = max(self.max_rssi, avg_rssi)
                self.baseline_samples += 1

                if self.baseline_samples == 200:
                    self.baseline_calibrated = True
                    # Add some margin to the range
                    range_db = self.max_rssi - self.baseline_rssi
                    if range_db < 20:  # Ensure minimum 20dB dynamic range
                        self.max_rssi = self.baseline_rssi + 20
            else:
                # Update max if we see something stronger
                self.max_rssi = max(self.max_rssi, avg_rssi)

            # Scale relative to adaptive baseline
            # Map from baseline to max_rssi across the full height
            dynamic_range = max(20, self.max_rssi - self.baseline_rssi)  # At least 20dB range
            rssi_clamped = max(self.baseline_rssi, min(self.max_rssi, avg_rssi))
            bar_height = int((rssi_clamped - self.baseline_rssi) * self.graph_height / dynamic_range)
            bar_height = max(2, min(self.graph_height, bar_height))

            # Get color for this RSSI value
            color = self.get_color_for_rssi(avg_rssi)

            # Update bar
            bar = self.spectrum_bars[self.current_channel]
            try:
                bar.set_size(self.bar_width - 1, bar_height)
                bar.set_pos(self.graph_x_offset + self.current_channel * self.bar_width,
                           self.graph_y_offset + self.graph_height - bar_height)
                bar.set_style_bg_color(lvgl.color_hex(color), 0)
            except:
                pass

            # Track peak RSSI
            if avg_rssi > self.peak_rssi:
                self.peak_rssi = avg_rssi
                self.peak_channel = self.current_channel

            # Update info label every full scan (when returning to channel 0)
            if self.current_channel == 0 and self.info_label:
                try:
                    if not self.baseline_calibrated:
                        # Show calibration progress
                        progress = int(self.baseline_samples * 100 / 200)
                        self.info_label.set_text(f"Calibrating... {progress}%")
                    else:
                        # Show peak and baseline info
                        peak_freq = self.start_freq + (self.peak_channel * self.channel_width)
                        self.info_label.set_text(f"Peak:{self.peak_rssi:.0f}dBm @ {peak_freq:.0f}MHz | Base:{self.baseline_rssi:.0f}dBm")
                        # Update scale labels after calibration
                        self.draw_scale_labels()
                except:
                    pass

            # Move to next channel
            self.current_channel = (self.current_channel + 1) % self.num_channels

            # Check buttons every 10 channels for responsiveness
            if self.current_channel % 10 == 0:
                if self.check_buttons():
                    return

            # If we just completed a full scan (wrapped to 0), update waterfall data
            if self.current_channel == 0:
                import time
                scan_complete_time = time.ticks_ms()
                print(f"\n[SCAN] Complete scan at {scan_complete_time}, mode: {self.display_mode}")

                # Get average RSSI for each channel for this scan
                scan_rssi = [sum(self.rssi_history[i]) / len(self.rssi_history[i])
                            for i in range(self.num_channels)]

                # Always add to waterfall data (collected in both modes)
                self.waterfall_data.append(scan_rssi)

                # Limit to waterfall_rows
                if len(self.waterfall_data) > self.waterfall_rows:
                    self.waterfall_data.pop(0)

                print(f"[SCAN] Waterfall data: {len(self.waterfall_data)} scans stored")

                # Check buttons before waterfall drawing (it can be slow)
                if self.check_buttons():
                    return

                # Only draw new row if actively in waterfall mode
                if self.display_mode == "waterfall":
                    print(f"[SCAN] Drawing waterfall row...")
                    self.add_waterfall_row(scan_rssi)

                # Check buttons after waterfall drawing
                if self.check_buttons():
                    return

        except Exception as e:
            # If scanning fails, just continue
            pass

    def check_buttons(self):
        """Check for button presses and handle them. Returns True if button was handled."""
        # Check for hold (pause scanning)
        if self.badge.keyboard.f1():
            self.scanning_active = not self.scanning_active
            if self.scanning_active:
                try:
                    self.status_label.set_text("Scanning...")
                    self.status_label.set_style_text_color(lvgl.color_hex(0x00FF00), 0)
                except:
                    pass
            else:
                try:
                    self.status_label.set_text("Held")
                    self.status_label.set_style_text_color(lvgl.color_hex(0xFFFF00), 0)
                except:
                    pass
            return True

        # Check for recalibrate
        if self.badge.keyboard.f3():
            self.recalibrate()
            return True

        # Check for mode toggle
        if self.badge.keyboard.f4():
            self.toggle_display_mode()
            return True

        # Check for exit
        if self.badge.keyboard.f5():
            self.switch_to_background()
            return True

        return False

    def run_foreground(self):
        """Main loop - scan spectrum."""
        # Check for button presses
        if self.check_buttons():
            return

        # Scan next channel
        if self.scanning_active:
            self.scan_spectrum()

    def switch_to_background(self):
        """Clean up when going to background."""
        super().switch_to_background()

        # Stop scanning
        self.scanning_active = False

        # Restore original radio frequency
        if self.original_freq:
            try:
                self.badge.lora.radio.setFrequency(self.original_freq)
                self.badge.lora.radio.standby()
            except:
                pass

        # Clear all bars
        for bar in self.spectrum_bars:
            try:
                bar.delete()
            except:
                pass
        self.spectrum_bars = []

        # Hide waterfall pixels instantly, then delete
        for row in self.waterfall_pixels:
            for pixel in row:
                try:
                    pixel.add_flag(lvgl.obj.FLAG.HIDDEN)
                except:
                    pass
        # Now delete them (hidden, so instant from user perspective)
        for row in self.waterfall_pixels:
            for pixel in row:
                try:
                    pixel.delete()
                except:
                    pass
        self.waterfall_pixels = []
        self.waterfall_next_row = 0  # Reset circular buffer index

        # Clear grid lines
        for line in self.grid_lines:
            try:
                line.delete()
            except:
                pass
        self.grid_lines = []

        # Clear labels
        for label in self.freq_labels:
            try:
                label.delete()
            except:
                pass
        self.freq_labels = []

        for label in self.scale_labels:
            try:
                label.delete()
            except:
                pass
        self.scale_labels = []

        if self.title_label:
            try:
                self.title_label.delete()
            except:
                pass
            self.title_label = None

        if self.status_label:
            try:
                self.status_label.delete()
            except:
                pass
            self.status_label = None

        if self.info_label:
            try:
                self.info_label.delete()
            except:
                pass
            self.info_label = None

        # Clear display
        try:
            self.badge.display.clear()
        except:
            pass


# Export the app class
App = SpectrumAnalyzer
