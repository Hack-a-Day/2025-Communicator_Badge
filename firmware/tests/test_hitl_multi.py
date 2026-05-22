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
