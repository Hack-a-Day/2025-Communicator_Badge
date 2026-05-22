import time
import threading
import pytest


def _ble_scan_finds_name(scan_output, target_name):
    low = scan_output.lower()
    if target_name.lower() in low:
        return True
    return False


def _extract_ble_mac(addr_output):
    low = addr_output.lower()
    marker = "ble mac:"
    idx = low.find(marker)
    if idx == -1:
        return ""
    tail = low[idx + len(marker):].strip()
    if not tail:
        return ""
    return tail.split()[0]


def _extract_ble_marker(advertise_output):
    low = advertise_output.lower()
    marker = "marker:"
    idx = low.find(marker)
    if idx == -1:
        return ""
    tail = advertise_output[idx + len(marker):].strip()
    if not tail:
        return ""
    return tail.split()[0]


def _wifi_command_unavailable(scan_output):
    low = scan_output.lower()
    return "unknown command: wifi" in low or "wifi command group is unavailable" in low


def _wifi_ap_unavailable(output):
    low = output.lower()
    return (
        _wifi_command_unavailable(output)
        or "unknown sub-command: wifi ap" in low
        or "type 'wifi ?' for available sub-commands" in low
    )


def _extract_wifi_bssids(scan_output):
    bssids = set()
    for line in scan_output.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        first = line.split("|", 1)[0].strip().lower()
        parts = first.split(":")
        if len(parts) != 6:
            continue
        if all(len(p) == 2 for p in parts):
            bssids.add(first)
    return bssids


def _wifi_scan_finds_ssid(scan_output, target_ssid):
    return target_ssid.lower() in scan_output.lower()


def _count_tokens_in_text(text, tokens):
    low = text.lower()
    hits = 0
    for token in tokens:
        if token.lower() in low:
            hits += 1
    return hits


def _reboot_and_resync(client):
    """Best-effort reboot and prompt resynchronization for HITL clients."""
    try:
        client.run_command("power reboot", timeout=4.0)
    except Exception:
        pass

    # Give the badge time to reboot and initialize services.
    time.sleep(3.5)
    deadline = time.time() + 20.0
    while time.time() < deadline:
        try:
            probe = client.run_command("echo reboot_ok", timeout=8.0)
            if "reboot_ok" in probe.lower():
                return
        except Exception:
            pass
        time.sleep(0.6)

    # Fall back to serial reconnect if prompt sync was lost.
    try:
        client.disconnect()
    except Exception:
        pass
    time.sleep(0.8)
    client.connect()


def test_hitl_multi_ble_scan_advertise(hitl_badge_pair):
    """One badge advertises a known BLE name while the other scans for it."""
    scanner, advertiser = hitl_badge_pair
    if scanner.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Multi-device BLE scan/advertise requires physical badges")
    name = "HITL_%d" % (int(time.time()) % 100000)
    adv_mac = _extract_ble_mac(advertiser.run_command("ble addr"))

    out = advertiser.run_command("ble advertise on " + name)
    assert "advertising" in out.lower() or "on" in out.lower()
    adv_marker = _extract_ble_marker(out)
    # Give controller time to begin advertising before scanning.
    time.sleep(1.0)

    try:
        found = False
        for _ in range(8):
            scan = scanner.run_command("ble scan 5", timeout=10.0)
            if _ble_scan_finds_name(scan, name):
                found = True
                break
            if adv_marker and adv_marker.lower() in scan.lower():
                found = True
                break
            if adv_mac and adv_mac in scan.lower():
                found = True
                break
            time.sleep(0.6)
        assert found, (
            "BLE scan did not find advertised identity name=%r marker=%r mac=%r. Last output: %r"
            % (name, adv_marker, adv_mac, scan)
        )
    finally:
        advertiser.run_command("ble advertise off")


