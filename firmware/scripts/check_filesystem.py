# This script is to run on the STM32 in micropython, not cpython on your computer!

import binascii
import hashlib
import os

def check_dir(path: str) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for file_info in os.ilistdir(path):
        filename, filetype, _, size = file_info
        full_path = path + filename
        if filetype == 0x4000:  # directory
            files.update(check_dir(full_path + "/"))
            files[full_path] = b""
        else:
            with open(full_path, "rb") as file:
                hasher = hashlib.sha256(file.read())
                files[full_path] = hasher.digest()
    return files

for name, hash in check_dir("/").items():
    print(f"{name} {binascii.hexlify(hash)}")
