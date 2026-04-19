"""Sub-GHz commands: subghz rx, subghz tx, scan, record, play."""

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
                "scan": (self._cmd_scan, "Real-time frequency analyzer: subghz scan"),
                "record": (self._cmd_record, "Record OOK to file: subghz record <freq> <file.ook>"),
                "play": (self._cmd_play, "Play recorded OOK: subghz play <freq> <file.ook>"),
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

    def _cmd_scan(self, args):
        """Real-time RSSI waterfall."""
        w = self.shell._write
        w_raw = self.shell._write_raw
        import time
        
        w("Starting Sub-GHz Scanner. Ctrl+C to stop.")
        self.shell._streaming = True
        
        freqs = [902.0 + i*1.0 for i in range(26)] # 902-928 MHz
        
        try:
            while self.shell._streaming:
                line = ""
                for f in freqs:
                    rssi = self.badge.lora.get_rssi(f)
                    # Convert RSSI (-120 to -20) to 0-10 scale
                    val = max(0, min(9, int((rssi + 120) / 10)))
                    line += " .:ioOMW#@"[val]
                w_raw("\r" + line)
                time.sleep(0.1)
                self.shell.check_interrupt()
            w("\nScanner stopped.")
        except KeyboardInterrupt:
            w("\nScanner stopped.")
        finally:
            self.shell._streaming = False

    def _cmd_record(self, args):
        w = self.shell._write
        w_raw = self.shell._write_raw
        if len(args) < 2:
            w("Usage: subghz record <freq> <file.ook>")
            return
            
        freq = float(args[0])
        path = args[1]
        
        w(f"Recording from {freq} MHz to {path}. Ctrl+C to stop.")
        self.shell._streaming = True
        
        try:
            with open(path, "wb") as f:
                while self.shell._streaming:
                    data = self.badge.lora.rx_ook(freq, timeout_ms=100)
                    if data:
                        f.write(data)
                        w_raw(".")
                    self.shell.check_interrupt()
            w("\nRecording saved.")
        except Exception as e:
            w("\nError: " + str(e))
        finally:
            self.shell._streaming = False

    def _cmd_play(self, args):
        w = self.shell._write
        if len(args) < 2:
            w("Usage: subghz play <freq> <file.ook>")
            return
            
        freq = float(args[0])
        path = args[1]
        
        try:
            with open(path, "rb") as f:
                data = f.read()
            w(f"Playing {len(data)} bytes from {path} on {freq} MHz...")
            self.badge.lora.tx_ook(freq, data)
            w("Playback complete.")
        except Exception as e:
            w("Error: " + str(e))
