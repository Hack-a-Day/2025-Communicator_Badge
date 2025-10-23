"""
Simple chat demo - shows the MAC protocol in action

Run this on multiple badges to see the collision avoidance working.

Usage:
    python simple_chat.py --node-id Alice --nodes 500
"""

import sys
import time
sys.path.append('../lib')

from lora_mac import LoRaMAC
from lora_hal import LoRaRadio
from config import Config


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Supercon Badge Chat')
    parser.add_argument('--node-id', required=True, help='Your badge name')
    parser.add_argument('--nodes', type=int, default=500, help='How many badges expected')
    parser.add_argument('--freq', type=float, default=915.0, help='Frequency (915 US, 868 EU)')
    parser.add_argument('--channel', type=str, default='#general', help='Chat room')

    args = parser.parse_args()

    print("="*60)
    print("  2025 SUPERCON COMMUNICATOR BADGE")
    print("  Dense Deployment Chat Demo")
    print("="*60)
    print(f"  Node:      {args.node_id}")
    print(f"  Expected:  ~{args.nodes} badges")
    print(f"  Frequency: {args.freq} MHz")
    print(f"  Channel:   {args.channel}")
    print("="*60)
    print()

    # Set up config for dense deployment
    config = Config.for_dense_deployment(node_count=args.nodes)
    config.node_id = args.node_id
    config.freq_mhz = args.freq

    print(f"[Config] {config}")
    print()

    # Initialize radio
    print("[Init] Initializing SX1262...")
    try:
        radio = LoRaRadio(
            spi_id=1,
            freq_mhz=config.freq_mhz,
            sf=config.spreading_factor,
            bw=config.bandwidth,
            tx_power=config.tx_power
        )
    except Exception as e:
        print(f"[Error] Radio init failed: {e}")
        print("[Info] This is expected if not running on actual hardware.")
        print("[Info] Code shows how it works though!")
        return

    # Initialize MAC layer
    print("[Init] Setting up collision avoidance...")
    mac = LoRaMAC(radio, config)
    print()

    # Handle incoming messages
    def on_message(data, rssi, snr):
        try:
            msg = data.decode('utf-8')
            print(f"\r[{args.channel}] {msg}")
            print(f"[{args.node_id}]> ", end='', flush=True)
        except:
            print(f"\r[{args.channel}] <binary: {len(data)} bytes>")
            print(f"[{args.node_id}]> ", end='', flush=True)

    mac.on_receive(on_message)
    mac.start_listening()

    print(f"[Ready] Type messages, 'quit' to exit")
    print(f"[Protocol] P={config.phase2_probability}, W={config.backoff_window}")
    print()

    # Main loop
    try:
        while True:
            print(f"[{args.node_id}]> ", end='', flush=True)
            message = input()

            if message.lower() in ['quit', 'exit', 'q']:
                break

            if not message.strip():
                continue

            # Format: "NodeID: message"
            msg_bytes = f"{args.node_id}: {message}".encode('utf-8')

            # Send it!
            print(f"[MAC] Sending ({len(msg_bytes)} bytes)...")
            success = mac.send_data(msg_bytes)

            if success:
                print(f"[MAC] Sent!")
            else:
                print(f"[MAC] Deferred (in NAV)")

            print()

    except KeyboardInterrupt:
        print("\n[Bye]")

    # Show stats
    print("\n" + "="*60)
    mac.print_stats()
    print("="*60)


if __name__ == '__main__':
    main()
