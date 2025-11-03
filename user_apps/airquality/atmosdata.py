
import uasyncio as aio  # type: ignore

from apps.base_app import BaseApp
from libs.micropython_scd30.scd30 import SCD30
from libs.sps30_micropython.sps30 import SPS30
from net.net import register_receiver, send, BROADCAST_ADDRESS
from net.protocols import Protocol, NetworkFrame
from ui.page import Page
import ui.styles as styles
import lvgl
import utime

# Yes, this is a Doctor Who reference
ATMOS_PROTOCOL = Protocol(port=25, name="AtmosphereData", structdef="!Bffffffff")

class AtmosphereData(BaseApp):
    """ This class either receives and displays atmosphere data (think air quality/AQI)
        or it uses attached I2C sensors to generate and display the same.

        It is currently inflexible with a very basic UI. Please feel free to make it better :)
    """

    def __init__(self, name: str, badge):
        super().__init__(name, badge)

        self.sensor_refresh_interval_ms = 5000
        scd30_address = 0x61
        sps30_address = 0x69
        # v0: c02, temp, hum
        # v1: add five particle count buckets
        self.ATMOS_VERSION = 1

        self.foreground_sleep_ms = 10
        self.background_sleep_ms = self.sensor_refresh_interval_ms

        i2c_scan_result = self.badge.sao_i2c.scan()

        if scd30_address in i2c_scan_result:
            self.scd30 = SCD30(self.badge.sao_i2c, scd30_address) # leave internal sleep at default 1000us
            self.scd30.set_measurement_interval(int(self.sensor_refresh_interval_ms/1000))
            self.producing_data = True
        else:
            self.scd30 = None
            self.producing_data = False

        if sps30_address in i2c_scan_result:
            self.sps30 = SPS30(self.badge.sao_i2c, sps30_address)
            self.sps30.start_measurement()
            #self.sps30 = None
        else:
            self.sps30 = None

        self.co2_measurement = [-1, -1, -1]
        self.particle_measurement = [-1, -1, -1, -1, -1] # five nc buckets
        self.screen_has_latest_data = True
        self.last_transmission = 0

        self.current_line_labels = []

    def start(self):
        super().start()
        register_receiver(ATMOS_PROTOCOL, self.receive_message)

    def receive_message(self, message: NetworkFrame):
        """Handle incoming messages."""
        print(f"atmos received message {message.payload}")
        # TODO do this check for register_receiver instead (this is easier to debug)
        if not self.producing_data and message.port == ATMOS_PROTOCOL.port and message.payload[0] == self.ATMOS_VERSION:
            self.co2_measurement = message.payload[1:3]
            self.particle_measurement = message.payload[4:8]
            self.screen_has_latest_data = False

    def poll_data(self):
        # safety
        if not self.producing_data:
            return
        # This scd30 driver isn't very resilient to the device falling off the bus sometimes,
        # but this is a wearable so we just deal with it.
        try:
            transmit_new_data = False
            now = utime.ticks_ms()
            if self.scd30 and self.scd30.get_status_ready():
                self.screen_has_latest_data = False
                transmit_new_data = True
                print(f"co2: {self.co2_measurement}")
                self.co2_measurement = self.scd30.read_measurement()
            if self.sps30 and self.sps30.read_data_ready():
                self.screen_has_latest_data = False
                transmit_new_data = True
                self.particle_measurement = self.sps30.read_measurement()
                print(f"part: {self.particle_measurement}")
            if transmit_new_data and (now - self.last_transmission) > self.sensor_refresh_interval_ms:
                tx_msg = NetworkFrame().set_fields(protocol=ATMOS_PROTOCOL,
                                                destination=BROADCAST_ADDRESS,
                                                payload=(
                                                    int(self.ATMOS_VERSION), # version
                                                    float(self.co2_measurement[0]), # ppm CO2
                                                    float(self.co2_measurement[1]), # deg C
                                                    float(self.co2_measurement[2]), # percent relative humidity
                                                    float(self.particle_measurement[4][1]), # particles/cm^3
                                                    float(self.particle_measurement[5][1]), # particles/cm^3
                                                    float(self.particle_measurement[6][1]), # particles/cm^3
                                                    float(self.particle_measurement[7][1]), # particles/cm^3
                                                    float(self.particle_measurement[8][1]), # particles/cm^3
                                                ))
                self.badge.lora.send(tx_msg)
                print("ATMOS transmitted")
                self.last_transmission = now
        except:
            print("scd30 read failure")

    def compose_lines(self) -> list[str]:
        l = []
        l.append(f"{self.co2_measurement[0]:.0f} ppm CO2")
        l.append(f"{self.co2_measurement[1]:.2f} deg C ({(self.co2_measurement[1] * 9 / 5) + 32:.0f} deg F)")
        l.append(f"{self.co2_measurement[2]}% rh")
        l.append(f"{self.particle_measurement[4][1]} {self.particle_measurement[4][0]} particles/cm^3")
        l.append(f"{self.particle_measurement[5][1]} {self.particle_measurement[5][0]} particles/cm^3")
        l.append(f"{self.particle_measurement[6][1]} {self.particle_measurement[6][0]} particles/cm^3")
        l.append(f"{self.particle_measurement[7][1]} {self.particle_measurement[7][0]} particles/cm^3")
        l.append(f"{self.particle_measurement[8][1]} {self.particle_measurement[8][0]} particles/cm^3")
        return l

    def refresh_labels(self) -> None:
        # I should be able to get LVGL to do vertical stacking for me
        # Many thanks to hwmon for showing how to do some of this
        y_pos = 18
        for label in self.current_line_labels:
            label.delete()
        self.current_line_labels = []
        text_to_display = self.compose_lines()
        for text in text_to_display:
            label = lvgl.label(self.badge.display.screen)
            self.current_line_labels.append(label)
            label.set_text(text)
            label.set_pos(25, y_pos)
            y_pos += 13

    def run_foreground(self):
        if self.producing_data:
            self.poll_data()
        else:
            pass # Wait for lora packets

        if not self.screen_has_latest_data:
            self.screen_has_latest_data = True
            self.refresh_labels()

        if self.badge.keyboard.f1():
            pass
        if self.badge.keyboard.f2():
            pass
        if self.badge.keyboard.f3():
            pass
        if self.badge.keyboard.f4():
            pass
        ## Co-op multitasking: all you have to do is get out
        if self.badge.keyboard.f5():
            self.badge.display.clear()
            self.switch_to_background()

    def run_background(self):
        super().run_background()
        if self.producing_data:
            self.poll_data()
        else:
            pass # Wait for lora packets

    def switch_to_foreground(self):
        super().switch_to_foreground()
        self.p = Page()
        ## Note this order is important: it renders top to bottom that the "content" section expands to fill empty space
        ## If you want to go fully clean-slate, you can draw straight onto the p.scr object, which should fit the full screen.
        self.p.create_infobar(["Atmospheric Data Display", ""])
        self.p.create_content()
        self.p.create_menubar(["", "", "", "", "Done"])
        self.p.replace_screen()
        if not self.producing_data:
            self.p.infobar_right.set_text("Awaiting packets")
        else:
            self.p.infobar_right.set_text(f"Polling sensors every ~{int(self.sensor_refresh_interval_ms/1000)}s")
        self.screen_has_latest_data = False

    def switch_to_background(self):
        # TODO: If the LVGL objects are properly parented, this loop may not be necessary.
        self.current_line_labels = []
        self.p = None
        super().switch_to_background()
