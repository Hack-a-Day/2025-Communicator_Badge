"""Nametag commands: nametag get, set."""


class NametagCommands:
    """Registers the 'nametag' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        self.badge = shell.badge
        shell.register_group(
            "nametag",
            {
                "get": (self._cmd_get, "Show nametag info"),
                "set": (self._cmd_set, "Set alias: nametag set <text>"),
            },
            "Badge nametag / alias"
        )

    def _cmd_get(self, args):
        w = self.shell._write
        try:
            alias = self.badge.config.get("alias", b"").decode().strip()
            nametag = self.badge.config.get("nametag", b"").decode().strip()
            show_image = self.badge.config.get("nametag_show_image", b"false").decode().strip()
            image = self.badge.config.get("nametag_image", b"").decode().strip()
            w("Alias:      " + (alias if alias else "(not set)"))
            w("Nametag:    " + (nametag if nametag else "(not set)"))
            w("Show Image: " + show_image)
            w("Image:      " + (image if image else "(none)"))
        except Exception as e:
            w("Error: " + str(e))

    def _cmd_set(self, args):
        w = self.shell._write
        if not args:
            w("Usage: nametag set <alias_text>")
            return
        alias = " ".join(args)[:10]  # Max 10 chars per badge convention
        self.badge.config.set("alias", alias)
        self.badge.config.flush()
        w("Alias set to: " + alias)
