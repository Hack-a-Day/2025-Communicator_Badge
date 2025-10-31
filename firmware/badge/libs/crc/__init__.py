# Micropython class to compute a CRC (16 or 32 bit) with different algorithms and implementations

from array import array

# bit reverse of all bits in a byte
def rbit8(v):
    v = (v & 0x0f) << 4 | (v & 0xf0) >> 4
    v = (v & 0x33) << 2 | (v & 0xcc) >> 2
    return (v & 0x55) << 1 | (v & 0xaa) >> 1

# bit reverse of all bits in a 16 bit halfword
def rbit16(v):
    v = (v & 0x00ff) << 8 | (v & 0xff00) >> 8
    v = (v & 0x0f0f) << 4 | (v & 0xf0f0) >> 4
    v = (v & 0x3333) << 2 | (v & 0xcccc) >> 2
    return (v & 0x5555) << 1 | (v & 0xaaaa) >> 1

# bit reverse of all bits in a 32 bit word
def rbit32(v):
    v = (v & 0x0000ffff) << 16 | (v & 0xffff0000) >> 16
    v = (v & 0x00ff00ff) << 8 | (v & 0xff00ff00) >> 8
    v = (v & 0x0f0f0f0f) << 4 | (v & 0xf0f0f0f0) >> 4
    v = (v & 0x33333333) << 2 | (v & 0xcccccccc) >> 2
    return (v & 0x55555555) << 1 | (v & 0xaaaaaaaa) >> 1

# bit reverse of all bits in a 32 bit word
def rbit64(v):
    v =    (v & 0x00000000ffffffff) << 32 | (v & 0xffffffff00000000) >> 32
    v =    (v & 0x0000ffff0000ffff) << 16 | (v & 0xffff0000ffff0000) >> 16
    v =    (v & 0x00ff00ff00ff00ff) <<  8 | (v & 0xff00ff00ff00ff00) >>  8
    v =    (v & 0x0f0f0f0f0f0f0f0f) <<  4 | (v & 0xf0f0f0f0f0f0f0f0) >>  4
    v =    (v & 0x3333333333333333) <<  2 | (v & 0xcccccccccccccccc) >>  2
    return (v & 0x5555555555555555) <<  1 | (v & 0xaaaaaaaaaaaaaaaa) >>  1

# swap bytes of 1-byte number
def rbyte1(v):
    return v  # no swap

# swap bytes of 2-byte number
def rbyte2(v):
    return (v & 0xff) << 8 | v >> 8 

# reverse bytes of 4-byte number
def rbyte4(v):
    v = (v & 0x0000ffff) << 16 | (v & 0xffff0000) >> 16
    return (v & 0x00ff00ff) << 8 | (v & 0xff00ff00) >> 8

# reverse bytes of 4-byte number
def rbyte8(v):
    v =    (v & 0x00000000ffffffff) << 32 | (v & 0xffffffff00000000) >> 32
    v =    (v & 0x0000ffff0000ffff) << 16 | (v & 0xffff0000ffff0000) >> 16
    return (v & 0x00ff00ff00ff00ff) <<  8 | (v & 0xff00ff00ff00ff00) >>  8


# -----  CRC 8-bit lookup table initializing functions ------

def _tinit_l(crc, poly, nb): # universal left-shift version, nb = number of bits, 8, 16, 32; 
    _and = 1 << nb
    crc <<= (nb-8)
    for _ in range(8):
        crc <<= 1
        if crc & _and:       # 0x100, 0x10000, 0x100000000
            crc ^= poly
    return crc & (_and-1)

def _tinit_r(crc, poly):
    for _ in range(8):
        if crc & 1:
            crc = (crc >> 1) ^ poly
        else:
            crc = crc >> 1
    return crc

class Crc8:
    # Name      (Width, Poly, Init, RefIn, RefOut, Xorout, Check)
    crc7ls    = (8,     0x12, 0x00, False, False,  0x00,   0xea)
    crc8      = (8,     0x07, 0x00, False, False,  0x00,   0xf4)
    ccitt     = crc8
    saej1850  = (8,     0x1d, 0x00, False, False,  0x00,   0x37)
    autosar   = (8,     0x2f, 0xff, False, False,  0xff,   0xdf)
    bluetooth = (8,     0xa7, 0x00, True,  True,   0x00,   0x26)
    maxim_dow = (8,     0x31, 0x00, True,  True,   0x00,   0xa1)
#     cdma2000  = (8,     0x9b, 0xff, False, False,  0x00,   0xda)
#     darc      = (8,     0x39, 0x00, True,  True,   0x00,   0x15)
#     dvb_s2    = (8,     0xd5, 0x00, False, False,  0x00,   0xbc)
#     ebu       = (8,     0x1d, 0xff, True,  True,   0x00,   0x97)
#     i_code    = (8,     0x1d, 0xfd, False, False,  0x00,   0x7e)
#     itu       = (8,     0x07, 0x00, False, False,  0x55,   0xa1)
#     rohc      = (8,     0x07, 0xff, True,  True,   0x00,   0xd0)
#     wcdma     = (8,     0x9b, 0x00, True,  True,   0x00,   0x25)

