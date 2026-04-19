"""BadUSB commands: badusb run, badusb type."""

class BadUsbCommands:
    """Registers the 'badusb' command group for Keystroke Injection."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "badusb",
            {
                "run": (self._cmd_run, "Run DuckyScript payload: badusb run <script.txt>"),
                "type": (self._cmd_type, "Type string directly: badusb type <string>"),
            },
            "USB Keystroke Injection (BadUSB)"
        )

    def _cmd_type(self, args):
        w = self.shell._write
        if not args:
            w("Usage: badusb type <string>")
            return
            
        text = " ".join(args)
        w(f"Typing: {text}")
        
        try:
            self._type_string(text)
            w("Done.")
        except Exception as e:
            w("Error typing: " + str(e))

    def _cmd_run(self, args):
        w = self.shell._write
        if not args:
            w("Usage: badusb run <script.txt>")
            return
            
        script_path = args[0]
        try:
            with open(script_path, "r") as f:
                lines = f.readlines()
        except OSError:
            w(f"Error: Could not read {script_path}")
            return
            
        w(f"Running DuckyScript from {script_path}...")
        
        import time
        try:
            for line in lines:
                line = line.strip()
                if not line or line.startswith("REM"):
                    continue
                    
                if line.startswith("DELAY "):
                    delay_ms = int(line[6:].strip())
                    time.sleep(delay_ms / 1000.0)
                elif line.startswith("STRING "):
                    text = line[7:]
                    self._type_string(text)
                elif line == "ENTER":
                    self._press_key(0x28) # ENTER
                elif line == "GUI r" or line == "WINDOWS r":
                    self._press_key(0x15, modifier=0x08) # GUI + r
                else:
                    w(f"Unsupported command: {line}")
            w("Payload complete.")
        except Exception as e:
            w("Error running payload: " + str(e))
            
    def _type_string(self, text):
        import time
        try:
            import usb.device
            from usb.device.keyboard import KeyboardInterface
            kbd = KeyboardInterface()
            # Note: This is pseudo-code for typical micropython usb device
            # as actual API varies by firmware build
            for char in text:
                kbd.write(char)
                time.sleep(0.01)
        except ImportError:
            # Mock / CPython fallback
            if not hasattr(self.shell.badge, "mock_hid_log"):
                self.shell.badge.mock_hid_log = []
            self.shell.badge.mock_hid_log.append(f"TYPE: {text}")

    def _press_key(self, keycode, modifier=0):
        import time
        try:
            import usb.device
            from usb.device.keyboard import KeyboardInterface
            kbd = KeyboardInterface()
            kbd.press(keycode, modifier)
            time.sleep(0.01)
            kbd.release()
        except ImportError:
            # Mock / CPython fallback
            if not hasattr(self.shell.badge, "mock_hid_log"):
                self.shell.badge.mock_hid_log = []
            self.shell.badge.mock_hid_log.append(f"KEY: {keycode} MOD: {modifier}")
