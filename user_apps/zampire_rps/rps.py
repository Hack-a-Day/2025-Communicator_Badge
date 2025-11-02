"""Template app for badge applications. Copy this file and update to implement your own app."""

import uasyncio as aio  # type: ignore

from apps.base_app import BaseApp
from net.net import register_receiver, send, BROADCAST_ADDRESS
from net.protocols import Protocol, NetworkFrame
from ui.page import Page
import ui.styles as styles
import lvgl
import random
import sys
import time

"""
All protocols must be defined in their apps with unique ports. Ports must fit in uint8.
Try to pick a protocol ID that isn't in use yet; good luck.
Structdef is the struct library format string. This is a subset of cpython struct.
https://docs.micropython.org/en/latest/library/struct.html
"""
# NEW_PROTOCOL = Protocol(port=<PORT>, name="<NAME>", structdef="!")

ROCK_PAPER_SCISSOR = Protocol(port=129, name="ROCK_PAPER_SCISSOR", structdef="!B10s")

TIE = 1
LOCAL_WIN = 2
REMOTE_WIN = 3

SHORT_TO_LONG = {
    "R": "Rock",
    "P": "Paper",
    "S": "Scissors",
}

PLAY_TIMEOUT = 10.0
RETRY_PERIOD = 0.15

def to_long(short):
    return SHORT_TO_LONG[short]

