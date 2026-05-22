import time
import pytest


pytestmark = [pytest.mark.hitl, pytest.mark.multi, pytest.mark.flipper, pytest.mark.ble]


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
