import gc
import lvgl 
from ui import graphics
from ui import styles
from micropython import const
from ui.page import Page


INTEREST_LEVELS = {"UNKNOWN": 0, "ATTEND": 1, "MAYBE": 2, "SKIP": 3}


class Talk(Page):
    """ Talk dict is a dictionary with:
        speaker, title, headshot, abstract, time, and stage defined """
    
    def __init__(self, talk_dict, menubar_labels):
        super().__init__()
        self.create_content()
        self.create_menubar(menubar_labels)

        self.headshot_box = graphics.create_image(talk_dict["headshot"], self.content)
        self.headshot_box.set_style_radius(40, 0) ## circle at 100x100
        self.headshot_box.align(lvgl.ALIGN.RIGHT_MID, -10, 0)  # align right, center

        line_one = lvgl.obj(self.content)
        line_one.add_style(styles.base_style,0)
        line_one.set_height(20)
        line_one.set_width(310)
        line_one.align(lvgl.ALIGN.TOP_LEFT, 10, 5)
        
        line_two = lvgl.obj(self.content)
        line_two.add_style(styles.base_style,0)
        line_two.set_height(20)
        line_two.set_width(300)
        line_two.align(lvgl.ALIGN.TOP_LEFT, 10, 25)

        self.speaker_line = lvgl.label(line_one)
        self.speaker_line.align(lvgl.ALIGN.TOP_LEFT, 0, 0)
        self.speaker_line.set_text(talk_dict["speaker"])
        self.speaker_line.set_style_text_font(lvgl.font_montserrat_14, 0)

        self.time_line = lvgl.label(line_one)
        self.time_line.align(lvgl.ALIGN.TOP_RIGHT, 0, 0)
        self.time_line.set_text(talk_dict["time"])
        self.time_line.set_style_text_font(lvgl.font_montserrat_14, 0)

        self.title_line = lvgl.label(line_two)
        self.title_line.align(lvgl.ALIGN.TOP_LEFT, 0, 0)
        self.title_line.set_text(talk_dict["title"])
        self.title_line.set_style_text_font(lvgl.font_montserrat_14, 0)

        #self.stage_line = lvgl.label(line_two)
        #self.stage_line.align(lvgl.ALIGN.TOP_RIGHT, 0, 0)
        #self.stage_line.set_text(talk_dict["stage"])
        #self.stage_line.set_style_text_font(lvgl.font_montserrat_14, 0)

        self.abstract_ta = lvgl.textarea(self.content)
        self.abstract_ta.align_to(line_two, lvgl.ALIGN.OUT_BOTTOM_MID, -30, 0)
        self.abstract_ta.set_style_bg_color(styles.lcd_color_bg, 0)
        self.abstract_ta.set_style_text_color(styles.lcd_color_fg, 0)
        self.abstract_ta.set_scrollbar_mode(0)
        self.abstract_ta.set_style_border_width(0,0)
        self.abstract_ta.set_style_text_font(lvgl.font_montserrat_12, 0)
        self.abstract_ta.set_size(300,80)
        self.abstract_ta.set_text(talk_dict["abstract"])
        
        self.apply_interest_coloring(talk_dict)


    def update(self, talk_dict):
        if self.headshot_box:
            self.headshot_box.delete()
            self.headshot_box = None
        self.headshot_box = graphics.create_image(talk_dict["headshot"], self.content)
        self.headshot_box.set_style_radius(40, 0) ## circle at 100x100
        self.headshot_box.align(lvgl.ALIGN.RIGHT_MID, -10, 0)  # align right, center
        self.speaker_line.set_text(talk_dict["speaker"])
        self.time_line.set_text(talk_dict["time"])
        self.title_line.set_text(talk_dict["title"])
        #self.stage_line.set_text(talk_dict["stage"])
        self.abstract_ta.set_text(talk_dict["abstract"])
        
        self.apply_interest_coloring(talk_dict)
        
    
    def apply_interest_coloring(self, talk_dict):
        if int(talk_dict["interest"]) == INTEREST_LEVELS["ATTEND"]:
            self.abstract_ta.set_style_bg_color(styles.lvg_color_green, 0)
            self.abstract_ta.set_style_text_color(styles.hackaday_white, 0)
        elif int(talk_dict["interest"]) == INTEREST_LEVELS["MAYBE"]:
            self.abstract_ta.set_style_bg_color(styles.hackaday_yellow, 0)
            self.abstract_ta.set_style_text_color(styles.lvg_color_black, 0)
        elif int(talk_dict["interest"]) == INTEREST_LEVELS["SKIP"]:
            self.abstract_ta.set_style_bg_color(styles.lvg_color_red, 0)
            self.abstract_ta.set_style_text_color(styles.hackaday_white, 0)
        else:
            self.abstract_ta.set_style_bg_color(styles.lcd_color_bg, 0)
            self.abstract_ta.set_style_text_color(styles.lvg_color_black, 0)


    def update_menu(self, menubar_labels):
        self.create_content()
        self.create_menubar(menubar_labels)
# EOF
