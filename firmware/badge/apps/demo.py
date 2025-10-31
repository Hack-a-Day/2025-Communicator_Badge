"""This app is a demo of as many library features as possible to show what's possible."""

from collections import deque

from apps.base_app import BaseApp
from net.net import register_receiver, send, BROADCAST_ADDRESS
from net.protocols import Protocol, NetworkFrame

DEMO_PROTOCOL = Protocol(port=255, name="DEMO", structdef="!dfQqLlIiBb11s")


class DemoApp(BaseApp):
    """Define a new app to run on the badge."""

    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.foreground_sleep_ms = 10
        self.background_sleep_ms = 1000
        self.receive_queue = deque([], 10)
        self.menu_or_text = False
        self.tx_counter = 0
        self.send_pressed = False
    
    def receive_message(self, message: NetworkFrame):
        """Handle incoming messages."""
        self.receive_queue.append(message)


    def start(self):
        super().start()
        register_receiver(DEMO_PROTOCOL, self.receive_message)

    def run_foreground(self):
        """ Run one pass of the app's behavior when it is in the foreground (has keyboard input and control of the screen).
            You do not need to loop here, and the app will sleep for at least self.foreground_sleep_ms milliseconds between calls.
            Don't block in this function, for it will block reading the radio and keyboard.
            If the app only runs in the background, you can delete this method.
        """

        # Example code to receive network messages:
        while self.receive_queue:
            message = self.receive_queue.popleft()
            print(
                f"Received message from {message.source} to {message.destination}: {message.payload}"
            )
            # Handle the message (e.g., update display, process data)
            # Add your message handling logic here. Example:
            # year = message.payload[0]
            # greeting = message.payload[1]
            # print(f"{greeting}! The year is {year}!")

        # If Dot 3 is pressed, send a message:
        if self.badge.keyboard.f3():
            if not self.send_pressed:
                self.send_pressed = True
                self.tx_counter += 1
                tx_message = NetworkFrame().set_fields(protocol=DEMO_PROTOCOL,
                                                       destination=BROADCAST_ADDRESS,
                                                       payload=(  # dfQqLlIiBb11s
                                                           float(self.tx_counter) / 2,  # double
                                                           float(self.tx_counter) / 4,  # float
                                                           self.tx_counter,  # unisnged long
                                                           -self.tx_counter,  # long
                                                           self.tx_counter & 0xFFFFFFFF,  # unsinged int
                                                           -self.tx_counter & 0xFFFFFFFF,  # int
                                                           self.tx_counter & 0xFFFF,  # unsigned short
                                                           -self.tx_counter & 0xFFFF, # short
                                                           self.tx_counter & 0xFF,  # unsigned byte
                                                           -self.tx_counter & 0xFF,  # byte
                                                           "hello world"  # String (fixed width)
                                                       ))
                send(tx_message)
        else:
            self.send_pressed = False

        # Check the dot buttons on the keyboard and switch between the display elements
        if self.badge.keyboard.f1():
            self.menu_or_text = False
        if self.badge.keyboard.f2():
            self.menu_or_text = True
        # Example code to read the keyboard and write it to the screen in a line of text:
        if self.menu_or_text:
            self.text.run()
        else:
            selected = self.menu.run()

    
    def run_background(self):
        while self.receive_queue:
            message = self.receive_queue.popleft()
            print(
                f"Received message from {message.source} to {message.destination}: {message.payload}"
            )

    def switch_to_foreground(self):
        self.badge.display.text(0, 0, "Sample App Menu")
        super().switch_to_foreground()

    def switch_to_background(self):
        super().switch_to_background()