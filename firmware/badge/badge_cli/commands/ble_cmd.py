"""BLE commands: ble scan."""

class BleCommands:
    """Registers the 'ble' command group for Wardriving."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "ble",
            {
                "scan": (self._cmd_scan, "Scan for BLE devices: ble scan [timeout_sec]"),
            },
            "Bluetooth Low Energy operations"
        )

    def _cmd_scan(self, args):
        w = self.shell._write
        timeout_sec = 5
        if args:
            try:
                timeout_sec = int(args[0])
            except ValueError:
                w("Invalid timeout. Using 5 seconds.")
                
        w(f"Scanning for BLE devices for {timeout_sec} seconds...")
        
        try:
            import bluetooth
            ble = bluetooth.BLE()
            ble.active(True)
            
            # Simple synchronous scan if using mock, but for real async hardware we might need an event loop
            # However, for simplicity in CLI, we'll use a blocking sleep or mock approach
            import time
            devices = []
            
            def bt_irq(event, data):
                if event == 5: # _IRQ_SCAN_RESULT
                    addr_type, addr, adv_type, rssi, adv_data = data
                    mac = ":".join("%02x" % b for b in addr)
                    devices.append((mac, rssi, bytes(adv_data)))
            
            if hasattr(ble, "irq"):
                ble.irq(bt_irq)
                ble.gap_scan(timeout_sec * 1000, 30000, 30000)
                
                # Wait for scan to finish
                start_scan = time.time()
                while time.time() - start_scan < timeout_sec + 0.5:
                    if self.shell.check_interrupt():
                        ble.gap_scan(None)  # Stop scan
                        w("Interrupted.")
                        break
                    time.sleep(0.1)
            elif hasattr(ble, "mock_scan"):
                devices = ble.mock_scan(timeout_sec)
            
            if not devices:
                w("No BLE devices found.")
                return
                
            w("MAC Address       | RSSI | DATA_LEN")
            w("-" * 45)
            # Deduplicate by MAC
            seen = set()
            for mac, rssi, adv_data in devices:
                if mac not in seen:
                    w(f"{mac} | {rssi:>4} | {len(adv_data):>8}")
                    seen.add(mac)
                    
        except Exception as e:
            w("Error scanning BLE: " + str(e))
