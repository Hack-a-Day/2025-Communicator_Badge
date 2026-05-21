"""Meta commands: help, echo, exit, version, and other top-level utilities.

These are the first commands available in the shell and require no
hardware access. MicroPython-compatible.
"""

import gc
import sys
import time


class MetaCommands:
    """Registers top-level meta commands with the shell."""

    def __init__(self, shell):
        self.shell = shell
        self._boot_ticks = None
        try:
            self._boot_ticks = time.ticks_ms()
        except AttributeError:
            # CPython doesn't have ticks_ms; fall back to time.time()
            self._boot_time = time.time()

        # Register top-level commands
        shell.register_command("help", self._cmd_help, "List all commands")
        shell.register_command("?", self._cmd_help, "Alias for help")
        shell.register_command("!", self._cmd_bang, "Alias for 'info device'")
        shell.register_command("echo", self._cmd_echo, "Echo text back")
        shell.register_command("clear", self._cmd_clear, "Clear terminal screen")
        shell.register_command("exit", self._cmd_exit, "Drop to MicroPython REPL")
        shell.register_command("version", self._cmd_version, "Firmware version info")
        shell.register_command("uptime", self._cmd_uptime, "Time since boot")
        shell.register_command("date", self._cmd_date, "Current date and time")
        shell.register_command("free", self._cmd_free, "Heap memory info")
        shell.register_command("free_blocks", self._cmd_free_blocks, "Heap free/alloc breakdown")
        shell.register_command("top", self._cmd_top, "Running apps (Ctrl+C to stop)")
        shell.register_command("sleep", self._cmd_sleep, "Delay N[ms|s] (Ctrl+C to abort)")
        shell.register_command("neofetch", self._cmd_neofetch, "System info with ASCII art")
        shell.register_command("factory_reset", self._cmd_factory_reset, "Erase config and reboot")
        shell.register_command("batch", self._cmd_batch, "Run CLI script: batch <file>")
        shell.register_command("history", self._cmd_history, "Show command history")

    def _cmd_help(self, args):
        """List all available commands and command groups."""
        w = self.shell._write
        colw = 20

        def pad(text, width):
            text = str(text)
            if len(text) >= width:
                return text
            return text + (" " * (width - len(text)))

        w("Commands:")

        # Top-level commands (sorted)
        cmds = sorted(self.shell._commands.keys())
        for name in cmds:
            _, help_text = self.shell._commands[name]
            w("  " + pad(name, colw) + help_text)

        # Command groups
        if self.shell._groups:
            w("")
            w("Command groups (type '<group> ?' for sub-commands):")
            groups = sorted(self.shell._groups.keys())
            for gname in groups:
                desc = self.shell._group_descriptions.get(gname, "")
                w("  " + pad(gname, colw) + desc)

    def _cmd_bang(self, args):
        """Alias for 'info device'."""
        self.shell.run_command("info device")

    def _cmd_echo(self, args):
        """Echo text back to the terminal."""
        self.shell._write(" ".join(args))

    def _cmd_clear(self, args):
        """Clear the terminal screen and move cursor to top-left."""
        # ANSI clear screen + cursor home
        self.shell._write_raw("\x1b[2J\x1b[H")

    def _cmd_exit(self, args):
        """Drop to the MicroPython REPL."""
        self.shell._write("Exiting CLI. Press Ctrl+D to return or reset to restart.")
        raise KeyboardInterrupt()

    def _cmd_version(self, args):
        """Show firmware version info."""
        from badge_cli import __version__
        w = self.shell._write
        w("Badge CLI v" + __version__)
        w("Platform: " + sys.platform)
        w("Python: " + sys.version)

    def _cmd_uptime(self, args):
        """Show time since boot."""
        if self._boot_ticks is not None:
            try:
                elapsed_ms = time.ticks_diff(time.ticks_ms(), self._boot_ticks)
            except AttributeError:
                elapsed_ms = int((time.time() - self._boot_time) * 1000)
        else:
            elapsed_ms = int((time.time() - self._boot_time) * 1000)

        secs = elapsed_ms // 1000
        mins = secs // 60
        hours = mins // 60
        secs = secs % 60
        mins = mins % 60
        self.shell._write("Uptime: %dh%dm%ds" % (hours, mins, secs))

    def _cmd_date(self, args):
        """Show current date and time."""
        try:
            t = time.localtime()
            self.shell._write(
                "%04d-%02d-%02d %02d:%02d:%02d" % (t[0], t[1], t[2], t[3], t[4], t[5])
            )
        except Exception:
            self.shell._write("RTC not available")

    def _cmd_free(self, args):
        """Show heap memory info."""
        w = self.shell._write
        try:
            import micropython
            # micropython.mem_info() prints directly to stdout
            # Capture by redirecting (or just call it)
            micropython.mem_info()
        except ImportError:
            # CPython fallback
            allocated = gc.mem_alloc() if hasattr(gc, "mem_alloc") else 0
            free = gc.mem_free() if hasattr(gc, "mem_free") else 0
            w("Heap: %d bytes free, %d bytes allocated" % (free, allocated))
            if free + allocated > 0:
                w("Usage: %d%%" % (allocated * 100 // (free + allocated)))

    def _cmd_free_blocks(self, args):
        """Show heap free/alloc breakdown."""
        w = self.shell._write
        if hasattr(gc, "mem_free") and hasattr(gc, "mem_alloc"):
            free = gc.mem_free()
            alloc = gc.mem_alloc()
            total = free + alloc
            w("Free:      %d bytes" % free)
            w("Allocated: %d bytes" % alloc)
            w("Total:     %d bytes" % total)
        else:
            # CPython: use gc.get_stats if available, otherwise basic info
            gc.collect()
            w("gc.collect() called")
            w("(Detailed heap info not available on this platform)")

    def _cmd_top(self, args):
        """List running apps and their state. Streams until Ctrl+C."""
        w = self.shell._write
        try:
            from apps.base_app import BaseApp
            apps = BaseApp.all_apps
        except ImportError:
            # No apps module (testing without badge firmware)
            apps = []

        if not apps:
            w("No apps registered.")
            return

        self.shell._streaming = True
        while self.shell._streaming:
            w("%-20s %-12s %-8s" % ("Name", "State", "Sleep(ms)"))
            w("-" * 44)
            for app in apps:
                if app.active_foreground:
                    state = "foreground"
                    sleep_ms = app.foreground_sleep_ms
                elif app.active_background:
                    state = "background"
                    sleep_ms = app.background_sleep_ms
                else:
                    state = "stopped"
                    sleep_ms = 0
                w("%-20s %-12s %-8d" % (app.name, state, sleep_ms))

            # Show memory
            if hasattr(gc, "mem_free"):
                w("")
                w("Heap: %d free / %d alloc" % (gc.mem_free(), gc.mem_alloc()))
            w("")

            # In real firmware, sleep before refresh. In test, break immediately.
            try:
                time.sleep_ms(1000)
            except AttributeError:
                # CPython: just break out (tests won't stream)
                break

    def _cmd_sleep(self, args):
        """Sleep for a duration. Usage: sleep <N>[ms|s]"""
        if not args:
            self.shell._write("Usage: sleep <N>[ms|s]  (default: ms)")
            return

        val = args[0]
        if val.endswith("ms"):
            ms = int(val[:-2])
        elif val.endswith("s"):
            ms = int(val[:-1]) * 1000
        else:
            ms = int(val)

        self.shell._write("Sleeping %d ms... (Ctrl+C to abort)" % ms)
        self.shell._streaming = True
        elapsed = 0
        step = min(ms, 100)
        while self.shell._streaming and elapsed < ms:
            try:
                time.sleep_ms(step)
            except AttributeError:
                time.sleep(step / 1000.0)
            elapsed += step
        self.shell._streaming = False
        self.shell._write("Done.")

    def _cmd_neofetch(self, args):
        """Display system info with ASCII art."""
        w = self.shell._write
        badge = self.shell.badge

        # Gather system info
        try:
            from net.net import MY_ADDRESS
            addr = "%08x" % MY_ADDRESS
        except ImportError:
            addr = "unknown"

        try:
            alias = badge.config.get("alias", b"").decode().strip()
        except Exception:
            alias = ""
        if not alias:
            alias = addr

        try:
            from badge_cli import __version__
            cli_ver = __version__
        except ImportError:
            cli_ver = "?"

        try:
            freq_slot = str(badge.lora.freq_slot)
            freq_mhz = "%.3f" % badge.lora.frequency
        except Exception:
            freq_slot = "?"
            freq_mhz = "?"

        if hasattr(gc, "mem_free") and hasattr(gc, "mem_alloc"):
            mem_free = gc.mem_free()
            mem_alloc = gc.mem_alloc()
            mem_total = mem_free + mem_alloc
            mem_str = "%d / %d KB (%d%%)" % (
                mem_alloc // 1024, mem_total // 1024,
                mem_alloc * 100 // mem_total if mem_total else 0
            )
        else:
            mem_str = "N/A"

        # ASCII art + info lines
        art = [
            r" _               _                   _ _  ",
            r"| |__   __ _  __| | __ _  ___    ___| (_) ",
            r"| '_ \ / _` |/ _` |/ _` |/ _ \  / __| | | ",
            r"| |_) | (_| | (_| | (_| |  __/ | (__| | | ",
            r"|_.__/ \__,_|\__,_|\__, |\___|  \___|_|_| ",
            r"                   |___/                  ",
            r"",
            r"",
            r"",
            r"",
        ]

        info = [
            "badge@" + addr,
            "──────────────",
            "OS: Badge CLI Hackaday Europe 2026",
            "Host: Hackaday Communicator Badge",
            "Kernel: MicroPython + asyncio",
            "Radio: SX1262 slot " + freq_slot + " (" + freq_mhz + " MHz)",
            "Shell: BadgeCLI v" + cli_ver,
            "CPU: ESP32-S3 @ 240 MHz",
            "Memory: " + mem_str,
            "Alias: " + alias,
        ]

        # Print side by side
        for i in range(max(len(art), len(info))):
            left = art[i] if i < len(art) else ""
            right = info[i] if i < len(info) else ""
            w("%-42s %s" % (left, right))

    def _cmd_factory_reset(self, args):
        """Erase config and reboot."""
        w = self.shell._write
        if not args or args[0] != "confirm":
            w("WARNING: This will erase all configuration!")
            w("Run 'factory_reset confirm' to proceed.")
            return

        w("Erasing config...")
        try:
            import os
            os.remove("/data/config")
            w("Config erased.")
        except Exception as e:
            w("Error: " + str(e))

        w("Rebooting...")
        try:
            import machine
            machine.reset()
        except ImportError:
            w("(machine.reset() not available on this platform)")

    def _cmd_batch(self, args):
        """Run a sequence of CLI commands from a file."""
        w = self.shell._write
        if not args:
            w("Usage: batch <filename.cli>")
            return
            
        filename = args[0]
        try:
            with open(filename, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    w(f"> {line}")
                    self.shell.run_command(line)
        except OSError:
            w(f"Error: Could not read {filename}")

    def _cmd_history(self, args):
        """Show command history."""
        w = self.shell._write
        if not self.shell._history:
            w("No history.")
            return
            
        for i, cmd in enumerate(self.shell._history):
            w(f"{i+1:3}  {cmd}")
