"""Word lists for TyperRoyale typing game"""

# Easy: 3-5 letter common words
WORDS_EASY = [
    "cat", "dog", "run", "jump", "code", "hack", "byte", "chip",
    "led", "usb", "key", "bus", "pin", "cpu", "ram", "rom",
    "web", "app", "api", "bug", "git", "log", "bit", "hex",
    "file", "port", "boot", "save", "load", "test", "init", "loop",
    "wire", "pcb", "smd", "fpga", "uart", "gpio", "pwm", "adc",
    "make", "hack", "build", "flash", "reset", "power", "clock", "timer",
    "hello", "world", "badge", "radio", "sensor", "motor", "servo", "relay",
    "pixel", "color", "sound", "beep", "tone", "light", "dark", "mode"
]

# Medium: 4-8 letter words, tech and conference themed
WORDS_MEDIUM = [
    "python", "badge", "hacker", "circuit", "solder", "firmware",
    "hardware", "software", "keyboard", "display", "wireless", "network",
    "protocol", "antenna", "bluetooth", "supercon", "hackaday", "wrencher",
    "workshop", "project", "speaker", "arduino", "raspberry", "espressif",
    "sensor", "actuator", "robotics", "electronics", "programming", "coding",
    "microchip", "voltage", "current", "resistor", "capacitor", "transistor",
    "diode", "inductor", "oscillator", "amplifier", "converter", "regulator",
    "compiler", "debugger", "terminal", "console", "kernel", "driver",
    "library", "function", "variable", "constant", "pointer", "memory",
    "register", "interrupt", "peripheral", "interface", "module", "package"
]

# Hard: 6-12 letter technical words
WORDS_HARD = [
    "microcontroller", "asynchronous", "cryptography", "encryption",
    "architecture", "synchronization", "authentication", "implementation",
    "optimization", "configuration", "initialization", "communication",
    "multiplexer", "oscilloscope", "soldering", "breadboard", "perfboard",
    "accelerometer", "gyroscope", "magnetometer", "thermistor", "photoresistor",
    "servomotor", "stepper", "encoder", "decoder", "transceiver", "modulation",
    "demodulation", "amplification", "attenuation", "impedance", "capacitance",
    "inductance", "frequency", "wavelength", "bandwidth", "throughput",
    "latency", "jitter", "collision", "congestion", "routing", "switching",
    "ethernet", "transmission", "reception", "bitrate", "baudrate", "checksum"
]

# Expert: Phrases (3-5 words)
PHRASES_EXPERT = [
    "hello world",
    "internet of things",
    "conference badge hacking",
    "open source hardware",
    "software defined radio",
    "maker faire project",
    "printed circuit board",
    "field programmable gate array",
    "embedded systems design",
    "wireless mesh network",
    "real time operating system",
    "pulse width modulation",
    "analog to digital converter",
    "serial peripheral interface",
    "universal asynchronous receiver transmitter",
    "light emitting diode",
    "integrated circuit chip",
    "through hole component",
    "surface mount device",
    "soldering iron tip",
    "logic level shifter",
    "voltage regulator circuit",
    "battery management system",
    "raspberry pi zero",
    "arduino uno board",
    "esp thirty two microcontroller",
    "super hackaday conference",
    "jolly wrencher logo",
    "pasadena convention center",
    "hardware hacking village"
]


def get_words(difficulty, count):
    """
    Get random words for difficulty level

    Args:
        difficulty: 'easy', 'medium', 'hard', or 'expert'
        count: number of words to return

    Returns:
        list of words/phrases
    """
    import urandom

    word_list = {
        'easy': WORDS_EASY,
        'medium': WORDS_MEDIUM,
        'hard': WORDS_HARD,
        'expert': PHRASES_EXPERT
    }[difficulty]

    # Simple shuffle and slice (MicroPython compatible)
    shuffled = list(word_list)
    for i in range(len(shuffled) - 1, 0, -1):
        j = urandom.getrandbits(16) % (i + 1)
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]

    return shuffled[:min(count, len(shuffled))]


def get_random_word(difficulty):
    """Get a single random word"""
    import urandom

    word_list = {
        'easy': WORDS_EASY,
        'medium': WORDS_MEDIUM,
        'hard': WORDS_HARD,
        'expert': PHRASES_EXPERT
    }[difficulty]

    idx = urandom.getrandbits(16) % len(word_list)
    return word_list[idx]
