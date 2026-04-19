"""LoRa commands: lora info, freq, tx, rx, rx_raw, chat.

Maps to the Flipper's 'subghz' command group but uses badge-specific
LoRa (SX1262) hardware and BadgeNet protocols.
"""


class LoraCommands:
    """Registers the 'lora' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge
        shell.register_group(
            "lora",
            {
                "info": (self._cmd_info, "Radio configuration and status"),
                "freq": (self._cmd_freq, "Get/set freq slot: lora freq [slot]"),
                "tx": (self._cmd_tx, "Transmit raw hex: lora tx <hex>"),
                "rx": (self._cmd_rx, "Receive decoded frames (Ctrl+C to stop)"),
                "rx_raw": (self._cmd_rx_raw, "Receive raw hex frames (Ctrl+C to stop)"),
                "chat": (self._cmd_chat, "LoRa chat: lora chat [slot]"),
            },
            "LoRa radio (SX1262)"
        )

    def _cmd_info(self, args):
        """Show current radio configuration and signal info."""
        w = self.shell._write
        lora = self.badge.lora
        w("LoRa Radio (SX1262)")
        w("  Freq Slot:       %d" % lora.freq_slot)
        w("  Frequency:       %.3f MHz" % lora.frequency)
        w("  Bandwidth:       %.1f kHz" % lora.bandwidth)
        w("  Spreading Factor: %d" % lora.spreading_factor)
        w("  Coding Rate:     4/%d" % lora.coding_rate)
        w("  Preamble Length: %d" % lora.preamble_length)
        w("  TX Power:        %d dBm" % lora.tx_power)
        w("  Sync Word:       0x%02x" % lora.sync_word)
        w("  CRC:             %s" % ("enabled" if lora.crc else "disabled"))
        w("  Last RSSI:       %.1f dBm" % lora.last_rssi)
        w("  Last SNR:        %.1f dB" % lora.last_snr)

    def _cmd_freq(self, args):
        """Get or set the frequency slot (1-52)."""
        w = self.shell._write
        lora = self.badge.lora

        if not args:
            w("Current: slot %d (%.3f MHz)" % (lora.freq_slot, lora.frequency))
            return

        try:
            slot = int(args[0])
            new_freq = lora.set_freq_slot(slot)
            w("Set to slot %d (%.3f MHz)" % (slot, new_freq))
        except ValueError as e:
            w("Error: " + str(e))

    def _cmd_tx(self, args):
        """Transmit raw hex bytes over LoRa."""
        w = self.shell._write
        if not args:
            w("Usage: lora tx <hex_string>")
            w("Example: lora tx 48454c4c4f")
            return

        hex_str = "".join(args)  # Join in case of spaces
        try:
            data = bytes.fromhex(hex_str)
        except ValueError:
            w("Error: Invalid hex string: " + hex_str)
            return

        try:
            # Try async send via the radio
            import uasyncio as asyncio
            asyncio.get_event_loop().run_until_complete(self.badge.lora.send(data))
            w("Sent %d bytes" % len(data))
        except ImportError:
            # Mock / CPython fallback — call send directly if it's synchronous
            try:
                import asyncio
                asyncio.get_event_loop().run_until_complete(self.badge.lora.send(data))
                w("Sent %d bytes" % len(data))
            except Exception as e:
                w("Send error: " + str(e))

    def _cmd_rx(self, args):
        """Receive and display decoded frames. Ctrl+C to stop.

        Uses the promiscuous queue from BadgeNet (same as BadgeShark).
        """
        w = self.shell._write
        w("Listening for LoRa frames... (Ctrl+C to stop)")

        try:
            from net.net import capture_all_packets, badgenet
            from net.protocols import NetworkFrame
            capture_all_packets(True)
        except ImportError:
            w("(BadgeNet not available — showing mock output)")
            self._mock_rx_loop()
            return

        self.shell._streaming = True
        try:
            while self.shell._streaming:
                while badgenet.promiscuous_queue:
                    frame = badgenet.promiscuous_queue.popleft()
                    try:
                        frame.deserialize(badgenet.protocols)
                        if frame.fields_set:
                            w("[%04x] %08x -> %08x port=%d proto=%s: %s RSSI=%.1f" % (
                                frame.seq_num,
                                frame.source,
                                frame.destination,
                                frame.port,
                                frame.protocol.name if frame.protocol else "?",
                                repr(frame.payload),
                                self.badge.lora.get_rssi(),
                            ))
                        elif frame.frame:
                            w("[raw] " + frame.frame.hex())
                    except Exception as e:
                        w("[decode error] " + str(e))
                try:
                    import uasyncio
                    uasyncio.sleep_ms(50)
                except ImportError:
                    import time
                    time.sleep(0.05)
        finally:
            try:
                capture_all_packets(False)
            except Exception:
                pass
            self.shell._streaming = False

    def _cmd_rx_raw(self, args):
        """Receive and display raw hex frames. Ctrl+C to stop."""
        w = self.shell._write
        w("Listening for raw LoRa frames... (Ctrl+C to stop)")

        try:
            from net.net import capture_all_packets, badgenet
            capture_all_packets(True)
        except ImportError:
            w("(BadgeNet not available — showing mock output)")
            self._mock_rx_loop()
            return

        self.shell._streaming = True
        try:
            while self.shell._streaming:
                while badgenet.promiscuous_queue:
                    frame = badgenet.promiscuous_queue.popleft()
                    if frame.frame:
                        w("RX: " + frame.frame.hex() + "  RSSI=%.1f SNR=%.1f" % (
                            self.badge.lora.get_rssi(),
                            self.badge.lora.get_snr(),
                        ))
                try:
                    import uasyncio
                    uasyncio.sleep_ms(50)
                except ImportError:
                    import time
                    time.sleep(0.05)
        finally:
            try:
                capture_all_packets(False)
            except Exception:
                pass
            self.shell._streaming = False

    def _cmd_chat(self, args):
        """Interactive LoRa chat. Usage: lora chat [slot]

        Uses the existing ChatApp's TEXT_CHAT protocol. Messages are shared
        between the LCD chat interface and this serial CLI.
        """
        w = self.shell._write

        # Optionally switch freq slot
        if args:
            try:
                slot = int(args[0])
                self.badge.lora.set_freq_slot(slot)
                w("Switched to freq slot %d" % slot)
            except ValueError as e:
                w("Error: " + str(e))
                return

        # Find the ChatApp instance
        chat_app = self.shell.find_app("Chat")
        if chat_app is None:
            w("ChatApp not running. Cannot join chat.")
            return

        w("Chat mode (Ctrl+C to exit). Type a message and press Enter to send.")
        w("Channel: %02d:%02d" % (chat_app.active_freq, chat_app.active_topic))

        # Show recent history
        channel = chat_app.active_channel
        messages = chat_app.channels.get(channel, [])
        for msg in messages:
            src = msg.source_alias if msg.source_alias else "%x" % msg.source_addr
            prefix = "[✓] " if msg.signed else ""
            w("  %s<%s> %s" % (prefix, src, msg.text))

        w("---")
        # In real firmware, this would enter a streaming loop reading stdin
        # and sending messages. For now, just indicate chat mode is available.
        w("(Chat streaming not yet implemented in this build)")

    def _mock_rx_loop(self):
        """Mock receive loop for testing without BadgeNet."""
        w = self.shell._write
        # Check if the mock lora has anything in its rx queue
        while self.badge.lora._rx_queue:
            data = self.badge.lora._rx_queue.popleft()
            w("RX: " + data.hex() + "  RSSI=%.1f SNR=%.1f" % (
                self.badge.lora.get_rssi(),
                self.badge.lora.get_snr(),
            ))
        w("(No more frames)")