class App(BaseApp):
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
        self.user_choice = None
        self.remote_choice = None
        self.choice_time = 0
        self.send_retry_time = 0
        self.send_retry_count = 0
        self.game_over = True
        self.my_alias = self.badge.config.get("alias").decode()

    def start(self):
        """ Register the app with the system.
            This is where to register any functions to be called when a message of that protocol is received.
            The app will start running in the background.
            If you don't have anything else to add, you can delete this method.
        """
        super().start()
        register_receiver(ROCK_PAPER_SCISSOR, self.receive_message)

    def play(self, user_choice, remote_choice):
        if user_choice == remote_choice:
            result = TIE
        elif user_choice == "R":
            if remote_choice == "P":
                result = REMOTE_WIN
            else:
                result = LOCAL_WIN
        elif user_choice == "P":
            if remote_choice == "R":
                result = LOCAL_WIN
            else:
                result = REMOTE_WIN
        else:
            if remote_choice == "R":
                result = REMOTE_WIN
            else:
                result = LOCAL_WIN

        if result == TIE:
            message = "Nobody Wins"
            status = f"Tied with {self.remote_alias}"
        elif result == LOCAL_WIN:
            message = f"Won w/ {to_long(user_choice)}"
            status = f"Won against {self.remote_alias}"
        else:
            message = f"Lost to {to_long(remote_choice)}"
            status = f"Lost to {self.remote_alias}"
        
        self.update_menu("Play", "", "", "")
        self.update_message(message)
        self.update_status(status)
        self.game_over = True
    
    def receive_message(self, message: NetworkFrame):
        print(f"Received message: {message}")
        if message.port == ROCK_PAPER_SCISSOR.port:
            remote_choice_id, remote_alias_bytes = message.payload
            self.remote_choice = chr(remote_choice_id)
            self.remote_alias = remote_alias_bytes.strip(b'\x00').decode()
    
    def send_message(self):
        tx_frame = NetworkFrame().set_fields(
            protocol=ROCK_PAPER_SCISSOR,
            destination=BROADCAST_ADDRESS,
            payload=(ord(self.user_choice), self.my_alias[:10]),
            ttl=2,
        )
        send(tx_frame)
        current_time = time.time()
        print(f"Sent message #{self.send_retry_count} @ {current_time - self.choice_time}s: {tx_frame}")
        self.send_retry_time = current_time + RETRY_PERIOD * (2**self.send_retry_count)
        self.send_retry_count += 1

    def update_menu(self, *items: list[str]):
        for button, text in enumerate(items):
            self.page.set_menubar_button_label(button, text)
    
    def update_message(self, message):
        self.label.set_text(message)
    
    def update_status(self, status):
        self.page.infobar_right.set_text(status)

    def run_foreground(self):
        """ Run one pass of the app's behavior when it is in the foreground (has keyboard input and control of the screen).
            You do not need to loop here, and the app will sleep for at least self.foreground_sleep_ms milliseconds between calls.
            Don't block in this function, for it will block reading the radio and keyboard.
            If the app only runs in the background, you can delete this method.
        """
        if self.game_over:
            if self.badge.keyboard.f1():
                self.user_choice = None
                self.remote_choice = None
                self.game_over = False
                self.update_menu("Rock", "Paper", "Scissors", "")
                self.update_message("Let's Play")
                self.update_status("Make your choice")
        else:
            if self.user_choice is None:
                if self.badge.keyboard.f1():
                    self.user_choice = "R"
                if self.badge.keyboard.f2():
                    self.user_choice = "P"
                if self.badge.keyboard.f3():
                    self.user_choice = "S"

                if self.user_choice:
                    self.update_menu("", "", "", "")
                    self.update_message(f"You chose {to_long(self.user_choice)}")
                    self.update_status("Waiting for remote")
                    self.choice_time = time.time()
                    self.send_retry_count = 0
                    self.send_message()
            elif self.remote_choice is None:
                current_time = time.time()
                time_left = self.choice_time + PLAY_TIMEOUT - current_time
                if time_left <= 0:
                    # receive a simulated message to exercise message handling
                    choice = random.choice(["R", "P", "S"])
                    alias = b'badge\x00\x00\x00\x00\x00'
                    message = NetworkFrame().set_fields(
                        protocol=ROCK_PAPER_SCISSOR,
                        destination=BROADCAST_ADDRESS,
                        payload=(ord(choice), alias),
                        ttl=2,
                    )
                    self.receive_message(message)
                else:
                    self.update_status(f"{time_left}s remaining")
                    if self.send_retry_time - current_time <= 0:
                        self.send_message()
            else:
                self.play(self.user_choice, self.remote_choice)
        
        
        ## Co-op multitasking: all you have to do is get out
        if self.badge.keyboard.f5():
            self.badge.display.clear()
            self.switch_to_background()
        

    def run_background(self):
        """ App behavior when running in the background.
            You do not need to loop here, and the app will sleep for at least self.background_sleep_ms milliseconds between calls.
            Don't block in this function, for it will block reading the radio and keyboard.
            If the app only does things when running in the foreground, you can delete this method.
        """
        super().run_background()

    def switch_to_foreground(self):
        """ Set the app as the active foreground app.
            This will be called by the Menu when the app is selected.
            Any one-time logic to run when the app comes to the foreground (such as setting up the screen) should go here.
            If you don't have special transition logic, you can delete this method.
        """
        super().switch_to_foreground()

        try:
            self.user_choice = None
            self.remote_choice = None
            self.remote_alias = None
            self.game_over = True

            self.page = Page()
            self.page.create_infobar(["Rock/Paper/Scissors", "Press Start to begin"])
            self.page.create_content()
            self.label = lvgl.label(self.page.content)
            self.label.set_style_text_font(lvgl.font_montserrat_42, lvgl.STATE.DEFAULT)
            self.label.align(lvgl.ALIGN.CENTER, 0, 0)
            self.update_message("Press Start")
            self.page.create_menubar(["Start", "", "", "", "Done"])
            self.page.replace_screen()
        except Exception as exc:
            sys.print_exception(exc)
            self.badge.display.clear()
            self.switch_to_background()

    def switch_to_background(self):
        """ Set the app as a background app.
            This will be called when the app is first started in the background and when it stops being in the foreground.
            If you don't have special transition logic, you can delete this method.
        """
        self.p = None
        super().switch_to_background()

APP_NAME="RPS"
APP_CLASS=App