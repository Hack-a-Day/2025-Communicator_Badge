"""Sub-GHz commands: subghz rx, tx, scan, record, replay.

`play` remains as a compatibility alias for replay.
"""

from radio.signal_player import SignalPlayer
from radio.signal_recorder import SignalRecorder

class SubGhzCommands:
    """Registers the 'subghz' command group for OOK replay."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge
        self.recorder = SignalRecorder(self.badge.lora)
        self.player = SignalPlayer(self.badge.lora)
        shell.register_group(
            "subghz",
            {
                "rx": (self._cmd_rx, "Receive raw Sub-GHz (OOK): subghz rx <freq>"),
                "tx": (self._cmd_tx, "Transmit raw Sub-GHz (OOK): subghz tx <freq> <hex_data>"),
                "scan": (self._cmd_scan, "Real-time frequency analyzer: subghz scan"),
                "record": (
                    self._cmd_record,
                    "Record OOK to file: subghz record <freq> <duration_s> <file.sub>",
                ),
                "play": (
                    self._cmd_play,
                    "Alias for replay: subghz play <file.sub> [repeat] [freq]",
                ),
                "replay": (
                    self._cmd_replay,
                    "Replay capture file: subghz replay <file.sub> [repeat] [freq]",
                ),
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
        if len(args) < 3:
            w("Usage: subghz record <freq> <duration_s> <file.sub>")
            return

        try:
            freq = float(args[0])
            duration_s = float(args[1])
            path = args[2]
        except ValueError:
            w("Error: invalid frequency or duration")
            return

        w("Recording from %.3f MHz for %.1f s to %s" % (freq, duration_s, path))
        try:
            count = self.recorder.record(
                frequency_mhz=freq,
                duration_s=duration_s,
                path=path,
                check_interrupt=self.shell.check_interrupt,
            )
            w("Saved %d packet(s)." % count)
        except Exception as e:
            w("Error: " + str(e))

    def _cmd_play(self, args):
        w = self.shell._write
        if not args:
            w("Usage: subghz play <file.sub> [repeat] [freq]")
            w("Compatibility: subghz play <freq> <file.sub> [repeat]")
            return

        # Compatibility mode for old syntax: play <freq> <file> [repeat]
        try:
            freq = float(args[0])
            if len(args) < 2:
                w("Usage: subghz play <freq> <file.sub> [repeat]")
                return
            path = args[1]
            repeat = int(args[2]) if len(args) > 2 else 1
        except ValueError:
            # Canonical syntax: play <file> [repeat] [freq]
            path = args[0]
            try:
                repeat = int(args[1]) if len(args) > 1 else 1
                freq = float(args[2]) if len(args) > 2 else None
            except ValueError:
                w("Error: invalid repeat or frequency")
                return

        try:
            sent = self.player.replay(path=path, repeat=repeat, frequency_mhz=freq)
            w("Playback complete. Sent %d packet(s)." % sent)
        except Exception as e:
            w("Error: " + str(e))

    def _cmd_replay(self, args):
        w = self.shell._write
        if not args:
            w("Usage: subghz replay <file.sub> [repeat] [freq]")
            return

        path = args[0]
        try:
            repeat = int(args[1]) if len(args) > 1 else 1
            freq = float(args[2]) if len(args) > 2 else None
        except ValueError:
            w("Error: invalid repeat or frequency")
            return

        try:
            sent = self.player.replay(path=path, repeat=repeat, frequency_mhz=freq)
            w("Replay complete. Sent %d packet(s)." % sent)
        except Exception as e:
            w("Error: " + str(e))
