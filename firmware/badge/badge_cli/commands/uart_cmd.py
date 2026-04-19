"""UART commands for serial terminal and bridge functionality."""

import sys
import time

class UartCommands:
    """Registers UART-related command groups with the shell."""

    def __init__(self, shell):
        self.shell = shell
        self.uart = None
        
        shell.register_group(
            "uart",
            {
                "bridge": (self._cmd_bridge, "USB <-> UART Bridge: uart bridge [baud]"),
                "terminal": (self._cmd_terminal, "Interactive terminal: uart terminal [baud]"),
            },
            "Serial UART (SAO header)"
        )

    def _init_uart(self, baud):
        """Initialize UART1 on SAO pins (TX=7, RX=6)."""
        from machine import UART
        # Deinit if already open
        if self.uart:
            try:
                self.uart.deinit()
            except:
                pass
        
        # ESP32-S3 UART1
        # SAO Pin 7 is TX, Pin 6 is RX
        self.uart = UART(1, baudrate=baud, tx=7, rx=6, timeout=10)
        return self.uart

    def _cmd_bridge(self, args):
        """Pure transparent bridge between USB Serial and SAO UART."""
        baud = 115200
        if args:
            try:
                baud = int(args[0])
            except ValueError:
                self.shell._write("Invalid baud rate.")
                return

        w = self.shell._write
        w(f"Entering UART Bridge Mode ({baud} baud).")
        w("Data from USB goes to SAO UART, data from SAO UART goes to USB.")
        w("Press Ctrl+X to exit.")

        uart = self._init_uart(baud)
        
        try:
            import uselect
            poll = uselect.poll()
            poll.register(sys.stdin, uselect.POLLIN)
            poll.register(uart, uselect.POLLIN)
            
            while True:
                # Check for events with short timeout
                events = poll.poll(50)
                for obj, ev in events:
                    if obj == sys.stdin:
                        # Read from USB
                        char = sys.stdin.read(1)
                        if char == '\x18': # Ctrl+X
                            raise KeyboardInterrupt
                        uart.write(char)
                    else:
                        # Read from UART
                        data = uart.read()
                        if data:
                            # Write raw bytes to stdout
                            sys.stdout.write(data)
        except (KeyboardInterrupt, Exception) as e:
            if not isinstance(e, KeyboardInterrupt):
                w(f"\r\nBridge Error: {e}")
        
        w("\r\nBridge Mode exited.")
        if self.uart:
            self.uart.deinit()
            self.uart = None

    def _cmd_terminal(self, args):
        """UART terminal with local echo and line ending options."""
        # For now, just an alias to bridge or a slightly more 'helpful' version
        # We'll implement a more featured one if needed.
        self._cmd_bridge(args)

