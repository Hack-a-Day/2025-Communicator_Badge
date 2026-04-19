"""WiFi commands: wifi scan."""

class WifiCommands:
    """Registers the 'wifi' command group for Wardriving."""

    def __init__(self, shell):
        self.shell = shell
        shell.register_group(
            "wifi",
            {
                "scan": (self._cmd_scan, "Scan for Wi-Fi networks: wifi scan"),
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
