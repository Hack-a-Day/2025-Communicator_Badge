"""Chat commands: chat send, chat history, chat channel.

Wraps the existing ChatApp instance for serial-based chat access.
ChatApp is the definitive owner of chat state; this is a thin CLI wrapper.
"""


class ChatCommands:
    """Registers the 'chat' command group with the shell."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "chat",
            {
                "send": (self._cmd_send, 'Send message: chat send <text>'),
                "history": (self._cmd_history, "Show chat history"),
                "channel": (self._cmd_channel, "Get/set channel: chat channel [freq] [topic]"),
                "status": (self._cmd_status, "Show chat app status"),
            },
            "LoRa text chat (wraps ChatApp)"
        )

    def _get_chat(self):
        app = self.shell.find_app("Chat")
        return app

    def _cmd_send(self, args):
        w = self.shell._write
        chat = self._get_chat()
        if not chat:
            w("Error: ChatApp not running.")
            return
        if not args:
            w("Usage: chat send <message_text>")
            return

        message = " ".join(args)
        # Use ChatApp's send mechanism
        try:
            from net.net import send, BROADCAST_ADDRESS
            from net.protocols import NetworkFrame

            # Build the same TEXT_CHAT frame ChatApp would
            alias = self.shell.badge.config.get("alias", b"").decode().strip()
            if not alias:
                alias = "cli"

            # Check if badge has private key for signed messages
            if self.shell.badge.crypto.private_key is not None:
                chat._compose_signed_message(message, alias)
                w("Sent (signed): " + message)
            else:
                chat._compose_message(message, alias)
                w("Sent: " + message)
        except (ImportError, AttributeError):
            # Fallback: just log that we would send
            w("(Network stack not available — message not sent)")
            w("Would send: " + message)

    def _cmd_history(self, args):
        w = self.shell._write
        chat = self._get_chat()
        if not chat:
            w("Error: ChatApp not running.")
            return

        channel = chat.active_channel
        messages = chat.channels.get(channel, [])
        w("Channel %02d:%02d (%d messages)" % (chat.active_freq, chat.active_topic, len(messages)))
        w("---")
        if not messages:
            w("(no messages)")
            return
        for msg in messages:
            src = msg.source_alias if msg.source_alias else "%x" % msg.source_addr
            prefix = "[✓] " if msg.signed else ""
            w("  %s<%s> %s" % (prefix, src, msg.text))

    def _cmd_channel(self, args):
        w = self.shell._write
        chat = self._get_chat()
        if not chat:
            w("Error: ChatApp not running.")
            return

        if not args:
            w("Current channel: %02d:%02d" % (chat.active_freq, chat.active_topic))
            w("Freq slot: %d  Topic: %d" % (chat.active_freq, chat.active_topic))
            return

        try:
            freq = int(args[0])
            topic = int(args[1]) if len(args) > 1 else chat.active_topic
            chat.active_freq = freq
            chat.active_topic = topic
            chat.active_channel = freq * 100 + topic
            # Ensure channel buffer exists
            if chat.active_channel not in chat.channels:
                from collections import deque
                chat.channels[chat.active_channel] = deque([], chat.channel_buffer_len)
            w("Switched to channel %02d:%02d" % (freq, topic))
        except (ValueError, IndexError) as e:
            w("Usage: chat channel <freq_slot> [topic_num]")

    def _cmd_status(self, args):
        w = self.shell._write
        chat = self._get_chat()
        if not chat:
            w("Error: ChatApp not running.")
            return

        w("Chat Status:")
        w("  Active Channel: %02d:%02d" % (chat.active_freq, chat.active_topic))
        w("  My Alias:       " + chat.my_alias)
        w("  Channels:")
        for ch_id, msgs in sorted(chat.channels.items()):
            freq = ch_id // 100
            topic = ch_id % 100
            w("    %02d:%02d  %d messages" % (freq, topic, len(msgs)))
