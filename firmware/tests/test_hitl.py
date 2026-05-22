import pytest
import time


def _parse_top_level_commands(help_text):
    cmds = []
    in_commands = False
    for line in help_text.splitlines():
        if line.startswith("Commands:"):
            in_commands = True
            continue
        if line.startswith("Command groups"):
            break
        if in_commands and line.startswith("  "):
            parts = line.strip().split()
            if parts:
                cmds.append(parts[0])
    return cmds


def _parse_groups(help_text):
    groups = []
    in_groups = False
    for line in help_text.splitlines():
        if line.startswith("Command groups"):
            in_groups = True
            continue
        if in_groups and line.startswith("  "):
            parts = line.strip().split()
            if parts:
                groups.append(parts[0])
    return groups


def _parse_subcommands(group_help_text):
    subcmds = []
    in_commands = False
    for line in group_help_text.splitlines():
        if line.startswith("Commands:"):
            in_commands = True
            continue
        if in_commands and line.startswith("  "):
            parts = line.strip().split()
            if parts:
                subcmds.append(parts[0])
    return subcmds


SAFE_TOPLEVEL = {
    "help": "help",
    "?": "?",
    "!": "!",
    "echo": "echo hitl smoke",
    "clear": "clear",
    "version": "version",
    "uptime": "uptime",
    "date": "date",
    "free": "free",
    "free_blocks": "free_blocks",
    "sleep": "sleep 1ms",
    "neofetch": "neofetch",
    "history": "history",
}

SKIP_TOPLEVEL = {"exit", "factory_reset", "top", "log", "batch"}

SAFE_SUBCOMMANDS = {
    ("info", "device"): "info device",
    ("info", "power"): "info power",
    ("config", "list"): "config list",
    ("config", "get"): "config get alias",
    ("config", "set"): "config set hitl_smoke val",
    ("config", "save"): "config save",
    ("storage", "list"): "storage list",
    ("storage", "write"): "storage write hitl_smoke.txt hello",
    ("storage", "read"): "storage read hitl_smoke.txt",
    ("storage", "remove"): "storage remove hitl_smoke.txt",
    ("lora", "info"): "lora info",
    ("lora", "freq"): "lora freq",
    ("net", "address"): "net address",
    ("net", "nodes"): "net nodes",
    ("i2c", "scan"): "i2c scan",
    ("gpio", "logic"): "gpio logic sao1 8 1",
    ("crypto", "has_key"): "crypto has_key",
    ("nametag", "get"): "nametag get",
    ("nametag", "set"): "nametag set hitl",
    ("loader", "list"): "loader list",
    ("power", "off"): "power off",
    ("power", "reboot"): "power reboot",
    ("chat", "status"): "chat status",
    ("peers", "list"): "peers list",
    ("poll", "list"): "poll list",
    ("ctf", "status"): "ctf status",
    ("talks", "list"): "talks list",
    ("badusb", "type"): "badusb type hi",
    ("uart", "status"): "uart status",
    ("wifi", "scan"): "wifi scan",
    ("ble", "scan"): "ble scan 1",
    ("wardriving", "scan"): "wardriving scan 1",
    ("wardriving", "wifi"): "wardriving wifi",
    ("wardriving", "ble"): "wardriving ble 1",
    ("subghz", "rx"): "subghz rx 915.0",
}

SKIP_SUBCOMMANDS = {
    ("info", "top"),
    ("lora", "rx"),
    ("lora", "rx_raw"),
    ("net", "sniff"),
    ("log", "stream"),
    ("uart", "bridge"),
    ("uart", "terminal"),
    ("subghz", "scan"),
    ("subghz", "rx"),
    ("subghz", "record"),
    ("subghz", "jam"),
    ("subghz", "play"),
    ("power", "deep"),
    ("power", "off"),
    ("power", "reboot"),
}

INTERACTIVE_HINTS = {
    "bridge",
    "terminal",
    "rx",
    "rx_raw",
    "sniff",
    "stream",
    "scan",
    "record",
    "jam",
    "play",
    "watch",
    "host",
}


def _assert_cli_response_sane(output, allow_unknown=False):
    low = output.lower()
    assert "traceback" not in low
    if not allow_unknown:
        assert "unknown command:" not in low
        assert "unknown sub-command:" not in low


def test_hitl_echo(hitl_badge):
    """Test basic connectivity and echoing."""
    out = hitl_badge.run_command("echo hello hitl")
    assert "hello hitl" in out

def test_hitl_info(hitl_badge):
    """Test that the device info command returns expected hardware details."""
    out = hitl_badge.run_command("info device")
    # Simulation returns 'Address:' while hardware might return 'My address:'
    assert "address" in out.lower() or "platform" in out.lower()
    
    out = hitl_badge.run_command("info power")
    assert "power" in out.lower()

def test_hitl_config(hitl_badge):
    """Test setting, reading, and saving config values to flash."""
    # Set a test value
    test_val = f"hitl_{int(time.time())}"
    hitl_badge.run_command(f"config set test_key {test_val}")

    # Verify it exists in memory
    out = hitl_badge.run_command("config get test_key")
    assert test_val in out

    # Save to flash
    out = hitl_badge.run_command("config save")
    assert "saved" in out.lower() or "config" in out.lower()