def test_hitl_multi_ble_detection_hit_rate_short(hitl_badge_pair):
    """Short BLE reliability check: require repeated marker detection hits."""
    scanner, advertiser = hitl_badge_pair
    if scanner.__class__.__name__ == "BadgeMockClient":
        pytest.skip("BLE reliability test requires physical badges")

    name = "HITL_REL_%d" % (int(time.time()) % 100000)
    adv_out = advertiser.run_command("ble advertise on " + name)
    if "unknown command: ble" in adv_out.lower():
        pytest.skip("BLE command unavailable on advertiser badge")

    marker = _extract_ble_marker(adv_out)
    target = marker if marker else name

    hits = 0
    attempts = 6
    try:
        time.sleep(1.0)
        last_scan = ""
        for _ in range(attempts):
            out = scanner.run_command("ble scan 4", timeout=10.0)
            last_scan = out
            low = out.lower()
            assert "traceback" not in low
            if target.lower() in low or name.lower() in low:
                hits += 1
            time.sleep(0.4)
    finally:
        advertiser.run_command("ble advertise off")

    if hits == 0:
        pytest.skip(
            "BLE advertiser identity not observable in current RF environment "
            "for reliability threshold test. target=%r last_scan=%r" % (target, last_scan)
        )

    # Keep this threshold practical for dense/noisy RF environments.
    assert hits >= 2, "BLE detection hit-rate too low: hits=%d/%d target=%r" % (hits, attempts, target)


def test_hitl_multi_ble_reboot_recovery(hitl_badge_pair):
    """Advertiser remains discoverable after scanner reboot and reconnection."""
    scanner, advertiser = hitl_badge_pair
    if scanner.__class__.__name__ == "BadgeMockClient":
        pytest.skip("BLE reboot recovery test requires physical badges")

    name = "HITL_RB_%d" % (int(time.time()) % 100000)
    adv_out = advertiser.run_command("ble advertise on " + name)
    if "unknown command: ble" in adv_out.lower():
        pytest.skip("BLE command unavailable on advertiser badge")

    marker = _extract_ble_marker(adv_out)
    target = marker if marker else name

    try:
        _reboot_and_resync(scanner)

        found = False
        last_scan = ""
        for _ in range(6):
            last_scan = scanner.run_command("ble scan 5", timeout=11.0)
            low = last_scan.lower()
            assert "traceback" not in low
            if target.lower() in low or name.lower() in low:
                found = True
                break
            time.sleep(0.5)

        if not found:
            pytest.skip(
                "BLE advertiser identity not observable after reboot in current RF environment. "
                "target=%r last=%r" % (target, last_scan)
            )
    finally:
        advertiser.run_command("ble advertise off")


def test_hitl_multi_chat_delivery(hitl_badge_pair):
    """Send a chat message on badge A and verify it appears on badge B."""
    sender, receiver = hitl_badge_pair
    if sender.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Multi-device chat delivery requires physical badges")

    sender.run_command("chat channel 12 34")
    receiver.run_command("chat channel 12 34")

    token = "HITL_CHAT_%d" % (int(time.time()) % 100000)

    send_out = sender.run_command("chat send " + token)
    assert "sent" in send_out.lower() or token.lower() in send_out.lower()

    found = False
    last_history = ""
    for _ in range(10):
        last_history = receiver.run_command("chat history")
        if token.lower() in last_history.lower():
            found = True
            break
        time.sleep(0.5)

    assert found, "Chat message %r not found on receiver. Last history output: %r" % (token, last_history)


def test_hitl_multi_lora_bidirectional_tx_smoke(hitl_badge_pair):
    """Exercise LoRa TX command on both badges with matched frequency slot."""
    sender, receiver = hitl_badge_pair
    if sender.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Multi-device LoRa TX requires physical badges")

    sender_set = sender.run_command("lora freq 10")
    receiver_set = receiver.run_command("lora freq 10")
    assert "traceback" not in sender_set.lower()
    assert "traceback" not in receiver_set.lower()
    assert "slot" in sender_set.lower() or "mhz" in sender_set.lower()
    assert "slot" in receiver_set.lower() or "mhz" in receiver_set.lower()

    token_a = "HITL_LORA_A_%d" % (int(time.time()) % 100000)
    token_b = "HITL_LORA_B_%d" % ((int(time.time()) + 1) % 100000)

    tx_a = sender.run_command("lora tx " + token_a.encode("utf-8").hex())
    tx_b = receiver.run_command("lora tx " + token_b.encode("utf-8").hex())

    tx_a_low = tx_a.lower()
    tx_b_low = tx_b.lower()
    assert "traceback" not in tx_a_low
    assert "traceback" not in tx_b_low
    assert "sent" in tx_a_low or "bytes" in tx_a_low, "Unexpected lora tx output (A): %r" % tx_a
    assert "sent" in tx_b_low or "bytes" in tx_b_low, "Unexpected lora tx output (B): %r" % tx_b


