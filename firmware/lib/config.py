"""
Configuration presets for different scenarios

Makes it easy to set up the MAC layer for various situations:
- Dense deployment (500 badges at Supercon)
- Testing (small group, faster settings)
- Long range (maximize distance)
- Low power (save battery)
"""


class MACConfig:
    """Settings for the MAC layer"""

    def __init__(self, **kwargs):
        # Core protocol params (from research paper)
        self.phase2_probability = kwargs.get('phase2_probability', 0.1)  # P
        self.backoff_window = kwargs.get('backoff_window', 7)  # W
        self.difs_ms = kwargs.get('difs_ms', 400)  # Time unit
        self.use_cad = kwargs.get('use_cad', True)  # Initial quick check

        # Radio settings
        self.freq_mhz = kwargs.get('freq_mhz', 915.0)
        self.spreading_factor = kwargs.get('spreading_factor', 12)
        self.bandwidth = kwargs.get('bandwidth', 125)
        self.tx_power = kwargs.get('tx_power', 14)
        self.coding_rate = kwargs.get('coding_rate', 5)

        # App stuff
        self.node_id = kwargs.get('node_id', 0)
        self.channel_id = kwargs.get('channel_id', 0)

    def to_dict(self):
        """Export as dict for JSON"""
        return {
            'mac': {
                'phase2_probability': self.phase2_probability,
                'backoff_window': self.backoff_window,
                'difs_ms': self.difs_ms,
                'use_cad': self.use_cad
            },
            'radio': {
                'freq_mhz': self.freq_mhz,
                'spreading_factor': self.spreading_factor,
                'bandwidth': self.bandwidth,
                'tx_power': self.tx_power,
                'coding_rate': self.coding_rate
            },
            'app': {
                'node_id': self.node_id,
                'channel_id': self.channel_id
            }
        }

    def __str__(self):
        return f"MACConfig(P={self.phase2_probability}, W={self.backoff_window}, " \
               f"DIFS={self.difs_ms}ms, SF{self.spreading_factor}BW{self.bandwidth})"


class Config:
    """Pre-made configs for common scenarios"""

    @staticmethod
    def for_dense_deployment(node_count=500):
        """
        Optimized for Supercon (500 badges in close quarters)

        Research paper tested with 9 badges in 100m x 100m.
        For 500 badges, we spread things out more with bigger W and smaller P.
        """
        if node_count <= 50:
            w = 7    # Small group, faster
            p = 0.1
        elif node_count <= 200:
            w = 15   # Medium density
            p = 0.08
        else:  # 200+
            w = 23   # Big crowd, need lots of spacing
            p = 0.05

        return MACConfig(
            phase2_probability=p,
            backoff_window=w,
            difs_ms=400,  # SF12BW125 preamble time
            use_cad=True,

            # SF12 = max range, slow but reliable
            freq_mhz=915.0,  # Change to 868.0 for EU
            spreading_factor=12,
            bandwidth=125,
            tx_power=14,
            coding_rate=5
        )

    @staticmethod
    def for_testing(node_count=10):
        """
        Quick testing with a handful of badges

        Uses faster settings so you don't wait forever
        """
        return MACConfig(
            phase2_probability=0.1,
            backoff_window=7,
            difs_ms=100,  # Shorter for faster iteration

            # SF7 = faster transmission, shorter range
            freq_mhz=915.0,
            spreading_factor=7,
            bandwidth=125,
            tx_power=14,
            coding_rate=5
        )

    @staticmethod
    def for_long_range():
        """
        Maximum range mode

        Slow, but will reach across the conference center
        """
        return MACConfig(
            phase2_probability=0.15,  # More aggressive (sparse deployment)
            backoff_window=7,
            difs_ms=400,
            use_cad=True,

            freq_mhz=915.0,
            spreading_factor=12,
            bandwidth=125,
            tx_power=22,  # Max power for SX1262
            coding_rate=8  # 4/8 = lots of error correction
        )

    @staticmethod
    def for_low_power():
        """
        Battery saver mode

        Lower SF = faster transmission = less time with radio on
        """
        return MACConfig(
            phase2_probability=0.1,
            backoff_window=7,
            difs_ms=200,  # SF9 preamble
            use_cad=False,  # Skip CAD to save power

            freq_mhz=915.0,
            spreading_factor=9,  # Balanced speed/range
            bandwidth=125,
            tx_power=10,  # Lower power
            coding_rate=5
        )

    @staticmethod
    def from_dict(config_dict):
        """Load from JSON/dict"""
        return MACConfig(
            # MAC
            phase2_probability=config_dict['mac']['phase2_probability'],
            backoff_window=config_dict['mac']['backoff_window'],
            difs_ms=config_dict['mac']['difs_ms'],
            use_cad=config_dict['mac']['use_cad'],

            # Radio
            freq_mhz=config_dict['radio']['freq_mhz'],
            spreading_factor=config_dict['radio']['spreading_factor'],
            bandwidth=config_dict['radio']['bandwidth'],
            tx_power=config_dict['radio']['tx_power'],
            coding_rate=config_dict['radio']['coding_rate'],

            # App
            node_id=config_dict['app']['node_id'],
            channel_id=config_dict['app']['channel_id']
        )


def calculate_difs(sf, bw_khz):
    """
    Figure out DIFS for a given SF/BW combo

    DIFS = preamble duration = how long the preamble takes to transmit
    Default preamble = 12.25 symbols
    Symbol time = (2^SF) / bandwidth

    Example values:
    - SF7BW125:  100ms
    - SF9BW125:  400ms
    - SF12BW125: 400ms
    """
    symbol_time_ms = (2 ** sf) / (bw_khz * 1000) * 1000
    preamble_symbols = 12.25
    return int(preamble_symbols * symbol_time_ms)
