"""Config commands: config list, get, set, save, broadcast.

Manages the badge's persistent key-value configuration stored in btree on flash.
"""


class ConfigCommands:
    """Registers the 'config' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge
        shell.register_group(
            "config",
            {
                "list": (self._cmd_list, "Show all config key=value pairs"),
                "get": (self._cmd_get, "Get a config value: config get <key>"),
                "set": (self._cmd_set, "Set a config value: config set <key> <value>"),
                "save": (self._cmd_save, "Flush config to flash"),
                "broadcast": (self._cmd_broadcast, "Broadcast signed config override"),
            },
            "Badge configuration (btree on flash)"
        )

    def _cmd_list(self, args):
        """List all config key=value pairs."""
        w = self.shell._write
        try:
            items = list(self.badge.config.db.items())
            if not items:
                w("(no config entries)")
                return
            items.sort()
            for key, value in items:
                k = key.decode() if isinstance(key, bytes) else str(key)
                v = value.decode() if isinstance(value, bytes) else str(value)
                w("  " + k + " = " + v)
        except Exception as e:
            w("Error reading config: " + str(e))

    def _cmd_get(self, args):
        """Get a single config value."""
        w = self.shell._write
        if not args:
            w("Usage: config get <key>")
            return
        key = args[0]
        value = self.badge.config.get(key)
        if value is None:
            w("Key not found: " + key)
        else:
            v = value.decode() if isinstance(value, bytes) else str(value)
            w(key + " = " + v)

    def _cmd_set(self, args):
        """Set a config value in memory (not flushed until 'config save')."""
        w = self.shell._write
        if len(args) < 2:
            w("Usage: config set <key> <value>")
            return
        key = args[0]
        value = " ".join(args[1:])
        self.badge.config.set(key, value)
        w("Set " + key + " = " + value)
        w("(Run 'config save' to persist to flash)")

    def _cmd_save(self, args):
        """Flush config to flash storage."""
        self.badge.config.flush()
        self.shell._write("Config saved to flash.")

    def _cmd_broadcast(self, args):
        """Broadcast a signed config override over LoRa.

        Usage: config broadcast <key> <value>
        Requires a private key on the badge.
        """
        w = self.shell._write
        if len(args) < 2:
            w("Usage: config broadcast <key> <value>")
            return
        key = args[0]
        value = " ".join(args[1:])

        if self.badge.crypto.private_key is None:
            w("Error: No private key on this badge. Cannot sign broadcasts.")
            return

        try:
            import struct
            kv_bytes = struct.pack("!20s80s", key.encode(), value.encode())
            signature = self.badge.crypto.sign(kv_bytes)
            check = self.badge.crypto.verify(kv_bytes, signature)
            if not check:
                w("Error: Signature self-check failed.")
                return

            # Try to send via badgenet
            try:
                from net.net import send, BROADCAST_ADDRESS
                from net.protocols import NetworkFrame, Protocol

                CONFIG_OVERRIDE = Protocol(port=4, name="CONFIG_OVERRIDE", structdef="!128s20s80s")
                send(
                    NetworkFrame().set_fields(
                        protocol=CONFIG_OVERRIDE,
                        destination=BROADCAST_ADDRESS,
                        ttl=15,
                        payload=(signature, key.encode(), value.encode()),
                    )
                )
                w("Broadcast sent: " + key + " = " + value)
            except ImportError:
                w("Signed OK, but network stack not available for broadcast.")
        except Exception as e:
            w("Error: " + str(e))