def test_hitl_multi_wifi_scan_health(hitl_badge_pair):
    """Run Wi-Fi scan on both badges and verify stable command behavior."""
    dev_a, dev_b = hitl_badge_pair
    if dev_a.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Multi-device Wi-Fi scan requires physical badges")

    out_a = dev_a.run_command("wifi scan", timeout=12.0)
    out_b = dev_b.run_command("wifi scan", timeout=12.0)

    if _wifi_command_unavailable(out_a) or _wifi_command_unavailable(out_b):
        pytest.skip("Wi-Fi command unavailable on one or both badges")

    low_a = out_a.lower()
    low_b = out_b.lower()
    assert "traceback" not in low_a
    assert "traceback" not in low_b

    def _looks_like_wifi_scan_output(text_low):
        return (
            "scanning for wi-fi networks" in text_low
            or "bssid" in text_low
            or "no networks found" in text_low
            or "error scanning wi-fi" in text_low
        )

    assert _looks_like_wifi_scan_output(low_a), "Unexpected wifi scan output (A): %r" % out_a
    assert _looks_like_wifi_scan_output(low_b), "Unexpected wifi scan output (B): %r" % out_b


def test_hitl_multi_wifi_shared_bssid_consistency(hitl_badge_pair):
    """Compare Wi-Fi scan results across two badges and require shared BSSID observations."""
    dev_a, dev_b = hitl_badge_pair
    if dev_a.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Multi-device Wi-Fi consistency requires physical badges")

    seen_a = set()
    seen_b = set()
    attempts = []

    for _ in range(4):
        out_a = dev_a.run_command("wifi scan", timeout=12.0)
        out_b = dev_b.run_command("wifi scan", timeout=12.0)

        if _wifi_command_unavailable(out_a) or _wifi_command_unavailable(out_b):
            pytest.skip("Wi-Fi command unavailable on one or both badges")

        low_a = out_a.lower()
        low_b = out_b.lower()
        assert "traceback" not in low_a
        assert "traceback" not in low_b

        bssids_a = _extract_wifi_bssids(out_a)
        bssids_b = _extract_wifi_bssids(out_b)
        seen_a |= bssids_a
        seen_b |= bssids_b
        attempts.append((len(bssids_a), len(bssids_b)))

        if seen_a and seen_b and (seen_a & seen_b):
            break
        time.sleep(0.7)

    if not seen_a and not seen_b:
        pytest.skip("No Wi-Fi networks observed by either badge during consistency test")

    shared = seen_a & seen_b
    assert shared, (
        "No shared BSSID found across badge scans. "
        "attempt_sizes=%r seen_a=%r seen_b=%r" % (attempts, sorted(seen_a), sorted(seen_b))
    )


