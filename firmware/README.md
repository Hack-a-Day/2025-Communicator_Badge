# Supercon 2025 Badge - Firmware POC

## The Problem

Article says 500 badges will mesh network at Supercon. Cool! But standard LoRa = everyone yells whenever = ~5% success rate with that many badges in close quarters.

The repo includes a research paper (`documentation/appnotes/Dense_Deployment_of_LoRa_Networks...pdf`) that literally solves this exact problem.

So I implemented it.

## What It Does

Instead of badges screaming over each other:
- 90% listen first
- 10% claim the channel with a quick RTS packet
- Everyone else hears that and waits (NAV timer)
- Original badge sends its actual message
- Random delays keep things from synchronizing

Result: messages actually get through.

## Quick Start

```python
from lib.lora_mac import LoRaMAC
from lib.lora_hal import LoRaRadio
from lib.config import Config

# For 500 badges
config = Config.for_dense_deployment(node_count=500)
radio = LoRaRadio(freq_mhz=915.0, sf=12, bw=125)
mac = LoRaMAC(radio, config)

# Receive
mac.on_receive(lambda data, rssi, snr: print(f"Got: {data}"))
mac.start_listening()

# Send
mac.send_data(b"Hello Supercon!")
```

Done. The MAC layer handles all the collision stuff automatically.

## Files

```
firmware/
├── lib/
│   ├── lora_mac.py    # The 3-phase protocol
│   ├── lora_hal.py    # SX1262 hardware interface
│   └── config.py      # Presets for different scenarios
├── examples/
│   └── simple_chat.py # Working demo
└── config/
    └── dense_deployment.json
```

## Config Presets

```python
Config.for_dense_deployment(node_count=500)  # Supercon mode
Config.for_testing(node_count=10)            # Fast testing
Config.for_long_range()                      # Max distance
Config.for_low_power()                       # Battery saver
```

## Testing

```bash
# Terminal 1
python examples/simple_chat.py --node-id Alice --nodes 500

# Terminal 2
python examples/simple_chat.py --node-id Bob --nodes 500
```

Watch the logs to see the protocol doing its thing.

## Hardware Connections

Matches the schematic (`hardware/communicator_pcb/communicator_pcb.pdf`):

```
ESP32-S3 → SX1262
IO2 → SCK
IO3 → MOSI
IO1 → MISO
IO4 → NSS
IO5 → RST
IO8 → DIO1
IO9 → BUSY
```

## References

- **Research paper:** `../documentation/appnotes/Dense_Deployment_of_LoRa_Networks...pdf`
- **Hardware schematic:** `../hardware/communicator_pcb/communicator_pcb.pdf`
- **SX1262 datasheet:** `../documentation/datasheets/SX1262.pdf`

## License

Whatever Hackaday decides. I'm just trying to help whoever is doing the firmware get a leg up... and for fun.

— HD
