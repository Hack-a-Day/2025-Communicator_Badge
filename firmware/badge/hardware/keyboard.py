import asyncio
import collections
import time

from hardware import board
from machine import I2C, Pin


FN_UNPRESSED = 0
FN_PRESSED_UNREAD = 1
FN_PRESSED_READ = 2


class Keyboard:
    """
    Communicator Badge Keyboard
    """

    # Keys starting with ` are special keys (since that's not possible):
    # 1 - 5 dot function keys
    F1 = "`1"
    F2 = "`2"
    F3 = "`3"
    F4 = "`4"
    F5 = "`5"
    ESC = "\x1b"  # Escape
    CTL = "`c"  # Control
    JW = "`m"  # Jolly Wrencher, aka Hack-A-Day logo
    SFT = "`s"  # Shift
    ALT = "`a"  # Alt
    LEFT = "`h"
    UP = "`j"
    DOWN = "`k"
    RIGHT = "`l"
    TAB = "\t"
    BS = "\b"  # Backspace
    DEL = "\x7f"  # Delete
    # \\: \
    ENTER = "\n"

    # fmt: off
    # Each key has an integer ID, which is the index of these tuples
    # Row becomes almost the 10's digit of the index, Col becomes the 1's digit of the index
    KEY_MATRIX = (
        None, # 0 - not a potential key, adding for the indexing trick to work
        # C0, C1,   C2,  C3,  C4,  C5,    C6,    C7,   C8,   C9
        None, F1,   "+", "9", "8", "7",   F2,    F3,   F4,   F5,    # 1-10 R0
        ESC,  "q",  "w", "e", "r", "t",   "y",   "u",  "i",  "o",   # 11-20 R1
        TAB,  "a",  "s", "d", "f", "g",   "h",   "j",  "k",  "l",   # 21-30 R2
        SFT,  "z",  "x", "c", "v", "b",   "n",   "m",  ",",  ".",   # 31-40 R3
        CTL,  JW,   ALT, "\\", " ", None, RIGHT, DOWN, LEFT, ALT,   # 41-50 R4
        None, None, "-", "6", "5", "4",   "]",   "[",  "p",  None,  # 51-60 R5
        None, None, "*", "3", "2", "1",   ENTER, "'",  ";",  None,  # 61-70 R6
        None, None, "/", "=", ".", "0",   SFT,   UP,   BS,  None,  # 71-80 R7
    )
    SHIFT_MATRIX = (
        None,  # 0 - not a potential key, adding for the indexing trick to work
        # C0, C1,   C2,  C3,  C4,  C5,   C6,    C7,   C8,   C9
        None, F1,   "+", "(", "*", "&",  F2,    F3,   F4,   F5,    # 1-10 R0
        "`",  "Q",  "W", "E", "R", "T",  "Y",   "U",  "I",  "O",   # 11-20 R1
        TAB,  "A",  "S", "D", "F", "G",  "H",   "J",  "K",  "L",   # 21-30 R2
        SFT,  "Z",  "X", "C", "V", "B",  "N",   "M",  "<",  ">",   # 31-40 R3
        CTL,  JW,   ALT, "|", " ", None, RIGHT, DOWN, LEFT, ALT,   # 41-50 R4
        None, None, "_", "^", "%", "$",  "}",   "{",  "P",  None,  # 51-60 R5
        None, None, "*", "#", "@", "!",  ENTER, '"',  ":",  None,  # 61-70 R6
        None, None, "?", "+", ",", ")",  SFT,   UP,   DEL,   None,  # 71-80 R7
    )
    # fmt: on

    PC_KEY_MAPPING = {"[A": UP, "[B": DOWN, "[C": RIGHT, "[D": LEFT, "[3~": DEL}

    def __init__(self):
        self.keybuffer = collections.deque([], 10)

        # JollyWrencher + <Other key> can register functions when pressed
        self.meta_actions = {}

        # Track is modifiers are currently pressed
        # Shift changes the value of keys.
        self.shift_pressed = False
        # Meta (Jolly Wrenher) triggers registered callback functions.
        # Use self.badge.keyboard.register_meta_action(key, function) to set up functions to call.
        self.meta_pressed = False
        # Control and Alt are available to be used by the applications.
        # Check self.badge.keyboard.control_pressed or self.badge.keyboard.alt_pressed to check their state.
        # Due to performance limits, the status of these keys may not perfectly match the physical behavior
        # when checked by the application reading other keys from the keyboard.
        self.control_pressed = False
        self.alt_pressed = False
        # Escape is special
        self.escape_pressed = False

        # Function keys can be checked directly from the keyboard, and don't produce text.
        # The f1() trough f5() functions should be use to get the pressed-state of these.
        # Each function key is a state machine:
        # 0: Unpressed
        # 1: Pressed but unread
        # 2: Pressed but read
        # The functions for checking the keys will only return True once per key press (only in state 2)
        self._f1 = FN_UNPRESSED
        self._f2 = FN_UNPRESSED
        self._f3 = FN_UNPRESSED
        self._f4 = FN_UNPRESSED
        self._f5 = FN_UNPRESSED

        # Create I2C Bus for keyboard.
        # Use standard (low) frequency because we don't need to send that much data, and it gives us more
        # signal margin.
        i2c = I2C(id=0, sda=board.KBD_SDA, scl=board.KBD_SCL, freq=100000)
        self.rst = board.KBD_RST
        # Reset chip before initializing
        self.rst.value(0)
        time.sleep_us(120)  # type: ignore # Reset pulse must be >120us
        # Assert !RESET line is high so chip is active
        self.rst.value(1)
        time.sleep_us(120)  # type: ignore # Recovery time after reset must be >120us

        self.mux = TCA8418(i2c)
        # Register interrupt to read keys on !INT
        self.irq = board.KBD_INT.irq(
            self.mux.notify_keys,
            Pin.IRQ_FALLING,
            # hard=False,
        )

    def f1(self) -> bool:
        """Checks if F1 has been pressed. Will only return True once until released."""
        if self._f1 == FN_PRESSED_UNREAD:
            self._f1 = FN_PRESSED_READ
            return True
        return False

    def f2(self) -> bool:
        """Checks if F2 has been pressed. Will only return True once until released."""
        if self._f2 == FN_PRESSED_UNREAD:
            self._f2 = FN_PRESSED_READ
            return True
        return False

    def f3(self) -> bool:
        """Checks if F3 has been pressed. Will only return True once until released."""
        if self._f3 == FN_PRESSED_UNREAD:
            self._f3 = FN_PRESSED_READ
            return True
        return False

    def f4(self) -> bool:
        """Checks if F4 has been pressed. Will only return True once until released."""
        if self._f4 == FN_PRESSED_UNREAD:
            self._f4 = FN_PRESSED_READ
            return True
        return False

    def f5(self) -> bool:
        """Checks if F5 has been pressed. Will only return True once until released."""
        if self._f5 == FN_PRESSED_UNREAD:
            self._f5 = FN_PRESSED_READ
            return True
        return False

    async def read_hw(self):
        """Check TCA8418 for new key press/release events, and update
        the keybuffer and state of special keys.
        """
        new_events = await self.mux.read_events()
        for event in new_events:
            # Event is (pressed(1)/released(0), key index)
            # Check modifier keys
            if self.KEY_MATRIX[event[1]] == self.SFT:  # check if event is shift key
                self.shift_pressed = bool(event[0])
            elif self.KEY_MATRIX[event[1]] == self.CTL:  # check if event is control key
                self.control_pressed = bool(event[0])
            elif (
                self.KEY_MATRIX[event[1]] == self.JW
            ):  # check if event is meta (Jolly Wrencher) key
                self.meta_pressed = bool(event[0])
            elif self.KEY_MATRIX[event[1]] == self.ALT:  # check if event is alt key
                self.alt_pressed = bool(event[0])
            elif self.KEY_MATRIX[event[1]] == self.ESC:  # check if event is esc key
                self.escape_pressed = bool(event[0])
            # Check function keys
            elif self.KEY_MATRIX[event[1]] == self.F1:
                if bool(event[0]):
                    if self._f1 != FN_PRESSED_READ:
                        self._f1 = FN_PRESSED_UNREAD
                else:
                    self._f1 = FN_UNPRESSED
            elif self.KEY_MATRIX[event[1]] == self.F2:
                if bool(event[0]):
                    if self._f2 != FN_PRESSED_READ:
                        self._f2 = FN_PRESSED_UNREAD
                else:
                    self._f2 = FN_UNPRESSED
            elif self.KEY_MATRIX[event[1]] == self.F3:
                if bool(event[0]):
                    if self._f3 != FN_PRESSED_READ:
                        self._f3 = FN_PRESSED_UNREAD
                else:
                    self._f3 = FN_UNPRESSED
            elif self.KEY_MATRIX[event[1]] == self.F4:
                if bool(event[0]):
                    if self._f4 != FN_PRESSED_READ:
                        self._f4 = FN_PRESSED_UNREAD
                else:
                    self._f4 = FN_UNPRESSED
            elif self.KEY_MATRIX[event[1]] == self.F5:
                if bool(event[0]):
                    if self._f5 != FN_PRESSED_READ:
                        self._f5 = FN_PRESSED_UNREAD
                else:
                    self._f5 = FN_UNPRESSED
            # Check the normal keyboard keys
            elif event[0]:  # Only submit presses, not releases
                if self.shift_pressed:
                    key_pressed = self.SHIFT_MATRIX[event[1]]
                else:
                    key_pressed = self.KEY_MATRIX[event[1]]

                if self.meta_pressed:
                    # If holding the Jolly Wrencher, call a function
                    action = self.meta_actions.get(key_pressed)
                    # If the action is defined, call it
                    if action:
                        action()
                elif self.control_pressed:
                    # Don't add key to keybuffer
                    pass
                elif self.alt_pressed:
                    # Don't add key to keybuffer
                    pass
                else:  # Otherwise, add the pressed key to the keybuffer
                    self.keybuffer.append(key_pressed)

    def read_key(self) -> str | None:
        """Read one key from the keyboard. None if no keys have been recently pressed."""
        if not self.keybuffer:
            return None
        return self.keybuffer.popleft()

    def register_meta_action(self, trigger_key: str, callback):
        """Register a function to run when JollyWrencher+<other key> is pressed.

        This function must:
        * Take no arguments and not expect it's return value to be used anywhere
        * Not be async (can't call await inside)
        * Run quickly, as the entire badge runtime will be blocked as long as it is running

        The trigger_key can be any key defined above in KEY_MATRIX or SHIFT_MATRIX. It cannot be None.
        There is no check if a function has already been registered, it will be overwritten.
        Register None to a key to disable a registered function.
        """
        self.meta_actions[trigger_key] = callback


