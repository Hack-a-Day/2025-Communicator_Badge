"""Power commands: power off, power reboot."""


class PowerCommands:
    """Registers the 'power' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "power",
            {
                "off": (self._cmd_off, "Deep sleep (power off)"),
                "reboot": (self._cmd_reboot, "Hard reset"),
            },
            "Power management"
        )

    def _cmd_off(self, args):
        w = self.shell._write
        w("Entering deep sleep...")
        try:
            import machine
            machine.deepsleep()
        except ImportError:
            w("(machine.deepsleep() not available on this platform)")

    def _cmd_reboot(self, args):
        w = self.shell._write
        w("Rebooting...")
        try:
            import machine
            machine.reset()
        except ImportError:
            w("(machine.reset() not available on this platform)")
