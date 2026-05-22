"""Tests for info, config, lora, net, hardware, crypto, storage, nametag, loader, power commands."""

from badge_cli.shell import Shell
from tests.mocks.mock_badge import MockBadge


class TestInfoDevice:
    def test_info_device_shows_radio(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("info device")
        assert "SX1262" in output.text
        assert "MHz" in output.text

    def test_info_device_shows_memory(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("info device")
        # Either shows heap info or "not available"
        text = output.text
        assert "Heap" in text or "heap" in text

    def test_info_power_shows_stub(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("info power")
        assert "No fuel gauge" in output.text


class TestConfigCommands:
    def test_config_list(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("config list")
        # MockConfig has default keys
        assert "alias" in output.text or "nametag" in output.text

    def test_config_get_existing(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("config get nametag")
        assert "Test Badge" in output.text

    def test_config_get_missing(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("config get nonexistent_key_xyz")
        assert "not found" in output.text.lower()

    def test_config_set_and_get(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("config set testkey testval")
        assert "testval" in output.text
        output.clear()
        shell.run_command("config get testkey")
        assert "testval" in output.text

    def test_config_save(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("config save")
        assert "saved" in output.text.lower()

    def test_config_broadcast_no_key(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("config broadcast testkey testval")
        assert "No private key" in output.text

    def test_config_broadcast_with_key(self, output):
        badge = MockBadge(has_private_key=True)
        shell = Shell(badge, write_func=output)
        shell.run_command("config broadcast testkey testval")
        # Should succeed signing but fail on network import
        text = output.text
        assert "Signed OK" in text or "Broadcast" in text or "network" in text.lower()

    def test_config_help(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("config ?")
        assert "list" in output.text
        assert "get" in output.text
        assert "set" in output.text


class TestLoraCommands:
    def test_lora_info(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("lora info")
        text = output.text
        assert "SX1262" in text
        assert "MHz" in text
        assert "Spreading Factor" in text

    def test_lora_freq_get(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("lora freq")
        assert "slot" in output.text.lower()
        assert "MHz" in output.text

    def test_lora_freq_set(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("lora freq 20")
        assert "slot 20" in output.text
        assert "MHz" in output.text

    def test_lora_freq_invalid(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("lora freq 99")
        assert "Error" in output.text

    def test_lora_tx_no_args(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("lora tx")
        assert "Usage" in output.text

    def test_lora_tx_sends(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("lora tx 48454c4c4f")
        assert "Sent" in output.text or "bytes" in output.text

    def test_lora_tx_invalid_hex(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("lora tx ZZZZ")
        assert "Error" in output.text or "Invalid" in output.text

    def test_lora_rx_no_badgenet(self, shell_and_output):
        shell, output = shell_and_output
        import threading, time
        def interrupter():
            time.sleep(0.1)
            shell.interrupt()
        t = threading.Thread(target=interrupter)
        t.start()
        shell.run_command("lora rx")
        t.join()
        assert "Listening" in output.text

    def test_lora_rx_raw_with_mock_data(self, shell_and_output):
        shell, output = shell_and_output
        import threading, time
        # Inject some data into mock lora rx queue
        shell.badge.lora.inject_rx(b"\x48\x45\x4c\x4c\x4f")
        def interrupter():
            time.sleep(0.1)
            shell.interrupt()
        t = threading.Thread(target=interrupter)
        t.start()
        shell.run_command("lora rx_raw")
        t.join()
        text = output.text
        assert "Listening" in text or "4845" in text.lower()

    def test_lora_help(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("lora ?")
        assert "info" in output.text
        assert "freq" in output.text
        assert "tx" in output.text
        assert "rx" in output.text


class TestNetCommands:
    def test_net_address(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("net address")
        # Without real net module, shows unavailable
        assert "address" in output.text.lower()

    def test_net_help(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("net ?")
        assert "address" in output.text
        assert "ping" in output.text
        assert "nodes" in output.text
        assert "sniff" in output.text


class TestHardwareCommands:
    def test_i2c_scan_empty(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("i2c scan")
        assert "No I2C devices" in output.text

    def test_i2c_scan_with_devices(self, shell_and_output):
        shell, output = shell_and_output
        shell.badge.sao_i2c.add_device(0x3C)
        shell.badge.sao_i2c.add_device(0x50)
        shell.run_command("i2c scan")
        assert "0x3c" in output.text
        assert "0x50" in output.text

    def test_i2c_dump(self, shell_and_output):
        shell, output = shell_and_output
        shell.badge.sao_i2c.add_device(0x50)
        shell.run_command("i2c dump 0x50 32")
        assert "Dump of 0x50" in output.text
        assert "0000  00 01 02 03 04 05 06 07" in output.text

    def test_gpio_logic(self, shell_and_output):
        import sys
        shell, output = shell_and_output
        
        # Mock machine.Pin to return an alternating sequence 1, 0, 1, 0...
        mock_machine = sys.modules["machine"]
        mock_pin = mock_machine.Pin.return_value
        mock_pin.value.side_effect = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
        
        shell.run_command("gpio logic sao1 10 1")
        assert "Capturing" in output.text
        assert "Waveform" in output.text
        assert "‾_‾_‾_‾_‾_" in output.text
        assert "Sequence: 1010101010" in output.text

    def test_vibro_unsupported(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("vibro")
        assert "No vibration" in output.text

    def test_buzzer_unsupported(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("buzzer")
        assert "No buzzer" in output.text


class TestCryptoCommands:
    def test_crypto_has_key_false(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("crypto has_key")
        assert "not present" in output.text

    def test_crypto_has_key_true(self, output):
        badge = MockBadge(has_private_key=True)
        shell = Shell(badge, write_func=output)
        shell.run_command("crypto has_key")
        assert "present" in output.text
        assert "not present" not in output.text.split("Public")[0]

    def test_crypto_sign_no_key(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("crypto sign hello")
        assert "Error" in output.text or "No private key" in output.text

    def test_crypto_sign_with_key(self, output):
        badge = MockBadge(has_private_key=True)
        shell = Shell(badge, write_func=output)
        shell.run_command("crypto sign hello")
        assert "Signature" in output.text

    def test_crypto_verify(self, output):
        badge = MockBadge(has_private_key=True)
        shell = Shell(badge, write_func=output)
        # Sign first to get a valid mock signature
        shell.run_command("crypto sign test_message")
        # Extract the hex signature from output
        for line in output.line_list:
            if "Signature:" in line:
                sig_hex = line.split("Signature:")[-1].strip()
                break
        output.clear()
        shell.run_command("crypto verify test_message " + sig_hex)
        assert "True" in output.text


class TestStorageCommands:
    def test_storage_list_root(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("storage list .")
        # Should list files in current directory (test runner CWD)
        assert len(output.line_list) > 0

    def test_storage_help(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("storage ?")
        assert "list" in output.text
        assert "read" in output.text
        assert "write" in output.text

    def test_storage_stat_missing(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("storage stat /nonexistent_file_xyz_test")
        assert "Error" in output.text

    def test_storage_push_pull(self, shell_and_output, tmp_path):
        import binascii
        shell, output = shell_and_output
        test_file = tmp_path / "test_base64.txt"
        test_data = b"Hello from the base64 push and pull test! This should work perfectly."
        
        # Test push
        b64_str = binascii.b2a_base64(test_data).decode('ascii').strip()
        shell.run_command(f"storage push {test_file} {b64_str}")
        assert "Wrote" in output.text
        assert test_file.exists()
        assert test_file.read_bytes() == test_data
        
        output.clear()
        
        # Test pull
        shell.run_command(f"storage pull {test_file}")
        # Reconstruct from output
        pulled_b64 = output.text.strip()
        # The output might have newlines or other logging, but we'll try parsing the last line
        # Actually it's just the base64 output
        decoded = binascii.a2b_base64(pulled_b64)
        assert decoded == test_data


class TestNametagCommands:
    def test_nametag_get(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("nametag get")
        assert "Nametag:" in output.text or "Alias:" in output.text

    def test_nametag_set(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("nametag set TestUser")
        assert "TestUser" in output.text
        output.clear()
        shell.run_command("config get alias")
        assert "TestUser" in output.text


class TestLoaderCommands:
    def test_loader_list_no_apps(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("loader list")
        text = output.text
        assert "No apps" in text or "Registered apps:" in text
        if "Registered apps:" in text:
            assert "CLI" in text

    def test_loader_help(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("loader ?")
        assert "list" in output.text
        assert "open" in output.text
        assert "info" in output.text


class TestPowerCommands:
    def test_power_off_no_machine(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("power off")
        # On CPython, machine module isn't available
        assert "not available" in output.text or "deep sleep" in output.text.lower()

    def test_power_reboot_no_machine(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("power reboot")
        assert "not available" in output.text or "Rebooting" in output.text

    def test_power_help(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("power ?")
        assert "off" in output.text
        assert "reboot" in output.text


class TestSubGhzCommands:
    def test_subghz_rx_no_data(self, shell_and_output):
        shell, output = shell_and_output
        # Without data, it should timeout and say no data received
        shell.run_command("subghz rx 433.92")
        assert "Listening" in output.text
        assert "No data received" in output.text

    def test_subghz_rx_with_data(self, shell_and_output):
        from collections import deque
        shell, output = shell_and_output
        shell.badge.lora._ook_rx_queue = deque([b"\xAA\xBB\xCC\xDD"])
        shell.run_command("subghz rx 433.92")
        assert "aabbccdd" in output.text

    def test_subghz_tx(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("subghz tx 433.92 AABBCCDD")
        assert "Transmitting" in output.text
        assert "complete" in output.text
        assert getattr(shell.badge.lora, "_ook_tx_log", None)
        assert shell.badge.lora._ook_tx_log[0] == (433.92, b"\xaa\xbb\xcc\xdd")


class TestWardrivingCommands:
    def test_wifi_scan(self, shell_and_output, monkeypatch):
        import sys
        shell, output = shell_and_output
        
        # Setup mock network module
        mock_network = sys.modules["network"]
        mock_sta = mock_network.WLAN.return_value
        mock_sta.active.return_value = True
        mock_sta.scan.return_value = [
            (b"TestNet_2G", b"\x11\x22\x33\x44\x55\x66", 6, -55, 3, 0),
            (b"OpenWifi", b"\xaa\xbb\xcc\xdd\xee\xff", 11, -80, 0, 0),
        ]
        
        shell.run_command("wifi scan")
        text = output.text
        assert "TestNet_2G" in text
        assert "OpenWifi" in text
        assert "WPA2" in text
        assert "OPEN" in text
        assert "11:22:33:44:55:66" in text

    def test_ble_scan(self, shell_and_output, monkeypatch):
        import sys
        shell, output = shell_and_output
        
        # Setup mock bluetooth module
        mock_bt = sys.modules["bluetooth"]
        mock_ble = mock_bt.BLE.return_value
        del mock_ble.irq
        # Add a mock_scan method since the real irq based one won't run its callback in tests natively without a fake event loop
        name = b"HITL_TEST"
        mock_ble.mock_scan.return_value = [
            (
                "12:34:56:78:90:ab",
                -60,
                b"\x02\x01\x06" + bytes([len(name) + 1, 0x09]) + name,
            ),
        ]
        
        shell.run_command("ble scan 1")
        text = output.text
        assert "Scanning" in text
        assert "12:34:56:78:90:ab" in text
        assert "HITL_TEST" in text

    def test_ble_advertise(self, shell_and_output, monkeypatch):
        import sys
        shell, output = shell_and_output

        mock_bt = sys.modules["bluetooth"]
        mock_ble = mock_bt.BLE.return_value

        shell.run_command("ble advertise on HITL_TAG")
        text = output.text
        assert "advertising on" in text.lower()
        mock_ble.gap_advertise.assert_called()

        output.clear()
        shell.run_command("ble advertise off")
        text = output.text
        assert "advertising off" in text.lower()

    def test_wardriving_scan(self, shell_and_output, monkeypatch):
        import sys
        shell, output = shell_and_output

        mock_network = sys.modules["network"]
        mock_sta = mock_network.WLAN.return_value
        mock_sta.active.return_value = True
        mock_sta.scan.return_value = [
            (b"SweepNet", b"\x11\x22\x33\x44\x55\x66", 1, -42, 3, 0),
        ]

        mock_bt = sys.modules["bluetooth"]
        mock_ble = mock_bt.BLE.return_value
        if hasattr(mock_ble, "irq"):
            del mock_ble.irq
        mock_ble.mock_scan.return_value = [
            ("aa:bb:cc:dd:ee:ff", -70, b"\x02\x01\x06"),
        ]

        shell.run_command("wardriving scan 1")
        text = output.text
        assert "Wardriving sweep" in text
        assert "SweepNet" in text
        assert "aa:bb:cc:dd:ee:ff" in text


class TestMetaCommands:
    def test_clear_command_registered_and_emits_ansi(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("clear")
        assert "\x1b[2J\x1b[H" in output.text

class TestBadUsbCommands:
    def test_badusb_type(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("badusb type hello world")
        assert "Typing: hello world" in output.text
        assert "Done" in output.text
        assert shell.badge.mock_hid_log[-1] == "TYPE: hello world"

    def test_badusb_run_script(self, shell_and_output, tmp_path):
        shell, output = shell_and_output
        script = tmp_path / "payload.txt"
        script.write_text("STRING hello\nDELAY 100\nENTER\nGUI r\n")
        
        shell.run_command(f"badusb run {script}")
        assert "Running" in output.text
        assert "Payload complete" in output.text
        
        logs = shell.badge.mock_hid_log
        assert "TYPE: hello" in logs
        assert "KEY: 40 MOD: 0" in logs  # ENTER is 0x28 (40 in decimal)
        assert "KEY: 21 MOD: 8" in logs  # GUI+r: r is 0x15 (21 in decimal)

class TestHelpShowsAllGroups:
    """Verify that help now shows all registered command groups."""

    def test_help_shows_all_groups(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("help")
        text = output.text
        expected_groups = [
            "info", "config", "lora", "net", "i2c", "gpio",
            "led", "crypto", "storage", "nametag", "loader",
            "power", "talks", "ctf", "poll", "peers", "chat",
            "wifi", "ble", "wardriving",
        ]
        for group in expected_groups:
            assert group in text, "Missing group in help: " + group
