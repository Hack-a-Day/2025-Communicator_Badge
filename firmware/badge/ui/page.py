import lvgl
from micropython import const
from ui import styles

SCREEN_WIDTH = const(428)
SCREEN_HEIGHT = const(142)
MENU_HEIGHT = const(20)
INFOBAR_HEIGHT = const(14)


class Page:
    """Base class for all kinds of screens. Defines a bunch of common elements.
    Pages.py inheirits from this, and creates the individual pages with their specific elements.
    infobar and menubar have fixed height, all other elements fill out between them.
    Because of the way they are packed, they need to be called a top-down order and at least
    some kind of content (do we _need_ menubar?)"""

    def __init__(self):
        self.scr = lvgl.obj()
        self.scr.set_scrollbar_mode(0)
        self.scr.add_style(styles.base_style, 0)

        self.flex_container = lvgl.obj(self.scr)
        ## totally fill the screen with a flex-align box
        self.flex_container.set_width(lvgl.pct(100))
        self.flex_container.set_height(lvgl.pct(100))
        self.flex_container.set_scrollbar_mode(0)
        self.flex_container.add_style(styles.base_style, 0)
        self.flex_container.set_flex_flow(lvgl.FLEX_FLOW.COLUMN)
        self.flex_container.set_flex_align(
            lvgl.FLEX_ALIGN.START, lvgl.FLEX_ALIGN.START, lvgl.FLEX_ALIGN.START
        )

    def create_infobar(self, infobar_content):
        self.infobar = lvgl.obj(self.flex_container)
        self.infobar.align(lvgl.ALIGN.TOP_LEFT, 0, 5)
        self.infobar.add_style(styles.infobar_style, 0)
        self.infobar.set_width(lvgl.pct(100))
        self.infobar.set_height(INFOBAR_HEIGHT)

        self.infobar_left = lvgl.label(self.infobar)
        self.infobar_left.add_style(styles.infobar_style, 0)
        self.infobar_left.align(lvgl.ALIGN.TOP_LEFT, 10, 0)
        self.infobar_left.set_text(infobar_content[0])

        self.infobar_right = lvgl.label(self.infobar)
        self.infobar_right.add_style(styles.infobar_style, 0)
        self.infobar_right.align(lvgl.ALIGN.TOP_RIGHT, -10, 0)
        self.infobar_right.set_text(infobar_content[1])

    def create_content(self):
        self.content = lvgl.obj(self.flex_container)
        self.content.set_scrollbar_mode(0)
        self.content.add_style(styles.content_style, 0)
        self.content.set_width(SCREEN_WIDTH)
        self.content.set_flex_grow(1)

    def add_message_rows(self, message_count, left_width=80):
        left_pad = 5
        self.message_rows = lvgl.table(self.content)
        self.message_rows.add_style(styles.content_style, 0)
        self.message_rows.add_style(styles.content_style, lvgl.PART.ITEMS)

        self.message_rows.set_style_pad_top(0, lvgl.PART.ITEMS)
        self.message_rows.set_style_pad_bottom(0, lvgl.PART.ITEMS)
        self.message_rows.set_style_pad_left(left_pad, lvgl.PART.ITEMS)

        self.message_rows.set_row_count(message_count)
        self.message_rows.set_width(lvgl.pct(100))
        self.message_rows.set_height(lvgl.pct(100))

        ## Set up two columns: sender, message
        self.message_rows.set_column_count(2)
        self.message_rows.set_column_width(0, left_width)
        self.message_rows.set_column_width(1, self.scr.get_x2() - left_width - left_pad)
        self.selected_row = None
 
    def populate_message_rows(self, messages):  ## Populate
        self.message_rows.set_row_count(len(messages))
        for i, message in enumerate(messages):
            self.message_rows.set_cell_value(i, 0, str(message[0]))
            self.message_rows.set_cell_value(i, 1, str(message[1]))
        if self.selected_row is None and len(messages):
            self.selected_row = len(messages) - 1
            self.message_rows.set_selected_cell(self.selected_row, 0)
        if self.selected_row == len(messages) - 1:
            self.scroll_down()  # Follow the bottom

    def scroll_up(self, pixels=13):
        self.message_rows.scroll_by_bounded(0, pixels, False)

    def scroll_down(self, pixels=13):
        self.message_rows.scroll_by_bounded(0, -1 * pixels, False)

    def scroll_bottom(self):
        dy_to_bottom = self.message_rows.get_scroll_bottom()
        self.message_rows.scroll_by_bounded(0, -1 * dy_to_bottom, False)

    def create_text_box(self, default_text="", one_line=False, char_limit=0):

        self.text_box = lvgl.textarea(self.content)
        self.text_box.add_style(styles.infobar_style, 0)
        self.text_box.set_height(lvgl.pct(80))
        self.text_box.set_width(lvgl.pct(80))
        self.text_box.align(lvgl.ALIGN.CENTER, 0, 0)
        self.text_box.set_style_border_width(2, 0)
        self.text_box.set_style_pad_all(5, 0)
        self.text_box.set_text(default_text)
        self.text_box.set_one_line(one_line)
        cursor_style = lvgl.style_t()
        self.text_box.set_style_border_color(styles.lcd_color_fg, lvgl.PART.CURSOR | lvgl.STATE.FOCUSED)
        self.text_box.add_state(lvgl.STATE.FOCUSED)

        self.tb_char_limit = char_limit

    def close_text_box(self) -> str:
        text = self.text_box.get_text()
        text = text.strip()
        self.text_box.delete()
        return text
    
    def text_box_type(self, keyboard):
        key = keyboard.read_key()
        text = self.text_box.get_text()
        if key is None:
            return None, text
        if key == keyboard.LEFT:
            self.text_box.cursor_left()
        elif key == keyboard.RIGHT:
            self.text_box.cursor_right()
        elif key == keyboard.UP:
            self.text_box.cursor_up()
        elif key == keyboard.DOWN:
            self.text_box.cursor_down()
        elif key == keyboard.BS:  # Backspace
            self.text_box.delete_char()
        elif key == keyboard.DEL:  # Delete
            self.text_box.delete_char_forward()
        else:
            self.text_box.add_text(key)
        return key, text

    def create_menubar(self, menubar_labels):
        self.menubar = lvgl.obj(self.flex_container)
        self.menubar.set_width(lvgl.pct(100))
        self.menubar.set_height(MENU_HEIGHT)
        self.menubar.add_style(styles.menubar_style, 0)
        self.menubar_buttons = [lvgl.button(self.menubar) for x in range(5)]
        for i in range(5):
            self.menubar_buttons[i].add_style(styles.menubar_style, 0)
            self.menubar_buttons[i].set_style_text_align(lvgl.ALIGN.CENTER, 0)
            btn_label = lvgl.label(self.menubar_buttons[i])
            btn_label.set_text(menubar_labels[i])
        self.menubar.update_layout()
        self._align_menubar_buttons()
        self.menubar.align(lvgl.ALIGN.BOTTOM_MID, 0, 0)

    def _align_menubar_buttons(self):
        ## Tricky b/c buttons aren't in a reasonable place,
        ## want to get as close to centered as possible, but not wrap off screen
        self.menubar_buttons[0].align(lvgl.ALIGN.BOTTOM_LEFT, 0, 0)
        self.menubar_buttons[1].align(
            lvgl.ALIGN.BOTTOM_LEFT,
            112 - self.get_menubar_button_label(1).get_width() // 2,
            0,
        )
        self.menubar_buttons[2].align(lvgl.ALIGN.BOTTOM_MID, 0, 0)
        self.menubar_buttons[3].align(
            lvgl.ALIGN.BOTTOM_LEFT,
            312 - self.get_menubar_button_label(3).get_width() // 2,
            0,
        )
        self.menubar_buttons[4].align(lvgl.ALIGN.BOTTOM_RIGHT, 0, 0)

    def get_menubar_button_label(self, which_button):
        ## Note: can address button labels through button.get_child(0)
        return self.menubar_buttons[which_button].get_child(0)

    def set_menubar_button_label(self, which_button, text):
        ## Note: can address button labels through button.get_child(0)
        button_label = self.menubar_buttons[which_button].get_child(0)
        button_label.set_text(text)
        self.menubar.update_layout()
        self._align_menubar_buttons()

    def replace_screen(self):
        old_screen = lvgl.screen_active()
        lvgl.screen_load(self.scr)
        old_screen.delete()

    def delete(self):
        self.scr.delete()
