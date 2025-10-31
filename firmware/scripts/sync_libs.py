#!/bin/env python3

import os
import shutil
import subprocess

if __name__ == "__main__":
    subprocess.run(["git", "submodule", "sync"], check=True)
    subprocess.run(["git", "submodule", "update", "--init", "--recursive"], check=True)
    os.makedirs("badge/libs/crc", exist_ok=True)
    shutil.copyfile("libs/mp-crc/crc/__init__.py", "badge/libs/crc/__init__.py")
    shutil.copyfile("libs/mp-crc/crc/Opt_viper.py", "badge/libs/crc/Opt_viper.py")
    # We tried micropython-lib's async sx1262 library, but it stalls out with the lvgl build of micropython needed to drive the display
    # os.makedirs("badge/libs/lora", exist_ok=True)
    # shutil.copyfile("libs/micropython-lib/micropython/lora/lora/lora/__init__.py", "badge/libs/lora/__init__.py")
    # shutil.copyfile("libs/micropython-lib/micropython/lora/lora/lora/modem.py", "badge/libs/lora/modem.py")
    # shutil.copyfile("libs/micropython-lib/micropython/lora/lora-async/lora/async_modem.py", "badge/libs/lora/async_modem.py")
    # shutil.copyfile("libs/micropython-lib/micropython/lora/lora-sx126x/lora/sx126x.py", "badge/libs/lora/sx126x.py")
