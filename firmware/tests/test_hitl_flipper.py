import pytest


pytestmark = [pytest.mark.hitl, pytest.mark.multi, pytest.mark.flipper]


def test_hitl_flipper_cli_smoke(hitl_flipper_cli, hitl_flipper_settings):
    """Verify Flipper CLI responds to a basic command over serial."""
    cmd = hitl_flipper_settings["smoke_cmd"] or "help"
    out = hitl_flipper_cli.run_command(cmd, timeout=5.0)

    assert "traceback" not in out.lower()
    assert len(out.strip()) > 0

    identifier = (hitl_flipper_settings.get("identifier") or "").strip()
    if identifier:
        assert identifier.lower() in out.lower(), (
            "Flipper smoke output missing identifier %r. Output: %r" % (identifier, out)
        )


def test_hitl_flipper_cli_repeatability(hitl_flipper_cli, hitl_flipper_settings):
    """Run repeated commands to ensure prompt synchronization remains stable."""
    cmd = hitl_flipper_settings["smoke_cmd"] or "help"
    outputs = []
    for _ in range(3):
        out = hitl_flipper_cli.run_command(cmd, timeout=5.0)
        outputs.append(out)

    assert all(o is not None and o.strip() for o in outputs)
    assert all("traceback" not in o.lower() for o in outputs)


def test_hitl_flipper_capability_probe(hitl_flipper_cli, hitl_flipper_settings):
    """Probe key Flipper capabilities used by this test rig."""
    info_cmd = (hitl_flipper_settings.get("info_cmd") or "info device").strip()
    bt_cmd = (hitl_flipper_settings.get("bt_cmd") or "bt hci_info").strip()

    info_out = hitl_flipper_cli.run_command(info_cmd, timeout=5.0)
    assert "traceback" not in info_out.lower()
    assert len(info_out.strip()) > 0

    bt_out = hitl_flipper_cli.run_command(bt_cmd, timeout=5.0)
    low = bt_out.lower()
    # Firmware variants may omit certain command families; classify as non-fatal.
    assert "traceback" not in low
    assert len(bt_out.strip()) > 0


@pytest.mark.stress
def test_hitl_flipper_interruptible_streaming_commands(hitl_flipper_cli, hitl_flipper_settings):
    """Optionally run long-running Flipper commands and stop them via Ctrl+C."""
    candidates = []
    for key in ("log_cmd", "subghz_cmd"):
        cmd = (hitl_flipper_settings.get(key) or "").strip()
        if cmd:
            candidates.append(cmd)

    if not candidates:
        pytest.skip("Set --hitl-flipper-log-cmd and/or --hitl-flipper-subghz-cmd to enable streaming test")

    for cmd in candidates:
        out = hitl_flipper_cli.run_command_interrupt(cmd, run_seconds=1.0, timeout=6.0)
        low = out.lower()
        assert "traceback" not in low
        # It is acceptable for command output to be sparse; this only validates command lifecycle.
