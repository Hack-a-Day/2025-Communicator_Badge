"""Radio commands: direct LoRa parameter controls.

Adds a hardware-focused surface for frequency and modulation settings.
"""


class RadioCommands:
    """Registers the 'radio' command group."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge
        shell.register_group(
            "radio",
            {
                "info": (self._cmd_info, "Current radio config"),
                "set_freq": (self._cmd_set_freq, "Set frequency MHz: radio set_freq <mhz>"),
                "set_power": (self._cmd_set_power, "Set TX power dBm: radio set_power <-9..22>"),
                "set_sf": (self._cmd_set_sf, "Set spreading factor: radio set_sf <7..12>"),
                "set_bw": (self._cmd_set_bw, "Set bandwidth kHz: radio set_bw <7.8..500>"),
                "freq_slot": (self._cmd_freq_slot, "Set frequency slot: radio freq_slot <1..52>"),
                "rssi": (self._cmd_rssi, "Read current RSSI"),
            },
            "Low-level SX1262 radio controls",
        )

    def _write_info(self):
        lora = self.badge.lora
        w = self.shell._write
        w("Radio (SX1262)")
        w("  Freq Slot:         %s" % getattr(lora, "freq_slot", "?"))
        w("  Frequency:         %.3f MHz" % float(getattr(lora, "frequency", 0.0)))
        w("  Bandwidth:         %.1f kHz" % float(getattr(lora, "bandwidth", 0.0)))
        w("  Spreading Factor:  %d" % int(getattr(lora, "spreading_factor", 0)))
        w("  TX Power:          %d dBm" % int(getattr(lora, "tx_power", 0)))
        w("  Sync Word:         0x%02x" % int(getattr(lora, "sync_word", 0)))

    def _cmd_info(self, args):
        self._write_info()

    def _cmd_set_freq(self, args):
        w = self.shell._write
        if not args:
            w("Usage: radio set_freq <mhz>")
            return

        try:
            freq = float(args[0])
        except ValueError:
            w("Error: invalid frequency")
            return

        if freq < 150.0 or freq > 960.0:
            w("Error: frequency out of range (150-960 MHz)")
            return

        lora = self.badge.lora
        try:
            if getattr(lora, "radio", None) and hasattr(lora.radio, "setFrequency"):
                lora.radio.setFrequency(freq)
            lora.frequency = freq
            w("Frequency set to %.3f MHz" % freq)
        except Exception as exc:
            w("Error: " + str(exc))

    def _cmd_set_power(self, args):
        w = self.shell._write
        if not args:
            w("Usage: radio set_power <-9..22>")
            return

        try:
            power = int(args[0])
        except ValueError:
            w("Error: invalid power")
            return

        if power < -9 or power > 22:
            w("Error: power out of range (-9..22 dBm)")
            return

        lora = self.badge.lora
        try:
            if getattr(lora, "radio", None) and hasattr(lora.radio, "setOutputPower"):
                lora.radio.setOutputPower(power)
            lora.tx_power = power
            w("TX power set to %d dBm" % power)
        except Exception as exc:
            w("Error: " + str(exc))

    def _cmd_set_sf(self, args):
        w = self.shell._write
        if not args:
            w("Usage: radio set_sf <7..12>")
            return

        try:
            sf = int(args[0])
        except ValueError:
            w("Error: invalid spreading factor")
            return

        if sf < 7 or sf > 12:
            w("Error: spreading factor out of range (7..12)")
            return

        lora = self.badge.lora
        try:
            if getattr(lora, "radio", None) and hasattr(lora.radio, "setSpreadingFactor"):
                lora.radio.setSpreadingFactor(sf)
            lora.spreading_factor = sf
            w("Spreading factor set to %d" % sf)
        except Exception as exc:
            w("Error: " + str(exc))

    def _cmd_set_bw(self, args):
        w = self.shell._write
        if not args:
            w("Usage: radio set_bw <khz>")
            return

        try:
            bw = float(args[0])
        except ValueError:
            w("Error: invalid bandwidth")
            return

        if bw <= 0 or bw > 500:
            w("Error: bandwidth out of range (0..500 kHz)")
            return

        lora = self.badge.lora
        try:
            if getattr(lora, "radio", None) and hasattr(lora.radio, "setBandwidth"):
                lora.radio.setBandwidth(bw)
            lora.bandwidth = bw
            w("Bandwidth set to %.1f kHz" % bw)
        except Exception as exc:
            w("Error: " + str(exc))

    def _cmd_freq_slot(self, args):
        w = self.shell._write
        if not args:
            w("Usage: radio freq_slot <1..52>")
            return

        try:
            slot = int(args[0])
        except ValueError:
            w("Error: invalid slot")
            return

        try:
            freq = self.badge.lora.set_freq_slot(slot)
            w("Set to slot %d (%.3f MHz)" % (slot, freq))
        except Exception as exc:
            w("Error: " + str(exc))

    def _cmd_rssi(self, args):
        w = self.shell._write
        try:
            rssi = self.badge.lora.get_rssi()
            w("RSSI: %.1f dBm" % float(rssi))
        except Exception as exc:
            w("Error: " + str(exc))
