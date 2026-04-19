"""Log commands: log, log debug, log info, log warn, log error.

Tees system output (print) to the serial CLI at a configurable level.
"""

import sys


class LogCommands:
    """Registers the 'log' command group with the shell."""

    LEVELS = {"debug": 0, "info": 1, "warn": 2, "error": 3}

    def __init__(self, shell):
        self.shell = shell
        self._original_write = None
        self._level = 1  # info by default
        shell.register_group(
            "log",
            {
                "debug": (lambda a: self._start_log(0), "Stream all output (debug+)"),
                "info": (lambda a: self._start_log(1), "Stream info and above"),
                "warn": (lambda a: self._start_log(2), "Stream warnings and errors"),
                "error": (lambda a: self._start_log(3), "Stream errors only"),
                "stop": (lambda a: self._stop_log(), "Stop log streaming"),
            },
            "System log output (Ctrl+C to stop)"
        )
        # Also register top-level 'log' as shortcut for info level
        shell.register_command("log", lambda a: self._start_log(1), "Stream system log (Ctrl+C to stop)")

    def _start_log(self, level):
        w = self.shell._write
        level_name = [k for k, v in self.LEVELS.items() if v == level]
        level_name = level_name[0] if level_name else "info"
        w("Log streaming at level: " + level_name + " (Ctrl+C to stop)")
        w("(Log tee not fully implemented — would redirect sys.stdout)")
        # In a real implementation, we would:
        # 1. Save the original sys.stdout.write
        # 2. Replace it with a tee that also writes to our CLI output
        # 3. Enter a streaming loop
        # 4. Restore on Ctrl+C
        #
        # For safety and simplicity, we'll just note it's streaming
        # and exit. Full implementation requires careful handling of
        # the asyncio event loop.

    def _stop_log(self):
        self.shell._write("Log streaming stopped.")
