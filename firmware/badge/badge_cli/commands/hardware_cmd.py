"""Hardware commands: i2c, gpio, led, vibro, buzzer."""

import sys


class HardwareCommands:
    """Registers hardware-related command groups with the shell."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge

        shell.register_group(
            "i2c",
            {
                "scan": (self._cmd_i2c_scan, "Scan SAO I2C bus for devices"),
                "dump": (self._cmd_i2c_dump, "Dump EEPROM/device data: i2c dump <addr> <size>"),
            },
            "I2C bus (SAO header)"
        )

        shell.register_group(
            "gpio",
            {
                "mode": (self._cmd_gpio_mode, "Set pin direction: gpio mode <pin> <in|out>"),
                "set": (self._cmd_gpio_set, "Set pin value: gpio set <pin> <0|1>"),
                "read": (self._cmd_gpio_read, "Read pin value: gpio read <pin>"),
                "logic": (self._cmd_gpio_logic, "Logic analyzer: gpio logic <pin> <samples> [delay_ms]"),
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

    def _cmd_i2c_dump(self, args):
        """Dump data from an I2C device (like an EEPROM)."""
        w = self.shell._write
        if len(args) < 2:
            w("Usage: i2c dump <addr> <size_bytes>")
            return
            
        try:
            addr = int(args[0], 0)
            size = int(args[1], 0)
            
            # Usually we write 0x00 to set the address pointer to 0, then read
            try:
                self.badge.sao_i2c.writeto(addr, b'\x00')
            except Exception:
                pass # Some devices don't need this or might fail, just continue
                
            data = self.badge.sao_i2c.readfrom(addr, size)
            if not data:
                w(f"No data returned from 0x{addr:02x}")
                return
                
            w(f"Dump of 0x{addr:02x} ({size} bytes):")
            
            # Print hex dump
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                hex_str = " ".join(f"{b:02x}" for b in chunk)
                ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                w(f"{i:04x}  {hex_str:<48}  |{ascii_str}|")
                
        except ValueError:
            w("Error: Address and size must be integers (hex or decimal)")
        except AttributeError:
            w("(I2C read/write not supported by current mock)")
        except Exception as e:
            w(f"Error dumping I2C: {e}")

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

    def _cmd_gpio_logic(self, args):
        """Simple logic analyzer: capture pin states."""
        w = self.shell._write
        if len(args) < 2:
            w("Usage: gpio logic <pin> <samples> [delay_ms]")
            return
            
        pin_num = self._resolve_pin(args[0])
        if pin_num is None:
            w("Unknown pin: " + args[0])
            return
            
        try:
            samples = int(args[1])
            delay_ms = int(args[2]) if len(args) > 2 else 10
            
            from machine import Pin
            p = Pin(pin_num, Pin.IN)
            
            w(f"Capturing {samples} samples on pin {pin_num} (delay {delay_ms}ms)...")
            results = []
            
            import time
            for _ in range(samples):
                results.append(p.value())
                time.sleep(delay_ms / 1000.0)
                
            w("Capture complete.")
            
            # Draw waveform
            w("Waveform:")
            waveform = "".join("‾" if v else "_" for v in results)
            w(waveform)
            
            # Print sequence
            seq = "".join(str(v) for v in results)
            w(f"Sequence: {seq}")
            
        except ImportError:
            w("(machine.Pin not available on this platform)")
        except ValueError:
            w("Error: samples and delay must be integers")
        except Exception as e:
            w("Error: " + str(e))

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
