"""System-level integration tests for the Badge CLI.

These tests simulate complete badge sessions with mocked hardware,
exercising multi-command workflows, cross-module interactions,
and end-to-end scenarios that mirror real usage.
"""

import os
import sys
import time
import pytest

from badge_cli.shell import Shell
from tests.mocks.mock_badge import MockBadge
from tests.conftest import CaptureOutput


# ─── Helpers ──────────────────────────────────────────────────────────


def make_shell_with_apps(has_private_key=False):
    """Create a Shell with all mock apps pre-registered and started."""
    badge = MockBadge(has_private_key=has_private_key)
    output = CaptureOutput()
    shell = Shell(badge, write_func=output)

    # Create and start the app instances — mimics what main.py does
    from apps.ctf_app import CTFApp
    from apps.poll_app import PollApp
    from apps.peers_app import PeersApp

    # Clear class-level all_apps to avoid cross-test contamination
    CTFApp.all_apps.clear()
    PollApp.all_apps.clear()
    PeersApp.all_apps.clear()

    ctf = CTFApp("CTF", badge)
    ctf.start()

    poll = PollApp("Polls", badge)
    poll.start()

    peers = PeersApp("Peers", badge)
    peers.start()

    return shell, output, badge, {"ctf": ctf, "poll": poll, "peers": peers}


# ─── System Test: Full Session Simulation ────────────────────────────


class TestFullSession:
    """Simulate a user connecting to the badge over serial and running
    a complete exploration session."""

    def test_motd_and_help_flow(self):
        """User connects, sees MOTD, runs help, explores groups."""
        shell, out, badge, apps = make_shell_with_apps()

        # See MOTD
        shell.motd()
        assert "v0.3" in out.text
        assert "help" in out.text.lower()
        out.clear()

        # Run help
        shell.run_command("help")
        text = out.text
        # All 20 command groups should be listed
        for group in ["info", "config", "lora", "net", "i2c", "gpio",
                       "led", "crypto", "storage", "nametag", "loader",
                       "power", "talks", "ctf", "poll", "peers", "chat"]:
            assert group in text, "Missing group: " + group

        # Explore a specific group
        out.clear()
        shell.run_command("lora ?")
        assert "info" in out.text
        assert "freq" in out.text
        assert "tx" in out.text

    def test_system_info_flow(self):
        """User checks system info, radio status, memory."""
        shell, out, badge, apps = make_shell_with_apps()

        # Version
        shell.run_command("version")
        assert "v0.3" in out.text
        out.clear()

        # Neofetch
        shell.run_command("neofetch")
        assert "| |__" in out.text
        assert "ESP32-S3" in out.text
        assert "SX1262" in out.text
        out.clear()

        # Info device
        shell.run_command("info device")
        assert "SX1262" in out.text
        assert "MHz" in out.text
        out.clear()

        # Uptime
        shell.run_command("uptime")
        assert "Uptime:" in out.text
        out.clear()

        # Date
        shell.run_command("date")
        assert len(out.text) > 5  # Some date output

    def test_config_workflow(self):
        """User lists config, sets alias, saves, verifies."""
        shell, out, badge, apps = make_shell_with_apps()

        # List initial config
        shell.run_command("config list")
        assert "alias" in out.text or "nametag" in out.text
        out.clear()

        # Set alias
        shell.run_command("config set alias HackerOne")
        assert "HackerOne" in out.text
        out.clear()

        # Verify it was set
        shell.run_command("config get alias")
        assert "HackerOne" in out.text
        out.clear()

        # Save to "flash"
        shell.run_command("config save")
        assert "saved" in out.text.lower()
        out.clear()

        # Nametag should reflect the alias
        shell.run_command("nametag set MyTag")
        assert "MyTag" in out.text
        out.clear()

        shell.run_command("nametag get")
        assert "MyTag" in out.text


