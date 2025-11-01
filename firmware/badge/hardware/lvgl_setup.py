import asyncio
import lvgl 
import lcd_bus
import nv3007
import task_handler

import machine
from machine import SPI, Pin, I2C, Signal
import time
from micropython import const

_LCD_BACKLIGHT_PIN = const(2)
_LCD_SDA_PIN       = const(21)
_LCD_SCL_PIN       = const(38)
_LCD_DC_PIN        = const(39)
_LCD_RESET_PIN     = const(40)
_LCD_CS_PIN        = const(41)
_LCD_TE_PIN        = const(42)

_WIDTH = const(142)
_HEIGHT = const(428)
_OFFSET_X = const(0)
_OFFSET_Y = const(12)

async def lvgl_task_handler(th):
    while(True):
        th._task_handler(None)

        await asyncio.sleep(0.033)

def lcd_init():
    ## this fails with "TypeError: can't convert module to int"
    ##  if the board hasn't been reset recently
    try:
        spi_bus = machine.SPI.Bus(
            host=1,
            mosi=_LCD_SDA_PIN,
            sck=_LCD_SCL_PIN,
            miso=-1  ## only have MOSI
        )
    except TypeError:
        print("SPI Bus needs resetting. Rebooting. Wait 2 sec and try again.\n")
        machine.reset()

    display_bus = lcd_bus.SPIBus(
        spi_bus=spi_bus,
        freq=80_000_000,
        dc=_LCD_DC_PIN,
        cs=_LCD_CS_PIN
    )

    display = nv3007.NV3007(
        data_bus=display_bus,
        display_width=_WIDTH,
        display_height=_HEIGHT,
        reset_pin=_LCD_RESET_PIN,
        reset_state=nv3007.STATE_LOW,
        backlight_pin=_LCD_BACKLIGHT_PIN,
        backlight_on_state=nv3007.STATE_LOW,
        offset_x=_OFFSET_X,
        offset_y=_OFFSET_Y,
        color_space=lvgl.COLOR_FORMAT.RGB565,
        rgb565_byte_swap=True
    )

    display.init()
    display.set_rotation(lvgl.DISPLAY_ROTATION._270) ## order important, after init!
        
    ## Start up screen tasks and return screen object
    lvgl.task_handler()
    th = task_handler.TaskHandler()

    ## So, LVGL uses micropython.schedule to schedule its task handler to run
    ## periodically. It seems like this might not play nice with asyncio's
    ## event loop, so we will disable LVGL's internal scheduling and run it
    ## ourselves in an asyncio task.
    th._timer.deinit()
    asyncio.create_task(lvgl_task_handler(th))

    return lvgl.screen_active()




