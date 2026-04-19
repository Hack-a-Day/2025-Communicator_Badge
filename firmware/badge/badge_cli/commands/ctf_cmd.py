"""CTF commands: ctf host, stop, scan, watch, reset.

Thin CLI wrapper around the CTFApp instance.
"""


class CTFCommands:
    """Registers the 'ctf' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "ctf",
            {
                "host": (self._cmd_host, "Start hosting CTF flag beacon"),
                "stop": (self._cmd_stop, "Stop hosting flag"),
                "scan": (self._cmd_scan, "Update scan: ctf scan <rssi>"),
                "watch": (self._cmd_watch, "Continuous scan (Ctrl+C to stop)"),
                "reset": (self._cmd_reset, "Reset scan history"),
                "status": (self._cmd_status, "Show CTF status and scan history"),
            },
            "Capture-the-Flag hot/cold game"
        )

    def _get_ctf(self):
        app = self.shell.find_app("CTF")
        if app is None:
            # Try importing directly for test environments
            try:
                from apps.ctf_app import CTFApp
                for a in CTFApp.all_apps:
                    if isinstance(a, CTFApp):
                        return a
            except ImportError:
                pass
        return app

    def _cmd_host(self, args):
        w = self.shell._write
        ctf = self._get_ctf()
        if not ctf:
            w("Error: CTF app not running. Start it first.")
            return
        ctf.host_flag()
        w("Hosting CTF flag beacon. Other badges can scan for you.")

    def _cmd_stop(self, args):
        w = self.shell._write
        ctf = self._get_ctf()
        if not ctf:
            w("Error: CTF app not running.")
            return
        ctf.stop_flag()
        w("Stopped hosting CTF flag. Beacons sent: %d" % ctf.beacon_count)

    def _cmd_scan(self, args):
        w = self.shell._write
        ctf = self._get_ctf()
        if not ctf:
            w("Error: CTF app not running.")
            return
        if not args:
            w("Usage: ctf scan <rssi_value>")
            w("Example: ctf scan -70")
            return
        try:
            rssi = float(args[0])
        except ValueError:
            w("Error: Invalid RSSI value: " + args[0])
            return
        trend = ctf.scan(rssi)
        markers = {"start": "●", "warmer": "▲", "colder": "▼", "same": "─"}
        w("%s RSSI=%.1f  %s" % (markers.get(trend, "?"), rssi, trend.upper()))

    def _cmd_watch(self, args):
        w = self.shell._write
        ctf = self._get_ctf()
        if not ctf:
            w("Error: CTF app not running.")
            return
        w("Watching for CTF beacons... (Ctrl+C to stop)")
        self.shell._streaming = True
        import time
        while self.shell._streaming:
            # In real firmware, this would read from ctf._receive_queue
            # For now, just show scan history updates
            if ctf.scan_history:
                last = ctf.scan_history[-1]
                markers = {"start": "●", "warmer": "▲", "colder": "▼", "same": "─"}
                w("%s RSSI=%.1f  %s" % (markers.get(last[1], "?"), last[0], last[1].upper()))
            try:
                time.sleep_ms(500)
            except AttributeError:
                break  # CPython — exit streaming in tests
        self.shell._streaming = False

    def _cmd_reset(self, args):
        w = self.shell._write
        ctf = self._get_ctf()
        if not ctf:
            w("Error: CTF app not running.")
            return
        ctf.reset_scan()
        w("Scan history cleared.")

    def _cmd_status(self, args):
        w = self.shell._write
        ctf = self._get_ctf()
        if not ctf:
            w("Error: CTF app not running.")
            return
        w("CTF Status:")
        w("  Hosting:    %s" % ("YES" if ctf.hosting else "no"))
        w("  Beacons TX: %d" % ctf.beacon_count)
        w("  Last RSSI:  %s" % (("%.1f" % ctf.last_rssi) if ctf.last_rssi is not None else "N/A"))
        w("  Scans:      %d" % len(ctf.scan_history))
        if ctf.scan_history:
            w("  History (last 10):")
            for rssi, trend in ctf.scan_history[-10:]:
                markers = {"start": "●", "warmer": "▲", "colder": "▼", "same": "─"}
                w("    %s %.1f %s" % (markers.get(trend, "?"), rssi, trend))
