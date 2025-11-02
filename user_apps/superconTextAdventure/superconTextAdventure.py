"""Template app for badge applications. Copy this file and update to implement your own app."""

import uasyncio as aio  # type: ignore

from apps.base_app import BaseApp
from net.net import register_receiver, send, BROADCAST_ADDRESS
from net.protocols import Protocol, NetworkFrame
from ui.page import Page
import ui.styles as styles
import lvgl

"""
All protocols must be defined in their apps with unique ports. Ports must fit in uint8.
Try to pick a protocol ID that isn't in use yet; good luck.
Structdef is the struct library format string. This is a subset of cpython struct.
https://docs.micropython.org/en/latest/library/struct.html
"""
# NEW_PROTOCOL = Protocol(port=<PORT>, name="<NAME>", structdef="!")

class Item:
    def __init__(self, name, description, can_take=True):
        self.name = name
        self.description = description
        self.can_take = can_take

class Room:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.exits = {}
        self.items = []
        self.locked = False
        self.lock_message = ""

    def describe(self, appObj):
        msg = f"=== {self.name} ===\n\n"
        msg += self.description
        if self.items:
            msg += "\n\nYou see:"
            for item in self.items:
                msg += f"\n - {item.name}"
        msg += "\n\nExits: "
        msg += ", ".join(self.exits.keys())
        appObj.p.msg_area.set_cell_value(0, 0, msg)

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

    def create_world(self):
        # Define rooms
        hq = Room("Supplyframe HQ", "The bustling heart of Hackaday, filled with posters, laptops, and badges blinking in unison.")
        lab = Room("Design Lab", "A quiet maker space with soldering irons, oscilloscopes, and a faint smell of flux.")
        alley = Room("The Alley", "A vendor-filled alley behind the venue with parts, stickers, and a friendly robot dog.")
        lacm = Room("LACM main room", "Rows of seats face a massive screen. Unfortunately, the projector is dark...")
        stage = Room("LACM stage", "*** YOU WIN! ***\n\nYour presentation goes excellently and you cannot wait for next years Supercon. :)\n\nThanks for hacking at Supercon!")

        # Define exits
        hq.exits = {"east": lab, "south": alley}
        lab.exits = {"west": hq, "south": lacm}
        alley.exits = {"north": hq}
        stage.exits = {"east": lacm}
        lacm.exits = {"west": stage, "north": lab}

        # Define items
        solder_iron = Item("soldering iron", "A well-used soldering iron. It might still work.")
        battery = Item("battery", "A 9V battery with just enough charge left.")
        cable = Item("hdmi cable", "A short HDMI cable. Looks slightly frayed.")
        projector = Item("projector", "A large but unpowered projector. It’s missing power and connection.", can_take=False)

        lab.items.append(solder_iron)
        alley.items.append(battery)
        hq.items.append(cable)
        lacm.items.append(projector)

        # Lock stage until puzzle solved
        stage.locked = True
        stage.lock_message = "The projector is not working yet. Maybe you can fix it."

        return {
            "Supplyframe HQ": hq,
            "Design Lab": lab,
            "The Alley": alley,
            "LACM main room" : lacm,
            "LACM stage": stage
        }


    def start(self):
        """ Register the app with the system.
            This is where to register any functions to be called when a message of that protocol is received.
            The app will start running in the background.
            If you don't have anything else to add, you can delete this method.
        """
        super().start()
        # register_receiver(NEW_PROTOCOL, self.receive_message)

    def run_foreground(self):
        """ Run one pass of the app's behavior when it is in the foreground (has keyboard input and control of the screen).
            You do not need to loop here, and the app will sleep for at least self.foreground_sleep_ms milliseconds between calls.
            Don't block in this function, for it will block reading the radio and keyboard.
            If the app only runs in the background, you can delete this method.
        """
        if self.badge.keyboard.f1():
            self.rooms = self.create_world()
            self.inventory = []
            self.current_room = "Supplyframe HQ"
            self.rooms[self.current_room].describe(self)
            self.p.msg_area.set_cell_value(1, 0, ">> ")
        if self.badge.keyboard.f5():
            self.badge.display.clear()
            self.switch_to_background()

        key = self.badge.keyboard.read_key()
        if key is not None:
            if key == self.badge.keyboard.UP:
                self.p.msg_area.scroll_by_bounded(0, 13, False)
            elif key == self.badge.keyboard.DOWN:
                self.p.msg_area.scroll_by_bounded(0, -13, False)
            elif key == self.badge.keyboard.ENTER:
                # Process command
                self.processCommand(self.p.msg_area.get_cell_value(1, 0)[3:].strip().lower())
                self.p.msg_area.set_cell_value(1, 0, ">> ")
            elif key == self.badge.keyboard.BS:
                # Remove last char
                cmd = self.p.msg_area.get_cell_value(1, 0)
                if len(cmd) > 3:
                    self.p.msg_area.set_cell_value(1, 0, cmd[:-1])
            else:
                # Append character
                cmd = self.p.msg_area.get_cell_value(1, 0)
                self.p.msg_area.set_cell_value(1, 0, cmd+key)
        

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
        self.p = Page()
        ## Note this order is important: it renders top to bottom that the "content" section expands to fill empty space
        ## If you want to go fully clean-slate, you can draw straight onto the p.scr object, which should fit the full screen.
        self.p.create_infobar(["Supercon: The Text Adventure!", ""])
        self.p.create_content()
        self.p.msg_area = lvgl.table(self.p.content)
        self.p.msg_area.add_style(styles.content_style, 0)
        self.p.msg_area.add_style(styles.content_style, lvgl.PART.ITEMS)
        self.p.msg_area.set_row_count(2)
        self.p.msg_area.set_width(lvgl.pct(100))
        self.p.msg_area.set_height(lvgl.pct(100))
        self.p.msg_area.set_column_count(1)
        self.p.msg_area.set_column_width(0, self.p.scr.get_x2() - 15)
        self.p.msg_area.set_cell_value(0, 0, "As you check in on Friday morning, excited to give your first talk, you are dejected to learn that the projector on the LACM stage is currently broken, preventing you from giving your beloved talk!\n\nCan you gather the requisite materials and use your hacking knowledge to fix the projector and save the day?")
        self.p.create_menubar(["Start", "", "", "", "Done"])
        self.p.replace_screen()


    def switch_to_background(self):
        """ Set the app as a background app.
            This will be called when the app is first started in the background and when it stops being in the foreground.
            If you don't have special transition logic, you can delete this method.
        """
        self.p = None
        super().switch_to_background()
        
    def processCommand(self, command):
        if command == "help":
            self.show_help()
        elif command.startswith("go "):
            self.move(command[3:])
        elif command.startswith("inspect "):
            self.inspect(command[8:])
        elif command.startswith("take "):
            self.take(command[5:])
        elif command == "inventory":
            self.show_inventory()
        elif command == "use soldering iron on projector":
            self.use_items("soldering iron", "projector")
        elif command == "use battery on projector":
            self.use_items("battery", "projector")
        elif command == "use hdmi cable on projector":
            self.use_items("hdmi cable", "projector")
        elif command == "show":
            self.rooms[self.current_room].describe(self)
        else:
            self.p.msg_area.set_cell_value(0, 0, "I do not understand that command.")
            
    def show_help(self):
        self.p.msg_area.set_cell_value(0, 0, """Commands:
  go <direction>\t\t\t- Move between rooms
  inspect <item>\t\t\t- Look at an object or item
  take <item>\t\t\t- Pick up an item
  inventory\t\t\t- Check your items
  use <item> on <item>\t- Try to use or combine things
  show\t\t\t\t- Show room description
""")

    def move(self, direction):
        if direction not in self.rooms[self.current_room].exits:
            self.p.msg_area.set_cell_value(0, 0, "You cannot go that way.")
            return
        next_room = self.rooms[self.current_room].exits[direction]
        if self.rooms[next_room.name].locked:
            self.p.msg_area.set_cell_value(0, 0, next_room.lock_message)
            return
        self.current_room = next_room.name
        self.rooms[self.current_room].describe(self)

    def inspect(self, item_name):
        for item in self.rooms[self.current_room].items + self.inventory:
            if item.name == item_name:
                self.p.msg_area.set_cell_value(0, 0, item.description)
                return
        self.p.msg_area.set_cell_value(0, 0, "You do not see that here.")

    def take(self, item_name):
        for item in self.rooms[self.current_room].items:
            if item.name == item_name:
                if item.can_take:
                    self.inventory.append(item)
                    self.rooms[self.current_room].items.remove(item)
                    self.p.msg_area.set_cell_value(0, 0, f"You picked up the {item.name}.")
                else:
                    self.p.msg_area.set_cell_value(0, 0, f"You cannot take the {item.name}.")
                return
        self.p.msg_area.set_cell_value(0, 0, "There is nothing like that here.")

    def show_inventory(self):
        if not self.inventory:
            msg = "You are carrying nothing."
        else:
            msg = "You are carrying:"
            for item in self.inventory:
                msg += f"\n - {item.name}"
            self.p.msg_area.set_cell_value(0, 0, msg)

    def use_items(self, item1_name, item2_name):
        item1 = next((i for i in self.inventory if i.name == item1_name), None)
        projector_room = "LACM main room"

        if not item1:
            self.p.msg_area.set_cell_value(f"You do not have the {item1_name}.")
            return
        if self.current_room != projector_room:
            self.p.msg_area.set_cell_value("You do not see a projector here.")
            return

        # Puzzle logic
        if all(any(i.name == n for i in self.inventory) for n in ["soldering iron", "battery", "hdmi cable"]):
            self.rooms[self.current_room].description = "You skillfully repair the projector, connecting power and signal lines!\n\nThe screen lights up with the Hackaday logo. The crowd cheers!\n\nEnter the stage!"
            self.rooms[self.current_room].describe(self)
            self.rooms["LACM stage"].locked = False
        else:
            self.p.msg_area.set_cell_value("You are missing some components. Keep searching!")