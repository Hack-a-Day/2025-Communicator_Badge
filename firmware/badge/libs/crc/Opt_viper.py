# Optimization import for Micropython crc class.
#
# 8-bit table based right shift viper crc 8, 16 and 32 implementations

# --- arguments ---
# .. lookup table address
# .. n lenght of data
# .. data to be processed (only 8-bit address is used)
# .. crc
@micropython.viper
def _crc8_tr(crc: int, data: ptr8, n: int, tab: ptr8) -> int:
    i: int  = 0
    while i < n:
        crc = tab[crc ^ data[i]]
        i += 1
    return crc

# --- arguments ---
# .. lookup table address
# .. n lenght of data
# .. data to be processed (only 8-bit address is used)
# .. crc
@micropython.viper
def _crc16_tr(crc: int, data: ptr8, n: int, tab: ptr16) -> int:
    i: int  = 0
    while i < n:
        crc = (crc >> 8) ^ tab[(crc & 0xff) ^ data[i]]
        i += 1
    return crc

# --- arguments ---
# .. lookup table address
# .. n lenght of data
# .. data to be processed (only 8-bit address is used)
# .. crc
@micropython.viper
def _crc32_tr(crc: uint, data: ptr8, n: int, tab: ptr32) -> uint:
    i: int  = 0
    while i < n:
        crc = (crc >> 8) ^ tab[(crc & 0xff) ^ data[i]]
        i += 1
    return crc

# --- arguments ---
# .. lookup table address
# .. n lenght of data
# .. data to be processed (only 8-bit address is used)
# .. crc
@micropython.viper
def _crc64_h(crc: ptr32, data: ptr8, n: int, tab: ptr32):  # just a helper function
    crc0: uint = uint(crc[0])
    crc1: uint = uint(crc[1])
    i: uint  = 0
    while i < n:
        idx:uint = (crc0 & 0xff) ^ data[i]
        crc0 = (crc1 << 24 | crc0 >> 8) ^ tab[2*idx]    # 64 bit pointer, low word
        crc1 = (crc1 >> 8) ^ tab[2*idx+1]               # 64 bit pointer, high word
        i += 1
    crc[0] = crc0
    crc[1] = crc1

from array import array
acrc = array('Q', (0,))

def _crc64_tr(crc, data, n, tab):
    acrc[0] = crc
    _crc64_h(acrc, data, n, tab)
    return acrc[0]

import crc
crc.Implementation = 'viper'
crc._crc8_tr  = _crc8_tr
crc._crc16_tr = _crc16_tr
crc._crc32_tr = _crc32_tr
crc._crc64_tr = _crc64_tr