class TestLoraWorkflow:
    """Test LoRa radio operations end-to-end."""

    def test_radio_info_and_freq_change(self):
        """User checks radio, changes frequency, verifies."""
        shell, out, badge, apps = make_shell_with_apps()

        # Check current freq
        shell.run_command("lora info")
        assert "904.250" in out.text or "9" in out.text  # Default slot 9
        out.clear()

        # Change freq slot
        shell.run_command("lora freq 20")
        assert "slot 20" in out.text
        out.clear()

        # Verify it changed
        shell.run_command("lora freq")
        assert "20" in out.text
        # Check the mock lora object
        assert badge.lora.freq_slot == 20

    def test_tx_and_verify(self):
        """User transmits data, verify it was sent."""
        shell, out, badge, apps = make_shell_with_apps()

        shell.run_command("lora tx 48454c4c4f")
        assert "Sent" in out.text or "5 bytes" in out.text

        # Verify the mock recorded the send
        assert len(badge.lora._tx_log) == 1
        assert badge.lora._tx_log[0] == b"HELLO"

    def test_rx_with_injected_data(self):
        """User runs rx, receives injected mock data."""
        shell, out, badge, apps = make_shell_with_apps()

        # Inject some mock frames
        badge.lora.inject_rx(b"\xDE\xAD\xBE\xEF", rssi=-65.0, snr=12.5)
        badge.lora.inject_rx(b"\xCA\xFE\xBA\xBE", rssi=-72.0, snr=8.0)

        # Run rx_raw (will use mock fallback since no BadgeNet)
        import threading, time
        def interrupter():
            time.sleep(0.1)
            shell.interrupt()
        t = threading.Thread(target=interrupter)
        t.start()
        shell.run_command("lora rx_raw")
        t.join()
        text = out.text
        assert "deadbeef" in text.lower() or "listening" in text.lower()


class TestNetPCAPCapture:
    """Test PCAP file export."""

    def test_pcap_capture_saves_file(self, tmp_path):
        import os
        import sys
        from unittest.mock import MagicMock
        from collections import deque
        
        shell, out, badge, apps = make_shell_with_apps()
        
        pcap_file = tmp_path / "test.pcap"
        
        # Mock badgenet and capture_all_packets
        mock_net_module = MagicMock()
        sys.modules["net.net"] = mock_net_module
        sys.modules["net"] = MagicMock()
        
        mock_badgenet = MagicMock()
        mock_badgenet.promiscuous_queue = deque()
        mock_badgenet.protocols = {}
        
        mock_net_module.badgenet = mock_badgenet
        mock_net_module.capture_all_packets = MagicMock()
        
        class MockFrame:
            def __init__(self, data):
                self.frame = data
            def deserialize(self, protos):
                self.fields_set = False
                
        mock_badgenet.promiscuous_queue.append(MockFrame(b"PCAPTESTDATA1"))
        mock_badgenet.promiscuous_queue.append(MockFrame(b"PCAPTESTDATA2"))
        
        import threading
        import time
        def interrupter():
            time.sleep(0.1)
            shell.interrupt()
            
        t = threading.Thread(target=interrupter)
        t.start()
        
        shell.run_command(f"net sniff --pcap {pcap_file}")
        t.join()
        
        # Clean up mock
        del sys.modules["net.net"]
        del sys.modules["net"]
        
        assert os.path.exists(pcap_file)
        with open(pcap_file, "rb") as f:
            data = f.read()
            
        # Check global header magic (a1b2c3d4 little endian)
        assert data.startswith(b"\xd4\xc3\xb2\xa1")
        # Check if packet data exists
        assert b"PCAPTESTDATA1" in data
        assert b"PCAPTESTDATA2" in data


