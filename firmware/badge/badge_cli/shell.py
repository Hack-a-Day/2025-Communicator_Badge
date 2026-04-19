"""Main Shell class for the Badge CLI.

Provides Flipper Zero-style command dispatch over USB serial.
Receives the Badge object and routes space-separated commands to
registered command modules.

MicroPython-compatible: no typing imports, no advanced Python features.
"""

import sys


# MOTD banner displayed on shell start
MOTD = r"""
 _               _                   _ _ 
| |__   __ _  __| | __ _  ___    ___| (_)
| '_ \ / _` |/ _` |/ _` |/ _ \  / __| | |
| |_) | (_| | (_| | (_| |  __/ | (__| | |
|_.__/ \__,_|\__,_|\__, |\___|  \___|_|_|
                   |___/         v0.1
Type 'help' or '?' for a list of commands.
"""


class Shell:
    """Flipper Zero-style command shell for the Hackaday Communicator Badge.

    Commands are either top-level (e.g. 'help', 'echo') or grouped
    (e.g. 'lora info', 'config set').  Groups support '?' for sub-help.

    Args:
        badge: The Badge hardware object (or mock for testing).
        write_func: Optional output function. Defaults to sys.stdout.write.
                    For testing, pass a capture function.
    """

    def __init__(self, badge, write_func=None):
        self.badge = badge
        self._write_func = write_func or self._default_write
        self._streaming = False

        # Top-level commands: name -> (handler, help_text)
        self._commands = {}
        # Grouped commands: group_name -> {subcmd: (handler, help_text)}
        self._groups = {}
        # Group descriptions: group_name -> description
        self._group_descriptions = {}

        # Register built-in command modules
        self._init_commands()

    def _default_write(self, text):
        """Default output: write to sys.stdout."""
        sys.stdout.write(text)

    def _write(self, text):
        """Write a line to the output with CRLF termination."""
        self._write_func(text + "\r\n")

    def _write_raw(self, text):
        """Write raw text without adding line termination."""
        self._write_func(text)

    def _prompt(self):
        """Write the shell prompt."""
        self._write_raw("\r\nbadge >: ")

    def motd(self):
        """Print the Message of the Day banner."""
        for line in MOTD.strip().split("\n"):
            self._write(line)

    def interrupt(self):
        """Called on Ctrl+C -- stops any streaming command."""
        self._streaming = False

    # ── Command registration ──────────────────────────────────────────

    def register_command(self, name, handler, help_text=""):
        """Register a top-level command.

        Args:
            name: Command name (e.g. 'help', 'echo').
            handler: Callable taking (args: list) -> None.
            help_text: One-line description for help output.
        """
        self._commands[name] = (handler, help_text)

    def register_group(self, group_name, commands, description=""):
        """Register a command group with sub-commands.

        Args:
            group_name: Group prefix (e.g. 'lora', 'config').
            commands: Dict of {subcmd_name: (handler, help_text)}.
            description: One-line description of the group.
        """
        self._groups[group_name] = commands
        self._group_descriptions[group_name] = description

    # ── Command dispatch ──────────────────────────────────────────────

    def run_command(self, line):
        """Parse and execute a single command line.

        Args:
            line: The raw input line (without trailing newline).
        """
        tokens = self._split_line(line.strip())
        if not tokens:
            return

        cmd = tokens[0]
        args = tokens[1:]

        # Check top-level commands first
        if cmd in self._commands:
            handler, _ = self._commands[cmd]
            try:
                handler(args)
            except Exception as e:
                try:
                    import traceback
                    traceback.print_exc()
                except ImportError:
                    import sys
                    sys.print_exception(e)
                self._write("Error: " + str(e))
            return

        # Check command groups
        if cmd in self._groups:
            group = self._groups[cmd]
            if not args or args[0] == "?":
                # Show group sub-command help
                self._show_group_help(cmd, group)
                return
            subcmd = args[0]
            sub_args = args[1:]
            if subcmd in group:
                handler, _ = group[subcmd]
                try:
                    handler(sub_args)
                except Exception as e:
                    try:
                        import traceback
                        traceback.print_exc()
                    except ImportError:
                        import sys
                        sys.print_exception(e)
                    self._write("Error: " + str(e))
            else:
                self._write("Unknown sub-command: " + cmd + " " + subcmd)
                self._write("Type '" + cmd + " ?' for available sub-commands.")
            return

        # Unknown command
        self._write("Unknown command: " + cmd)
        self._write("Type 'help' or '?' for a list of commands.")

    def _show_group_help(self, group_name, group):
        """Show help for all sub-commands in a group."""
        desc = self._group_descriptions.get(group_name, "")
        if desc:
            self._write(group_name + ": " + desc)
        self._write("Commands:")
        # Sort sub-commands for consistent output
        subcmds = sorted(group.keys())
        for subcmd in subcmds:
            _, help_text = group[subcmd]
            self._write("  " + group_name + " " + subcmd.ljust(16) + help_text)

    # ── Token splitting ───────────────────────────────────────────────

    def _split_line(self, line):
        """Split a command line into tokens, honoring quoted strings."""
        tokens = []
        current = ""
        in_quotes = False
        i = 0
        while i < len(line):
            c = line[i]
            if c == '"':
                in_quotes = not in_quotes
                i += 1
                continue
            if not in_quotes and (c == " " or c == "\t"):
                if current:
                    tokens.append(current)
                    current = ""
                i += 1
                continue
            current += c
            i += 1
        if current:
            tokens.append(current)
        return tokens

    # ── Built-in command modules ──────────────────────────────────────

    def _init_commands(self):
        """Initialize all built-in command modules."""
        from badge_cli.commands.meta import MetaCommands
        from badge_cli.commands.info_cmd import InfoCommands
        from badge_cli.commands.config_cmd import ConfigCommands
        from badge_cli.commands.lora_cmd import LoraCommands
        from badge_cli.commands.net_cmd import NetCommands
        from badge_cli.commands.hardware_cmd import HardwareCommands
        from badge_cli.commands.crypto_cmd import CryptoCommands
        from badge_cli.commands.storage_cmd import StorageCommands
        from badge_cli.commands.nametag_cmd import NametagCommands
        from badge_cli.commands.loader_cmd import LoaderCommands
        from badge_cli.commands.power_cmd import PowerCommands
        from badge_cli.commands.log_cmd import LogCommands
        from badge_cli.commands.talks_cmd import TalksCommands
        from badge_cli.commands.ctf_cmd import CTFCommands
        from badge_cli.commands.poll_cmd import PollCommands
        from badge_cli.commands.peers_cmd import PeersCommands
        from badge_cli.commands.chat_cmd import ChatCommands
        from badge_cli.commands.subghz_cmd import SubGhzCommands
        from badge_cli.commands.wifi_cmd import WifiCommands
        from badge_cli.commands.ble_cmd import BleCommands
        from badge_cli.commands.badusb_cmd import BadUsbCommands

        MetaCommands(self)
        InfoCommands(self)
        ConfigCommands(self)
        LoraCommands(self)
        NetCommands(self)
        HardwareCommands(self)
        CryptoCommands(self)
        StorageCommands(self)
        NametagCommands(self)
        LoaderCommands(self)
        PowerCommands(self)
        LogCommands(self)
        TalksCommands(self)
        CTFCommands(self)
        PollCommands(self)
        PeersCommands(self)
        ChatCommands(self)
        SubGhzCommands(self)
        WifiCommands(self)
        BleCommands(self)
        BadUsbCommands(self)

    # ── App discovery ─────────────────────────────────────────────────

    def find_app(self, name_or_cls):
        """Find a running app by name (string) or class.

        Searches BaseApp.all_apps for a matching app instance.
        Returns None if not found or if BaseApp is not available.
        """
        try:
            from apps.base_app import BaseApp
            for app in BaseApp.all_apps:
                if isinstance(name_or_cls, str):
                    if app.name == name_or_cls:
                        return app
                elif isinstance(app, name_or_cls):
                    return app
        except ImportError:
            pass
        return None
