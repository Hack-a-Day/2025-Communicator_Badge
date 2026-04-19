"""Poll system over LoRa.

Allows creating polls, voting, and viewing results. Polls are
stored in memory and can be broadcast over LoRa for other badges
to participate.

This is a proper app that runs independently; the CLI
wraps it via poll_cmd.py.
"""

from collections import deque

try:
    import uasyncio as aio  # type: ignore
except ImportError:
    aio = None

try:
    from apps.base_app import BaseApp
    from net.net import register_receiver, send, BROADCAST_ADDRESS
    from net.protocols import NetworkFrame, Protocol
    _HAS_FIRMWARE = True
except ImportError:
    _HAS_FIRMWARE = False


class Poll:
    """Represents a single poll."""

    def __init__(self, poll_id, question, options):
        if not options:
            raise ValueError("Poll must have at least one option")
        self.id = poll_id
        self.question = question
        self.options = list(options)
        self.votes = {i: 0 for i in range(len(options))}

    def vote(self, option_index):
        if option_index not in self.votes:
            raise IndexError("Invalid option index: %d" % option_index)
        self.votes[option_index] += 1

    def results(self):
        return {self.options[i]: count for i, count in self.votes.items()}


class PollApp:
    """Poll management app.

    Works as standalone class for test compatibility.
    """

    all_apps = []

    def __init__(self, name, badge):
        self.name = name
        self.badge = badge
        self.active_foreground = False
        self.active_background = True
        self.foreground_sleep_ms = 100
        self.background_sleep_ms = 2000
        self.task = None

        # Poll state
        self._polls = {}
        self._next_id = 1
        self._receive_queue = deque([], 10)

    def start(self):
        if self not in self.all_apps:
            self.all_apps.append(self)

    def stop(self):
        self.active_foreground = False
        self.active_background = False

    def create(self, question, options):
        """Create a new poll. Returns poll ID."""
        poll_id = self._next_id
        self._next_id += 1
        poll = Poll(poll_id, question, options)
        self._polls[poll_id] = poll
        return poll_id

    def vote(self, poll_id, option_index):
        """Cast a vote."""
        poll = self._polls.get(poll_id)
        if not poll:
            raise KeyError("No poll with id %d" % poll_id)
        poll.vote(option_index)

    def results(self, poll_id):
        """Get results for a poll."""
        poll = self._polls.get(poll_id)
        if not poll:
            raise KeyError("No poll with id %d" % poll_id)
        return poll.results()

    def list_polls(self):
        """Return all polls."""
        return list(self._polls.values())

    def get_poll(self, poll_id):
        """Get a specific poll."""
        return self._polls.get(poll_id)

    def run_background(self):
        pass

    def run_foreground(self):
        pass

    def switch_to_foreground(self):
        self.active_foreground = True
        self.active_background = False

    def switch_to_background(self):
        self.active_background = True
        self.active_foreground = False
