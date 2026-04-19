"""Peers commands: peers list, nearest, clear.

Thin CLI wrapper around the PeersApp instance.
"""

import time


class PeersCommands:
    """Registers the 'peers' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "peers",
            {
                "list": (self._cmd_list, "List known peers"),
                "nearest": (self._cmd_nearest, "Show nearest peer by RSSI"),
                "clear": (self._cmd_clear, "Forget all peers"),
            },
            "Peer tracking"
        )

    def _get_peers_app(self):
        app = self.shell.find_app("Peers")
        if app is None:
            try:
                from apps.peers_app import PeersApp
                for a in PeersApp.all_apps:
                    if isinstance(a, PeersApp):
                        return a
            except ImportError:
                pass
        return app

    def _cmd_list(self, args):
        w = self.shell._write
        peers_app = self._get_peers_app()
        if not peers_app:
            w("Error: Peers app not running.")
            return
        peers = peers_app.get_peers()
        if not peers:
            w("No peers seen yet.")
            return
        w("%-12s %-8s %-6s %-6s %s" % ("Address", "RSSI", "SNR", "Count", "Last Seen"))
        w("-" * 56)
        for addr, info in sorted(peers.items()):
            ago = time.time() - info["last_seen"]
            if ago < 60:
                age_str = "%ds ago" % int(ago)
            elif ago < 3600:
                age_str = "%dm ago" % int(ago / 60)
            else:
                age_str = "%dh ago" % int(ago / 3600)
            w("%08x    %-8.1f %-6.1f %-6d %s" % (
                addr, info["rssi"], info["snr"], info["count"], age_str
            ))
        w("(%d peers total)" % len(peers))

    def _cmd_nearest(self, args):
        w = self.shell._write
        peers_app = self._get_peers_app()
        if not peers_app:
            w("Error: Peers app not running.")
            return
        nearest = peers_app.nearest_peer()
        if nearest is None:
            w("No peers seen yet.")
            return
        info = peers_app.get_peers()[nearest]
        w("Nearest peer: %08x (RSSI=%.1f, SNR=%.1f)" % (nearest, info["rssi"], info["snr"]))

    def _cmd_clear(self, args):
        w = self.shell._write
        peers_app = self._get_peers_app()
        if not peers_app:
            w("Error: Peers app not running.")
            return
        count = len(peers_app.get_peers())
        peers_app.clear()
        w("Cleared %d peers." % count)
