"""Pytest fixtures for Badge CLI testing.

Provides a MockBadge, a Shell instance with captured output,
and helper utilities for all test modules.
"""

import sys
import os
import pytest


def _discover_serial_ports():
    try:
        from serial.tools import list_ports
    except Exception:
        return []
    return [p.device for p in list_ports.comports()]


def _build_hitl_client(port):
    from tests.hitl_client import BadgeSerialClient, BadgeMockClient

    if port.lower() == "mock":
        from tests.mocks.mock_badge import MockBadge
        return BadgeMockClient(MockBadge())
    return BadgeSerialClient(port)


def _resolve_secondary_port(primary_port, explicit_secondary):
    if explicit_secondary:
        return explicit_secondary

    if primary_port and primary_port.lower() == "mock":
        return "mock"

    ports = _discover_serial_ports()
    if not ports:
        return None

    if not primary_port:
        return ports[0] if len(ports) == 1 else ports[1]

    primary_low = primary_port.lower()
    for port in ports:
        if port.lower() != primary_low:
            return port
    return None


def _resolve_flipper_port(primary_port, secondary_port, explicit_flipper):
    if explicit_flipper:
        return explicit_flipper

    ports = _discover_serial_ports()
    if not ports:
        return None

    excluded = set()
    if primary_port:
        excluded.add(primary_port.lower())
    if secondary_port:
        excluded.add(secondary_port.lower())

    for port in ports:
        if port.lower() not in excluded:
            return port
    return None

# Add the badge source directory to the Python path so we can import
# badge_cli and apps modules as if running on the badge
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "badge"))

def pytest_addoption(parser):
    """Add custom command line options for HITL testing."""
    parser.addoption(
        "--hitl-port", 
        action="store", 
        default=None, 
        help="Serial port for physical hardware-in-the-loop tests (e.g., COM3, /dev/ttyUSB0)"
    )
    parser.addoption(
        "--hitl-port-secondary",
        action="store",
        default=None,
        help="Secondary serial port for 2-device HITL tests; if omitted we auto-detect another connected serial device",
    )
    parser.addoption(
        "--hitl-flipper-port",
        action="store",
        default=None,
        help="Serial port for Flipper Zero optional HITL integration (e.g., COM7)",
    )
    parser.addoption(
        "--hitl-flipper-baud",
        action="store",
        type=int,
        default=230400,
        help="Baud rate for Flipper Zero serial console",
    )
    parser.addoption(
        "--hitl-flipper-prompt",
        action="store",
        default=">:",
        help="Prompt hint used to detect end of Flipper CLI output",
    )
    parser.addoption(
        "--hitl-flipper-smoke-cmd",
        action="store",
        default="help",
        help="Flipper CLI command used for smoke verification",
    )
    parser.addoption(
        "--hitl-flipper-identifier",
        action="store",
        default="",
        help="Optional expected substring in Flipper smoke output (e.g., flipper, firmware)",
    )
    parser.addoption(
        "--hitl-flipper-ble-activity-cmd",
        action="store",
        default="",
        help="Optional Flipper CLI command to generate BLE activity during badge BLE tests",
    )
    parser.addoption(
        "--hitl-flipper-ble-stop-cmd",
        action="store",
        default="",
        help="Optional Flipper CLI command to stop BLE activity started by --hitl-flipper-ble-activity-cmd",
    )
    parser.addoption(
        "--hitl-flipper-info-cmd",
        action="store",
        default="info device",
        help="Flipper CLI command for capability probe (device info)",
    )
    parser.addoption(
        "--hitl-flipper-bt-cmd",
        action="store",
        default="bt hci_info",
        help="Flipper CLI command for BLE capability probe",
    )
    parser.addoption(
        "--hitl-flipper-log-cmd",
        action="store",
        default="",
        help="Optional long-running Flipper log command (e.g., 'log info')",
    )
    parser.addoption(
        "--hitl-flipper-subghz-cmd",
        action="store",
        default="",
        help="Optional Flipper Sub-GHz command to run in interruptible mode",
    )
    parser.addoption(
        "--hitl-flipper-wifi-activity-cmd",
        action="store",
        default="",
        help="Optional Flipper CLI command to generate activity during badge Wi-Fi tests",
    )
    parser.addoption(
        "--hitl-flipper-wifi-stop-cmd",
        action="store",
        default="",
        help="Optional Flipper CLI command to stop activity started by --hitl-flipper-wifi-activity-cmd",
    )
    parser.addoption(
        "--hitl-flipper-radio-activity-cmd",
        action="store",
        default="",
        help="Optional Flipper CLI command to generate RF activity during LoRa/radio tests",
    )
    parser.addoption(
        "--hitl-flipper-radio-stop-cmd",
        action="store",
        default="",
        help="Optional Flipper CLI command to stop activity started by --hitl-flipper-radio-activity-cmd",
    )
    parser.addoption(
        "--hitl-known-wifi-ssid",
        action="store",
        default="",
        help="Optional known SSID expected in multi-device Wi-Fi tests",
    )
    parser.addoption(
        "--hitl-known-wifi-bssid",
        action="store",
        default="",
        help="Optional known BSSID expected in multi-device Wi-Fi tests",
    )

