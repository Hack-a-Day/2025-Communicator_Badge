"""Wardriving command group: combined Wi-Fi and BLE scanning helpers."""


class WardrivingCommands:
    """Registers the 'wardriving' command group."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "wardriving",
            {
                "scan": (
                    self._cmd_scan,
                    "Run Wi-Fi then BLE scan: wardriving scan [ble_timeout_sec]",
                ),
                "wifi": (self._cmd_wifi, "Run Wi-Fi scan: wardriving wifi"),
                "ble": (self._cmd_ble, "Run BLE scan: wardriving ble [timeout_sec]"),
            },
            "Combined wardriving workflows",
        )

    def _run_group_subcommand(self, group_name, subcommand, args):
        group = self.shell._groups.get(group_name)
        if not group:
            self.shell._write(group_name + " command group is unavailable.")
            return False

        entry = group.get(subcommand)
        if not entry:
            self.shell._write(group_name + " " + subcommand + " is unavailable.")
            return False

        handler, _ = entry
        handler(args)
        return True

    def _cmd_wifi(self, args):
        self._run_group_subcommand("wifi", "scan", [])

    def _cmd_ble(self, args):
        self._run_group_subcommand("ble", "scan", args)

    def _cmd_scan(self, args):
        w = self.shell._write
        ble_timeout = "5"

        if args:
            try:
                ble_timeout = str(int(args[0]))
            except ValueError:
                w("Usage: wardriving scan [ble_timeout_sec]")
                return

        w("Wardriving sweep: Wi-Fi + BLE")
        w("--- Wi-Fi ---")
        self._run_group_subcommand("wifi", "scan", [])

        w("--- BLE ---")
        self._run_group_subcommand("ble", "scan", [ble_timeout])
