"""Net commands: net address, ping, nodes, send, sniff.

Badge-specific network commands built on the BadgeNet stack.
"""


class NetCommands:
    """Registers the 'net' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge
        shell.register_group(
            "net",
            {
                "address": (self._cmd_address, "Show my network address"),
                "ping": (self._cmd_ping, "Ping a badge: net ping [address]"),
                "nodes": (self._cmd_nodes, "List seen network nodes"),
                "send": (self._cmd_send, "Send raw frame: net send <port> <hex>"),
                "sniff": (self._cmd_sniff, "Promiscuous capture (Ctrl+C to stop)"),
            },
            "BadgeNet network stack"
        )

    def _cmd_address(self, args):
        """Show my 4-byte network address."""
        w = self.shell._write
        try:
            from net.net import MY_ADDRESS
            w("My address: %08x" % MY_ADDRESS)
        except ImportError:
            w("My address: (network stack not available)")

    def _cmd_ping(self, args):
        """Send a PING to a badge and wait for PONG response.

        Usage: net ping [address_hex]
        If no address given, broadcasts a ping.
        """
        w = self.shell._write

        try:
            from net.net import send, MY_ADDRESS, BROADCAST_ADDRESS
            from net.protocols import NetworkFrame, Protocol
        except ImportError:
            w("Network stack not available.")
            return

        PING = Protocol(port=1, name="PING", structdef="!IB")

        if args:
            try:
                dest = int(args[0], 16)
            except ValueError:
                w("Error: Invalid hex address: " + args[0])
                return
        else:
            dest = BROADCAST_ADDRESS

        w("Pinging %08x..." % dest)

        try:
            send(
                NetworkFrame().set_fields(
                    protocol=PING,
                    destination=dest,
                    ttl=7,
                    payload=(MY_ADDRESS, 0),
                )
            )
            w("PING sent. PONGs will appear in 'lora rx' or 'net sniff'.")
        except Exception as e:
            w("Error sending ping: " + str(e))

    def _cmd_nodes(self, args):
        """List all nodes seen on the network."""
        w = self.shell._write
        try:
            from net.net import badgenet
            nodes = badgenet.seen_nodes
            if not nodes:
                w("No nodes seen yet.")
                return
            w("Seen nodes:")
            for addr in sorted(nodes):
                w("  %08x" % addr)
        except ImportError:
            w("Network stack not available.")

    def _cmd_send(self, args):
        """Send a raw frame on a given port.

        Usage: net send <port_num> <hex_payload>
        """
        w = self.shell._write
        if len(args) < 2:
            w("Usage: net send <port> <hex_payload>")
            return

        try:
            port = int(args[0])
        except ValueError:
            w("Error: Invalid port number: " + args[0])
            return

        hex_str = "".join(args[1:])
        try:
            data = bytes.fromhex(hex_str)
        except ValueError:
            w("Error: Invalid hex string: " + hex_str)
            return

        try:
            from net.net import send, BROADCAST_ADDRESS
            from net.protocols import NetworkFrame, Protocol

            proto = Protocol(port=port, name="CLI_RAW", structdef="!" + str(len(data)) + "s")
            send(
                NetworkFrame().set_fields(
                    protocol=proto,
                    destination=BROADCAST_ADDRESS,
                    ttl=7,
                    payload=(data,),
                )
            )
            w("Sent %d bytes on port %d" % (len(data), port))
        except ImportError:
            w("Network stack not available.")
        except Exception as e:
            w("Error: " + str(e))

    def _cmd_sniff(self, args):
        """Promiscuous packet capture. Ctrl+C to stop.

        Uses the same promiscuous_queue as BadgeShark.
        """
        w = self.shell._write
        w("Sniffing packets... (Ctrl+C to stop)")

        try:
            from net.net import capture_all_packets, badgenet
            capture_all_packets(True)
        except ImportError:
            w("(BadgeNet not available)")
            return

        self.shell._streaming = True
        count = 0
        try:
            while self.shell._streaming:
                while badgenet.promiscuous_queue:
                    frame = badgenet.promiscuous_queue.popleft()
                    count += 1
                    try:
                        frame.deserialize(badgenet.protocols)
                        if frame.fields_set:
                            w("#%d [%04x] %08x->%08x port=%d %s" % (
                                count,
                                frame.seq_num,
                                frame.source,
                                frame.destination,
                                frame.port,
                                frame.protocol.name if frame.protocol else "?",
                            ))
                        elif frame.frame:
                            w("#%d [raw] %s" % (count, frame.frame.hex()))
                    except Exception:
                        if frame.frame:
                            w("#%d [raw] %s" % (count, frame.frame.hex()))
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
            w("Captured %d packets." % count)