@pytest.fixture(scope="function")
def hitl_badge(request):
    """Fixture that connects to physical hardware or simulates it."""
    port = request.config.getoption("--hitl-port")
    if not port:
        pytest.skip("Skipping HITL test: no --hitl-port specified")

    client = _build_hitl_client(port)
        
    client.connect()
    yield client
    client.disconnect()


@pytest.fixture(scope="function")
def hitl_badge_pair(request):
    """Fixture that connects to two physical badges or two mock clients."""
    primary_port = request.config.getoption("--hitl-port")
    if not primary_port:
        pytest.skip("Skipping 2-device HITL test: no --hitl-port specified")

    secondary_port = _resolve_secondary_port(
        primary_port,
        request.config.getoption("--hitl-port-secondary"),
    )
    if not secondary_port:
        pytest.skip("Skipping 2-device HITL test: no secondary serial port found")

    if secondary_port.lower() == primary_port.lower() and secondary_port.lower() != "mock":
        pytest.skip("Skipping 2-device HITL test: primary and secondary ports are the same")

    dev_a = _build_hitl_client(primary_port)
    dev_b = _build_hitl_client(secondary_port)

    dev_a.connect()
    dev_b.connect()
    try:
        yield (dev_a, dev_b)
    finally:
        dev_b.disconnect()
        dev_a.disconnect()


@pytest.fixture(scope="function")
def hitl_badge_secondary(hitl_badge_pair):
    """Convenience fixture for direct access to secondary badge."""
    _, dev_b = hitl_badge_pair
    return dev_b


@pytest.fixture(scope="function")
def hitl_flipper_cli(request):
    """Optional fixture for a Flipper Zero serial CLI endpoint."""
    primary_port = request.config.getoption("--hitl-port")
    secondary_port = request.config.getoption("--hitl-port-secondary")
    flipper_port = _resolve_flipper_port(
        primary_port,
        secondary_port,
        request.config.getoption("--hitl-flipper-port"),
    )
    if not flipper_port:
        pytest.skip("Skipping Flipper HITL test: no --hitl-flipper-port and no extra serial port detected")

    from tests.hitl_client import FlipperSerialClient

    client = FlipperSerialClient(
        port=flipper_port,
        baudrate=request.config.getoption("--hitl-flipper-baud"),
        prompt_hint=request.config.getoption("--hitl-flipper-prompt"),
    )

    client.connect()
    try:
        yield client
    finally:
        client.disconnect()


