"""IRC-like chat app"""

from collections import deque, namedtuple

from apps.base_app import BaseApp
from net.net import BROADCAST_ADDRESS, MY_ADDRESS, register_receiver, send
from net.protocols import NetworkFrame, Protocol
from ui.chat import Chat

MAX_MESSAGE_LEN = 100
TEXT_CHAT = Protocol(
    port=6, name="TEXT_CHAT", structdef=f"!H10s{MAX_MESSAGE_LEN}s"
)  # Text (ASCII) message to a chat channel
SIGNED_TEXT_CHAT = Protocol(
    port=7, name="SIGNED_TEXT_CHAT", structdef=f"!H10s128s90s"
)  # Text (ASCII) message to a chat channel with a signature to verify authenticity


ChatMessage = namedtuple(
    "ChatMessage", ["source_addr", "source_alias", "text", "signed"]
)

# Modes
MODE_CHANNEL_LIST = 0
MODE_CHANNEL = 1
MODE_COMPOSE = 2


class ChatApp(BaseApp):
    """Text messaging and chat."""

    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.foreground_sleep_ms = 10
        self.background_sleep_ms = 2000
        self.refresh_counter = 0
        self.refresh_counter_divider_factor = 0x0F
        self.channel_buffer_len = 100
        self.channels: dict[int, deque[ChatMessage]] = {
            1: deque([], self.channel_buffer_len)
        }
        self.active_freq: int = 9
        self.active_topic: int = 1
        self.active_channel: int = self.active_freq * 100 + self.active_topic
        self.channel_messages_updated = True
        self.my_alias = self.badge.config.get("alias").decode()

        self.page = None
        self.compose_active = False
        self.freq_picker_active = False
        self.topic_picker_active = False
        self.auto_follow = False
        try:
            self.chat_ttl = int(self.badge.config.get("chat_ttl", b"3"))
        except ValueError:
            self.chat_ttl = 2

    def _update_channel_messages(self, seek = None):
        if not self.channel_messages_updated:
            return
        messages = self.channels.get(self.active_channel)
        while seek and not messages and self.active_topic < 99 and self.active_topic > 1:
            self.active_topic += seek
            self.active_channel = self.active_freq * 100 + self.active_topic
            messages = self.channels.get(self.active_channel)
        self.page.infobar_left.set_text(f"Channel: {self.active_freq:02d}:{self.active_topic:02d}    {MY_ADDRESS:x} : {self.my_alias}")

        if not messages:
            # clear the display
            self.page.populate_message_rows([])
            return
        display_messages = []
        for message in messages:
            if(message.source_alias and message.source_alias != ''):
                source = f"{message.source_alias}"
            else:
                source = f"{message.source_addr:x}"
            display_messages.append((source, message.text))
        self.page.populate_message_rows(display_messages)
        self.channel_messages_updated = False

    def receive_message(self, message: NetworkFrame):
        if message.port == TEXT_CHAT.port:
            channel_num, source_alias, text = message.payload
            signed = False
            # print(
            #     f"Chat rx: {message.source:x} {source_alias}: {channel_num}: {text[:16]}"
            # )
        elif message.port == SIGNED_TEXT_CHAT.port:
            channel_num, source_alias, signature, text = message.payload
            # Only verifying the message, not packet headers. Risky?
            signed = self.badge.crypto.verify(text, signature)
            # print(
            #     f"Signed Chat rx: {message.source:x} {source_alias}: {channel_num}: {text[:16]} verified: {signed}"
            # )
            if not signed:
                return
        new_message = ChatMessage(
            message.source,
            source_alias.strip(b"\0").decode(),
            text.strip(b"\0").decode(),
            signed,
        )
        if channel_num in self.channels:
            self.channels[channel_num].append(new_message)
        else:
            self.channels[channel_num] = deque(
                [new_message],
                self.channel_buffer_len,
            )
        self.channel_messages_updated = channel_num == self.active_channel

    def start(self):
        super().start()
        register_receiver(TEXT_CHAT, self.receive_message)
        register_receiver(SIGNED_TEXT_CHAT, self.receive_message)

    def switch_to_foreground(self):
        super().switch_to_foreground()
        self.my_alias = self.badge.config.get("alias").decode()
        self.page = Chat(
            infobar_contents=(
                f"Channel: {self.active_freq:02d}:{self.active_topic:02d}    {MY_ADDRESS:x} : {self.my_alias}",
                "Hackaday Chat",
            ),
            menubar_labels=("Post", "Latest", "Freq", "Topic", "Home"),
            messages=[],
        )
        self.page.add_message_rows(1, left_width=80)
        self.channel_messages_updated = True
        self._update_channel_messages()
        self.page.replace_screen()

    def switch_to_background(self):
        self.page = None
        return super().switch_to_background()

    def _refresh_channel_list(self):
        self.channels_listed = list(self.channels.keys())
        self.channels_listed.sort()

    def run_foreground(self):
        if self.refresh_counter == 0:
            self._update_channel_messages()

        if self.compose_active:
            key, text = self.page.text_box_type(self.badge.keyboard)
            self.page.infobar_right.set_text(f"{len(text)}/{MAX_MESSAGE_LEN}  F1 to send")
            if self.badge.keyboard.escape_pressed:
                self.page.close_text_box()
                self.compose_active = False
                self.page.infobar_right.set_text("Hackaday Chat")
            if self.badge.keyboard.f1():  # Send
                if self.page.text_box.get_text():
                    message_text = self.page.close_text_box()
                    self.send(message_text)
                    self.compose_active = False
                    self.page.infobar_right.set_text("Hackaday Chat")


        if self.freq_picker_active:
            key, text = self.page.text_box_type(self.badge.keyboard)
            self.page.infobar_right.set_text(f"{len(text)}/2  F3 to set")
            self.page.infobar_left.set_text("Enter Frequency band: 1-52")
            if self.badge.keyboard.escape_pressed:
                self.page.close_text_box()
                self.freq_picker_active = False
                self.page.infobar_left.set_text(f"Channel: {self.active_freq:02d}:{self.active_topic:02d}    {MY_ADDRESS:x} : {self.my_alias}")
                self.page.infobar_right.set_text("Hackaday Chat")
            if self.badge.keyboard.f3() or key == self.badge.keyboard.ENTER:  
                if self.page.text_box.get_text():
                    new_freq_str = self.page.close_text_box()
                    self.freq_picker_active = False
                    self.page.infobar_right.set_text("Hackaday Chat")
                    try:
                        new_freq = max(1, min(52, int(new_freq_str)))
                        self.badge.lora.set_freq_slot(new_freq)
                        self.active_freq = new_freq
                        self.active_channel = self.active_freq * 100 + self.active_topic
                        self.page.infobar_left.set_text(f"Channel: {self.active_freq:02d}:{self.active_topic:02d}    {MY_ADDRESS:x} : {self.my_alias}")
                        self._update_channel_messages()
                    except ValueError as err:
                        print(f"Unable to set frequency slot: {err}. Must be [1-52]")

        if self.topic_picker_active:
            key, text = self.page.text_box_type(self.badge.keyboard)
            self.page.infobar_right.set_text(f"{len(text)}/2 F4 to set")
            self.page.infobar_left.set_text("Enter Topic Number: 1-99")
            if self.badge.keyboard.escape_pressed:
                self.page.close_text_box()
                self.topic_picker_active = False
                self.page.infobar_left.set_text(f"Channel: {self.active_freq:02d}:{self.active_topic:02d}    {MY_ADDRESS:x} : {self.my_alias}")
                self.page.infobar_right.set_text("Hackaday Chat")
            if self.badge.keyboard.f4() or key == self.badge.keyboard.ENTER:
                if self.page.text_box.get_text():
                    new_topic_str = self.page.close_text_box()
                    self.topic_picker_active = False
                    self.page.infobar_right.set_text("Hackaday Chat")
                    try:
                        self.active_topic = max(1, min(99, int(new_topic_str)))
                        self.active_channel = self.active_freq * 100 + self.active_topic
                        self.page.infobar_left.set_text(f"Channel: {self.active_freq:02d}:{self.active_topic:02d}    {MY_ADDRESS:x} : {self.my_alias}")
                        self.channel_messages_updated = True
                        self._update_channel_messages()
                    except ValueError as err:
                        print(f"Unable to set topic: {err}. Must be [1-99]")


        if not self.compose_active and not self.freq_picker_active and not self.topic_picker_active:
            if self.badge.keyboard.f5():
                self.switch_to_background()

            key = self.badge.keyboard.read_key()
            scroll_amount = 13
            if self.badge.keyboard.shift_pressed:
                scroll_amount *= 5
            if key == self.badge.keyboard.UP:
                self.page.scroll_up(scroll_amount)
                self.auto_follow = False
            elif key == self.badge.keyboard.DOWN:
                self.page.scroll_down(scroll_amount)
                self.auto_follow = False
            elif key == self.badge.keyboard.LEFT:
                self.active_topic = max(1, min(99, int(self.active_topic - 1)))
                self.active_channel = self.active_freq * 100 + self.active_topic
                self.channel_messages_updated = True
                self._update_channel_messages(seek = -1)
            elif key == self.badge.keyboard.RIGHT:
                self.active_topic = max(1, min(99, int(self.active_topic + 1)))
                self.active_channel = self.active_freq * 100 + self.active_topic
                self.channel_messages_updated = True
                self._update_channel_messages(seek = 1)

            if self.badge.keyboard.f2():
                self.auto_follow = True

            if self.badge.keyboard.f1():  # Compose a message
                self.page.create_text_box()
                self.compose_active = True

            if self.badge.keyboard.f3():  # Set Freq Slot
                self.page.create_text_box(
                    # Switch to Frequency Slot 01-52
                    default_text="",
                    one_line=True,
                    char_limit=2,
                )
                self.freq_picker_active = True

            if self.badge.keyboard.f4():  # Set Topic 
                self.page.create_text_box(
                    # Switch to Topic 01-99
                    default_text="",
                    one_line=True,
                    char_limit=2,
                )
                self.topic_picker_active = True

        if self.auto_follow:
            if self.page:
                self.page.scroll_bottom()

        self.refresh_counter = (
            self.refresh_counter + 1
        ) & self.refresh_counter_divider_factor

    def send(self, text):
        chat_message = ChatMessage(MY_ADDRESS, self.my_alias, text, False)
        if self.active_channel in self.channels:
            self.channels[self.active_channel].append(chat_message)
        else:
            self.channels[self.active_channel] = deque(
                [chat_message], self.channel_buffer_len
            )
        self.channel_messages_updated = True
        tx_message = NetworkFrame().set_fields(
            protocol=TEXT_CHAT,
            destination=BROADCAST_ADDRESS,
            ttl=self.chat_ttl,
            payload=(self.active_channel, self.my_alias[:10], text),
        )
        send(tx_message)
