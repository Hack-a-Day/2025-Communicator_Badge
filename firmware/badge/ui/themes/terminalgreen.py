"""
A green on black theme, reminiscent of old terminals.
For people that are nostalgic and hackers alike.
"""


import lvgl



""" Colors """

# Color palette for this theme
theme_color_bg_1 = lvgl.color_hex(0x000a05) # Dark background
theme_color_bg_2 = lvgl.color_hex(0x000a05) # Slightly lighter background

theme_color_fg_1 = lvgl.color_hex(0x00994c) # Color for text 
theme_color_fg_2 = lvgl.color_hex(0x00994c) # Another foreground color (not used for now) 



# Keep these default color names in case some app import them directly
lcd_color_bg      = lvgl.color_hex(0x000a05)
lcd_color_fg      = lvgl.color_hex(0x00994c)
lcd_color_fg_dark = lvgl.color_hex(0x00994c)


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
base_style.set_text_font(lvgl.font_unscii_8)
base_style.set_bg_color(theme_color_bg_1)
base_style.set_text_color(theme_color_fg_1)
base_style.set_radius(0)
base_style.set_border_width(0)
base_style.set_pad_all(0)

# Content
content_style = lvgl.style_t()
content_style.init()
content_style.set_text_font(lvgl.font_unscii_8)
content_style.set_bg_color(theme_color_bg_1)
content_style.set_text_color(theme_color_fg_1)
content_style.set_radius(0)
content_style.set_border_width(0)
content_style.set_pad_all(0)

# Menubar
menubar_style = lvgl.style_t()
menubar_style.init()
menubar_style.set_text_font(lvgl.font_unscii_8)
menubar_style.set_bg_color(theme_color_bg_1)
menubar_style.set_text_color(theme_color_fg_1)
menubar_style.set_radius(0)
menubar_style.set_border_width(0)
menubar_style.set_pad_all(0)

# Infobar
infobar_style = lvgl.style_t()
infobar_style.init()
infobar_style.set_text_font(lvgl.font_unscii_8)
infobar_style.set_bg_color(theme_color_fg_1)
infobar_style.set_text_color(theme_color_bg_1)
infobar_style.set_radius(0)
infobar_style.set_border_width(0)
infobar_style.set_pad_all(0)


# Button
button_style = lvgl.style_t()
button_style.init()
button_style.set_text_font(lvgl.font_unscii_8)
button_style.set_bg_color(theme_color_bg_1)
button_style.set_text_color(theme_color_fg_1)
button_style.set_radius(0)
button_style.set_border_width(1)
button_style.set_pad_all(1)
button_style.set_border_color(theme_color_fg_1)


# Textbox
textbox_style = lvgl.style_t()
textbox_style.init()
textbox_style.set_text_font(lvgl.font_unscii_8)
textbox_style.set_bg_color(theme_color_bg_1)
textbox_style.set_text_color(theme_color_fg_1)
textbox_style.set_radius(0)
textbox_style.set_border_width(2)
textbox_style.set_pad_all(5)
textbox_style.set_border_color(theme_color_fg_1)


# Cursor
cursor_style = lvgl.style_t()
cursor_style.set_border_width(0)
cursor_style.set_bg_color(theme_color_fg_1)
cursor_style.set_bg_opa(255)