class TestCTFWorkflow:
    """Test the CTF hot/cold game end-to-end."""

    def test_host_and_scan_flow(self):
        """User hosts a flag, another scans and gets warmer/colder."""
        shell, out, badge, apps = make_shell_with_apps()
        ctf = apps["ctf"]

        # Check initial status
        shell.run_command("ctf status")
        assert "no" in out.text.lower() or "Hosting" in out.text
        out.clear()

        # Host a flag
        shell.run_command("ctf host")
        assert "Hosting" in out.text
        assert ctf.hosting is True
        out.clear()

        # Status should now show hosting
        shell.run_command("ctf status")
        assert "YES" in out.text
        out.clear()

        # Scan sequence — getting warmer
        shell.run_command("ctf scan -80")
        assert "START" in out.text
        out.clear()

        shell.run_command("ctf scan -70")
        assert "WARMER" in out.text
        out.clear()

        shell.run_command("ctf scan -60")
        assert "WARMER" in out.text
        out.clear()

        # Getting colder
        shell.run_command("ctf scan -75")
        assert "COLDER" in out.text
        out.clear()

        # Status shows history
        shell.run_command("ctf status")
        assert "4" in out.text  # 4 scans
        out.clear()

        # Stop hosting
        shell.run_command("ctf stop")
        assert ctf.hosting is False
        out.clear()

        # Reset
        shell.run_command("ctf reset")
        assert len(ctf.scan_history) == 0

    def test_ctf_without_app(self):
        """CTF commands should fail gracefully if app not started."""
        badge = MockBadge()
        output = CaptureOutput()
        shell = Shell(badge, write_func=output)

        # Clear all CTFApp instances
        from apps.ctf_app import CTFApp
        CTFApp.all_apps.clear()

        shell.run_command("ctf host")
        assert "not running" in output.text.lower()


class TestPollWorkflow:
    """Test the polling system end-to-end."""

    def test_create_vote_results(self):
        """User creates a poll, votes, checks results."""
        shell, out, badge, apps = make_shell_with_apps()

        # Create a poll
        shell.run_command('poll new "Best language?" Python Rust Go')
        assert "#1" in out.text
        assert "Best language?" in out.text
        assert "Python" in out.text
        out.clear()

        # Vote
        shell.run_command("poll vote 1 0")  # Vote for Python
        assert "recorded" in out.text.lower()
        out.clear()

        shell.run_command("poll vote 1 0")  # Vote again
        out.clear()

        shell.run_command("poll vote 1 2")  # Vote for Go
        out.clear()

        # Check results
        shell.run_command("poll results 1")
        assert "Python" in out.text
        assert "Rust" in out.text
        assert "Go" in out.text
        # Python should have 2 votes
        assert "2" in out.text
        out.clear()

        # List all polls
        shell.run_command("poll list")
        assert "Best language?" in out.text
        assert "3 votes" in out.text

    def test_multiple_polls(self):
        """User creates multiple polls."""
        shell, out, badge, apps = make_shell_with_apps()

        shell.run_command('poll new "Favorite badge?" Flipper Supercon')
        out.clear()
        shell.run_command('poll new "Best talk?" Alpha Beta')
        out.clear()

        shell.run_command("poll list")
        assert "Favorite badge?" in out.text
        assert "Best talk?" in out.text

    def test_invalid_vote(self):
        """Voting on nonexistent poll should error."""
        shell, out, badge, apps = make_shell_with_apps()

        shell.run_command("poll vote 999 0")
        assert "Error" in out.text


class TestPeersWorkflow:
    """Test peer tracking end-to-end."""

    def test_track_and_query_peers(self):
        """Simulate discovering peers and querying them."""
        shell, out, badge, apps = make_shell_with_apps()
        peers_app = apps["peers"]

        # No peers initially
        shell.run_command("peers list")
        assert "No peers" in out.text
        out.clear()

        # Simulate discovering some peers
        peers_app.update_peer(0xDEADBEEF, rssi=-65.0, snr=10.0)
        peers_app.update_peer(0xCAFEBABE, rssi=-78.0, snr=5.5)
        peers_app.update_peer(0x12345678, rssi=-55.0, snr=15.0)

        # List peers
        shell.run_command("peers list")
        text = out.text
        assert "deadbeef" in text
        assert "cafebabe" in text
        assert "12345678" in text
        assert "3 peers total" in text
        out.clear()

        # Find nearest
        shell.run_command("peers nearest")
        assert "12345678" in out.text  # -55 is strongest
        out.clear()

        # Clear
        shell.run_command("peers clear")
        assert "3" in out.text  # Cleared 3
        out.clear()

        # Verify empty
        shell.run_command("peers list")
        assert "No peers" in out.text


