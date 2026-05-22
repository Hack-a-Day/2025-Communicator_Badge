"""Input commands: keyboard injection and key stream dump."""

import time


class InputCommands:
    """Registers the 'input' command group."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge
        shell.register_group(
            "input",
            {
                "dump": (self._cmd_dump, "Dump keybuffer events: input dump [count]"),
                "send": (self._cmd_send, "Inject one key: input send <key>"),
                "send_text": (self._cmd_send_text, "Inject text: input send_text <text>"),
            },
            "Keyboard input helpers",
        )

    def _normalize_key(self, token):
        kbd = self.badge.keyboard
        named = {
            "ENTER": getattr(kbd, "ENTER", "\n"),
            "TAB": getattr(kbd, "TAB", "\t"),
            "ESC": getattr(kbd, "ESC", "\x1b"),
            "BS": getattr(kbd, "BS", "\b"),
            "BACKSPACE": getattr(kbd, "BS", "\b"),
            "DEL": getattr(kbd, "DEL", "\x7f"),
            "DELETE": getattr(kbd, "DEL", "\x7f"),
            "UP": getattr(kbd, "UP", "`j"),
            "DOWN": getattr(kbd, "DOWN", "`k"),
            "LEFT": getattr(kbd, "LEFT", "`h"),
            "RIGHT": getattr(kbd, "RIGHT", "`l"),
        }
        upper = token.upper()
        if upper in named:
            return named[upper]
        return token

    def _cmd_send(self, args):
        w = self.shell._write
        if not args:
            w("Usage: input send <key>")
            return

        key = self._normalize_key(" ".join(args))
        self.badge.keyboard.keybuffer.append(key)
        w("Injected key: " + repr(key))

    def _cmd_send_text(self, args):
        w = self.shell._write
        if not args:
            w("Usage: input send_text <text>")
            return

        text = " ".join(args)
        for ch in text:
            self.badge.keyboard.keybuffer.append(ch)
        w("Injected %d characters" % len(text))

    def _cmd_dump(self, args):
        w = self.shell._write
        if not args:
            key = self.badge.keyboard.read_key()
            if key is None:
                w("No input queued.")
            else:
                w("[1] %r" % key)
            return

        count = 20
        if args:
            try:
                count = int(args[0])
            except ValueError:
                w("Usage: input dump [count]")
                return

        if count <= 0:
            w("Usage: input dump [count]")
            return

        w("Dumping up to %d key events (Ctrl+C to stop)..." % count)
        emitted = 0
        self.shell._streaming = True

        try:
            while self.shell._streaming and emitted < count:
                key = self.badge.keyboard.read_key()
                if key is not None:
                    w("[%d] %r" % (emitted + 1, key))
                    emitted += 1
                else:
                    try:
                        self.shell.check_interrupt()
                    except Exception:
                        pass
                    try:
                        time.sleep_ms(20)
                    except AttributeError:
                        time.sleep(0.02)
        finally:
            self.shell._streaming = False
            w("Input dump complete (%d event%s)." % (emitted, "" if emitted == 1 else "s"))
