"""Poll commands: poll new, vote, results, list.

Thin CLI wrapper around the PollApp instance.
"""


class PollCommands:
    """Registers the 'poll' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "poll",
            {
                "new": (self._cmd_new, 'Create poll: poll new "Question?" opt1 opt2 ...'),
                "vote": (self._cmd_vote, "Vote: poll vote <id> <option_index>"),
                "results": (self._cmd_results, "Show results: poll results <id>"),
                "list": (self._cmd_list, "List all polls"),
            },
            "Polling system"
        )

    def _get_poll_app(self):
        app = self.shell.find_app("Polls")
        if app is None:
            try:
                from apps.poll_app import PollApp
                for a in PollApp.all_apps:
                    if isinstance(a, PollApp):
                        return a
            except ImportError:
                pass
        return app

    def _cmd_new(self, args):
        w = self.shell._write
        poll_app = self._get_poll_app()
        if not poll_app:
            w("Error: Poll app not running.")
            return
        if len(args) < 2:
            w('Usage: poll new "Question?" option1 option2 ...')
            return
        question = args[0]
        options = args[1:]
        poll_id = poll_app.create(question, options)
        w("Created poll #%d: %s" % (poll_id, question))
        for i, opt in enumerate(options):
            w("  [%d] %s" % (i, opt))

    def _cmd_vote(self, args):
        w = self.shell._write
        poll_app = self._get_poll_app()
        if not poll_app:
            w("Error: Poll app not running.")
            return
        if len(args) < 2:
            w("Usage: poll vote <poll_id> <option_index>")
            return
        try:
            poll_id = int(args[0])
            option_idx = int(args[1])
        except ValueError:
            w("Error: Invalid poll_id or option_index.")
            return
        try:
            poll_app.vote(poll_id, option_idx)
            w("Vote recorded for poll #%d, option %d." % (poll_id, option_idx))
        except (KeyError, IndexError) as e:
            w("Error: " + str(e))

    def _cmd_results(self, args):
        w = self.shell._write
        poll_app = self._get_poll_app()
        if not poll_app:
            w("Error: Poll app not running.")
            return
        if not args:
            w("Usage: poll results <poll_id>")
            return
        try:
            poll_id = int(args[0])
        except ValueError:
            w("Error: Invalid poll_id.")
            return
        try:
            results = poll_app.results(poll_id)
            poll = poll_app.get_poll(poll_id)
            w("Poll #%d: %s" % (poll_id, poll.question))
            total = sum(results.values())
            for option, count in results.items():
                pct = (count * 100 // total) if total else 0
                bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                w("  %-16s %s %d (%d%%)" % (option, bar, count, pct))
        except KeyError as e:
            w("Error: " + str(e))

    def _cmd_list(self, args):
        w = self.shell._write
        poll_app = self._get_poll_app()
        if not poll_app:
            w("Error: Poll app not running.")
            return
        polls = poll_app.list_polls()
        if not polls:
            w("No polls created yet.")
            return
        w("Polls:")
        for poll in polls:
            total = sum(poll.votes.values())
            w("  #%d: %s (%d votes, %d options)" % (
                poll.id, poll.question, total, len(poll.options)
            ))