class Crc16:
    # Name      (Width,  Poly,   Init,   RefIn, RefOut, Xorout, Check)
    xmodem    = (16,    0x1021, 0x0000, False, False,  0x0000, 0x31c3)
    usb       = (16,    0x8005, 0xffff, True,  True,   0xffff, 0xb4c8)
    ccitt     = xmodem
    gsm       = (16,    0x1021, 0x0000, False, False,  0xffff, 0xce3c)
    profibus  = (16,    0x1dcf, 0xffff, False, False,  0xffff, 0xa819)
    modbus    = (16,    0x8005, 0xffff, True,  True,   0x0000, 0x4b37)
#     arc       = (16,    0x8005, 0x0000, True,  True,   0x0000, 0xbb3d),
#     buypass   = (16,    0x8005, 0x0000, False, False,  0x0000, 0xfee8),
#     dds_110   = (16,    0x8005, 0x800d, False, False,  0x0000, 0x9ecf),
#     maxim     = (16,    0x8005, 0x0000, True,  True,   0xffff, 0x44c2),
#     aug_ccitt = (16,    0x1021, 0x1d0f, False, False,  0x0000, 0xe5cc),
#     ccitt_false=(16,    0x1021, 0xffff, False, False,  0x0000, 0x29b1),
#     genibus   = (16,    0x1021, 0xffff, False, False,  0xffff, 0xd64e),
#     kermit    = (16,    0x1021, 0x0000, True,  True,   0x0000, 0x2189),
#     mcrf4xx   = (16,    0x1021, 0xffff, True,  True,   0x0000, 0x6f91),
#     riello    = (16,    0x1021, 0xb2aa, True,  True,   0x0000, 0x63d0),
#     tms37157  = (16,    0x1021, 0x89ec, True,  True,   0x0000, 0x26b1),
#     x_25        (16,    0x1021, 0xffff, True,  True,   0xffff, 0x906e),
#     a           (16,    0x1021, 0xc6c6, True,  True,   0x0000, 0xbf05)
#     cdma2000  = (16,    0xc867, 0xffff, False, False,  0x0000, 0x4c06),
#     dect_r    = (16,    0x0589, 0x0000, False, False,  0x0001, 0x007e),
#     dect_x    = (16,    0x0589, 0x0000, False, False,  0x0000, 0x007f),
#     dnp       = (16,    0x3d65, 0x0000, True,  True,   0xffff, 0xea82),
#     en_13757  = (16,    0x3d65, 0x0000, False, False,  0xffff, 0xc2b7),
#     t10-dif   = (16,    0x8bb7, 0x0000, False, False,  0x0000, 0xd0db),
#     teledisk  = (16,    0xa097, 0x0000, False, False,  0x0000, 0x0fb3),

class Crc32:
    # Name     (Width,  Poly,       Init,       RefIn, RefOut, Xorout,     Check)
    crc32      = (32,    0x04c11db7, 0xffffffff, True,  True,   0xffffffff, 0xcbf43926)
    autosar    = (32,    0xf4acfb13, 0xffffffff, True,  True,   0xffffffff, 0x1697d06a)
    bzip2      = (32,    0x04c11db7, 0xffffffff, False, False,  0xffffffff, 0xfc891918)
    posix      = (32,    0x04c11db7, 0x00000000, False, False,  0xffffffff, 0x765e7680)
    sata       = (32,    0x04c11db7, 0x52325032, False, False,  0x00000000, 0xcf72afe8)
#     jamcrc     = (32,    0x04c11db7, 0xffffffff, True,  True,   0x00000000, 0x340bc6d9)
#     mpeg-2     = (32,    0x04c11db7, 0xffffffff, False, False,  0x00000000, 0x0376e6e7)
#     xfer       = (32,    0x000000af, 0x00000000, False, False,  0x00000000, 0xbd0be338)
#     c          = (32,    0x1edc6f41, 0xffffffff, True,  True,   0xffffffff, 0xe3069283)
#     d          = (32,    0xa833982b, 0xffffffff, True,  True,   0xffffffff, 0x87315576)
#     q          = (32,    0x814141ab, 0x00000000, False, False,  0x00000000, 0x3010bf7f)
    
class Crc64:
    # Name   (Width,  Poly,           Init,                RefIn, RefOut, Xorout,             Check)
    crc64   = (64, 0x42f0e1eba9ea3693, 0x0000000000000000, False, False,  0x0000000000000000, 0x6c40df5f0b497347)
    ecma_182 = crc64
    go_iso  = (64, 0x000000000000001b, 0xffffffffffffffff, True,  True,   0xffffffffffffffff, 0xb90956c775a41001)
