"""BLE commands: scan and advertise."""

class BleCommands:
    """Registers the 'ble' command group for Wardriving."""

    def __init__(self, shell):
        self.shell = shell
        self._ble = None
        shell.register_group(
            "ble",
            {
                "scan": (self._cmd_scan, "Scan for BLE devices: ble scan [timeout_sec]"),
                "advertise": (
                    self._cmd_advertise,
                    "Start/stop BLE advertising: ble advertise <on|off> [name]",
                ),
                "addr": (self._cmd_addr, "Show local BLE MAC address"),
            },
            "Bluetooth Low Energy operations"
        )

    def _get_ble(self):
        if self._ble is None:
            import bluetooth
            self._ble = bluetooth.BLE()
        self._ble.active(True)
        return self._ble

    def _extract_local_name(self, adv_data):
        idx = 0
        data = bytes(adv_data)
        while idx < len(data):
            field_len = data[idx]
            if field_len == 0:
                break
            field_end = idx + 1 + field_len
            if field_end > len(data):
                break
            ad_type = data[idx + 1]
            if ad_type in (0x08, 0x09):
                raw = data[idx + 2:field_end]
                try:
                    return raw.decode("utf-8", errors="ignore")
                except Exception:
                    return ""
            idx = field_end
        return ""

    def _build_name_adv_payload(self, name):
        if not name:
            name = "Badge"

        marker = self._build_hitl_marker(name)
        payload = bytearray()
        # Flags: LE General Discoverable Mode, BR/EDR not supported.
        payload.extend(b"\x02\x01\x06")

        marker_bytes = marker.encode("utf-8", errors="ignore")[:12]
        mfg_data = b"\xFF\xFF" + marker_bytes
        marker_field_len = 2 + len(mfg_data)  # len/type + data
        if len(payload) + marker_field_len <= 31:
            payload.append(1 + len(mfg_data))
            payload.append(0xFF)
            payload.extend(mfg_data)

        # Keep payload <= 31 bytes.
        max_name_len = max(0, 31 - len(payload) - 2)
        name_raw = name.encode("utf-8", errors="ignore")
        name_bytes = name_raw[:max_name_len]
        name_type = 0x09 if len(name_bytes) == len(name_raw) else 0x08
        if name_bytes:
            payload.append(1 + len(name_bytes))
            payload.append(name_type)
            payload.extend(name_bytes)

        return bytes(payload), marker

    def _build_hitl_marker(self, name):
        cleaned = ""
        for ch in name.upper():
            if ("A" <= ch <= "Z") or ("0" <= ch <= "9"):
                cleaned += ch
        if not cleaned:
            cleaned = "BADGE"
        return "HT" + cleaned[-6:]

    def _extract_hitl_marker(self, adv_data):
        idx = 0
        data = bytes(adv_data)
        while idx < len(data):
            field_len = data[idx]
            if field_len == 0:
                break
            field_end = idx + 1 + field_len
            if field_end > len(data):
                break
            ad_type = data[idx + 1]
            if ad_type == 0xFF and field_len >= 3:
                raw = data[idx + 2:field_end]
                if len(raw) >= 2 and raw[0] == 0xFF and raw[1] == 0xFF:
                    try:
                        return raw[2:].decode("utf-8", errors="ignore")
                    except Exception:
                        return ""
            idx = field_end
        return ""

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
            ble = self._get_ble()
            
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
                try:
                    # Active scan requests scan-response payloads (often where names live).
                    ble.gap_scan(timeout_sec * 1000, 30000, 30000, True)
                except TypeError:
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
                
            w("MAC Address       | RSSI | NAME                     | MARKER     | DATA_LEN")
            w("-" * 68)
            # Deduplicate by MAC, but keep the best record (prefer one with a name).
            best_by_mac = {}
            for mac, rssi, adv_data in devices:
                name = self._extract_local_name(adv_data)
                marker = self._extract_hitl_marker(adv_data)
                current = best_by_mac.get(mac)
                if current is None:
                    best_by_mac[mac] = (rssi, name, marker, len(adv_data))
                    continue

                cur_rssi, cur_name, cur_marker, cur_len = current
                # Prefer records with marker/name. If both/none, keep stronger/larger sample.
                if (
                    (not cur_marker and marker)
                    or (not cur_name and name)
                    or (
                        bool(cur_name) == bool(name)
                        and bool(cur_marker) == bool(marker)
                        and (rssi > cur_rssi or len(adv_data) > cur_len)
                    )
                ):
                    best_by_mac[mac] = (rssi, name, marker, len(adv_data))

            for mac, (rssi, name, marker, data_len) in best_by_mac.items():
                w(f"{mac} | {rssi:>4} | {name[:24]:<24} | {marker[:10]:<10} | {data_len:>8}")
                    
        except Exception as e:
            w("Error scanning BLE: " + str(e))

    def _cmd_advertise(self, args):
        w = self.shell._write
        if not args or args[0] not in ("on", "off"):
            w("Usage: ble advertise <on|off> [name]")
            return

        action = args[0]
        name = " ".join(args[1:]).strip() if len(args) > 1 else "Badge"

        try:
            ble = self._get_ble()

            if action == "on":
                payload, marker = self._build_name_adv_payload(name)
                # interval_us=100ms for easy scan visibility while keeping CPU use reasonable.
                ble.gap_advertise(100000, adv_data=payload)
                w("BLE advertising ON as: %s marker:%s" % (name, marker))
            else:
                ble.gap_advertise(None)
                w("BLE advertising OFF")
        except Exception as e:
            w("Error advertising BLE: " + str(e))

    def _cmd_addr(self, args):
        w = self.shell._write
        try:
            ble = self._get_ble()
            if hasattr(ble, "config"):
                cfg = ble.config("mac")
                if isinstance(cfg, tuple) and len(cfg) >= 2:
                    mac = cfg[1]
                else:
                    mac = cfg
                if isinstance(mac, (bytes, bytearray)):
                    mac_text = ":".join("%02x" % b for b in mac)
                    w("BLE MAC: " + mac_text)
                    return
            w("BLE MAC unavailable")
        except Exception as e:
            w("Error reading BLE MAC: " + str(e))
