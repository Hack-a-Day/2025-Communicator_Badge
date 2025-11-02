"""Conway's Game Of Life."""

import random
import lvgl

from ui import styles
from apps.base_app import BaseApp
from ui.page import Page
from machine import Pin
from hardware import board

SCREEN_WIDTH = 428
SCREEN_HEIGHT = 142

def capitalize(s):
    """A capitalize function for MicroPython's str."""
    if not s:
        return ""
    return s[0].upper() + s[1:].lower()

class Pattern:
    """Represents a pattern of cells."""
    def __init__(self, name, shape):
        self.name = name
        self.shape = shape

PATTERNS = {
    "glider": Pattern("glider", [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]),
    "lwss": Pattern("lwss", [(0, 1), (0, 4), (1, 0), (2, 0), (3, 0), (4, 0), (4, 1), (4, 2), (3, 3)]),
}

class Grid:
    """Represents the grid of cells."""
    def __init__(self, width, height, randomize=False):
        self.width = width
        self.height = height
        self.cells = [[0 for _ in range(width)] for _ in range(height)]
        if randomize:
            self.randomize()

    def get_cell_state(self, x, y):
        return self.cells[y][x]

    def set_cell_state(self, x, y, state):
        self.cells[y][x] = state if state in (0, 1) else 0

    def place_pattern(self, pattern, x, y):
        """Places a pattern on the grid at the given coordinates."""
        for dx, dy in pattern.shape:
            self.set_cell_state((x + dx) % self.width, (y + dy) % self.height, 1)

    def randomize(self):
        """Fills the grid with random cell states."""
        for y in range(self.height):
            for x in range(self.width):
                self.cells[y][x] = random.randint(0, 1)

    def fill(self):
        """Fills the grid with all live cells."""
        for y in range(self.height):
            for x in range(self.width):
                self.cells[y][x] = 1

