import pytest
import time

def test_hitl_echo(hitl_badge):
    """Test basic connectivity and echoing."""
    out = hitl_badge.run_command("echo hello hitl")
    assert "hello hitl" in out

def test_hitl_info(hitl_badge):
    """Test that the device info command returns expected hardware details."""
    out = hitl_badge.run_command("info device")
    assert "Address:" in out or "Platform:" in out
    
    out = hitl_badge.run_command("info power")
    assert "Power source:" in out

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
    assert "Saved" in out or "config" in out.lower()

def test_hitl_storage(hitl_badge):
    """Test writing and reading a file to the physical flash filesystem."""
    # Debug: Check help
    h = hitl_badge.run_command("help")
    if "storage" not in h:
         pytest.fail(f"STORAGE MISSING! Available commands: {h!r}")
         
    test_file = "test_hitl.txt"
    test_data = f"data_{int(time.time())}"

    # Write file
    out = hitl_badge.run_command(f"storage write {test_file} {test_data}")
    assert "Written" in out or "bytes" in out

    # Read file
    out = hitl_badge.run_command(f"storage cat {test_file}")
    assert test_data in out

    # Delete file
    hitl_badge.run_command(f"storage rm {test_file}")

def test_hitl_i2c(hitl_badge):
    """Test scanning the I2C bus. Even if empty, it shouldn't crash."""
    out = hitl_badge.run_command("i2c scan")
    assert "Found" in out or "No I2C devices found" in out

def test_hitl_nametag(hitl_badge):
    """Test setting the nametag alias."""
    out = hitl_badge.run_command("nametag set hitl_test")
    assert "Alias set to: hitl_test" in out
    
    out = hitl_badge.run_command("nametag get")
    assert "hitl_test" in out

# --- Hacker Companion Coverage ---

def test_hitl_lora(hitl_badge):
    """Test LoRa radio status and frequency."""
    out = hitl_badge.run_command("lora info")
    assert "Radio:" in out or "Freq Slot:" in out
    
    # Test setting frequency
    hitl_badge.run_command("lora freq 10")
    out = hitl_badge.run_command("lora freq")
    assert "10" in out

def test_hitl_net(hitl_badge):
    """Test network stack status."""
    out = hitl_badge.run_command("net address")
    assert "Address" in out or len(out) == 8
    
    out = hitl_badge.run_command("net nodes")
    assert "nodes" in out.lower()

def test_hitl_wardriving(hitl_badge):
    """Test Wi-Fi and BLE scanning."""
    out = hitl_badge.run_command("wifi scan")
    assert "Found" in out or "No" in out
    
    out = hitl_badge.run_command("ble scan 1")
    assert "BLE" in out or "scanning" in out.lower()

def test_hitl_badusb(hitl_badge):
    """Test BadUSB keyboard injection."""
    out = hitl_badge.run_command("badusb type 'Hello World'")
    assert "Typing" in out

def test_hitl_subghz(hitl_badge):
    """Test Sub-GHz RF operations."""
    # We test with a short capture/timeout
    out = hitl_badge.run_command("subghz rx 915.000")
    assert "915.000" in out

def test_hitl_crypto(hitl_badge):
    """Test RSA cryptographic signatures."""
    out = hitl_badge.run_command("crypto has_key")
    assert "True" in out or "False" in out
    
    if "True" in out:
        out = hitl_badge.run_command("crypto sign 'test message'")
        assert len(out) > 32 # Signature should be hex string

def test_hitl_apps(hitl_badge):
    """Test background app status (CTF, Polls, Peers)."""
    out = hitl_badge.run_command("ctf status")
    assert "CTF" in out
    
    out = hitl_badge.run_command("poll list")
    assert "Polls" in out
    
    out = hitl_badge.run_command("peers list")
    assert "Peers" in out
