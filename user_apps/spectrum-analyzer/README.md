# Spectrum Analyzer

Real-time RF spectrum analyzer and waterfall display for the 902-928 MHz ISM band using the SX1262 LoRa radio.

## Controls

- **F1**: Hold/Resume scanning
- **F3**: Recalibrate baseline and dynamic range
- **F4**: Toggle between Spectrum and Waterfall modes
- **F5**: Exit to menu

## Display Modes

### Spectrum Mode
Shows instantaneous signal strength across all frequencies as vertical bars. Color indicates relative signal strength from blue (noise floor) to red (strongest signals). Great for finding active channels and identifying interference.

### Waterfall Mode
Displays signal activity over time with frequency on X-axis and time on Y-axis. Newest data appears at the bottom, older data scrolls upward. Ideal for visualizing intermittent signals, frequency hopping patterns, and temporal RF activity.

## Technical Details

- **Frequency Range**: 902-928 MHz (US ISM band)
- **Channels**: 52 frequencies, 0.5 MHz spacing
- **Scan Rate**: ~1-2 complete scans per second
- **RSSI Method**: Instantaneous RSSI via SX126X_CMD_GET_RSSI_INST
- **Calibration**: First 200 samples (~4 scans) learn noise floor and dynamic range
- **Color Coding**: Adaptive percentile-based (0-20% blue, 20-40% green, 40-60% yellow, 60-80% orange, 80-100% red)

### Radio Settling
The radio requires time to settle after frequency changes:
- 5ms delay after `setFrequency()`
- 2ms delay after entering RX mode

This ensures accurate RSSI measurements. Without proper settling, readings can be unreliable.

### Adaptive Baseline
The spectrum analyzer automatically learns the RF environment during initial calibration:
- **Baseline**: Minimum RSSI observed (noise floor)
- **Max**: Maximum RSSI observed (strongest signal)
- **Dynamic Range**: Automatically maintains at least 20 dB range

All colors and scales adjust relative to these learned values, making the display useful in both quiet and busy RF environments.

### Signal Detection
The instantaneous RSSI measurement detects any RF energy in the 902-928 MHz ISM band, regardless of modulation type. You'll see WiFi, Zigbee, LoRa, and other ISM band users. Typical RSSI values are:
- **Noise floor**: -110 to -120 dBm (shown in blue)
- **Nearby transmitters**: -40 to -80 dBm (shown in yellow/orange/red)
- **Distant signals**: -90 to -110 dBm (shown in green/yellow)

Channels that remain blue are at or near the noise floor with no detectable signal activity, which is normal for unused frequencies.

### Calibration
At startup, the analyzer displays "Calibrating..." while it learns the noise floor and signal range of your RF environment. This initial calibration takes about 4 full scans (~2-4 seconds). If the RF environment changes significantly (e.g., moving locations, strong transmitter turns on/off), use F3 to recalibrate for improved display sensitivity.

### Radio Usage
The analyzer saves and restores the original radio frequency when entering/exiting. However, the radio cannot send/receive LoRa packets while spectrum scanning is active.

## Known Issues

- **Waterfall Performance**: When the waterfall display fills the screen, the refresh rate becomes slow and may appear buggy. This is due to the overhead of managing the circular buffer display on the hardware.
- **Mode Switching**: Toggling between Spectrum and Waterfall modes or exiting the app can sometimes be unresponsive or cause the app to hang. If this occurs, you may need to restart the badge. For best results, use F1 (Hold) to pause scanning before switching modes or exiting.