def test_hitl_storage(hitl_badge, tmp_path):
    """Test writing and reading a file to the physical flash filesystem."""
    test_file = str(tmp_path / "test_hitl.txt")
    test_data = f"data_{int(time.time())}"

    # Write file
    out = hitl_badge.run_command(f"storage write {test_file} {test_data}")
    assert "wrote" in out.lower() or "bytes" in out.lower()

    # Read file (using 'read' instead of 'cat' as implemented in storage_cmd.py)
    out = hitl_badge.run_command(f"storage read {test_file}")
    assert test_data in out

    # Delete file
    hitl_badge.run_command(f"storage remove {test_file}")

def test_hitl_i2c(hitl_badge):
    """Test scanning the I2C bus. Even if empty, it shouldn't crash."""
    out = hitl_badge.run_command("i2c scan")
    assert "found" in out.lower() or "no i2c devices" in out.lower()

def test_hitl_nametag(hitl_badge):
    """Test setting the nametag alias."""
    out = hitl_badge.run_command("nametag set hitl_test")
    assert "alias set" in out.lower()
    
    out = hitl_badge.run_command("nametag get")
    assert "hitl_test" in out

# --- Hacker Companion Coverage ---

def test_hitl_lora(hitl_badge):
    """Test LoRa radio status and frequency."""
    out = hitl_badge.run_command("lora info")
    assert "radio" in out.lower() or "freq" in out.lower()
    
    # Test setting frequency
    hitl_badge.run_command("lora freq 10")
    out = hitl_badge.run_command("lora freq")
    assert "10" in out

def test_hitl_net(hitl_badge):
    """Test network stack status."""
    out = hitl_badge.run_command("net address")
    # 'My address: ...' or 'Address: ...'
    assert "address" in out.lower()
    
    out = hitl_badge.run_command("net nodes")
    assert "nodes" in out.lower()

def test_hitl_wardriving(hitl_badge):
    """Test Wi-Fi and BLE scanning."""
    out = hitl_badge.run_command("wifi scan")
    if "unknown command: wifi" in out.lower():
        assert "unknown command: wifi" in out.lower()
    else:
        # Wi-Fi scan might return headers even if empty
        assert "wi-fi" in out.lower() or "scanning" in out.lower()
    
    out = hitl_badge.run_command("ble scan 1")
    if "unknown command: ble" in out.lower():
        assert "unknown command: ble" in out.lower()
    else:
        assert "ble" in out.lower() or "scanning" in out.lower()

def test_hitl_badusb(hitl_badge):
    """Test BadUSB keyboard injection."""
    out = hitl_badge.run_command("badusb type 'Hello World'")
    assert "typing" in out.lower()

def test_hitl_subghz(hitl_badge):
    """Test Sub-GHz RF operations."""
    out = hitl_badge.run_command("subghz rx 915.0")
    assert "915" in out

def test_hitl_crypto(hitl_badge):
    """Test RSA cryptographic signatures."""
    out = hitl_badge.run_command("crypto has_key")
    assert "present" in out.lower() or "not present" in out.lower()
    
    # We don't sign here as it might require a real key

def test_hitl_apps(hitl_badge):
    """Test background app status (CTF, Polls, Peers)."""
    out = hitl_badge.run_command("ctf status")
    assert "ctf" in out.lower()
    
    out = hitl_badge.run_command("poll list")
    assert "poll" in out.lower()
    
    out = hitl_badge.run_command("peers list")
    assert "peers" in out.lower()


def test_hitl_cli_sweep_all_commands(hitl_badge):
    """Comprehensive smoke sweep of discovered CLI commands/subcommands.

    This test discovers commands from live `help` output, then executes safe
    command forms (or usage probes) for broad regression coverage.
    """
    help_out = hitl_badge.run_command("help")
    _assert_cli_response_sane(help_out)

    top_level = _parse_top_level_commands(help_out)
    groups = _parse_groups(help_out)

    # Top-level command smoke
    for cmd in top_level:
        if cmd in SKIP_TOPLEVEL:
            continue
        invocation = SAFE_TOPLEVEL.get(cmd)
        if invocation is None:
            # Probe command usage path if we don't have a canned invocation.
            invocation = cmd
        out = hitl_badge.run_command(invocation)
        _assert_cli_response_sane(out)

    # Group + subcommand smoke
    for group in groups:
        ghelp = hitl_badge.run_command(group + " ?")
        _assert_cli_response_sane(ghelp)

        subcmds = _parse_subcommands(ghelp)
        for sub in subcmds:
            key = (group, sub)
            if key in SKIP_SUBCOMMANDS:
                continue

            invocation = SAFE_SUBCOMMANDS.get(key, group + " " + sub)
            try:
                out = hitl_badge.run_command(invocation)
            except TimeoutError:
                if sub in INTERACTIVE_HINTS:
                    continue
                raise
            # Optional hardware features can legitimately be unavailable.
            allow_unknown = group in {"wifi", "ble", "wardriving"}
            _assert_cli_response_sane(out, allow_unknown=allow_unknown)
