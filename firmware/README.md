# Hackaday Supercon 2025 Communicator Badge Firmware

The Communicator Badge is running Micropython, compiled with LVGL and ucryptography, and running with asyncio, to stay interactive with the display and keyboard while still managing the LoRa radio in the background. Behaviors are driven by a Badge class, which manages hardware devices, a Network Stack, which manages receiving, transmitting, and repeating LoRa messages, and various Apps, which define various protocols on the network and interactions with the User Interface (UI). Apps can interact with the hardware stack to send and receive messages even when they aren't active in the UI.

- [Hackaday Supercon 2025 Communicator Badge Firmware](#hackaday-supercon-2025-communicator-badge-firmware)
- [Firmware Components](#firmware-components)
  - [Badge Hardware](#badge-hardware)
  - [Network Stack](#network-stack)
    - [RF Frequency Control](#rf-frequency-control)
    - [Security Implications](#security-implications)
    - [Packet Analysis with ImHex](#packet-analysis-with-imhex)
  - [Apps](#apps)
    - [App Structure](#app-structure)
    - [Using LVGL](#using-lvgl)
- [Badge Firmware Development](#badge-firmware-development)
  - [Installing an Editor](#installing-an-editor)
    - [Beginner: Thonny](#beginner-thonny)
    - [Advanced: VS Code](#advanced-vs-code)
  - [Setting up your computer](#setting-up-your-computer)
  - [Setting up the repository](#setting-up-the-repository)
  - [Syncing to the badge](#syncing-to-the-badge)
  - [Developing new Apps and Protocols](#developing-new-apps-and-protocols)
  - [REPL and debugging on the badge](#repl-and-debugging-on-the-badge)


# Firmware Components

All micropython code that runs on the badge lives in the firmware/badge/ directory. 

## Badge Hardware

The classes for managing the badge hardware components are all singletons, and are all stored in the Badge class in [badge.py](badge/badge.py), which is passed around the firmware for easy reference. Hardware pinouts are defined in [board.py](badge/board.py).

Most development will be inside apps, which will store a reference to the Badge object as `self.badge`. It is generally recommended to only interact with the badge when an app is active in the foreground, which ensures apps don't create adverse behaviors with the active foreground app. 

Accessing the various hardware devices for example:

```python
# Scan the SAO I2C bus
print(self.badge.sao_i2c.scan())

# Get the RSSI of the last received message
print(self.badge.lora.get_rssi())

# Erase everything on the screen
self.badge.display.clear()

# Check if the F1 button beneath the screen is pressed
print(self.badge.keyboard.f1())
```

## Network Stack

The network stack is based around Protocols that structure messages between badges. These messages can be sent, received, and repeated asyncrhonously from other badge behaviors. When sending a message, it is added to a queue with other messages to be sent. Received messages are pushed to registered callback functions by apps that want them. All messages are repeated until their TTL (time to live, or allowed repeat counter) drains to 0. Badges will not repeat a message if it is addressed only to them (not to `BROADCAST_ADDRESS`), and not if they hear another badge within range repeat it first.

Import network stack functions and values:
```python
from net.net import BROADCAST_ADDRESS, register_receiver, register_protocol, send
from net.protocols import NetworkFrame, Protocol
```

Each message protocol requires a port number, a name, and a struct definition. The port number must be unique across all protocols used on the badge, so pick a new number between 10 and 254 that seems unused. Make a pull request to officially claim it. The struct definition is using the [Micropython Struct library](https://docs.micropython.org/en/latest/library/struct.html), which is slightly less powerful than the [CPython Struct library](https://docs.python.org/3.5/library/struct.html#module-struct). The struct definition must start with `!` for network (big) endian encoding. Tip: `Xs` allocates X bytes for strings, or whatever else you want to pack in yourself, extra space in strings will be padded with 0 bytes.
```python
DEEP_THOUGHT_PROTOCOL = Protocol(port=42, name="DEEP_THOUGHT", structdef="!100sIf")
```

If you only need to send a protocol and don't need to receive it, you need to register it with the network stack so it knows the protocol exists:
```python
register_protocol(DEEP_THOUGHT_PROTOCOL)
```

Receiving a message requires registering a callback function with the network stack for whever a message of that protocol is received. If a callback isn't registered for a port, then messages will be repeated, but not otherwise handled by the badge. The callback will only get messages that have already been validated on the registered port and have a payload matching the length specified by `structdef`. If somebody else defines a different protocol on the same port, it will get passed to the callback if the payloads are the same length.

These callback functions:
* MUST return quickly, for it blocks all other badge behaviors (no sleeping)
* MUST NOT be async
* MUST NOT touch the screen (lvgl)
* SHOULD NOT interact with other badge hardware

```python
def answer_question(message: NetworkFrame) -> None:
    # Print the source address in hexadecimal so it looks nice
    print(f"Got a question from; {message.source:x}")
    # The payload has already been deserialzed for you, so you just need to pull the fields out
    question, president_heads, computation_years = message.payload
    print(f"Question: {question}")
    print(f"Computational years allocated: {computation_years}")
    print(f"Security question: How many heads does the president of the galaxy have? {president_heads} Correct: {president_heads == 2}")


register_receiver(DEEP_THOUGHT_PROTOCOL, answer_question)
```

To send a message to the network, you first need to create the message object, and then `send()` it.

```python
question = "what is the ultimate answer to life the universe and everything?"
zaphod_heads = 2
computation_years = 7.5e6
send(
    NetworkFrame().set_fields(
        protocol=DEEP_THOUGHT_PROTOCOL,  # Pass in which protocol to send
        destination=BROADCAST_ADDRESS,  # Send to Broadcast, or a particular badge's address
        ttl=1,  # How many times it can be repeated. Valid values are [0, 15]
        payload=(question, zaphod_heads, computation_years),
        # This should be the tuple of arguments to pack into the structdef struct
        # You can also pass in a bytes object, but the structdef needs to allocate enough space
        # Tip: to pack a python tuple with only one value, the syntax is (value, ). Or use a list [value].
    )
)
The message will be queued in the network stack and sent when next available.
```

### RF Frequency Control

We are using the LoRa protocol on the 915MHz ISM band, which goes from 902 to 928 MHz. We are using 500kHz bandwidth (legal in the US), and for convenience are using Meshtastic `SHORT_TURBO` frequency slot numbers. Badges will default at `9` because this is Supercon 9. Frequency slots that overlap with default Meshtastic channels for the various modes will not be allowed, so we can be good neighbors with Meshtastic users (which include many of you).

### Security Implications

This network stack is not trying to be secure. The goals are discoverability and exploratory hacking, not making an ultra secure network that it would be a fun challenge to break. We kindly ask you don't try to break the network, for the enjoyment of everyone. We're already aware of the following vulnerabilities (and more), so please don't exploit them:
* Denial of Service (DOS) due to spamming messages or other RF on the spectrum used
* Spoofing the identity of other badges
* Small RSA key size

### Packet Analysis with ImHex

An [ImHex](https://github.com/WerWolv/ImHex) pattern file is provided at [lora.hexpat](lora.hexpat) for parsing and inspecting raw LoRa packets used by the badge. It allows decoding the packet header (flags, addresses, and checksum), and protocol-specific payloads (Ping, Pong, TextChat, SignedTextChat, ConfigOverride). The pattern can be extended to support additional protocols.

<details>

<summary>ImHex screenshot</summary>

![ImHex screenshot](../images/imhex_screenshot.png)

</details>

## Apps

Apps are python classes that can asynchronously run behaviors, and potentially take control of the display for user interactions. Each app has its own async task and runs on its own update rate. Check out [demo.py](badge/apps/demo.py) to see many different app behaviors demonstrated, or the other apps in the `badge/apps/` directory. If you want to make a new App, start by copying [template_app.py](badge/apps/template_app.py) and populating or deleting methods as needed.

### App Structure

Each App is running a `while True:` loop inside the `BaseApp` class that all apps subclass from, and are cooperatively multitasking via `asyncio`. We are only using one core of the ESP32, so only one bit of Python runs at once. You primarily only need to define behaviors in `run_foreground()` and/or `run_background()`, which are called once for each pass through your app's loop, depending on if it is currently in the foreground (control of the UI) or background (not in control of the UI). If you need to persist state through each of these calls, that should be saved in class attributes (`self.thing1 = ...`). These functions are not `async`, so it is best not to sleep in them, and ideally they return as quickly as possible.

You can think of each app as a simple state machine, and you only need to implement the behavior in the states, and not worry of the transitions.

```
------------      ---------      ------------------------      ---------------------
| __init__ | ---> | start | ---> | switch_to_background | ---> | run_in_background | -\
------------      ---------      ------------------------      ---------------------  |
                                              ^                         |       ^     |
                              /----\          |                         |       \----/
                              |    V          |                         V
                              |  ---------------------      ------------------------
                              \_ | run_in_foreground | <--- | switch_to_foreground |
                                 ---------------------      ------------------------
```

Apps will loop in the `run_in_background` or `run_in_foreground` states, depending on if they currently are in the background or foreground. Call `self.switch_to_background()` to tell an app to put itself in the background. Never call `self.switch_to_foreground()`, because it will be called by the `AppMenu` when your app is selected.

`__init__` is used to set up the class for your App. It is given the `Badge` object, which is used to reference the hardware. You don't need to do anything with `badge`, as long as it passes to `super().__init__(name, badge)`, which sets it up as `self.badge` for easy access. It is advised to use this method to set up any class attributes (`self.foo`) that you want to use later to store objects or state.
Two attributes that will be created automatically by `super().__init__()` but you may want to change are `self.foreground_sleep_ms` and `self.background_sleep_ms`. When in the background, calls to `run_in_background()` will sleep for `self.background_sleep_ms` milliseconds between calls. When in the foreground, calls to `run_in_foreground()` will sleep for `self.foreground_sleep_ms` milliseconds between calls. Don't forget to call `super().__init__(name, badge)`.
```python
def __init__(self, name: str, badge):
    super().__init__(name, badge)
    self.foreground_sleep_ms = 10
    self.background_sleep_ms = 1000
```

`start` is used to start your app into the state machine loop. It's primary job is to register `Protocol`s with the network stack using `register_protocol()` and `register_receiver()`. A Protocol that is being sent and received should be registered via `register_receiver()`. If the App only needs to transmit the protocol and not receive it, then use `register_protocol()` instead. Registration is important so the network stack knows to handle messages with the port number of this protocol.
```python
def start(self):
    super().start()
    register_receiver(DEEP_THOUGHT_PROTOCOL, self.receive_message)
    # or
    register_protocol(DEEP_THOUGHT_PROTOCOL)
```

`run_foreground` is what gets called when your App is running in the foreground (is allowed to interact with the keyboard and display). It will be called repeatedly in a loop until you call `self.switch_to_background()`. Between each call, `self.foreground_sleep_ms` will delay the next call of `run_foreground()` by that many milliseconds. It is very important that `run_foreground()` does not block. If you want to wait for a button press or a delay, you can grab the time and wait until enough time has passed to do the next action. If you want to read keys or draw to the display, this is where to do it. Nothing will stop you from doing so from other functions, but it will interfere for whatever app is in the foreground, so please don't. Check out the demo apps in `apps/` to see examples of what you can do in here.
```python
def run_foreground(self):
    if self.badge.keyboard.f1():
      self.press_time = time.time()
    if self.press_time > 0 and time.time() - self.press_time > 1:
      self.do_next_step()
      self.press_time = 0

    # This is a general block of code to send your app to the background and return
    # to the main AppMenu
    if self.badge.keyboard.f5():
        self.badge.display.clear()
        self.switch_to_background()
```

`run_background` is what gets called when your App is running in the background (is not allowed to interact with the keyboard and display). It will be called repeatedly in a loop until the AppMenu calls `switch_to_foreground()` on your App class. Between each call, `self.background_sleep_ms` will delay the next call of `run_background()` by that many milliseconds. It is very important that `run_background()` does not block. It is also important that it does not draw to the screen or try to read from the keyboard, for it will interfere with the current app running `run_foreground()`. However, in the background you can still send messages to the network stack and other badges.
```python
def run_background(self):
    self.send_message()
```

`switch_to_foreground` is used to transition your App from the background to the foreground. It will be called once during the transition between states, and only should be called by the `AppMenu`. You should not call it yourself. This is where it is recommended to set up a `Page` and other elements drawn to the screen that only need to be done once. It is important to call `super().switch_to_foreground()`, which handles the important state transition logic.
```python
def switch_to_foreground(self):
    super().switch_to_foreground()
    # Page is a class with several helper methods for generating graphical elements usinv LVGL
    self.page = Page()
    # Page.create_infobar() will display two strings at the top of the display
    self.page.create_infobar(["Displays Top Left", "Displays Top Right"])
    # Page.create_content() creates an area that can be filled with other visual elements
    self.page.create_content()
    # Page.create_menubar() sets up the labels over the function buttons.
    self.page.create_menubar(["F1", "F2", "F3", "F4", "F5"])
    # Page.replace_screen() is what renders the Page you have constructed onto the display
    self.page.replace_screen()
```

`switch_to_background` is used to transition your App from the foreground to the background. It will be called once during the transition between states, and should be called at some point in `run_foreground()` when the App should transition. It is up to your app to call `switch_to_background()` if you don't want the badge to be stuck in it until you reboot. If you create a `Page` or other LVGL elements to display on the display, it is recommended to delete those objects or set them to `None` so they can be cleaned up and garbage collected. Trying to use those LVGL objects later often causes issues (LVGL will clean up objects even if you haven't) and thus it is recommended to clean up when switching to the background. It is important to call `super().switch_to_background()`, which handles the important state transition logic.
```python
def switch_to_background(self):
  super().switch_to_background()
  self.page = None
```

### Using LVGL

`LVGL` is a graphics library for embedded applications. We are using a port in Micropython to enable running it on the badge. The documentation is not great, and it is easy to encounter memory errors. However, if you're careful, you have a lot of flexibility creating detailed and beautiful graphics.

# Badge Firmware Development

## Installing an Editor

It is recommended to have a modern Integrated Development Environment (IDE) for working on Python and Micropython code. A modern IDE will have tools such as syntax highlighting, identifying potential errors, auto-formatting, and other integrations.

### Beginner: Thonny

Thonny is a easy to use Python editor, that comes built in with tools to connect to an ESP32 running Micropython and enable you to easily edit files directly on the badge.

### Advanced: VS Code

VS Code (Visual Studio) is a development environment with a ton of flexibility and extensions for working in almost any programming langauge. After installing, it is recommended to install extensions `Python` and `Serial Monitor`.

## Setting up your computer

These steps are only required if you want to be able to update the entire badge at once. If you only want to modify files already flashed to your badge, you can use `Thonny` (described above) to modify files on the badge without needing them on your computer.

## Setting up the repository

You will need `git` and `python3.9` or above on your computer to clone the repository.

Clone the repository to your system:
```bash
# If you use SSH keys for github.com:
git clone git@github.com:Hack-a-Day/2025-Communicator_Badge.git

# If you don't use SSH keys or don't know what that means
git clone https://github.com/Hack-a-Day/2025-Communicator_Badge.git
```

You want to be doing work out of the `firmware/` directory of the repository.
```bash
cd 2025-Communicator_Badge/firmware/
```

You will want to set up a Python Virtual Environment to install a few packages.
```bash
# Create the virtual environment (venv). You only need to do this once.
python -m venv venv

# Activate the virtual environment. You will need to do this each time you open a new terminal/shell.
# Linux
source venv/bin/activate

# Windows
venv/Scripts/activate

# You need to install Python packages into the virtual environment. You only need to do this once.
pip install -r requirements.txt
```

## Syncing to the badge

There are two methods to copy all the files to the badge.

`mpremote` will copy everything in the target directory to or from the badge.
```bash
# Copy from computer to badge
mpremote cp -r badge/* :

# Copy from badge to computer
mpremote cp -r : badge-backup/
```

There's also a helper script to selectively copy files. `scripts/update.py` will also delete files off the badge that have been removed from your computer, enforcing a more consistent state.
```bash
# Copy all the files to the badge and reset it automatically after the copy.
scripts/update.py --reset push

# Copy all the files on the badge to firmware/badge-backup/
scripts/update.py pull
```

## Developing new Apps and Protocols

To make a new App, start by copying `apps/template_app.py` and giving the copy a new name. You will also want to rename the class inside it. Read the docstrings for the included methods, and refer to the above guide for how to use each method. Methods you don't need to customize the behavior of can be deleted from your file.

After creating a new App file, you will need to import it and load it into the `AppMenu`. Lets say your file is named `my_app.py` and the class inside is named `MyApp`. Open `main.py`:
```python
# Add the import inside the try:
try:
    # Other imports here
    from apps import your_app_filename

except Exception as ex:
    # Exception handling here
```

Construct your app, and add it into the `user_apps` menu list. The first argument should be a short string to name the App, and will be how it appears in the `AppMenu` above the Function key. The second argument must be `badge`, so your app will have easy access to the `Badge`.
```python
users_apps = [
    my_app.MyApp("My App", badge),
    # other apps
]
```

## REPL and debugging on the badge

While the badge is running, you can connect to it via a serial terminal and monitor the prints to understand what is happening under the hood. If you want to access the Micropython `REPL` (Read Execute Print Loop), you can try pressing `Ctrl+C` or `Ctrl+D` once to interrupt the running program. This will drop you to a Python prompt `>>>`, where you can run any Micropython command. If you want to access the `Badge` object to get access to the hardware devices, you can create get to it as the `badge_obj` object via:
```python
>>> from hardware.badge import badge_obj
```
