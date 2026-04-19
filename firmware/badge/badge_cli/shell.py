"""Main Shell class for the Badge CLI.

Provides Flipper Zero-style command dispatch over USB serial.
Receives the Badge object and routes space-separated commands to
registered command modules.

MicroPython-compatible: no typing imports, no advanced Python features.
"""

import sys


# ANSI Color codes for MicroPython
class Colors:
    BLUE = "\x1b[34m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    RED = "\x1b[31m"
    CYAN = "\x1b[36m"
    MAGENTA = "\x1b[35m"
    BOLD = "\x1b[1m"
    UNDERLINE = "\x1b[4m"
    END = "\x1b[0m"


# MOTD banner displayed on shell start
MOTD = r"""
 """ + Colors.CYAN + r"""_               _                   _ _ 
| |__   __ _  __| | __ _  ___    ___| (_)
| '_ \ / _` |/ _` |/ _` |/ _ \  / __| | |
| |_) | (_| | (_| | (_| |  __/ | (__| | |
|_.__/ \__,_|\__,_|\__, |\___|  \___|_|_|
                   |___/         """ + Colors.YELLOW + r"""v0.2""" + Colors.END + r"""
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
        self.check_interrupt_func = None

        # Top-level commands: name -> (handler, help_text)
        self._commands = {}
        # Grouped commands: group_name -> {subcmd: (handler, help_text)}
        self._groups = {}
        # Group descriptions: group_name -> description
        self._group_descriptions = {}

        # Register built-in command modules
        self._init_commands()
        
        # Current working directory
        self.cwd = "/"
        
        # History management
        self._history = []
        self._history_idx = -1
        self._temp_line = ""

    def check_interrupt(self):
        """Allows long-running commands to check for Ctrl+C.
        
        If check_interrupt_func is set, calls it to process I/O.
        """
        if self.check_interrupt_func:
            self.check_interrupt_func()

    def _default_write(self, data):
        """Default output: write to sys.stdout."""
        if isinstance(data, bytes):
            if hasattr(sys.stdout, 'buffer'):
                sys.stdout.buffer.write(data)
            else:
                sys.stdout.write(data.decode('latin-1'))
        else:
            sys.stdout.write(str(data))
        if hasattr(sys.stdout, "flush"):
            sys.stdout.flush()

    def _write(self, text):
        """Write a line to the output with CRLF termination."""
        self._write_raw(text + "\r\n")

    def _write_raw(self, data):
        """Write raw bytes or text without adding line termination."""
        self._write_func(data)

    def _read_raw(self, count=1):
        """Read raw bytes from stdin."""
        if hasattr(sys.stdin, 'buffer'):
            return sys.stdin.buffer.read(count)
        return sys.stdin.read(count).encode('latin-1')

    def _read_byte(self, timeout_ms=1000):
        """Read a single byte from stdin with timeout.
        
        Returns byte or None on timeout.
        """
        import time
        # Try non-blocking read if possible, else just try to read
        # This is tricky across platforms. 
        # For now, we'll try a simplified version.
        start = time.time()
        while (time.time() - start) * 1000 < timeout_ms:
            # Check for interrupt to keep shell alive
            self.check_interrupt()
            
            # In MicroPython, sys.stdin.any() might exist
            try:
                if hasattr(sys.stdin, 'any') and not sys.stdin.any():
                    time.sleep(0.01)
                    continue
            except:
                pass

            # Try reading 1 byte
            # Note: buffer.read(1) is usually blocking on CPython and MicroPython
            # To be truly non-blocking we'd need select/poll.
            # As a fallback, we'll just try to read.
            b = self._read_raw(1)
            if b:
                return b
            time.sleep(0.01)
        return None

    def _prompt(self):
        """Write the shell prompt."""
        prompt = "\r\n" + Colors.GREEN + "badge" + Colors.END + " [" + Colors.CYAN + self.cwd + Colors.END + "] >: "
        self._write_raw(prompt)

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

        # Add to history if not empty and not same as last
        if line.strip():
            if not self._history or self._history[-1] != line.strip():
                self._history.append(line.strip())
                if len(self._history) > 50:
                    self._history.pop(0)
        self._history_idx = -1

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

    def complete(self, prefix):
        """Find potential completions for a given prefix.
        
        Returns a list of matching command/group names.
        """
        matches = []
        # Check top-level commands
        for cmd in self._commands:
            if cmd.startswith(prefix):
                matches.append(cmd)
        # Check groups
        for group in self._groups:
            if group.startswith(prefix):
                matches.append(group)
        
        # If prefix contains a space, check sub-commands or paths
        if " " in prefix:
            parts = prefix.split(" ")
            group_name = parts[0]
            sub_prefix = " ".join(parts[1:])
            
            if group_name in self._groups:
                group = self._groups[group_name]
                for sub in group:
                    if sub.startswith(sub_prefix):
                        matches.append(group_name + " " + sub)
                
                # Special case for storage paths
                if group_name == "storage" and len(parts) > 1:
                    path_prefix = parts[-1]
                    dir_path = ""
                    search_term = path_prefix
                    
                    if "/" in path_prefix:
                        if path_prefix.endswith("/"):
                            dir_path = path_prefix
                            search_term = ""
                        else:
                            parts_path = path_prefix.rsplit("/", 1)
                            dir_path = parts_path[0] if parts_path[0] else "/"
                            search_term = parts_path[1]
                    
                    try:
                        import os
                        if path_prefix.startswith("/") or (len(path_prefix) > 1 and path_prefix[1] == ":"):
                            abs_dir = dir_path
                        else:
                            abs_dir = (self.cwd.rstrip("/") + "/" + dir_path).replace("//", "/").replace("\\", "/")
                        
                        for entry in os.listdir(abs_dir):
                            if entry.startswith(search_term):
                                if dir_path:
                                    full_p = (dir_path.rstrip("/") + "/" + entry).replace("//", "/").replace("\\", "/")
                                else:
                                    full_p = entry
                                matches.append(group_name + " " + parts[1] + " " + full_p)
                    except Exception as e:
                        pass
        
        return matches

    def get_history_nav(self, direction, current_line):
        """Navigate history based on direction (up/down).
        
        Returns the new line string.
        """
        if not self._history:
            return current_line
            
        if self._history_idx == -1:
            self._temp_line = current_line
            
        if direction == "up":
            if self._history_idx < len(self._history) - 1:
                self._history_idx += 1
                return self._history[-(self._history_idx + 1)]
        elif direction == "down":
            if self._history_idx > 0:
                self._history_idx -= 1
                return self._history[-(self._history_idx + 1)]
            elif self._history_idx == 0:
                self._history_idx = -1
                return self._temp_line
                
        return current_line

    def _show_group_help(self, group_name, group):
        """Show help for all sub-commands in a group."""
        desc = self._group_descriptions.get(group_name, "")
        if desc:
            self._write(group_name + ": " + desc)
        self._write("Commands:")
        # Sort sub-commands for consistent output
        subcmds = sorted(group.keys())
        for sub in subcmds:
            _, help_text = group[sub]
            self._write("  " + sub.ljust(15) + help_text)

    def _split_line(self, line):
        """Split a command line into tokens, respecting double-quoted strings.

        Args:
            line: String like 'net send 0x1234 "hello world"'
        Returns:
            List of strings like ['net', 'send', '0x1234', 'hello world']
        """
        import re
        # This regex matches either a quoted string (group 1) or a non-space
        # sequence (group 2).
        pattern = r'"([^"]*)"|(\S+)'
        matches = re.findall(pattern, line)
        # matches is a list of tuples like [('', 'net'), ('', 'send'), ('hello world', '')]
        return [m[0] if m[0] else m[1] for m in matches]

    def _init_commands(self):
        """Initialize and register all command modules."""
        # Standard system commands
        from .commands.meta import MetaCommands
        from .commands.info_cmd import InfoCommands
        from .commands.config_cmd import ConfigCommands
        from .commands.storage_cmd import StorageCommands
        from .commands.power_cmd import PowerCommands
        from .commands.log_cmd import LogCommands

        # Peripheral / Hardware commands
        from .commands.lora_cmd import LoraCommands
        from .commands.subghz_cmd import SubGhzCommands
        from .commands.wifi_cmd import WifiCommands
        from .commands.ble_cmd import BleCommands
        from .commands.net_cmd import NetCommands
        from .commands.hardware_cmd import HardwareCommands

        # High-level Badge/App commands
        from .commands.chat_cmd import ChatCommands
        from .commands.peers_cmd import PeersCommands
        from .commands.talks_cmd import TalksCommands
        from .commands.badusb_cmd import BadUsbCommands
        from .commands.crypto_cmd import CryptoCommands
        from .commands.ctf_cmd import CTFCommands
        from .commands.poll_cmd import PollCommands
        from .commands.nametag_cmd import NametagCommands
        from .commands.loader_cmd import LoaderCommands

        # Instantiate (these auto-register via self.shell.register_group/command)
        MetaCommands(self)
        InfoCommands(self)
        ConfigCommands(self)
        StorageCommands(self)
        PowerCommands(self)
        LogCommands(self)

        LoraCommands(self)
        SubGhzCommands(self)
        WifiCommands(self)
        BleCommands(self)
        NetCommands(self)
        HardwareCommands(self)

        ChatCommands(self)
        PeersCommands(self)
        TalksCommands(self)
        BadUsbCommands(self)
        CryptoCommands(self)
        CTFCommands(self)
        PollCommands(self)
        NametagCommands(self)
        LoaderCommands(self)

    def find_app(self, name_prefix):
        """Helper to find a running app by name prefix.
        
        Args:
            name_prefix: App name start (e.g. 'Chat')
        Returns:
            App instance or None
        """
        try:
            from apps.base_app import BaseApp
            for app in BaseApp.all_apps:
                if app.name.startswith(name_prefix):
                    return app
        except ImportError:
            pass
        return None
