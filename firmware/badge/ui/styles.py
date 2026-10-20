import lvgl


from hardware.datafile import Config


theme = 'default'


try:
    
    # Retrieve the theme from the config
    config = Config()
    theme_config = config.get('theme')
    config.close()
    
    # Update the name of the selected theme only if the "theme"
    # key exists in the config file.
    # Otherwise, we'll use the default value set at the beginning of the file
    if theme_config is not None:
        theme = theme_config.decode()
    
    # Programmatically load the module corresponding to the selected theme
    # Inspired from https://stackoverflow.com/a/69619972, with modifications
    # to take into account the fact that importlib does not exist in Micropython
    
    # (We cannot simply do "from module_str import *", with module_str a str 
    # containing the name of the module/theme. That's why we do it this way.)
    
    # Import the module to a namespace
    module_name = 'ui.themes.'+theme
    module = __import__(module_name, globals(), locals(), [theme])
    
    # Extract the variable/settings from the module to a dict
    module_dict = {}
    for key, value in module.__dict__.items():
        if not key.startswith('__'): # We do not want '__name__', ...
            module_dict[key] = value
    
    # Add the variables extracted from the module namespace to the global namespace
    # Note : they are global inside the current (=styles.py) module, not in
    # the whole Python interpreter
    globals().update(module_dict)
            

except:
    print("UI theme import failed ... Loading default theme from 'styles.py' instead")
    
    
    """
    Default style from the 2025 Supercon and 2026 Hackaday Europe
    
    Copied here in case something goes wrong while importing the theme
    (eg. the 'themes' folder does not exists, the 'default' theme
    is absent from that folder, a setting is incorrect, ...)
    """

    # Colors
    lcd_color_bg      = lvgl.color_hex(0xabc5a0)
    lcd_color_fg      = lvgl.color_hex(0x292b29)
    lcd_color_fg_dark = lvgl.color_hex(0x080908)


    hackaday_grey   = lvgl.color_hex(0x1a1a1a)
    hackaday_yellow = lvgl.color_hex(0xe39810) ## adjusted for screen gamma
    hackaday_white  = lvgl.color_hex(0xffffff)


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



    # Some colors
    lvg_color_black  	= lvgl.color_hex(0x000000)
    lvg_color_red   	= lvgl.color_hex(0x990000)
    lvg_color_green 	= lvgl.color_hex(0x006600)