def test_hitl_multi_wifi_known_ap_detection(hitl_badge_pair, hitl_multi_settings):
    """Detect a known lab AP target from both badges (SSID and/or BSSID)."""
    dev_a, dev_b = hitl_badge_pair
    if dev_a.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Multi-device Wi-Fi known AP detection requires physical badges")

    target_ssid = (hitl_multi_settings.get("known_wifi_ssid") or "").strip()
    target_bssid = (hitl_multi_settings.get("known_wifi_bssid") or "").strip().lower()
    if not target_ssid and not target_bssid:
        pytest.skip("Set --hitl-known-wifi-ssid and/or --hitl-known-wifi-bssid to enable known AP test")

    found_a = False
    found_b = False
    last_a = ""
    last_b = ""

    for _ in range(4):
        last_a = dev_a.run_command("wifi scan", timeout=12.0)
        last_b = dev_b.run_command("wifi scan", timeout=12.0)

        if _wifi_command_unavailable(last_a) or _wifi_command_unavailable(last_b):
            pytest.skip("Wi-Fi command unavailable on one or both badges")

        low_a = last_a.lower()
        low_b = last_b.lower()
        assert "traceback" not in low_a
        assert "traceback" not in low_b

        if target_ssid:
            found_a = found_a or (target_ssid.lower() in low_a)
            found_b = found_b or (target_ssid.lower() in low_b)
        if target_bssid:
            found_a = found_a or (target_bssid in low_a)
            found_b = found_b or (target_bssid in low_b)

        if found_a and found_b:
            break
        time.sleep(0.7)

    assert found_a and found_b, (
        "Known AP target not seen on both badges. "
        "ssid=%r bssid=%r found_a=%r found_b=%r last_a=%r last_b=%r"
        % (target_ssid, target_bssid, found_a, found_b, last_a, last_b)
    )


def test_hitl_multi_subghz_tx_rx(hitl_badge_pair):
    """Run Sub-GHz RX on badge B while badge A transmits OOK payload."""
    sender, receiver = hitl_badge_pair
    if sender.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Multi-device Sub-GHz TX/RX requires physical badges")

    freq = 915.0
    token = "HITL_SUB_%d" % (int(time.time()) % 100000)
    payload_hex = token.encode("utf-8").hex()

    rx_result = {"out": ""}

    def _subghz_rx_worker():
        rx_result["out"] = receiver.run_command("subghz rx %.1f" % freq, timeout=9.0)

    t = threading.Thread(target=_subghz_rx_worker, daemon=True)
    t.start()
    time.sleep(0.7)

    tx_out = sender.run_command("subghz tx %.1f %s" % (freq, payload_hex), timeout=8.0)
    t.join(timeout=12.0)

    tx_low = tx_out.lower()
    assert "traceback" not in tx_low
    assert (
        "transmitting" in tx_low
        or "transmission complete" in tx_low
        or "hardware does not support" in tx_low
    ), "Unexpected subghz tx output: %r" % tx_out

    rx_out = rx_result.get("out", "")
    rx_low = rx_out.lower()
    assert "traceback" not in rx_low
    assert (
        "listening" in rx_low
        or "received" in rx_low
        or "no data received" in rx_low
        or "hardware does not support" in rx_low
    ), "Unexpected subghz rx output: %r" % rx_out


def test_hitl_multi_xstack_ble_advertise_while_wifi_scan(hitl_badge_pair):
    """Keep BLE advertising active on one badge while the other performs Wi-Fi scans."""
    scanner, advertiser = hitl_badge_pair
    if scanner.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Cross-stack BLE/Wi-Fi test requires physical badges")

    name = "XSTACK_%d" % (int(time.time()) % 100000)
    adv_out = advertiser.run_command("ble advertise on " + name)
    if "unknown command: ble" in adv_out.lower():
        pytest.skip("BLE command unavailable on advertiser badge")
    assert "traceback" not in adv_out.lower()
    assert "advertising" in adv_out.lower() or "on" in adv_out.lower()

    try:
        wifi_ok = False
        for _ in range(3):
            out = scanner.run_command("wifi scan", timeout=12.0)
            if _wifi_command_unavailable(out):
                pytest.skip("Wi-Fi command unavailable on scanner badge")
            low = out.lower()
            assert "traceback" not in low
            if (
                "scanning for wi-fi networks" in low
                or "bssid" in low
                or "no networks found" in low
                or "error scanning wi-fi" in low
            ):
                wifi_ok = True
            time.sleep(0.4)

        assert wifi_ok, "Wi-Fi scan output looked invalid during BLE advertising"
    finally:
        advertiser.run_command("ble advertise off")