@pytest.fixture(scope="function")
def hitl_flipper_settings(request):
    """Configuration bundle for Flipper smoke/interoperability tests."""
    return {
        "smoke_cmd": request.config.getoption("--hitl-flipper-smoke-cmd"),
        "identifier": request.config.getoption("--hitl-flipper-identifier"),
        "ble_activity_cmd": request.config.getoption("--hitl-flipper-ble-activity-cmd"),
        "ble_stop_cmd": request.config.getoption("--hitl-flipper-ble-stop-cmd"),
        "info_cmd": request.config.getoption("--hitl-flipper-info-cmd"),
        "bt_cmd": request.config.getoption("--hitl-flipper-bt-cmd"),
        "log_cmd": request.config.getoption("--hitl-flipper-log-cmd"),
        "subghz_cmd": request.config.getoption("--hitl-flipper-subghz-cmd"),
        "wifi_activity_cmd": request.config.getoption("--hitl-flipper-wifi-activity-cmd"),
        "wifi_stop_cmd": request.config.getoption("--hitl-flipper-wifi-stop-cmd"),
        "radio_activity_cmd": request.config.getoption("--hitl-flipper-radio-activity-cmd"),
        "radio_stop_cmd": request.config.getoption("--hitl-flipper-radio-stop-cmd"),
    }


@pytest.fixture(scope="function")
def hitl_multi_settings(request):
    """Configuration bundle for multi-device non-Flipper HITL tests."""
    return {
        "known_wifi_ssid": request.config.getoption("--hitl-known-wifi-ssid"),
        "known_wifi_bssid": request.config.getoption("--hitl-known-wifi-bssid"),
    }


# Mock hardware modules that don't exist in CPython
from unittest.mock import MagicMock
mock_machine = MagicMock()
mock_machine.unique_id.return_value = b"12345678"
sys.modules["machine"] = mock_machine
sys.modules["lvgl"] = MagicMock()
sys.modules["lcd_bus"] = MagicMock()
sys.modules["ili9341"] = MagicMock()
sys.modules["xpt2046"] = MagicMock()
sys.modules["nv3007"] = MagicMock()
sys.modules["task_handler"] = MagicMock()
sys.modules["net.crypto"] = MagicMock()
sys.modules["network"] = MagicMock()
sys.modules["bluetooth"] = MagicMock()

mock_micropython = MagicMock()
mock_micropython.const = lambda x: x
sys.modules["micropython"] = mock_micropython

import builtins
builtins.const = lambda x: x

import select
if not hasattr(select, "poll"):
    class MockPoll:
        def register(self, *args): pass
        def poll(self, *args): return []
    select.poll = MockPoll
    select.POLLIN = 1

sys.modules["uselect"] = select

from tests.mocks.mock_badge import MockBadge
from badge_cli.shell import Shell


class CaptureOutput:
    """Captures all output lines from the shell for test assertions.

    Usage:
        out = CaptureOutput()
        shell = Shell(badge, write_func=out)
        shell.run_command("help")
        assert "help" in out.text
    """

    def __init__(self):
        self.lines = []

    def __call__(self, text):
        self.lines.append(text)

    @property
    def text(self):
        """All output joined as a single string."""
        return "".join(self.lines)

    @property
    def line_list(self):
        """Output split into individual lines (strips CRLF)."""
        result = []
        for chunk in self.lines:
            for line in chunk.split("\r\n"):
                if line:
                    result.append(line)
        return result

    def clear(self):
        self.lines.clear()


@pytest.fixture
def badge():
    """Create a fresh MockBadge for each test."""
    return MockBadge()


@pytest.fixture
def badge_with_key():
    """Create a MockBadge that has a private key."""
    return MockBadge(has_private_key=True)


@pytest.fixture
def output():
    """Create a fresh CaptureOutput for each test."""
    return CaptureOutput()


@pytest.fixture
def shell(badge, output):
    """Create a Shell with MockBadge and CaptureOutput."""
    return Shell(badge, write_func=output)


@pytest.fixture
def shell_and_output(badge, output):
    """Return (shell, output) tuple for tests that need both."""
    s = Shell(badge, write_func=output)
    return s, output
