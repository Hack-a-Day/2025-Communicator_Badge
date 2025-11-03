
This application is a simple (for now, I hope) tool for reading air quality
sensors, displaying the data, and sending it over LoRa. If the sensors are absent
(well, the SCD30), then instead the app will listen over LoRa for data and display
that.

cd firmware/
git clone https://github.com/toddauer/SPS30-MicroPython.git sps30_micropython
git clone https://github.com/agners/micropython-scd30.git micropython_scd30
copy ../user_apps/airquality/atmosdata.py badge/apps/
