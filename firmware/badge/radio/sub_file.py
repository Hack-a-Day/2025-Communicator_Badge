"""Minimal .sub-like file format for captured RF packets."""


class SubFile:
    """Read/write Sub-GHz capture files with timestamped packets."""

    HEADER = [
        "Filetype: Badgenet SubGhz RAW File",
        "Version: 1",
    ]

    @classmethod
    def write(cls, path, frequency_mhz, modulation, packets):
        with open(path, "w") as f:
            f.write("# Badgenet Sub-GHz RAW File\n")
            for line in cls.HEADER:
                f.write(line + "\n")
            f.write("Frequency: %.6f\n" % float(frequency_mhz))
            f.write("Modulation: %s\n" % modulation)
            for pkt in packets:
                ts_ms = int(pkt.get("ts_ms", 0))
                data = pkt.get("data", b"")
                if isinstance(data, bytes):
                    hex_data = data.hex()
                else:
                    hex_data = str(data)
                f.write("Packet: %d %s\n" % (ts_ms, hex_data))

    @classmethod
    def read(cls, path):
        freq = None
        modulation = "OOK"
        packets = []

        with open(path, "r") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("Frequency:"):
                    freq = float(line.split(":", 1)[1].strip())
                    continue
                if line.startswith("Modulation:"):
                    modulation = line.split(":", 1)[1].strip()
                    continue
                if line.startswith("Packet:"):
                    body = line.split(":", 1)[1].strip()
                    parts = body.split(" ", 1)
                    if len(parts) != 2:
                        continue
                    ts_ms = int(parts[0])
                    data = bytes.fromhex(parts[1])
                    packets.append({"ts_ms": ts_ms, "data": data})

        return {
            "frequency_mhz": freq,
            "modulation": modulation,
            "packets": packets,
        }
