"""Tests for info, config, lora, net, hardware, crypto, storage, nametag, loader, power commands."""

import pytest
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
        shell.run_command("lora rx")
        # Without BadgeNet, should show mock output
        assert "BadgeNet not available" in output.text or "Listening" in output.text

    def test_lora_rx_raw_with_mock_data(self, shell_and_output):
        shell, output = shell_and_output
        # Inject some data into mock lora rx queue
        shell.badge.lora.inject_rx(b"\x48\x45\x4c\x4c\x4f")
        shell.run_command("lora rx_raw")
        text = output.text
        assert "4845" in text.lower() or "BadgeNet" in text

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
        assert "No apps" in output.text

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
        ]
        for group in expected_groups:
            assert group in text, "Missing group in help: " + group
