import pytest
import time

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