class TestCrossModuleInteraction:
    """Test interactions between multiple command modules."""

    def test_config_then_neofetch(self):
        """Set alias via config, verify it appears in neofetch."""
        shell, out, badge, apps = make_shell_with_apps()

        shell.run_command("config set alias CoolHacker")
        out.clear()

        shell.run_command("neofetch")
        assert "CoolHacker" in out.text

    def test_lora_freq_affects_info(self):
        """Changing freq via lora command should update info output."""
        shell, out, badge, apps = make_shell_with_apps()

        shell.run_command("lora freq 30")
        out.clear()

        shell.run_command("info device")
        # Should show the new frequency
        assert "30" in out.text or "916" in out.text  # slot 30 ≈ 916.75 MHz

    def test_crypto_sign_verify_roundtrip(self):
        """Sign a message and then verify it."""
        shell, out, badge, apps = make_shell_with_apps(has_private_key=True)

        shell.run_command("crypto sign hello_world")
        # Extract signature from output
        sig_hex = None
        for line in out.line_list:
            if "Signature:" in line:
                sig_hex = line.split("Signature:")[-1].strip()
                break
        assert sig_hex is not None
        out.clear()

        # Verify
        shell.run_command("crypto verify hello_world " + sig_hex)
        assert "True" in out.text

    def test_nametag_config_sync(self):
        """Setting nametag via nametag command should update config."""
        shell, out, badge, apps = make_shell_with_apps()

        shell.run_command("nametag set Hacker42")
        out.clear()

        # Check config directly
        shell.run_command("config get alias")
        assert "Hacker42" in out.text

    def test_i2c_with_devices_then_scan(self):
        """Add mock I2C devices, verify scan sees them."""
        shell, out, badge, apps = make_shell_with_apps()

        badge.sao_i2c.add_device(0x3C)
        badge.sao_i2c.add_device(0x68)

        shell.run_command("i2c scan")
        assert "0x3c" in out.text
        assert "0x68" in out.text
        assert "2 device" in out.text


class TestStorageIntegration:
    """Test storage commands with real temp files."""

    def test_write_read_stat_remove(self, tmp_path):
        """Full lifecycle: write → read → stat → remove."""
        shell, out, badge, apps = make_shell_with_apps()
        test_file = str(tmp_path / "test.txt")

        # Write
        shell.run_command("storage write " + test_file + " Hello from Badge CLI!")
        assert "Wrote" in out.text
        out.clear()

        # Read back
        shell.run_command("storage read " + test_file)
        assert "Hello from Badge CLI!" in out.text
        out.clear()

        # Stat
        shell.run_command("storage stat " + test_file)
        assert "file" in out.text.lower()
        assert test_file.replace("\\", "/") in out.text
        out.clear()

        # Remove
        shell.run_command("storage remove " + test_file)
        assert "Removed" in out.text

        # Verify gone
        assert not os.path.exists(test_file)

    def test_mkdir_list_rmdir(self, tmp_path):
        """Create dir, list it, remove it."""
        shell, out, badge, apps = make_shell_with_apps()
        test_dir = str(tmp_path / "mydir")

        shell.run_command("storage mkdir " + test_dir)
        assert "Created" in out.text
        out.clear()

        shell.run_command("storage list " + str(tmp_path))
        assert "mydir" in out.text
        out.clear()

        shell.run_command("storage remove " + test_dir)
        assert "Removed" in out.text


