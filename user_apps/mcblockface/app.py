"""BlockyBlockMcBlockFace game logic.

"""

try:
    import utime as time  # type: ignore
except ImportError:  # pragma: no cover - desktop type checking
    import time  # type: ignore

try:
    import urandom as random  # type: ignore
except ImportError:  # pragma: no cover
    import random  # type: ignore

import lvgl  # type: ignore
import uasyncio as aio  # type: ignore

try:
    from uasyncio import CancelledError  # type: ignore
except (ImportError, AttributeError):
    CancelledError = Exception  # type: ignore[misc]

from apps.base_app import BaseApp
from net.net import register_receiver, send, BROADCAST_ADDRESS
from net.protocols import Protocol, NetworkFrame
from ui.page import Page, SCREEN_HEIGHT, SCREEN_WIDTH
import ui.styles as styles

if False:  # pragma: no cover - reserved for future networking hooks
    _ = (register_receiver, send, BROADCAST_ADDRESS, Protocol, NetworkFrame)

# Piece identifiers match the original watch firmware for easier diffing.
BLOCK_L = 0
BLOCK_J = 1
BLOCK_O = 2
BLOCK_I = 3
BLOCK_T = 4
BLOCK_S = 5
BLOCK_Z = 6
BLOCK_NUM_PIECES = 7

# Bit patterns copied from pieces.cpp; each byte encodes two 4-cell rows.
PIECE_MASKS = (
    0x2E,  # L
    0x8E,  # J
    0x66,  # O
    0x0F,  # I
    0x4E,  # T
    0xC6,  # S
    0x6C,  # Z
)

BOARD_WIDTH = 10
BOARD_HEIGHT = 20
EMPTY_SENTINEL = 7  # Matches firmware sentinel value.

GRAVITY_MS = 300  # Slower baseline gravity for level 1.
ROTATE_COOLDOWN_MS = 100
LINE_CLEAR_DELAY_MS = 200

