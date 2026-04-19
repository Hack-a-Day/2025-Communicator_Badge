"""Talks commands: talks list, talks now.

Reads schedule data from the Talks app or schedule.csv directly.
"""


class TalksCommands:
    """Registers the 'talks' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "talks",
            {
                "list": (self._cmd_list, "Show full schedule"),
                "now": (self._cmd_now, "Show current/next talk"),
            },
            "Conference schedule"
        )

    def _cmd_list(self, args):
        """List all talks from the schedule."""
        w = self.shell._write

        # Try to get from the running Talks app first
        talks_app = self.shell.find_app("Talks")
        if talks_app and hasattr(talks_app, "talks") and talks_app.talks:
            talks = talks_app.talks
            for t in talks:
                w("%s %s [%s] %s — %s" % (t.day, t.time, t.stage, t.title, t.speaker))
            w("(%d talks total)" % len(talks))
            return

        # Fallback: parse schedule.csv directly
        try:
            with open("schedule.csv", "r") as f:
                count = 0
                for line in f:
                    parts = line.strip().split("$")
                    if len(parts) >= 5:
                        w("%s %s [%s] %s — %s" % (parts[0], parts[1], parts[2], parts[3], parts[4]))
                        count += 1
                w("(%d talks)" % count)
        except OSError:
            w("schedule.csv not found.")

    def _cmd_now(self, args):
        """Show the current or next upcoming talk."""
        w = self.shell._write
        w("(Time-based filtering requires RTC. Showing all talks instead.)")
        self._cmd_list(args)