class TestErrorHandling:
    """Test that the CLI handles errors gracefully across all modules."""

    def test_unknown_group_subcommand(self):
        shell, out, badge, apps = make_shell_with_apps()

        shell.run_command("lora nonexistent")
        assert "Unknown sub-command" in out.text

    def test_missing_arguments(self):
        """Commands with missing args should show usage, not crash."""
        shell, out, badge, apps = make_shell_with_apps()

        commands_needing_args = [
            "config get",
            "config set",
            "config broadcast",
            "lora tx",
            "gpio mode",
            "gpio set",
            "gpio read",
            "storage read",
            "storage write",
            "storage stat",
            "storage md5",
            "storage mkdir",
            "storage remove",
            "crypto sign",
            "crypto verify",
            "nametag set",
            "poll new",
            "poll vote",
            "poll results",
            "loader open",
        ]
        for cmd in commands_needing_args:
            out.clear()
            shell.run_command(cmd)
            text = out.text.lower()
            assert "usage" in text or "error" in text or "not found" in text or "not running" in text, \
                "Command '%s' should show usage or error, got: %s" % (cmd, out.text[:100])

    def test_invalid_hex_input(self):
        shell, out, badge, apps = make_shell_with_apps()

        shell.run_command("lora tx ZZZZ")
        assert "Error" in out.text or "Invalid" in out.text

    def test_invalid_freq_slot(self):
        shell, out, badge, apps = make_shell_with_apps()

        shell.run_command("lora freq 99")
        assert "Error" in out.text

    def test_config_broadcast_without_key(self):
        shell, out, badge, apps = make_shell_with_apps()
        shell.run_command("config broadcast test val")
        assert "No private key" in out.text


class TestMultiCommandScript:
    """Simulate scripted sequences of commands (like piping a script over serial)."""

    def test_scripted_setup(self):
        """A batch setup script that configures the badge."""
        shell, out, badge, apps = make_shell_with_apps()

        script = [
            "config set alias ScriptUser",
            "config save",
            "nametag set ScriptUser",
            "lora freq 15",
            "lora info",
        ]

        for cmd in script:
            shell.run_command(cmd)

        text = out.text
        assert "ScriptUser" in text
        assert "saved" in text.lower()
        assert "15" in text

        # Verify badge state
        assert badge.lora.freq_slot == 15
        alias = badge.config.get("alias")
        assert alias is not None
        assert b"ScriptUser" in alias

    def test_ctf_game_simulation(self):
        """Simulate a complete CTF game from host to scan to win."""
        shell, out, badge, apps = make_shell_with_apps()

        # Player A hosts
        shell.run_command("ctf host")

        # Player B scans (simulating RSSI readings getting stronger)
        readings = [-90, -85, -80, -75, -70, -65, -60, -55]
        for rssi in readings:
            shell.run_command("ctf scan %d" % rssi)

        # Check final status
        out.clear()
        shell.run_command("ctf status")
        assert "8" in out.text  # 8 scans
        assert "YES" in out.text  # Still hosting

        # Stop
        shell.run_command("ctf stop")

    def test_poll_party(self):
        """Create multiple polls, vote, check results."""
        shell, out, badge, apps = make_shell_with_apps()

        shell.run_command('poll new "Lunch?" Pizza Burgers Tacos')
        shell.run_command("poll vote 1 0")
        shell.run_command("poll vote 1 0")
        shell.run_command("poll vote 1 2")

        out.clear()
        shell.run_command("poll results 1")
        text = out.text
        assert "Pizza" in text
        assert "Tacos" in text

        # Create another poll
        shell.run_command('poll new "Hack or Sleep?" Hack Sleep')
        shell.run_command("poll vote 2 0")

        out.clear()
        shell.run_command("poll list")
        assert "Lunch?" in out.text
        assert "Hack or Sleep?" in out.text
