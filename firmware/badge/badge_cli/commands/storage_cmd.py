"""Storage commands: storage list, read, write, stat, md5, mkdir, remove."""

import os


class StorageCommands:
    """Registers the 'storage' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "storage",
            {
                "list": (self._cmd_list, "List directory: storage list [path]"),
                "read": (self._cmd_read, "Print file contents: storage read <path>"),
                "write": (self._cmd_write, "Write to file: storage write <path> <data>"),
                "stat": (self._cmd_stat, "File info: storage stat <path>"),
                "md5": (self._cmd_md5, "MD5 hash: storage md5 <path>"),
                "mkdir": (self._cmd_mkdir, "Create directory: storage mkdir <path>"),
                "remove": (self._cmd_remove, "Delete file/dir: storage remove <path>"),
            },
            "Flash filesystem operations"
        )

    def _cmd_list(self, args):
        """List directory contents."""
        w = self.shell._write
        path = args[0] if args else "/"
        try:
            entries = os.listdir(path)
            entries.sort()
            for entry in entries:
                full_path = path.rstrip("/") + "/" + entry
                try:
                    stat = os.stat(full_path)
                    is_dir = stat[0] & 0x4000
                    size = stat[6]
                    if is_dir:
                        w("  [DIR]  " + entry + "/")
                    else:
                        w("  %6d  %s" % (size, entry))
                except OSError:
                    w("  ?      " + entry)
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_read(self, args):
        """Print file contents to serial."""
        w = self.shell._write
        if not args:
            w("Usage: storage read <path>")
            return
        path = args[0]
        try:
            with open(path, "r") as f:
                for line in f:
                    w(line.rstrip("\r\n"))
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_write(self, args):
        """Write data to a file.

        Usage: storage write <path> <data...>
        All remaining arguments are joined and written.
        """
        w = self.shell._write
        if len(args) < 2:
            w("Usage: storage write <path> <data...>")
            return
        path = args[0]
        data = " ".join(args[1:])
        try:
            with open(path, "w") as f:
                f.write(data)
            w("Wrote %d bytes to %s" % (len(data), path))
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_stat(self, args):
        """Show file/directory info."""
        w = self.shell._write
        if not args:
            w("Usage: storage stat <path>")
            return
        path = args[0]
        try:
            stat = os.stat(path)
            is_dir = stat[0] & 0x4000
            w("Path:  " + path)
            w("Type:  " + ("directory" if is_dir else "file"))
            w("Size:  %d bytes" % stat[6])
            w("Mode:  0x%04x" % stat[0])
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_md5(self, args):
        """Compute MD5 hash of a file."""
        w = self.shell._write
        if not args:
            w("Usage: storage md5 <path>")
            return
        path = args[0]
        try:
            import hashlib
            h = hashlib.md5()
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(512)
                    if not chunk:
                        break
                    h.update(chunk)
            w("MD5: " + h.hexdigest() + "  " + path)
        except ImportError:
            w("hashlib.md5 not available on this platform")
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_mkdir(self, args):
        """Create a directory."""
        w = self.shell._write
        if not args:
            w("Usage: storage mkdir <path>")
            return
        try:
            os.mkdir(args[0])
            w("Created: " + args[0])
        except OSError as e:
            w("Error: " + str(e))

    def _cmd_remove(self, args):
        """Remove a file or empty directory."""
        w = self.shell._write
        if not args:
            w("Usage: storage remove <path>")
            return
        path = args[0]
        try:
            stat = os.stat(path)
            is_dir = stat[0] & 0x4000
            if is_dir:
                os.rmdir(path)
            else:
                os.remove(path)
            w("Removed: " + path)
        except OSError as e:
            w("Error: " + str(e))
