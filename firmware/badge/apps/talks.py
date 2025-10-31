# App to load talks from CSV. All blame goes to Tom Nardi

import uasyncio as aio  # type: ignore

from apps.base_app import BaseApp

# from net.net import register_receiver, send, BROADCAST_ADDRESS
# from net.protocols import Protocol, NetworkFrame
from ui.talk import Talk
import gc


# Class for talk data
class talk:
    def __init__(self, day, time, stage, title, speaker, image, desc):
        self.day = day
        self.time = time
        self.stage = stage
        self.title = title
        self.speaker = speaker
        self.image = image
        self.desc = desc


class Talks(BaseApp):
    """Define a new app to run on the badge."""

    def __init__(self, name: str, badge):
        """Define any attributes of the class in here, after super().__init__() is called.
        self.badge will be available in the rest of the class methods for accessing the badge hardware.
        If you don't have anything else to add, you can delete this method.
        """
        super().__init__(name, badge)

        # Location of headshots
        self.image_dir = "images/headshots/"

        # Variables to remember state
        self.talk_index = 0
        self.day_index = "SAT"
        self.stage_index = "LACM"
        self.talk_changed = False

        # Data structure that holds talks
        self.talks = []

    def start(self):
        # Run at startup
        super().start()

        # Load data from file
        # talks = []
        with open("schedule.csv", "r") as schedule:
            for line in schedule:
                t_data = line.strip().split("$")
                if len(t_data) == 7:
                    new_talk = talk(
                        t_data[0],
                        t_data[1],
                        t_data[2],
                        t_data[3],
                        t_data[4],
                        t_data[5],
                        t_data[6],
                    )
                    self.talks.append(new_talk)

    def run_foreground(self):
        gc.collect()
        # Handle user input
        if self.badge.keyboard.f1():
            self.talk_changed = True
            self.talk_index = 0
            if self.day_index == "SAT":
                self.day_index = "SUN"
            else:
                self.day_index = "SAT"

        if self.badge.keyboard.f2():
            self.talk_changed = True
            self.talk_index = 0
            if self.stage_index == "LACM":
                self.stage_index = "DSLB"
            else:
                self.stage_index = "LACM"

        # Find matching talks
        matching_talks = []
        for talk in self.talks:
            if talk.day == self.day_index and talk.stage == self.stage_index:
                matching_talks.append(talk)

        # Move forward and backward through results
        num_talks = len(matching_talks)
        if self.badge.keyboard.f3():
            if self.talk_index > 0:
                self.talk_index = self.talk_index - 1
            self.talk_changed = True

        if self.badge.keyboard.f4():
            if self.talk_index < (num_talks - 1):
                self.talk_index = self.talk_index + 1
                self.talk_changed = True

        # print(matching_talks[self.talk_index].title)
        current_talk = matching_talks[self.talk_index]

        # Update if changed
        if self.talk_changed:
            print(current_talk.image)
            self.page.update(
                talk_dict={
                    "speaker": current_talk.speaker,
                    "headshot": self.image_dir + current_talk.image,
                    "title": current_talk.title,
                    "time": (current_talk.day + " " + current_talk.time)
                    + " @ "
                    + current_talk.stage,
                    "abstract": current_talk.desc,
                }
            )
            # self.page.update_menu(menubar_labels=(self.day_index, self.stage_index, "Prev", "Next", "Home"))
            self.talk_changed = False

        # Go back to top level
        if self.badge.keyboard.f5():
            self.badge.display.clear()
            self.switch_to_background()

    def run_background(self):
        """App behavior when running in the background.
        You do not need to loop here, and the app will sleep for at least self.background_sleep_ms milliseconds between calls.
        Don't block in this function, for it will block reading the radio and keyboard.
        If the app only does things when running in the foreground, you can delete this method.
        """

    def switch_to_foreground(self):
        super().switch_to_foreground()

        # Load in first result in list TODO make this time sensitive
        current_talk = self.talks[0]
        self.page = Talk(
            talk_dict={
                "speaker": current_talk.speaker,
                "headshot": self.image_dir + current_talk.image,
                "title": current_talk.title,
                "time": (current_talk.day + " " + current_talk.time)
                + " @ "
                + current_talk.stage,
                "abstract": current_talk.desc,
            },
            menubar_labels=("Day", "Stage", "Prev", "Next", "Home"),
        )
        """ 
        self.page = Talk(talk_dict = { "speaker":"Bob Hickman", "headshot":"images/headshots/hickman.png",
                                    "title":"SAOs with SACs", "time":"14:00", "stage":"LACM",
                            "abstract":"Maximize your Simple Add-On builds using SACs: sketchy, affordable components that can deliver surprising results."},
                menubar_labels=("Day", "Stage", "Prev", "Next", "Home"))
        """
        self.page.replace_screen()

    def switch_to_background(self):
        """Set the app as a background app.
        This will be called when the app is first started in the background and when it stops being in the foreground.
        If you don't have special transition logic, you can delete this method.
        """
        super().switch_to_background()
