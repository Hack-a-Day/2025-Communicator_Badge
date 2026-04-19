"""Sub-GHz commands: subghz rx, subghz tx."""

class SubGhzCommands:
    """Registers the 'subghz' command group for OOK replay."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge
        shell.register_group(
            "subghz",
            {
                "rx": (self._cmd_rx, "Receive raw Sub-GHz (OOK): subghz rx <freq>"),
                "tx": (self._cmd_tx, "Transmit raw Sub-GHz (OOK): subghz tx <freq> <hex_data>"),
            },
            "Sub-GHz RF (OOK/FSK) operations"
        )

    def _cmd_rx(self, args):
        w = self.shell._write
        if not args:
            w("Usage: subghz rx <freq_mhz>")
            return
            
        freq = float(args[0])
        w(f"Listening on {freq} MHz OOK...")
        try:
            if hasattr(self.badge.lora, "rx_ook"):
                data = self.badge.lora.rx_ook(freq, timeout_ms=5000)
                if data:
                    w("Received: " + data.hex())
                else:
                    w("No data received.")
            else:
                w("Hardware does not support rx_ook.")
        except Exception as e:
            w("Error: " + str(e))

    def _cmd_tx(self, args):
        w = self.shell._write
        if len(args) < 2:
            w("Usage: subghz tx <freq_mhz> <hex_data>")
            return
            
        freq = float(args[0])
        try:
            data = bytes.fromhex(args[1])
        except ValueError:
            w("Invalid hex data")
            return
            
        w(f"Transmitting {len(data)} bytes on {freq} MHz OOK...")
        try:
            if hasattr(self.badge.lora, "tx_ook"):
                self.badge.lora.tx_ook(freq, data)
                w("Transmission complete.")
            else:
                w("Hardware does not support tx_ook.")
        except Exception as e:
            w("Error: " + str(e))