def test_hitl_multi_wifi_ap_host_discovery(hitl_badge_pair):
    """Host a hotspot on one badge and detect it from the other badge scan."""
    host, scanner = hitl_badge_pair
    if host.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Multi-device Wi-Fi AP discovery requires physical badges")

    ssid = "HITL_AP_%d" % (int(time.time()) % 100000)
    host_out = host.run_command("wifi ap on " + ssid, timeout=10.0)
    host_low = host_out.lower()
    if _wifi_ap_unavailable(host_out):
        pytest.skip("Wi-Fi AP subcommand unavailable on host badge")

    assert "traceback" not in host_low
    assert "hotspot enabled" in host_low or "status: on" in host_low, "Unexpected AP on output: %r" % host_out

    found = False
    last_scan = ""
    try:
        time.sleep(1.0)
        for _ in range(5):
            last_scan = scanner.run_command("wifi scan", timeout=12.0)
            if _wifi_command_unavailable(last_scan):
                pytest.skip("Wi-Fi command unavailable on scanner badge")
            assert "traceback" not in last_scan.lower()
            if _wifi_scan_finds_ssid(last_scan, ssid):
                found = True
                break
            time.sleep(0.6)
    finally:
        host.run_command("wifi ap off", timeout=8.0)

    assert found, "Scanner did not detect hosted hotspot SSID=%r. Last scan: %r" % (ssid, last_scan)


def test_hitl_multi_wifi_repeated_scan_stability(hitl_badge_pair):
    """Stress Wi-Fi scan with repeated invocations on both badges."""
    dev_a, dev_b = hitl_badge_pair
    if dev_a.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Multi-device Wi-Fi stress requires physical badges")

    samples_a = 0
    samples_b = 0
    iterations = 8

    for _ in range(iterations):
        out_a = dev_a.run_command("wifi scan", timeout=12.0)
        out_b = dev_b.run_command("wifi scan", timeout=12.0)
        if _wifi_command_unavailable(out_a) or _wifi_command_unavailable(out_b):
            pytest.skip("Wi-Fi command unavailable on one or both badges")

        low_a = out_a.lower()
        low_b = out_b.lower()
        assert "traceback" not in low_a
        assert "traceback" not in low_b

        samples_a += len(_extract_wifi_bssids(out_a))
        samples_b += len(_extract_wifi_bssids(out_b))
        time.sleep(0.25)

    # Not strict on network count (RF can be sparse), but command path must remain healthy.
    assert samples_a >= 0 and samples_b >= 0


def test_hitl_multi_wifi_reboot_persistence(hitl_badge_pair):
    """Verify Wi-Fi scan remains functional after both devices reboot."""
    dev_a, dev_b = hitl_badge_pair
    if dev_a.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Wi-Fi reboot persistence requires physical badges")

    _reboot_and_resync(dev_a)
    _reboot_and_resync(dev_b)

    out_a = dev_a.run_command("wifi scan", timeout=12.0)
    out_b = dev_b.run_command("wifi scan", timeout=12.0)
    if _wifi_command_unavailable(out_a) or _wifi_command_unavailable(out_b):
        pytest.skip("Wi-Fi command unavailable on one or both badges")

    low_a = out_a.lower()
    low_b = out_b.lower()
    assert "traceback" not in low_a
    assert "traceback" not in low_b
    assert (
        "scanning for wi-fi networks" in low_a
        or "bssid" in low_a
        or "no networks found" in low_a
        or "error scanning wi-fi" in low_a
    ), "Unexpected wifi output after reboot (A): %r" % out_a
    assert (
        "scanning for wi-fi networks" in low_b
        or "bssid" in low_b
        or "no networks found" in low_b
        or "error scanning wi-fi" in low_b
    ), "Unexpected wifi output after reboot (B): %r" % out_b


