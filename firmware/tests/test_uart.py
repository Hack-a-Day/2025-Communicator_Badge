import pytest
from unittest.mock import MagicMock, patch
import sys

# Ensure machine and select are mocked before importing shell
# (Done in conftest.py, but good to be aware)

class CaptureOutput:
    def __init__(self):
        self.lines = []
    def __call__(self, text):
        self.lines.append(text)
    @property
    def text(self):
        return "".join(self.lines)

@pytest.fixture
def shell_setup():
    from tests.mocks.mock_badge import MockBadge
    from badge_cli.shell import Shell
    
    badge = MockBadge()
    out = CaptureOutput()
    shell = Shell(badge, write_func=out)
    return shell, out, badge

def test_uart_help_registration(shell_setup):
    shell, out, badge = shell_setup
    # 'uart' is a group, so 'uart ?' or just 'uart' shows sub-commands
    shell.run_command("uart ?")
    assert "bridge" in out.text
    assert "terminal" in out.text

def test_uart_bridge_invalid_baud(shell_setup):
    shell, out, badge = shell_setup
    shell.run_command("uart bridge invalid")
    assert "Invalid baud rate" in out.text

@patch("machine.UART")
def test_uart_bridge_start(mock_uart, shell_setup):
    shell, out, badge = shell_setup
    
    # Mock uselect.poll to exit immediately
    mock_poll_obj = MagicMock()
    mock_poll_obj.poll.side_effect = KeyboardInterrupt()
    
    with patch("uselect.poll", return_value=mock_poll_obj):
        shell.run_command("uart bridge 9600")
    
    assert "Entering UART Bridge Mode (9600 baud)" in out.text
    mock_uart.assert_called_with(1, baudrate=9600, tx=7, rx=6, timeout=10)
    assert "Bridge Mode exited" in out.text

def test_terminal_app_exists():
    from apps.serial_terminal import SerialTerminalApp
    from tests.mocks.mock_badge import MockBadge
    badge = MockBadge()
    app = SerialTerminalApp("Terminal", badge)
    assert app.name == "Terminal"
    assert app.baud == 115200