class TCA8418:
    """
    Driver for TCA8418 Keyboard Mux
    Inspiration from https://github.com/adafruit/Adafruit_CircuitPython_TCA8418/blob/main/adafruit_tca8418.py
    """

    ADDR = 0x34

    def __init__(self, i2c):
        self.i2c = i2c
        self.keys_ready = asyncio.ThreadSafeFlag()  # type: ignore

        # Configure TCA8418
        # Start with guide on page 41 of TCA8418 datasheet

        # Setup key array
        try:
            self.i2c.writeto_mem(
                self.ADDR, 0x1D, b"\xff"
            )  # KP_GPIO1 all ROW7:0 to KP matrix
            self.i2c.writeto_mem(
                self.ADDR, 0x1E, b"\xff"
            )  # KP_GPIO2 all COL7:0 to KP matrix
            self.i2c.writeto_mem(
                self.ADDR, 0x1F, b"\x03"
            )  # KP_GPIO3 all COL9:8 to KP matrix
            self.i2c.writeto_mem(
                self.ADDR, 0x01, b"\x91"
            )  # CFG Set the KE_IEN, INT_CFG, and AI bits
            # Clear Interrupts
            self.i2c.writeto_mem(self.ADDR, 0x02, b"\x01")  # INT_STAT K_INT 1 to clear
        except OSError as err:
            if err.errno == 19:  # ENODEV
                print("Keyboard mux TCA8418 not found")
                kbd_i2c_bus = self.i2c.scan()
                print(f"Found I2C addresses on the keyboard bus: {kbd_i2c_bus}")

    def notify_keys(self, _):
        self.keys_ready.set()

    async def read_events(self):
        """Execute in interrupt"""
        await self.keys_ready.wait()

        num_events = self.i2c.readfrom_mem(self.ADDR, 0x03, 1)
        events = []
        # Key events are stored in a FIFO and get shifted to KEY_EVENT_A as each is read
        # TODO: Evaluate if it's faster to disable the FIFO and read multiple registers in a single transaction
        for _ in range(num_events[0]):
            event = self.i2c.readfrom_mem(self.ADDR, 0x04, 1)  # KEY_EVENT_A
            # Each event is (pressed(1)/released(0), Key ID)
            events.append((event[0] & 0x80, event[0] & 0x7F))

        # Clear interrupt
        self.i2c.writeto_mem(self.ADDR, 0x02, b"\x01")  # INT_STAT K_INT 1 to clear
        return events
