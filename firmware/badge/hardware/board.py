from machine import Pin, Signal, PWM

# https://docs.micropython.org/en/latest/esp32/quickref.html

DEBUG_LED = Signal(Pin(1, Pin.OUT), invert=True)
GPIO_0 = Pin(0, Pin.IN)

# Keyboard I2C
KBD_SCL = Pin(14)
KBD_SDA = Pin(47)
KBD_INT = Pin(13, Pin.IN)
KBD_RST = Pin(48, Pin.OUT)

# LCD I2C
LCD_SCL = Pin(38)
LCD_SDA = Pin(21)
LCD_RST = Pin(40, Pin.OUT)
LCD_CS = Pin(41, Pin.OUT)
LCD_TE = Pin(42, Pin.OUT)
LCD_BACKLIGHT = PWM(Pin(2, Pin.OUT))
LCD_DATA_CMD = Pin(39, Pin.OUT)

# Radio SPI + Extras
RF_NSS = 17  # Pin(17, Pin.IN)  # CS
RF_RST = Pin(18)
RF_MOSI = 3  # Pin(3, Pin.OUT)
RF_SCK = 8  # Pin(8, Pin.OUT)
RF_MISO = 9  # Pin(9, Pin.IN)
RF_SW = Pin(10, Pin.OUT, value=1)  # Dir ?
RF_BUSY = Pin(15, Pin.IN)
RF_DIO1 = Pin(16)  # Dir ?

# SAO
SAO_SCL = Pin(5)
SAO_SDA = Pin(4)
SAO_GPIO1 = Pin(7)
SAO_GPIO2 = Pin(6)
