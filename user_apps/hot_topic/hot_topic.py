"""Template app for badge applications. Copy this file and update to implement your own app."""

import uasyncio as aio  # type: ignore

from apps.base_app import BaseApp
from net.net import register_receiver, send, BROADCAST_ADDRESS, capture_all_packets
from net.protocols import Protocol, NetworkFrame
from ui.page import Page


"""
There are a lot of directions we could take this

   - we could find the active frequency # and subtract 100*that value to get the raw topic #
   - we could add cursor functionality like in the chat
   - we could represent each seen topic in terms of percentage of recent traffic
   - we could put a timestamp on each topic to age out stale activity

I'm reasonably certain there's a way we can use the sequence number or the checksum in the message to help get the actual message count; what
I've exposed here is an estimate, at best.
"""


"""
All protocols must be defined in their apps with unique ports. Ports must fit in uint8.
Try to pick a protocol ID that isn't in use yet; good luck.
Structdef is the struct library format string. This is a subset of cpython struct.
https://docs.micropython.org/en/latest/library/struct.html
"""
# NEW_PROTOCOL = Protocol(port=<PORT>, name="<NAME>", structdef="!")

MAX_MESSAGE_LEN = 100
TEXT_CHAT = Protocol(
    port=6, name="TEXT_CHAT", structdef=f"!H10s{MAX_MESSAGE_LEN}s"
)

class HotTopic(BaseApp):
    """Define a new app to run on the badge."""

    def __init__(self, name: str, badge):
        """ Define any attributes of the class in here, after super().__init__() is called.
            self.badge will be available in the rest of the class methods for accessing the badge hardware.
            If you don't have anything else to add, you can delete this method.
        """
        super().__init__(name, badge)
        # You can also set the sleep time when running in the foreground or background. Uncomment and update.
        # Remember to make background sleep longer so this app doesn't interrupt other processing.
        # self.foreground_sleep_ms = 10
        # self.background_sleep_ms = 1000
        self.topics = {}
        #self.topics[900] = {"count": 0, "alias": "min"}
        #self.topics[999] = {"count": 999999999, "alias": "max"}
        self.received_count = 0
        self.reverse_sort = False

    def start(self):
        """ Register the app with the system.
            This is where to register any functions to be called when a message of that protocol is received.
            The app will start running in the background.
            If you don't have anything else to add, you can delete this method.
        """
        super().start()
        register_receiver(TEXT_CHAT, self.receive_message)

    def receive_message(self, message: NetworkFrame):
        self.received_count += 1
        channel_num, source_alias, text = message.payload
        #print(f"channel num is {channel_num}")
        tmp_count = 0
        if channel_num in self.topics:
            tmp_count = self.topics[channel_num]["count"]            
        tmp_count += 1
        self.topics[channel_num] = {"alias": source_alias, "count": tmp_count}
        #print(f"added {self.topics[channel_num]}")
        if self.received_count >= 100:
            print(f"received {self.received_count} messages; snapshotting")
            print(self.topics)
            self.received_count = 0

    def run_foreground(self):
        """ Run one pass of the app's behavior when it is in the foreground (has keyboard input and control of the screen).
            You do not need to loop here, and the app will sleep for at least self.foreground_sleep_ms milliseconds between calls.
            Don't block in this function, for it will block reading the radio and keyboard.
            If the app only runs in the background, you can delete this method.
        """
        mrows = [("-1", "No messages seen yet")]
        if len(self.topics) > 0:
            pre_sorted = [[channel, self.topics[channel]["count"], self.topics[channel]["alias"]] for channel in self.topics]
            sorted_topics = [i for i in sorted(pre_sorted, key=lambda topic: topic[1], reverse=self.reverse_sort)]
            mrows = [(t[0], f"{t[1]} messages, most recent from {t[2][:10]}") for t in sorted_topics]
        self.p.populate_message_rows(mrows)

        if self.badge.keyboard.f1():
            self.reverse_sort = not self.reverse_sort

        if self.badge.keyboard.f5():
            self.badge.display.clear()
            self.switch_to_background()

    def run_background(self):
        """ App behavior when running in the background.
            You do not need to loop here, and the app will sleep for at least self.background_sleep_ms milliseconds between calls.
            Don't block in this function, for it will block reading the radio and keyboard.
            If the app only does things when running in the foreground, you can delete this method.
        """

    def switch_to_foreground(self):
        """ Set the app as the active foreground app.
            This will be called by the Menu when the app is selected.
            Any one-time logic to run when the app comes to the foreground (such as setting up the screen) should go here.
            If you don't have special transition logic, you can delete this method.
        """
        #print(f"setting capture all packets to true")
        capture_all_packets(True)

        self.p = Page()
        ## Note this order is important: it renders top to bottom that the "content" section expands to fill empty space
        ## If you want to go fully clean-slate, you can draw straight onto the p.scr object, which should fit the full screen.
        self.p.create_infobar(["Hot Topic", "Most active topics seen"])
        self.p.create_content()
        self.p.add_message_rows(len(self.topics), 50)
        self.p.create_menubar(["Sort Asc" if self.reverse_sort else "Sort Desc", "", "", "", "Done"])
        self.p.replace_screen()

        super().switch_to_foreground()

    def switch_to_background(self):
        """ Set the app as a background app.
            This will be called when the app is first started in the background and when it stops being in the foreground.
            If you don't have special transition logic, you can delete this method.
        """
        #print(f"exiting foreground; {self.topics}")
        capture_all_packets(False)
        self.p = None
        super().switch_to_background()

    def stop(self):
        capture_all_packets(False)
        super().stop()
