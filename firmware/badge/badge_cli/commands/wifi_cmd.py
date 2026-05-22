"""WiFi commands: wifi scan and hotspot/AP management."""

class WifiCommands:
    """Registers the 'wifi' command group for Wardriving."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "wifi",
            {
                "scan": (self._cmd_scan, "Scan for Wi-Fi networks: wifi scan"),
                "ap": (
                    self._cmd_ap,
                    "Manage hotspot/AP mode: wifi ap <on|off|status> [ssid] [password] [channel]",
                ),
            },
            "Wi-Fi operations"
        )

    def _cmd_scan(self, args):
        w = self.shell._write
        w("Scanning for Wi-Fi networks...")
        
        try:
            import network
            sta_if = network.WLAN(network.STA_IF)
            if not sta_if.active():
                sta_if.active(True)
            
            networks = sta_if.scan()
            if not networks:
                w("No networks found.")
                return
                
            w("BSSID             | RSSI | CH | AUTH | SSID")
            w("-" * 65)
            for net in networks:
                ssid = net[0].decode('utf-8', 'ignore')
                bssid = ":".join("%02x" % b for b in net[1])
                channel = net[2]
                rssi = net[3]
                auth = net[4]
                auth_str = self._auth_to_str(auth)
                
                w(f"{bssid} | {rssi:>4} | {channel:>2} | {auth_str:>4} | {ssid}")
                
        except Exception as e:
            w("Error scanning Wi-Fi: " + str(e))
            
    def _auth_to_str(self, auth):
        # 0=open, 1=WEP, 2=WPA-PSK, 3=WPA2-PSK, 4=WPA/WPA2-PSK, 5=WPA2-ENTERPRISE, 6=WPA3-PSK
        auth_map = {
            0: "OPEN",
            1: "WEP",
            2: "WPA",
            3: "WPA2",
            4: "WPA+",
            5: "ENT",
            6: "WPA3",
        }
        return auth_map.get(auth, str(auth))

    def _cmd_ap(self, args):
        w = self.shell._write
        if not args or args[0] not in ("on", "off", "status"):
            w("Usage: wifi ap <on|off|status> [ssid] [password] [channel]")
            w("Examples:")
            w("  wifi ap on BadgeHotspot")
            w("  wifi ap on BadgeHotspot pass12345 6")
            w("  wifi ap status")
            w("  wifi ap off")
            return

        action = args[0]
        try:
            import network
            ap_if = network.WLAN(getattr(network, "AP_IF", 1))
        except Exception as e:
            w("Error opening AP interface: " + str(e))
            return

        if action == "off":
            try:
                ap_if.active(False)
                w("Hotspot disabled")
            except Exception as e:
                w("Error disabling hotspot: " + str(e))
            return

        if action == "status":
            self._write_ap_status(ap_if)
            return

        # action == "on"
        ssid = args[1] if len(args) > 1 else "BadgeHotspot"
        password = args[2] if len(args) > 2 else ""
        channel = 6
        if len(args) > 3:
            try:
                channel = int(args[3])
            except ValueError:
                w("Invalid channel, using 6")
                channel = 6
        if channel < 1 or channel > 13:
            w("Channel out of range (1-13), using 6")
            channel = 6

        if password and len(password) < 8:
            w("Password must be at least 8 characters")
            return

        try:
            ap_if.active(True)

            if password:
                auth_mode = getattr(network, "AUTH_WPA_WPA2_PSK", None)
                if auth_mode is not None:
                    ap_if.config(essid=ssid, password=password, channel=channel, authmode=auth_mode)
                else:
                    ap_if.config(essid=ssid, password=password, channel=channel)
            else:
                open_mode = getattr(network, "AUTH_OPEN", None)
                if open_mode is not None:
                    ap_if.config(essid=ssid, channel=channel, authmode=open_mode)
                else:
                    ap_if.config(essid=ssid, channel=channel)

            security = "WPA/WPA2" if password else "OPEN"
            w("Hotspot enabled: SSID=%s CH=%d SECURITY=%s" % (ssid, channel, security))
            self._write_ap_status(ap_if)
        except Exception as e:
            w("Error enabling hotspot: " + str(e))

    def _write_ap_status(self, ap_if):
        w = self.shell._write
        try:
            active = ap_if.active()
        except Exception:
            active = False

        if not active:
            w("Hotspot status: OFF")
            return

        ssid = self._safe_ap_config(ap_if, "essid", "")
        channel = self._safe_ap_config(ap_if, "channel", "?")
        auth = self._safe_ap_config(ap_if, "authmode", "?")
        ip = "?"
        try:
            ip = ap_if.ifconfig()[0]
        except Exception:
            pass

        w("Hotspot status: ON")
        w("  SSID: " + str(ssid))
        w("  Channel: " + str(channel))
        w("  Auth: " + str(auth))
        w("  IP: " + str(ip))

    def _safe_ap_config(self, ap_if, key, default):
        try:
            return ap_if.config(key)
        except Exception:
            return default
