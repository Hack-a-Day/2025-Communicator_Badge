"""Hardware commands: i2c, gpio, led, vibro, buzzer."""

import sys


class HardwareCommands:
    """Registers hardware-related command groups with the shell."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge

        shell.register_group(
            "i2c",
            {"scan": (self._cmd_i2c_scan, "Scan SAO I2C bus for devices")},
            "I2C bus (SAO header)"
        )

        shell.register_group(
            "gpio",
            {
                "mode": (self._cmd_gpio_mode, "Set pin direction: gpio mode <pin> <in|out>"),
                "set": (self._cmd_gpio_set, "Set pin value: gpio set <pin> <0|1>"),
                "read": (self._cmd_gpio_read, "Read pin value: gpio read <pin>"),
            },
            "SAO GPIO pins"
        )

        shell.register_group(
            "led",
            {"set": (self._cmd_led, "Toggle debug LED: led set <0|1>")},
            "Debug LED"
        )

        shell.register_command("vibro", self._cmd_vibro, "Vibration motor (unsupported)")
        shell.register_command("buzzer", self._cmd_buzzer, "Buzzer (unsupported)")

    # ── I2C ─────────────────────────────────────────────────

    def _cmd_i2c_scan(self, args):
        """Scan the SAO I2C bus and list device addresses."""
        w = self.shell._write
        try:
            devices = self.badge.sao_i2c.scan()
            if not devices:
                w("No I2C devices found on SAO bus.")
                return
            w("Found %d device(s):" % len(devices))
            for addr in devices:
                w("  0x%02x (%d)" % (addr, addr))
        except Exception as e:
            w("I2C scan error: " + str(e))

    # ── GPIO ────────────────────────────────────────────────

    _PIN_MAP = {
        "sao1": 7,
        "sao2": 6,
        "gpio1": 7,
        "gpio2": 6,
        "7": 7,
        "6": 6,
    }

    def _resolve_pin(self, name):
        """Resolve a pin name to a pin number."""
        return self._PIN_MAP.get(name.lower())

    def _cmd_gpio_mode(self, args):
        """Set a SAO GPIO pin direction."""
        w = self.shell._write
        if len(args) < 2:
            w("Usage: gpio mode <pin> <in|out>")
            w("Pins: sao1 (Pin 7), sao2 (Pin 6)")
            return

        pin_num = self._resolve_pin(args[0])
        if pin_num is None:
            w("Unknown pin: " + args[0] + ". Available: sao1, sao2")
            return

        direction = args[1].lower()
        try:
            from machine import Pin
            if direction in ("in", "0", "input"):
                Pin(pin_num, Pin.IN)
                w("Pin %d set to INPUT" % pin_num)
            elif direction in ("out", "1", "output"):
                Pin(pin_num, Pin.OUT)
                w("Pin %d set to OUTPUT" % pin_num)
            else:
                w("Unknown direction: " + direction + ". Use 'in' or 'out'.")
        except ImportError:
            w("(machine.Pin not available on this platform)")

    def _cmd_gpio_set(self, args):
        """Set a SAO GPIO pin value."""
        w = self.shell._write
        if len(args) < 2:
            w("Usage: gpio set <pin> <0|1>")
            return

        pin_num = self._resolve_pin(args[0])
        if pin_num is None:
            w("Unknown pin: " + args[0])
            return

        try:
            value = int(args[1])
            from machine import Pin
            p = Pin(pin_num, Pin.OUT)
            p.value(value)
            w("Pin %d = %d" % (pin_num, value))
        except ImportError:
            w("(machine.Pin not available on this platform)")
        except Exception as e:
            w("Error: " + str(e))

    def _cmd_gpio_read(self, args):
        """Read a SAO GPIO pin value."""
        w = self.shell._write
        if not args:
            w("Usage: gpio read <pin>")
            return

        pin_num = self._resolve_pin(args[0])
        if pin_num is None:
            w("Unknown pin: " + args[0])
            return

        try:
            from machine import Pin
            p = Pin(pin_num, Pin.IN)
            val = p.value()
            w("Pin %d = %d" % (pin_num, val))
        except ImportError:
            w("(machine.Pin not available on this platform)")

    # ── LED ─────────────────────────────────────────────────

    def _cmd_led(self, args):
        """Toggle the debug LED."""
        w = self.shell._write
        if not args:
            w("Usage: led set <0|1>")
            return

        try:
            value = int(args[0])
            from hardware import board
            if value:
                board.DEBUG_LED.on()
            else:
                board.DEBUG_LED.off()
            w("LED " + ("ON" if value else "OFF"))
        except ImportError:
            w("(board.DEBUG_LED not available on this platform)")
        except Exception as e:
            w("Error: " + str(e))

    # ── Unsupported ─────────────────────────────────────────

    def _cmd_vibro(self, args):
        self.shell._write("No vibration motor on this badge.")

    def _cmd_buzzer(self, args):
        self.shell._write("No buzzer on this badge.")
