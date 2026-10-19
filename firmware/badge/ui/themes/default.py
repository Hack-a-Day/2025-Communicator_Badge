"""
Default style from the 2025 Supercon and 2026 Hackaday Europe
"""

import lvgl



""" Colors """

# Keep these default color names in case some app import them directly

lcd_color_bg      = lvgl.color_hex(0xabc5a0)
lcd_color_fg      = lvgl.color_hex(0x292b29)
lcd_color_fg_dark = lvgl.color_hex(0x080908)


hackaday_grey   = lvgl.color_hex(0x1a1a1a)
hackaday_yellow = lvgl.color_hex(0xe39810) ## adjusted for screen gamma
hackaday_white  = lvgl.color_hex(0xffffff)

# Some colors
lvg_color_black  	= lvgl.color_hex(0x000000)
lvg_color_red   	= lvgl.color_hex(0x990000)
lvg_color_green 	= lvgl.color_hex(0x006600)



""" Styles for the UI elements """

# Base style
base_style = lvgl.style_t()
base_style.init()
base_style.set_text_font(lvgl.font_montserrat_12)
base_style.set_bg_color(lcd_color_bg)
base_style.set_text_color(lcd_color_fg)
base_style.set_radius(0)
base_style.set_border_width(0)
base_style.set_pad_all(0)

# Content
content_style = lvgl.style_t()
content_style.init()
content_style.set_text_font(lvgl.font_montserrat_12)
content_style.set_bg_color(lcd_color_bg)
content_style.set_text_color(lcd_color_fg)
content_style.set_radius(0)
content_style.set_border_width(0)
content_style.set_pad_all(0)

# Menubar
menubar_style = lvgl.style_t()
menubar_style.init()
menubar_style.set_text_font(lvgl.font_montserrat_16)
menubar_style.set_bg_color(lcd_color_fg)
menubar_style.set_text_color(lcd_color_bg)
menubar_style.set_radius(0)
menubar_style.set_border_width(0)
menubar_style.set_pad_all(0)

# Infobar
infobar_style = lvgl.style_t()
infobar_style.init()
infobar_style.set_text_font(lvgl.font_montserrat_14)
infobar_style.set_bg_color(lcd_color_bg)
infobar_style.set_text_color(lcd_color_fg_dark)
infobar_style.set_radius(0)
infobar_style.set_border_width(0)
infobar_style.set_pad_all(0)


# Button
button_style = lvgl.style_t()
button_style.init()
button_style.set_text_font(lvgl.font_montserrat_16)
button_style.set_bg_color(lcd_color_fg)
button_style.set_text_color(lcd_color_bg)
button_style.set_radius(0)
button_style.set_border_width(0)
button_style.set_pad_all(0)


# Textbox
textbox_style = lvgl.style_t()
textbox_style.init()
textbox_style.set_text_font(lvgl.font_montserrat_14)
textbox_style.set_bg_color(lcd_color_bg)
textbox_style.set_text_color(lcd_color_fg_dark)
textbox_style.set_radius(0)
textbox_style.set_border_width(2)
textbox_style.set_pad_all(5)


# Cursor
cursor_style = lvgl.style_t()
cursor_style.set_border_color(lcd_color_fg)