class App(BaseApp):
    """Define a new app to run on the badge."""

    def __init__(self, name: str, badge):
        super().__init__(name, badge)
        self.foreground_sleep_ms = 100
        self.background_sleep_ms = 10000 # Run very infrequently in background

        self.resolutions = [2, 4, 6, 8, 10, 12, 14, 16]
        self.current_res_index = self.resolutions.index(8)
        self.cell_size = self.resolutions[self.current_res_index]

        self.selection_index = 0
        self.selection_labels = []

        self.page = None
        self.cell_objects = None

        self.GRID_WIDTH = SCREEN_WIDTH // self.cell_size
        self.GRID_HEIGHT = SCREEN_HEIGHT // self.cell_size

        self.grid_a = None
        self.grid_b = None
        self.display_grid = None
        self.compute_grid = None
        self.frame_number = 0

        self.live_color = lvgl.color_hex(0xFFFFFF)
        self.dead_color = lvgl.color_hex(0x000000)

        # Used for triggering an external camera after each frame renders
        self.camera_trigger_pin = board.SAO_GPIO1
        self.camera_trigger_pin.init(Pin.OUT)

        self.app_states = ["MAIN_MENU", "RUNNING", "MODE_SELECT", "RESOLUTION_SELECT"]
        self.app_state = self.app_states.index("MAIN_MENU")

        self.modes = ["random", "empty", "full", "glider", "lwss"]
        self.current_mode_index = 0 # Default to "random"

    def run_foreground(self):
        # print("============================================")
        current_state = self.app_states[self.app_state]

        if current_state == "MAIN_MENU":
            if self.badge.keyboard.f1(): # Start
                print("GoL: F1 pressed in MAIN_MENU. Switching to RUNNING state.")
                self.app_state = self.app_states.index("RUNNING")
                self.badge.keyboard.read_key() # Consume the key press
                self.setup_simulation_screen()
            elif self.badge.keyboard.f2(): # Mode Select
                print("GoL: F2 pressed in MAIN_MENU. Switching to MODE_SELECT state.")
                self.app_state = self.app_states.index("MODE_SELECT")
                self.setup_mode_select_screen()
            elif self.badge.keyboard.f3(): # Resolution
                print("GoL: F3 pressed in MAIN_MENU. Switching to RESOLUTION_SELECT state.")
                self.app_state = self.app_states.index("RESOLUTION_SELECT")
                self.setup_resolution_select_screen()
            elif self.badge.keyboard.f5(): # Home
                print("GoL: F5 pressed in MAIN_MENU. Going home.")
                self.switch_to_background()

        elif current_state == "RUNNING":
            # Don't run if grid isn't initialized yet
            if not self.display_grid:
                return # Should not happen if state is RUNNING

            # print(f"GoL: Running frame {self.frame_number}")
            self.compute_and_draw_next_gen()
            self.camera_trigger_pin.value(self.frame_number % 2)

            # Exit simulation on any function key press
            if (self.badge.keyboard.f1() or
                self.badge.keyboard.f2() or
                self.badge.keyboard.f3() or
                self.badge.keyboard.f4() or
                self.badge.keyboard.f5()):
                print("GoL: Function key pressed. Exiting simulation to MAIN_MENU.")
                self.app_state = self.app_states.index("MAIN_MENU")
                self.setup_menu_screen()
                return # Exit run_foreground to avoid incrementing frame_number

            self.frame_number += 1
        
        elif current_state == "MODE_SELECT":
            key = self.badge.keyboard.read_key()
            if self.badge.keyboard.f1() or key == self.badge.keyboard.ENTER: # Select
                self.current_mode_index = self.selection_index
                print(f"GoL: F1 pressed in MODE_SELECT. Setting mode to '{self.modes[self.current_mode_index]}'.")
                self.app_state = self.app_states.index("MAIN_MENU")
                self.setup_menu_screen()
            elif self.badge.keyboard.f2() or key == self.badge.keyboard.UP: # Up
                self.selection_index = (self.selection_index - 1) % len(self.modes)
                if self.app_states[self.app_state] == "MODE_SELECT":
                    self.draw_selection_list(self.modes, self.selection_index, self.format_mode)
            elif self.badge.keyboard.f3() or key == self.badge.keyboard.DOWN: # Down
                self.selection_index = (self.selection_index + 1) % len(self.modes)
                if self.app_states[self.app_state] == "MODE_SELECT":
                    self.draw_selection_list(self.modes, self.selection_index, self.format_mode)
            elif self.badge.keyboard.f5(): # Back to MAIN_MENU
                self.app_state = self.app_states.index("MAIN_MENU")
                self.setup_menu_screen()
        
        elif current_state == "RESOLUTION_SELECT":
            key = self.badge.keyboard.read_key()
            if self.badge.keyboard.f1() or key == self.badge.keyboard.ENTER: # Select
                self.current_res_index = self.selection_index
                self.cell_size = self.resolutions[self.selection_index]
                self.GRID_WIDTH = SCREEN_WIDTH // self.cell_size
                self.GRID_HEIGHT = SCREEN_HEIGHT // self.cell_size
                self.app_state = self.app_states.index("MAIN_MENU")
                self.setup_menu_screen()
            elif self.badge.keyboard.f2() or key == self.badge.keyboard.UP: # Up
                self.selection_index = (self.selection_index - 1) % len(self.resolutions)
                if self.app_states[self.app_state] == "RESOLUTION_SELECT":
                    self.draw_selection_list(self.resolutions, self.selection_index, self.format_resolution)
            elif self.badge.keyboard.f3() or key == self.badge.keyboard.DOWN: # Down
                self.selection_index = (self.selection_index + 1) % len(self.resolutions)
                if self.app_states[self.app_state] == "RESOLUTION_SELECT":
                    self.draw_selection_list(self.resolutions, self.selection_index, self.format_resolution)
            elif key == self.badge.keyboard.ENTER: # Also Select
                # Emulate F1 press for selection
                self.badge.keyboard.f1()
            elif self.badge.keyboard.f5(): # Back
                self.app_state = self.app_states.index("MAIN_MENU")
                self.setup_menu_screen()

    def run_background(self):
        # Game of Life only runs in the foreground
        super().run_background()

    def setup_menu_screen(self):
        print("GoL: Setting up MAIN_MENU screen.")
        self.foreground_sleep_ms = 100
        self.page = None # Force page recreation
        self.cell_objects = None
        self.page = Page()
        current_mode_str = self.modes[self.current_mode_index]
        grid_size_str = f"{self.GRID_WIDTH}x{self.GRID_HEIGHT}"
        infobar_text = f"Mode: {capitalize(current_mode_str)} ({grid_size_str})"
        self.page.create_infobar(["Game of Life", infobar_text])
        content = self.page.create_content()
        self.page.create_menubar(["Start", "Mode", "Res", "", "Home"])
        self.page.replace_screen()

    def setup_mode_select_screen(self):
        print("GoL: Setting up mode select screen.")
        self.foreground_sleep_ms = 100
        self.page = None # Force page recreation
        self.selection_labels = []
        self.page = Page()
        self.page.create_infobar(["Editing Mode", ""])
        content = self.page.create_content()
        self.page.create_menubar(["Select", "Up", "Down", "", "Back"])
        self.selection_index = self.current_mode_index
        self.draw_selection_list(self.modes, self.selection_index, self.format_mode)
        self.page.replace_screen()

    def setup_resolution_select_screen(self):
        print("GoL: Setting up resolution select screen.")
        self.foreground_sleep_ms = 100
        self.page = None # Force page recreation
        self.selection_labels = []
        self.page = Page()
        self.page.create_infobar(["Editing Resolution", ""])
        content = self.page.create_content()
        self.page.create_menubar(["Select", "Up", "Down", "", "Back"])
        self.selection_index = self.current_res_index
        self.draw_selection_list(self.resolutions, self.selection_index, self.format_resolution)
        self.page.replace_screen()

    def format_mode(self, mode, _):
        return capitalize(mode)

    def format_resolution(self, cell_size, _):
        grid_w = SCREEN_WIDTH // cell_size
        grid_h = SCREEN_HEIGHT // cell_size
        return f"Grid: {grid_w}x{grid_h} (Cell: {cell_size}px)"

    def draw_selection_list(self, items, selected_idx, formatter):
        # Clear old labels
        for label in self.selection_labels:
            label.delete()
        self.selection_labels = []

        if not self.page or not self.page.content:
            return

        # Determine visible range
        max_visible = 5
        start_idx = 0
        if len(items) > max_visible:
            start_idx = max(0, selected_idx - max_visible // 2)
            start_idx = min(start_idx, len(items) - max_visible)

        end_idx = min(start_idx + max_visible, len(items))

        y_pos = 5
        for i in range(start_idx, end_idx):
            prefix = "> " if i == selected_idx else "  "
            text = prefix + formatter(items[i], i)
            label = lvgl.label(self.page.content)
            label.set_text(text)
            label.align(lvgl.ALIGN.TOP_LEFT, 10, y_pos)
            self.selection_labels.append(label)
            y_pos += 18

    def setup_simulation_screen(self):
        print("GoL: Setting up simulation screen.")
        self.foreground_sleep_ms = 5
        self.page = Page()

        # Create a grid of lvgl objects for cells
        self.cell_objects = []
        parent = self.page.scr
        for y in range(self.GRID_HEIGHT):
            row = []
            for x in range(self.GRID_WIDTH):
                cell = lvgl.obj(parent)
                cell.set_size(self.cell_size, self.cell_size)
                cell.set_pos(x * self.cell_size, y * self.cell_size)
                cell.set_style_radius(0, 0)
                cell.set_style_border_width(0, 0)
                cell.set_style_bg_color(self.dead_color, 0)
                row.append(cell)
            self.cell_objects.append(row)

        # Initialize grids
        current_mode = self.modes[self.current_mode_index]
        is_random = current_mode == "random"

        self.grid_a = Grid(self.GRID_WIDTH, self.GRID_HEIGHT, randomize=is_random)
        self.grid_b = Grid(self.GRID_WIDTH, self.GRID_HEIGHT)
        self.display_grid = self.grid_a
        self.compute_grid = self.grid_b

        if current_mode in PATTERNS:
            pattern = PATTERNS[current_mode]
            # Center the pattern
            max_w = max(p[0] for p in pattern.shape)
            max_h = max(p[1] for p in pattern.shape)
            start_x = (self.GRID_WIDTH - max_w) // 2
            start_y = (self.GRID_HEIGHT - max_h) // 2
            self.grid_a.place_pattern(pattern, start_x, start_y)

        elif current_mode == "full":
            self.grid_a.fill()

        # Draws the first grid to the screen
        for y in range(self.GRID_HEIGHT):
            for x in range(self.GRID_WIDTH):
                state = self.display_grid.get_cell_state(x, y)
                if state == 1:
                    self.draw_cell(x, y, self.live_color)

        self.frame_number = 0
        self.page.replace_screen()


    def switch_to_foreground(self):
        print("GoL: Switching to foreground.")
        super().switch_to_foreground()
        self.app_state = self.app_states.index("MAIN_MENU")
        self.setup_menu_screen()

    def switch_to_background(self):
        print("GoL: Switching to background.")
        super().switch_to_background()
        self.cell_objects = None
        self.page = None
        self.selection_labels = []
        self.camera_trigger_pin.value(0) # Ensure trigger is off

    def draw_cell(self, x, y, color):
        """Draws a single cell on the canvas."""
        self.cell_objects[y][x].set_style_bg_color(color, 0)

    def compute_and_draw_next_gen(self):
        """Computes the next generation into the compute_grid, draws changed cells, and swaps grids."""
        # 1. Compute next generation and draw changed cells in a single pass
        for y in range(self.GRID_HEIGHT):
            for x in range(self.GRID_WIDTH):
                neighbors = self.count_neighbors(self.display_grid, x, y)
                old_state = self.display_grid.get_cell_state(x, y)
                new_state = old_state

                if old_state == 1 and (neighbors < 2 or neighbors > 3):
                    new_state = 0  # Dies
                elif old_state == 0 and neighbors == 3:
                    new_state = 1  # Becomes alive

                self.compute_grid.set_cell_state(x, y, new_state)

                if new_state != old_state:
                    self.draw_cell(x, y, self.live_color if new_state == 1 else self.dead_color)

        # 2. Swap buffers
        temp = self.display_grid
        self.display_grid = self.compute_grid
        self.compute_grid = temp

    def count_neighbors(self, grid, x, y):
        """Counts the number of live neighbors for a given cell."""
        count = 0
        for i in range(-1, 2):
            for j in range(-1, 2):
                if i == 0 and j == 0:
                    continue

                # Toroidal grid (wraps around)
                col = (x + i + self.GRID_WIDTH) % self.GRID_WIDTH
                row = (y + j + self.GRID_HEIGHT) % self.GRID_HEIGHT
                count += grid.get_cell_state(col, row)
        return count
