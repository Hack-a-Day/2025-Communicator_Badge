# ai_wifi.py - WiFi manager for AI Chat badge app
# Adapted from cyberdreck/app/wifi_mgr.py (NVS credential storage, connect/scan)
# Upload to /apps/ on the badge alongside ai_secrets.py

import network, time

_PREFS_MAX    = 9
_RETRY_DELAY  = 0.3   # seconds between connection checks
_MAX_ATTEMPTS = 50    # 50 × 0.3s = 15s total connect timeout

_wlan  = None
_creds = []   # list of {'ssid': str, 'pass': str}

def _get_wlan():
    global _wlan
    if _wlan is None:
        network.country('GB')
        _wlan = network.WLAN(network.STA_IF)
        _wlan.active(True)
    return _wlan

# ── NVS credential store ──────────────────────────────────────────────────────
def load_creds():
    global _creds
    _creds = []
    try:
        import esp32
        nvs = esp32.NVS("aiwifi")
        n = nvs.get_i32("n")
        for i in range(min(n, _PREFS_MAX)):
            buf = bytearray(33)
            nb  = nvs.get_blob(f"s{i}", buf)
            ssid = buf[:nb].decode()
            buf2 = bytearray(64)
            nb2  = nvs.get_blob(f"p{i}", buf2)
            pwd  = buf2[:nb2].decode()
            _creds.append({'ssid': ssid, 'pass': pwd})
    except Exception:
        pass

def save_creds():
    try:
        import esp32
        nvs = esp32.NVS("aiwifi")
        nvs.set_i32("n", len(_creds))
        for i, c in enumerate(_creds):
            nvs.set_blob(f"s{i}", c['ssid'].encode())
            nvs.set_blob(f"p{i}", c['pass'].encode())
        nvs.commit()
    except Exception:
        pass

def insert_cred(ssid, password):
    global _creds
    _creds = [c for c in _creds if c['ssid'] != ssid]
    _creds.insert(0, {'ssid': ssid, 'pass': password})
    if len(_creds) > _PREFS_MAX:
        _creds = _creds[:_PREFS_MAX]
    save_creds()

def find_pass(ssid):
    for c in _creds:
        if c['ssid'] == ssid:
            return c['pass'] if c['pass'] else None
    return None

# ── Connection ────────────────────────────────────────────────────────────────
def connect(ssid, password):
    w = _get_wlan()
    w.disconnect()
    w.connect(ssid, password)
    for _ in range(_MAX_ATTEMPTS):
        if w.isconnected():
            return True
        time.sleep(_RETRY_DELAY)
    return False

def disconnect():
    if _wlan:
        _wlan.disconnect()

def is_connected():
    return _wlan is not None and _wlan.isconnected()

def rssi():
    if not is_connected():
        return -100
    try:
        return _wlan.status('rssi')
    except Exception:
        return -100

def scan_aps():
    """Scan and return list of (ssid, rssi) sorted by signal strength."""
    w = _get_wlan()
    seen = {}
    for r in w.scan():
        try:
            ssid = r[0].decode() if isinstance(r[0], bytes) else r[0]
        except Exception:
            continue
        if ssid and (ssid not in seen or r[3] > seen[ssid]):
            seen[ssid] = r[3]
    return sorted(seen.items(), key=lambda x: -x[1])[:9]

def ensure_connected(ssid=None, password=None):
    """Connect using stored NVS creds first, then ssid/password from secrets.
    Saves successful credentials to NVS for next time. Returns True if connected."""
    if is_connected():
        return True
    load_creds()
    for c in _creds:
        if connect(c['ssid'], c['pass']):
            return True
    if ssid:
        if connect(ssid, password or ''):
            insert_cred(ssid, password or '')
            return True
    return False