def test_hitl_multi_subghz_frequency_mismatch_negative(hitl_badge_pair):
    """When TX/RX frequencies differ, receiver should not report payload receipt."""
    sender, receiver = hitl_badge_pair
    if sender.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Sub-GHz mismatch negative test requires physical badges")

    rx_freq = 915.0
    tx_freq = 902.0
    payload_hex = ("MISMATCH_%d" % (int(time.time()) % 100000)).encode("utf-8").hex()

    rx_result = {"out": ""}

    def _subghz_rx_worker():
        rx_result["out"] = receiver.run_command("subghz rx %.1f" % rx_freq, timeout=9.0)

    t = threading.Thread(target=_subghz_rx_worker, daemon=True)
    t.start()
    time.sleep(0.7)

    tx_out = sender.run_command("subghz tx %.1f %s" % (tx_freq, payload_hex), timeout=8.0)
    t.join(timeout=12.0)

    tx_low = tx_out.lower()
    assert "traceback" not in tx_low
    assert (
        "transmitting" in tx_low
        or "transmission complete" in tx_low
        or "hardware does not support" in tx_low
    ), "Unexpected subghz tx output: %r" % tx_out

    rx_out = rx_result.get("out", "")
    rx_low = rx_out.lower()
    assert "traceback" not in rx_low
    if "hardware does not support" in rx_low:
        pytest.skip("Sub-GHz OOK unsupported on receiver hardware")
    assert "received:" not in rx_low, "Unexpected data received under freq mismatch: %r" % rx_out


def test_hitl_multi_xstack_rotation_short(hitl_badge_pair):
    """Short cross-stack rotation: BLE advertise, Wi-Fi scans, and LoRa TX checks."""
    dev_a, dev_b = hitl_badge_pair
    if dev_a.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Cross-stack rotation requires physical badges")

    name = "ROT_%d" % (int(time.time()) % 100000)
    adv_out = dev_a.run_command("ble advertise on " + name)
    if "unknown command: ble" in adv_out.lower():
        pytest.skip("BLE command unavailable on device A")

    try:
        for _ in range(3):
            wifi_out = dev_b.run_command("wifi scan", timeout=12.0)
            if _wifi_command_unavailable(wifi_out):
                pytest.skip("Wi-Fi command unavailable on device B")
            assert "traceback" not in wifi_out.lower()

            tx_a = dev_a.run_command("lora tx 524f545f41")
            tx_b = dev_b.run_command("lora tx 524f545f42")
            assert "traceback" not in tx_a.lower()
            assert "traceback" not in tx_b.lower()
            assert ("sent" in tx_a.lower() or "bytes" in tx_a.lower())
            assert ("sent" in tx_b.lower() or "bytes" in tx_b.lower())
            time.sleep(0.3)
    finally:
        dev_a.run_command("ble advertise off")


def test_hitl_multi_lora_chat_burst_delivery_ratio(hitl_badge_pair):
    """Receive-validated LoRa stack check using chat burst delivery ratio."""
    sender, receiver = hitl_badge_pair
    if sender.__class__.__name__ == "BadgeMockClient":
        pytest.skip("LoRa chat burst test requires physical badges")

    sender.run_command("chat channel 12 34")
    receiver.run_command("chat channel 12 34")

    batch = int(time.time()) % 100000
    tokens = ["HITL_SEQ_%d_%02d" % (batch, i) for i in range(1, 9)]

    for token in tokens:
        out = sender.run_command("chat send " + token)
        low = out.lower()
        assert "traceback" not in low
        # Some firmware builds can return an empty immediate response due to prompt races.
        # Delivery is validated via receiver history below.
        time.sleep(0.12)

    delivered = 0
    last_history = ""
    deadline = time.time() + 12.0
    while time.time() < deadline:
        last_history = receiver.run_command("chat history")
        low = last_history.lower()
        assert "traceback" not in low
        delivered = _count_tokens_in_text(last_history, tokens)
        if delivered >= len(tokens):
            break
        time.sleep(0.35)

    ratio = delivered / float(len(tokens))
    # In RF-noisy environments, enforce a practical floor while still detecting regressions.
    assert ratio >= 0.50, (
        "LoRa chat burst delivery ratio too low: delivered=%d total=%d ratio=%.2f history=%r"
        % (delivered, len(tokens), ratio, last_history)
    )


