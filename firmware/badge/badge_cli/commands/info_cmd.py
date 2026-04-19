"""Info commands: info device, info power.

Displays system information about the badge hardware and firmware.
"""


class InfoCommands:
    """Registers the 'info' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge
        shell.register_group(
            "info",
            {
                "device": (self._cmd_device, "Hardware and firmware info"),
                "power": (self._cmd_power, "Battery / power info"),
                "top": (self._cmd_top, "Interactive system monitor (Ctrl+C to stop)"),
            },
            "System information"
        )

    def _cmd_device(self, args):
        """Show badge hardware and firmware info."""
        w = self.shell._write
        badge = self.badge

        # Address
        try:
            from net.net import MY_ADDRESS
            w("Address:    %08x" % MY_ADDRESS)
        except ImportError:
            w("Address:    (unavailable)")

        # Alias
        try:
            alias = badge.config.get("alias", b"").decode().strip()
            w("Alias:      " + (alias if alias else "(not set)"))
        except Exception:
            w("Alias:      (not set)")

        # Platform
        import sys
        w("Platform:   " + sys.platform)

        # Radio
        try:
            lora = badge.lora
            w("Radio:      SX1262 LoRa")
            w("  Freq:     %.3f MHz (slot %d)" % (lora.frequency, lora.freq_slot))
            w("  BW:       %.1f kHz" % lora.bandwidth)
            w("  SF:       %d" % lora.spreading_factor)
            w("  CR:       4/%d" % lora.coding_rate)
            w("  TX Power: %d dBm" % lora.tx_power)
            w("  RSSI:     %.1f dBm" % lora.last_rssi)
            w("  SNR:      %.1f dB" % lora.last_snr)
        except Exception as e:
            w("Radio:      (error: " + str(e) + ")")

        # Memory
        import gc
        from badge_cli.shell import Colors
        if hasattr(gc, "mem_free") and hasattr(gc, "mem_alloc"):
            free = gc.mem_free()
            alloc = gc.mem_alloc()
            total = free + alloc
            used_pct = alloc * 100 // total if total else 0
            color = Colors.GREEN
            if used_pct > 70: color = Colors.YELLOW
            if used_pct > 90: color = Colors.RED
            w("Heap:       " + color + "%d / %d bytes (%d%% used)" % (
                alloc, total, used_pct
            ) + Colors.END)
        else:
            w("Heap:       (info not available)")

    def _cmd_top(self, args):
        """Interactive system monitor."""
        import gc
        import time
        from badge_cli.shell import Colors
        
        self.shell._streaming = True
        self.shell._write(Colors.CYAN + "System Monitor (top) - Press Ctrl+C to exit" + Colors.END)
        self.shell._write("Time       | Heap Used  | Free      | % Used")
        self.shell._write("-" * 45)
        
        try:
            while self.shell._streaming:
                self.shell.check_interrupt()
                
                free = gc.mem_free()
                alloc = gc.mem_alloc()
                total = free + alloc
                used_pct = alloc * 100 // total if total else 0
                
                # Get uptime or current time
                try:
                    uptime = time.ticks_ms() // 1000
                except AttributeError:
                    uptime = int(time.time())
                
                color = Colors.GREEN
                if used_pct > 70: color = Colors.YELLOW
                if used_pct > 90: color = Colors.RED
                
                line = "\r%08d s | %10d | %9d | " % (uptime, alloc, free)
                line += color + ("%2d%%" % used_pct) + Colors.END
                
                self.shell._write_raw(line)
                
                # Wait 1 second but check for interrupts
                for _ in range(10):
                    if not self.shell._streaming: break
                    self.shell.check_interrupt()
                    time.sleep(0.1)
            
            self.shell._write("\r\nStopped.")
        finally:
            self.shell._streaming = False

    def _cmd_power(self, args):
        """Show battery / power info (stub — no fuel gauge on badge)."""
        w = self.shell._write
        w("Power source: USB")
        w("Battery:      No fuel gauge on this badge")
        w("Charging:     N/A")