#     we      = (64, 0x42f0e1eba9ea3693, 0xffffffffffffffff, False, False,  0xffffffffffffffff, 0x62ec59e3f1a4f00a)
#     xz      = (64, 0x42f0e1eba9ea3693, 0xffffffffffffffff, True,  True,   0xffffffffffffffff, 0x995dc9bbdf1939fa)

# --- These are the ordinary MP bytecode implementations of the 8-bit table lookup CRC8 16 and 32 ---
#
# -- Arguments ---
# tab  .. lookup table address
# n    .. (length of data, will be ignored here, but is there for the optimized versions)
# data .. data to be processed, iterable of bytes
# crc  .. previous crc value to be updated
def _crc8_tr(crc, data, n, tab):    # we could have taken that same code as below ...
    for d in data:
        crc = tab[crc ^ d]
    return crc

def _crc16_tr(crc, data, n, tab):   # this is quite universal
    for d in data:
        crc = (crc >> 8) ^ tab[(crc & 0xff) ^ d]
    return crc

_crc64_tr = _crc32_tr = _crc16_tr   # we keep the different names for the optimized implementations

Implementation = 'bytecode'

class Calculator:
    """
    Micropython CRC computation class
    """
    # Arguments:
    #
    # width  .. The width of CRC calculation (16 or 32)
    # poly   .. The CRC polynomial
    # init   .. Initial CRC value.
    # refin  .. True if input bytes are to be reflected before processing (bit7 <--> bit0, bit6 <--> bit1, etc). Default: False.
    # refout .. True if computed CRC is to be reflected after processing. Default: False
    # xorout .. 16-bit word, that is Xor'ed to the computed CRC after processing the bit shifts. Default: 0
    # check  .. CRC expected in processing the bytes b'\x31\x32\x33\x34\x35\x36\x37\x38\x39' (123456789 in Ascii). Default: None
    # tab    .. optional array, where the lookup table will be stored in, needs to have the proper typecode (e.g. 'H')
    #
    def __init__(self, width, poly=None, init=None, refin=False, refout=False, xorout=0, check=None, tab=None):
        
        if isinstance(width, tuple):
            if len(width) == 7:    # if we have a tuple containing all the args
                width, poly, init, refin, refout, xorout, check = width
            elif len(width) == 6:
                width, poly, init, refin, refout, xorout = width
        elif isinstance (width, dict):  # we have a config dictionary
            if 'check' in width:        # first test for optional parameter 'check'
                check = width['check']
            poly, init, refin, refout, xorout, width = (width[k] for k in ('poly', 
                'init', 'refin', 'refout', 'xorout', 'width'))
        self.width = width  
        self.poly = poly
        self.init = init
        self.refin = refin
        self.refout = refout
        self.xorout = xorout
        self.check = check
        self.implementation = Implementation
        
        if width == 8:
            self._crcfun = _crc8_tr    # bytecode implementations, unless overwritten before
            tab_tc = 'B'
            self._rbit = rbit8
            self._rbyte = rbyte1
        elif width == 16:
            self._crcfun = _crc16_tr   # bytecode implementations, unless overwritten before
            tab_tc = 'H'
            self._rbit = rbit16
            self._rbyte = rbyte2
        elif width == 32:
            self._crcfun = _crc32_tr
            tab_tc = 'I'
            self._rbit = rbit32
            self._rbyte = rbyte4
        elif width == 64:
            self._crcfun = _crc64_tr
            tab_tc = 'Q'
            self._rbit = rbit64
            self._rbyte = rbyte8

        else:
            raise ValueError('crc.Calculator: width was not 8, 16, 32 or 64')
            
        if tab:
            self._tab = tab                                   # needs to be checked for typecode, length !!!!
        else:
            self._tab = array(tab_tc, 0 for _ in range(256))  # create lookup table 

        rpoly = self._rbit(poly)                              # and fill it, depending on input reflection
        for i in range(256):
            self._tab[i] = _tinit_r(i, rpoly) if self.refin else self._rbyte(_tinit_l(i, poly, width))
            
        self.reset()                
        
    def digest(self, data):
        self._crc = self._crcfun(self._crc, data, len(data), self._tab)    # this always updates self._crc
        
    def checksum(self, data=None):                            # includes a reset; if this is not desrired use digest()
        if data:
            self.digest(data)
        rcrc = self._crc if self.refout else self._rbyte(self._crc)
        self.reset()
        return rcrc ^ self.xorout

    def reset(self):
        self._crc = self._rbit(self.init) if self.refout else self._rbyte(self.init)

#     def selftest_ok(self):  # works only if we have the 'check' parameter, which we have with the predefined CRC methods
#         self.reset()
#         if self.check is None:
#             raise ValueError('crc.Calculator: selftest needs a check value')
#         return self.check == self.checksum(b'\x31\x32\x33\x34\x35\x36\x37\x38\x39')