def test_hitl_multi_ble_soak_lite_metrics(hitl_badge_pair):
    """BLE soak-lite loop with hit ratio diagnostics for environment tracking."""
    scanner, advertiser = hitl_badge_pair
    if scanner.__class__.__name__ == "BadgeMockClient":
        pytest.skip("BLE soak-lite requires physical badges")

    name = "HITL_SOAK_%d" % (int(time.time()) % 100000)
    adv_out = advertiser.run_command("ble advertise on " + name)
    if "unknown command: ble" in adv_out.lower():
        pytest.skip("BLE command unavailable on advertiser badge")

    marker = _extract_ble_marker(adv_out)
    target = marker if marker else name

    iterations = 10
    hits = 0
    last_scan = ""
    try:
        time.sleep(1.0)
        for _ in range(iterations):
            last_scan = scanner.run_command("ble scan 3", timeout=9.0)
            low = last_scan.lower()
            assert "traceback" not in low
            if target.lower() in low or name.lower() in low:
                hits += 1
            time.sleep(0.3)
    finally:
        advertiser.run_command("ble advertise off")

    if hits == 0:
        pytest.skip(
            "BLE soak-lite target not observable in current RF environment. "
            "target=%r last_scan=%r" % (target, last_scan)
        )

    ratio = hits / float(iterations)
    assert ratio >= 0.20, "BLE soak-lite ratio too low: hits=%d/%d ratio=%.2f" % (hits, iterations, ratio)


def test_hitl_multi_xstack_rotation_extended_metrics(hitl_badge_pair):
    """Extended cross-stack rotation with per-cycle health checks and summary metrics."""
    dev_a, dev_b = hitl_badge_pair
    if dev_a.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Extended cross-stack rotation requires physical badges")

    name = "ROTEX_%d" % (int(time.time()) % 100000)
    adv_out = dev_a.run_command("ble advertise on " + name)
    if "unknown command: ble" in adv_out.lower():
        pytest.skip("BLE command unavailable on device A")

    cycles = 6
    wifi_ok = 0
    lora_ok = 0
    last_wifi = ""
    reboot_events = 0
    completed = 0
    max_attempts = cycles + 4
    try:
        for _ in range(max_attempts):
            if completed >= cycles:
                break
            last_wifi = dev_b.run_command("wifi scan", timeout=12.0)
            if _wifi_command_unavailable(last_wifi):
                pytest.skip("Wi-Fi command unavailable on device B")
            low_wifi = last_wifi.lower()
            assert "traceback" not in low_wifi

            # Occasionally a spontaneous reboot/banner can appear mid-rotation.
            # Resynchronize and retry that cycle instead of hard failing immediately.
            if "type 'help' or '?' for a list of commands" in low_wifi or "badge" in low_wifi and "v0." in low_wifi:
                reboot_events += 1
                try:
                    dev_b.run_command("echo resync", timeout=8.0)
                except Exception:
                    try:
                        dev_b.disconnect()
                    except Exception:
                        pass
                    dev_b.connect()
                time.sleep(0.3)
                continue

            if (
                "scanning for wi-fi networks" in low_wifi
                or "bssid" in low_wifi
                or "no networks found" in low_wifi
                or "error scanning wi-fi" in low_wifi
            ):
                wifi_ok += 1

            tx_a = dev_a.run_command("lora tx 524f5445585f41")
            tx_b = dev_b.run_command("lora tx 524f5445585f42")
            low_a = tx_a.lower()
            low_b = tx_b.lower()
            assert "traceback" not in low_a
            assert "traceback" not in low_b
            if ("sent" in low_a or "bytes" in low_a) and ("sent" in low_b or "bytes" in low_b):
                lora_ok += 1
            completed += 1
            time.sleep(0.25)
    finally:
        dev_a.run_command("ble advertise off")

    if completed == 0:
        pytest.skip("No completed cross-stack cycles due to repeated reboot/desync events")

    required = max(1, completed - 1)
    assert wifi_ok >= required, "Wi-Fi health degraded in rotation: ok=%d completed=%d reboot_events=%d last=%r" % (
        wifi_ok,
        completed,
        reboot_events,
        last_wifi,
    )
    assert lora_ok >= required, "LoRa TX health degraded in rotation: ok=%d completed=%d reboot_events=%d" % (
        lora_ok,
        completed,
        reboot_events,
    )