CELL_SIZE = max(4, SCREEN_HEIGHT // BOARD_WIDTH)
CANVAS_WIDTH = BOARD_WIDTH * CELL_SIZE
CANVAS_HEIGHT = BOARD_HEIGHT * CELL_SIZE
# Align the 20-row playfield along the long axis (original screen width) and keep a gutter for HUD text.
BOARD_HORIZONTAL_MARGIN = max(0, (SCREEN_HEIGHT - CANVAS_WIDTH) // 2)
BASE_HORIZONTAL_OFFSET = max(0, (SCREEN_WIDTH - CANVAS_HEIGHT) // 2)
SCOREBOARD_GUTTER = 40
BOARD_VERTICAL_OFFSET = min(SCREEN_WIDTH - CANVAS_HEIGHT, BASE_HORIZONTAL_OFFSET + SCOREBOARD_GUTTER)
CONTAINER_WIDTH = SCREEN_WIDTH
CONTAINER_HEIGHT = SCREEN_HEIGHT
BOARD_BG_COLOR = lvgl.color_hex(0x0B1018)
EMPTY_CELL_COLOR = lvgl.color_hex(0x1E2C40)
ACTIVE_CELL_COLOR = lvgl.color_hex(0xF4F8FB)

PIECE_COLORS = (
    lvgl.color_hex(0xF68C1E),  # L - orange
    lvgl.color_hex(0x1E3A8A),  # J - darker blue
    lvgl.color_hex(0xFFD93B),  # O - yellow
    lvgl.color_hex(0x6AD5FF),  # I - lighter blue
    lvgl.color_hex(0xCC3ED0),  # T - magenta
    lvgl.color_hex(0x4FCB68),  # S - green
    lvgl.color_hex(0xFF4D4D),  # Z - red
)
def _get_layout_constant(name):
    """Resolve LVGL layout constants across legacy bindings."""
    layout_group = getattr(lvgl, "LAYOUT", None)
    if layout_group:
        value = getattr(layout_group, name, None)
        if value is not None:
            return value
    return getattr(lvgl, f"LAYOUT_{name}", None)


def _get_obj_flag(name):
    """Resolve LVGL object flag constants."""
    obj_cls = getattr(lvgl, "obj", None)
    if obj_cls:
        flag_group = getattr(obj_cls, "FLAG", None)
        if flag_group:
            value = getattr(flag_group, name, None)
            if value is not None:
                return value
    return getattr(lvgl, f"OBJ_FLAG_{name}", None)


def _set_scrollbar_off(widget):
    """Disable scrollbars on a widget across LVGL versions."""
    mode_off = None
    mode_group = getattr(lvgl, "SCROLLBAR_MODE", None)
    if mode_group:
        mode_off = getattr(mode_group, "OFF", None)
    if mode_off is None:
        enum = getattr(lvgl, "scrollbar_mode_t", None)
        if enum:
            mode_off = getattr(enum, "OFF", None)
    if mode_off is None:
        mode_off = getattr(lvgl, "SCROLLBAR_MODE_OFF", None)
    if mode_off is None:
        return
    setter = getattr(widget, "set_scrollbar_mode", None)
    if setter:
        setter(mode_off)
    else:
        try:
            lvgl.obj_set_scrollbar_mode(widget, mode_off)
        except AttributeError:
            pass


def _calc_occupation(piece, x, y, rotation):
    """Replicates calc_occupation from pieces.cpp."""

    mask = PIECE_MASKS[piece]
    coords = []

    if rotation == 0 or piece == BLOCK_O:
        cur_x = x
        cur_y = y
        for i in range(4):
            if mask & (0x80 >> i):
                coords.append((cur_x, cur_y))
            cur_x += 1
        cur_x = x
        cur_y += 1
        for i in range(4, 8):
            if mask & (0x80 >> i):
                coords.append((cur_x, cur_y))
            cur_x += 1
            if len(coords) == 4:
                break
    elif rotation == 1:
        cur_y = y
        cur_x = x + (2 if piece == BLOCK_I else 1)
        for i in range(4, 8):
            if mask & (0x80 >> i):
                coords.append((cur_x, cur_y))
            cur_y += 1
        cur_y = y
        cur_x += 1
        for i in range(4):
            if mask & (0x80 >> i):
                coords.append((cur_x, cur_y))
            cur_y += 1
            if len(coords) == 4:
                break
    elif rotation == 2:
        if piece == BLOCK_I:
            cur_x = x
            cur_y = y + 2
        else:
            cur_x = x - 1
            cur_y = y + 1
        for i in range(7, 3, -1):
            if mask & (0x80 >> i):
                coords.append((cur_x, cur_y))
            cur_x += 1
        cur_x = x - 1
        cur_y += 1
        for i in range(3, -1, -1):
            if mask & (0x80 >> i):
                coords.append((cur_x, cur_y))
            cur_x += 1
            if len(coords) == 4:
                break
    else:  # rotation == 3
        cur_x = x
        cur_y = y - 1
        for i in range(3, -1, -1):
            if mask & (0x80 >> i):
                coords.append((cur_x, cur_y))
            cur_y += 1
        cur_x += 1
        cur_y = y - 1
        for i in range(7, 3, -1):
            if mask & (0x80 >> i):
                coords.append((cur_x, cur_y))
            cur_y += 1
            if len(coords) == 4:
                break
    return coords


def _rand_piece():
    if hasattr(random, "getrandbits"):
        return random.getrandbits(8) % BLOCK_NUM_PIECES
    return random.randrange(BLOCK_NUM_PIECES)  # type: ignore


class App(BaseApp):
    """Falling-block gameplay with a simple LVGL grid renderer."""

    def __init__(self, name, badge):
        super().__init__(name, badge)
        self.page = None
        self.board_container = None
        self.board_cells = []
        self.status_label = None
        self.score_label = None
        self._input_task = None
        self._render_cache = []

        self.foreground_sleep_ms = 4
        self.background_sleep_ms = 600

        self.board = []
        self.current_piece = None
        self.next_piece = None
        self.piece_x = 4
        self.piece_y = 0
        self.piece_rot = 0
        self.active_cells = []

        self.state = "idle"  # idle | falling | clearing | game_over
        self.lines_cleared = 0
        self.level = 1
        self.score = 0
        self.lines_pending = []
        self.clear_started_ms = 0

        now = time.ticks_ms()
        self.last_gravity_ms = now
        self.last_rotate_ms = now
        self.board_dirty = True

    def start(self):
        super().start()
        # register_receiver(NEW_PROTOCOL, self.receive_message)

    # ------------------------------------------------------------------ #
    # App lifecycle

    def switch_to_foreground(self):
        super().switch_to_foreground()
        self._build_ui()
        self._set_status("F1 start | .← 5→ | 2↓ | 7⟲ 8⟳")

    def switch_to_background(self):
        self._teardown_ui()
        super().switch_to_background()

    def run_foreground(self):
        now = time.ticks_ms()
        self.update(now)
        self._refresh_board()

    def run_background(self):
        super().run_background()

    # ------------------------------------------------------------------ #
    # Inputs & UI

    def _build_ui(self):
        self._teardown_ui()
        self.page = Page()
        self.page.create_content()
        _set_scrollbar_off(self.page.content)

        self.board_container = None
        self.board_cells = []
        self.board_container = lvgl.obj(self.page.content)
        self.board_container.add_style(styles.content_style, 0)
        self.board_container.set_style_radius(0, 0)
        self.board_container.set_size(CONTAINER_WIDTH, CONTAINER_HEIGHT)
        layout_off = _get_layout_constant("OFF")
        if layout_off is not None and hasattr(self.board_container, "set_layout"):
            self.board_container.set_layout(layout_off)
        _set_scrollbar_off(self.board_container)
        scroll_flag = _get_obj_flag("SCROLLABLE")
        if scroll_flag is not None:
            if hasattr(self.board_container, "clear_flag"):
                self.board_container.clear_flag(scroll_flag)
            else:
                try:
                    lvgl.obj_clear_flag(self.board_container, scroll_flag)
                except AttributeError:
                    pass
        self.board_container.set_style_pad_all(0, 0)
        self.board_container.set_style_border_width(0, 0)
        self.board_container.set_style_bg_color(BOARD_BG_COLOR, 0)
        self.board_container.set_style_bg_opa(lvgl.OPA.COVER, 0)
        if hasattr(self.board_container, "align"):
            self.board_container.align(lvgl.ALIGN.CENTER, 0, 0)
        else:
            try:
                lvgl.obj_align(self.board_container, lvgl.ALIGN.CENTER, 0, 0)
            except AttributeError:
                pass

        for y in range(BOARD_HEIGHT):
            row = []
            for x in range(BOARD_WIDTH):
                cell = lvgl.obj(self.board_container)
                if hasattr(cell, "set_size"):
                    cell.set_size(CELL_SIZE, CELL_SIZE)
                else:
                    cell.set_width(CELL_SIZE)
                    cell.set_height(CELL_SIZE)
                pixel_x = BOARD_VERTICAL_OFFSET + y * CELL_SIZE
                pixel_y = BOARD_HORIZONTAL_MARGIN + (BOARD_WIDTH - 1 - x) * CELL_SIZE
                cell.set_pos(pixel_x, pixel_y)
                cell.set_style_pad_all(0, 0)
                cell.set_style_border_width(0, 0)
                cell.set_style_radius(0, 0)
                cell.set_style_bg_color(EMPTY_CELL_COLOR, 0)
                cell.set_style_bg_opa(lvgl.OPA.COVER, 0)
                _set_scrollbar_off(cell)
                if scroll_flag is not None:
                    if hasattr(cell, "clear_flag"):
                        cell.clear_flag(scroll_flag)
                    else:
                        try:
                            lvgl.obj_clear_flag(cell, scroll_flag)
                        except AttributeError:
                            pass
                row.append(cell)
            self.board_cells.append(row)
        self._render_cache = [[None for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]

        self.score_label = lvgl.label(self.page.content)
        self.score_label.add_style(styles.content_style, 0)
        _set_scrollbar_off(self.score_label)
        if hasattr(self.score_label, "align"):
            self.score_label.align(lvgl.ALIGN.TOP_LEFT, 4, 4)
        else:
            try:
                lvgl.obj_align(self.score_label, lvgl.ALIGN.TOP_LEFT, 4, 4)
            except AttributeError:
                pass

        self.status_label = lvgl.label(self.page.content)
        self.status_label.add_style(styles.content_style, 0)
        _set_scrollbar_off(self.status_label)
        if hasattr(self.status_label, "align"):
            self.status_label.align(lvgl.ALIGN.BOTTOM_LEFT, 4, -4)
        else:
            try:
                lvgl.obj_align(self.status_label, lvgl.ALIGN.BOTTOM_LEFT, 4, -4)
            except AttributeError:
                pass

        self.page.replace_screen()
        self._update_infobar()
        self.board_dirty = True
        self._refresh_board()
        self._start_input_loop()

    def _teardown_ui(self):
        self._stop_input_loop()
        if self.page:
            self.page.delete()
        self.page = None
        if self.board_container:
            self.board_container.delete()
        self.board_container = None
        self.board_cells = []
        self.score_label = None
        self.status_label = None
        self._render_cache = []

    def _start_input_loop(self):
        if self._input_task:
            return
        self._input_task = aio.create_task(self._input_loop())

    def _stop_input_loop(self):
        task = self._input_task
        if not task:
            return
        self._input_task = None
        try:
            task.cancel()
        except AttributeError:
            pass

    def _exit_to_background(self):
        if not self.active_foreground:
            return
        self.badge.display.clear()
        self.switch_to_background()

    def _handle_key_press(self, key):
        if key in (".", ">", self.badge.keyboard.LEFT):
            self.move_piece(-1)
        elif key in ("5", "%", self.badge.keyboard.RIGHT):
            self.move_piece(1)
        elif key in ("2", "@", self.badge.keyboard.DOWN):
            self.drop_piece()
        elif key in ("7", "&", self.badge.keyboard.UP):
            self.rotate_piece(-1)
        elif key in ("8", "*"):
            self.rotate_piece(1)
        elif key == self.badge.keyboard.ESC:
            self._exit_to_background()

    async def _input_loop(self):
        try:
            while self.active_foreground:
                if self.badge.keyboard.f1():
                    self.start_new_game()
                    await aio.sleep_ms(0)
                    continue
                if self.badge.keyboard.f5():
                    self._exit_to_background()
                    break
                key = self.badge.keyboard.read_key()
                if key is None:
                    await aio.sleep_ms(1)
                    continue
                self._handle_key_press(key)
                await aio.sleep_ms(0)
        except CancelledError:
            pass
        finally:
            self._input_task = None

    def _set_status(self, message):
        if self.status_label:
            self.status_label.set_text(message)

    def _update_infobar(self):
        if self.score_label:
            self.score_label.set_text(f"L{self.lines_cleared} Lv{self.level}")

    def _refresh_board(self):
        if not self.board_dirty:
            return
        if self.board:
            grid = [row[:] for row in self.board]
        else:
            grid = [[EMPTY_SENTINEL for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]
        for x, y in self.active_cells:
            if 0 <= y < BOARD_HEIGHT and 0 <= x < BOARD_WIDTH:
                grid[y][x] = 8
        if self.board_cells:
            if not self._render_cache or len(self._render_cache) != BOARD_HEIGHT:
                self._render_cache = [[None for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]
            for y, row in enumerate(grid):
                for x, occupant in enumerate(row):
                    if self._render_cache[y][x] == occupant:
                        continue
                    self._render_cache[y][x] = occupant
                    if occupant == EMPTY_SENTINEL:
                        color = EMPTY_CELL_COLOR
                    elif occupant == 8:
                        if self.current_piece is None:
                            color = ACTIVE_CELL_COLOR
                        else:
                            color = PIECE_COLORS[self.current_piece]
                    else:
                        color = PIECE_COLORS[occupant]
                    try:
                        self.board_cells[y][x].set_style_bg_color(color, 0)
                    except IndexError:
                        pass
        self.board_dirty = False

    # ------------------------------------------------------------------ #
    # Game logic

    def start_new_game(self):
        self.board = [[EMPTY_SENTINEL for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]
        self.lines_cleared = 0
        self.level = 1
        self.score = 0
        self.state = "falling"
        self.current_piece = _rand_piece()
        self.next_piece = _rand_piece()
        self.piece_x = 4
        self.piece_y = 0
        self.piece_rot = 0
        self.active_cells = _calc_occupation(self.current_piece, self.piece_x, self.piece_y, self.piece_rot)
        self.lines_pending = []
        self.clear_started_ms = 0
        now = time.ticks_ms()
        self.last_gravity_ms = now
        self.last_rotate_ms = now
        self.board_dirty = True
        self._update_infobar()
        if not self._can_place(self.active_cells):
            self._trigger_game_over()
        else:
            self._set_status("Game on! .← 5→ 2↓ 7⟲ 8⟳")

    def update(self, now):
        if self.state == "idle" or self.state == "game_over":
            return
        if self.state == "clearing":
            if time.ticks_diff(now, self.clear_started_ms) >= LINE_CLEAR_DELAY_MS:
                self._apply_line_clear()
                if not self._spawn_next_piece():
                    self._trigger_game_over()
            return

        # Falling state
        gravity_interval = max(100, GRAVITY_MS - (self.level - 1) * 12)
        if time.ticks_diff(now, self.last_gravity_ms) >= gravity_interval:
            self.last_gravity_ms = now
            if not self._try_step_down():
                self._lock_piece()
                if self.lines_pending:
                    self.state = "clearing"
                    self.clear_started_ms = now
                else:
                    if not self._spawn_next_piece():
                        self._trigger_game_over()

    def move_piece(self, delta):
        if self.state != "falling":
            return
        new_cells = _calc_occupation(self.current_piece, self.piece_x + delta, self.piece_y, self.piece_rot)
        if self._can_place(new_cells):
            self.piece_x += delta
            self.active_cells = new_cells
            self.board_dirty = True

    def rotate_piece(self, direction=1):
        if self.state != "falling":
            return
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_rotate_ms) < ROTATE_COOLDOWN_MS:
            return
        self.last_rotate_ms = now
        candidate_rot = (self.piece_rot + direction) % 4
        if self._try_rotate(candidate_rot):
            self.piece_rot = candidate_rot
            self.board_dirty = True

    def drop_piece(self, hard=False):
        if self.state != "falling":
            return
        moved = False
        if hard:
            while self._try_step_down():
                moved = True
            if not moved:
                # Hard drop without movement still locks immediately.
                self._lock_piece()
                now = time.ticks_ms()
                if self.lines_pending:
                    self.state = "clearing"
                    self.clear_started_ms = now
                else:
                    if not self._spawn_next_piece():
                        self._trigger_game_over()
        else:
            steps = 2
            while steps and self._try_step_down():
                moved = True
                steps -= 1
            if not moved:
                self._lock_piece()
                now = time.ticks_ms()
                if self.lines_pending:
                    self.state = "clearing"
                    self.clear_started_ms = now
                else:
                    if not self._spawn_next_piece():
                        self._trigger_game_over()
        if moved:
            self.board_dirty = True

    # ------------------------------------------------------------------ #
    # Helpers

    def _try_rotate(self, candidate_rot):
        base_cells = _calc_occupation(self.current_piece, self.piece_x, self.piece_y, candidate_rot)
        if self._can_place(base_cells):
            self.active_cells = base_cells
            return True
        # Wall kicks: try left then right.
        for offset in (-1, 1):
            adjusted_cells = _calc_occupation(self.current_piece, self.piece_x + offset, self.piece_y, candidate_rot)
            if self._can_place(adjusted_cells):
                self.piece_x += offset
                self.active_cells = adjusted_cells
                return True
        return False

    def _try_step_down(self):
        new_cells = _calc_occupation(self.current_piece, self.piece_x, self.piece_y + 1, self.piece_rot)
        if self._can_place(new_cells):
            self.piece_y += 1
            self.active_cells = new_cells
            self.board_dirty = True
            return True
        return False

    def _can_place(self, cells):
        for x, y in cells:
            if x < 0 or x >= BOARD_WIDTH:
                return False
            if y < 0:
                return False
            if y >= BOARD_HEIGHT:
                return False
            if self.board[y][x] != EMPTY_SENTINEL:
                return False
        return True

    def _lock_piece(self):
        for x, y in self.active_cells:
            if y < 0:
                self._trigger_game_over()
                return
            if 0 <= y < BOARD_HEIGHT:
                self.board[y][x] = self.current_piece
        full_rows = [
            idx
            for idx, row in enumerate(self.board)
            if all(cell != EMPTY_SENTINEL for cell in row)
        ]
        self.lines_pending = full_rows
        self.board_dirty = True

    def _apply_line_clear(self):
        cleared = len(self.lines_pending)
        if cleared == 0:
            return
        for row in sorted(self.lines_pending, reverse=True):
            del self.board[row]
            self.board.insert(0, [EMPTY_SENTINEL for _ in range(BOARD_WIDTH)])
        self.lines_cleared += cleared
        self.level = 1 + self.lines_cleared // 10
        self.score += cleared * 100 * self.level
        self.lines_pending = []
        self.board_dirty = True
        self._render_cache = []
        self._update_infobar()
        self._set_status(f"Cleared {cleared} line(s)! Score {self.score}")

    def _spawn_next_piece(self):
        self.current_piece = self.next_piece
        self.next_piece = _rand_piece()
        self.piece_x = 4
        self.piece_y = 0
        self.piece_rot = 0
        self.active_cells = _calc_occupation(self.current_piece, self.piece_x, self.piece_y, self.piece_rot)
        self.state = "falling"
        self.last_gravity_ms = time.ticks_ms()
        self.board_dirty = True
        if not self._can_place(self.active_cells):
            return False
        self._set_status("New piece spawned")
        return True

    def _trigger_game_over(self):
        self.state = "game_over"
        self._set_status("Game over — press F1 to restart")
        self.board_dirty = True
