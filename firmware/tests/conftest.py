"""Pytest fixtures for Badge CLI testing.

Provides a MockBadge, a Shell instance with captured output,
and helper utilities for all test modules.
"""

import sys
import os
import pytest

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

@pytest.fixture(scope="function")
def hitl_badge(request):
    """Fixture that connects to physical hardware or simulates it."""
    port = request.config.getoption("--hitl-port")
    if not port:
        pytest.skip("Skipping HITL test: no --hitl-port specified")
        
    from tests.hitl_client import BadgeSerialClient, BadgeMockClient
    if port.lower() == "mock":
        from tests.mocks.mock_badge import MockBadge
        badge = MockBadge()
        client = BadgeMockClient(badge)
    else:
        # Serial port client can be session-scoped in theory, 
        # but we use function scope for consistency here.
        client = BadgeSerialClient(port)
        
    client.connect()
    yield client
    client.disconnect()


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
