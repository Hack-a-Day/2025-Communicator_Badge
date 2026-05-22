"""Runtime feature flags and boot-time policy hooks."""

# Global serial print toggle.
# Set True while debugging boot/runtime internals over USB serial.
SERIAL_PRINTS_ENABLED = False


def apply_serial_print_policy():
    """Optionally silence print() globally to keep serial CLI clean."""
    if SERIAL_PRINTS_ENABLED:
        return

    import builtins

    def _quiet_print(*args, **kwargs):
        return None

    builtins.print = _quiet_print
