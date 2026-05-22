"""Display commands: basic text, clear, backlight, and image rendering."""


class DisplayCommands:
    """Registers the 'display' command group."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge
        shell.register_group(
            "display",
            {
                "text": (self._cmd_text, "Draw text: display text <x> <y> <text>"),
                "clear": (self._cmd_clear, "Clear display"),
                "backlight": (self._cmd_backlight, "Set backlight PWM: display backlight <0..1023>"),
                "image": (self._cmd_image, "Draw image: display image [x] [y] <path>"),
            },
            "Display controls",
        )

    def _cmd_text(self, args):
        w = self.shell._write
        if len(args) < 3:
            w("Usage: display text <x> <y> <text>")
            return

        try:
            x = int(args[0])
            y = int(args[1])
        except ValueError:
            w("Error: x and y must be integers")
            return

        text = " ".join(args[2:])
        try:
            self.badge.display.text(x, y, text)
            w("Rendered text at (%d, %d)" % (x, y))
        except Exception as exc:
            w("Error: " + str(exc))

    def _cmd_clear(self, args):
        w = self.shell._write
        try:
            self.badge.display.clear()
            w("Display cleared")
        except Exception as exc:
            w("Error: " + str(exc))

    def _cmd_backlight(self, args):
        w = self.shell._write
        if not args:
            w("Usage: display backlight <0..1023>")
            return

        try:
            value = int(args[0])
        except ValueError:
            w("Error: backlight value must be an integer")
            return

        if value < 0 or value > 1023:
            w("Error: backlight out of range (0..1023)")
            return

        try:
            bl = self.badge.display.backlight
            if hasattr(bl, "duty"):
                bl.duty(value)
            elif hasattr(bl, "duty_u16"):
                bl.duty_u16(value << 6)
            else:
                raise RuntimeError("Unsupported backlight interface")
            w("Backlight set to %d" % value)
        except Exception as exc:
            w("Error: " + str(exc))

    def _cmd_image(self, args):
        w = self.shell._write
        if not args:
            w("Usage: display image [x] [y] <path>")
            return

        x = 0
        y = 0
        path = None

        if len(args) >= 3:
            try:
                x = int(args[0])
                y = int(args[1])
                path = " ".join(args[2:])
            except ValueError:
                path = " ".join(args)
        else:
            path = " ".join(args)

        if not path:
            w("Usage: display image [x] [y] <path>")
            return

        try:
            self.badge.display.image(x, y, path)
            w("Rendered image: " + path)
        except Exception as exc:
            w("Error: " + str(exc))
