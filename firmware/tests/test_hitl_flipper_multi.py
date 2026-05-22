import time
import threading
import pytest


pytestmark = [pytest.mark.hitl, pytest.mark.multi, pytest.mark.flipper, pytest.mark.ble]


def _wifi_output_ok(text):
    low = text.lower()
    return (
        "scanning for wi-fi networks" in low
        or "bssid" in low
        or "no networks found" in low
        or "error scanning wi-fi" in low
    )


def _count_tokens(text, tokens):
    low = text.lower()
    return sum(1 for t in tokens if t.lower() in low)


def test_hitl_multi_ble_scan_with_flipper_activity(
    hitl_badge_pair,
    hitl_flipper_cli,
    hitl_flipper_settings,
):
    """Run badge BLE scan while Flipper emits optional BLE activity via CLI."""
    scanner, advertiser = hitl_badge_pair
    if scanner.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Requires physical badges")

    activity_cmd = (hitl_flipper_settings.get("ble_activity_cmd") or "").strip()
    if not activity_cmd:
        pytest.skip("Set --hitl-flipper-ble-activity-cmd to enable Flipper BLE activity test")

    stop_cmd = (hitl_flipper_settings.get("ble_stop_cmd") or "").strip()
    name = "HITL_FZ_%d" % (int(time.time()) % 100000)

    out = advertiser.run_command("ble advertise on " + name)
    assert "advertising" in out.lower() or "on" in out.lower()

    flipper_out = ""
    try:
        flipper_out = hitl_flipper_cli.run_command(activity_cmd, timeout=6.0)
        assert "traceback" not in flipper_out.lower()

        time.sleep(0.8)
        scan = scanner.run_command("ble scan 5", timeout=10.0)
        low = scan.lower()
        assert "traceback" not in low
        assert "scanning" in low or "mac address" in low
    finally:
        advertiser.run_command("ble advertise off")
        if stop_cmd:
            hitl_flipper_cli.run_command(stop_cmd, timeout=4.0)


@pytest.mark.wifi
def test_hitl_multi_wifi_scan_with_flipper_activity(
    hitl_badge_pair,
    hitl_flipper_cli,
    hitl_flipper_settings,
):
    """Run badge Wi-Fi scans while Flipper executes optional activity command."""
    dev_a, dev_b = hitl_badge_pair
    if dev_a.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Requires physical badges")

    activity_cmd = (hitl_flipper_settings.get("wifi_activity_cmd") or "").strip()
    if not activity_cmd:
        pytest.skip("Set --hitl-flipper-wifi-activity-cmd to enable Flipper Wi-Fi perturbation test")

    stop_cmd = (hitl_flipper_settings.get("wifi_stop_cmd") or "").strip()
    out = hitl_flipper_cli.run_command(activity_cmd, timeout=6.0)
    if "unknown command" in out.lower() or "usage" in out.lower() and "traceback" not in out.lower():
        pytest.skip("Configured Flipper Wi-Fi activity command not supported by this firmware")
    assert "traceback" not in out.lower()

    try:
        for _ in range(3):
            out_a = dev_a.run_command("wifi scan", timeout=12.0)
            out_b = dev_b.run_command("wifi scan", timeout=12.0)
            low_a = out_a.lower()
            low_b = out_b.lower()
            if "unknown command: wifi" in low_a or "unknown command: wifi" in low_b:
                pytest.skip("Wi-Fi command unavailable on one or both badges")
            assert "traceback" not in low_a
            assert "traceback" not in low_b
            assert _wifi_output_ok(out_a), "Unexpected Wi-Fi output A: %r" % out_a
            assert _wifi_output_ok(out_b), "Unexpected Wi-Fi output B: %r" % out_b
            time.sleep(0.25)
    finally:
        if stop_cmd:
            hitl_flipper_cli.run_command(stop_cmd, timeout=4.0)


@pytest.mark.lora
def test_hitl_multi_lora_chat_with_flipper_radio_activity(
    hitl_badge_pair,
    hitl_flipper_cli,
    hitl_flipper_settings,
):
    """Characterize chat-over-LoRa delivery while Flipper runs optional RF activity."""
    sender, receiver = hitl_badge_pair
    if sender.__class__.__name__ == "BadgeMockClient":
        pytest.skip("Requires physical badges")

    activity_cmd = (hitl_flipper_settings.get("radio_activity_cmd") or "").strip()
    if not activity_cmd:
        pytest.skip("Set --hitl-flipper-radio-activity-cmd to enable Flipper radio characterization test")

    stop_cmd = (hitl_flipper_settings.get("radio_stop_cmd") or "").strip()
    sender.run_command("chat channel 12 34")
    receiver.run_command("chat channel 12 34")

    flipper_activity_out = {"out": ""}

    def _activity_worker():
        # Use interruptible mode so long-running Flipper commands do not hang tests.
        flipper_activity_out["out"] = hitl_flipper_cli.run_command_interrupt(
            activity_cmd,
            run_seconds=1.8,
            timeout=8.0,
        )

    t = threading.Thread(target=_activity_worker, daemon=True)
    t.start()
    time.sleep(0.2)

    batch = int(time.time()) % 100000
    tokens = ["HITL_FZ_SEQ_%d_%02d" % (batch, i) for i in range(1, 7)]
    for token in tokens:
        out = sender.run_command("chat send " + token)
        assert "traceback" not in out.lower()
        time.sleep(0.12)

    t.join(timeout=10.0)
    activity_low = (flipper_activity_out.get("out", "") or "").lower()
    if "unknown command" in activity_low:
        pytest.skip("Configured Flipper radio activity command not supported by this firmware")
    assert "traceback" not in activity_low

    delivered = 0
    last_history = ""
    deadline = time.time() + 10.0
    while time.time() < deadline:
        last_history = receiver.run_command("chat history")
        low = last_history.lower()
        assert "traceback" not in low
        delivered = _count_tokens(last_history, tokens)
        if delivered >= len(tokens):
            break
        time.sleep(0.3)

    if stop_cmd:
        hitl_flipper_cli.run_command(stop_cmd, timeout=4.0)

    ratio = delivered / float(len(tokens))
    assert ratio >= 0.40, (
        "LoRa chat delivery ratio too low under Flipper activity: delivered=%d total=%d ratio=%.2f history=%r"
        % (delivered, len(tokens), ratio, last_history)
    )
