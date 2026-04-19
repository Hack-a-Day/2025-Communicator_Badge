import sys
import os
from unittest.mock import MagicMock

# Mocks
mock_machine = MagicMock()
mock_machine.unique_id.return_value = b"12345678"
sys.modules["machine"] = mock_machine
sys.modules["micropython"] = MagicMock()
sys.modules["lcd_bus"] = MagicMock()
sys.modules["ili9341"] = MagicMock()
sys.modules["xpt2046"] = MagicMock()
sys.modules["nv3007"] = MagicMock()
sys.modules["task_handler"] = MagicMock()
sys.modules["net.crypto"] = MagicMock()
sys.modules["network"] = MagicMock()
sys.modules["bluetooth"] = MagicMock()

# Path
sys.path.append(os.path.abspath("badge"))
sys.path.append(os.path.abspath("."))

from tests.mocks.mock_badge import MockBadge
from apps.cli_app import CliApp

badge = MockBadge()
app = CliApp("CLI", badge)

def run_cmd(cmd):
    print(f"\n--- Running: {cmd} ---")
    app._line_buf = ""
    stdin_buf = list(cmd + "\n")
    stdout_lines = []
    app.stdout.write = stdout_lines.append
    app.shell._write_func = stdout_lines.append
    
    orig_read = app.read_stdin_noblock
    app.read_stdin_noblock = MagicMock()
    app.read_stdin_noblock.side_effect = lambda: stdin_buf.pop(0) if stdin_buf else ""
    
    max_iters = 1000
    for i in range(max_iters):
        app.run_background()
        if not stdin_buf and "badge >: " in "".join(stdout_lines):
            print(f"Found prompt at iter {i}")
            break
            
    app.read_stdin_noblock = orig_read
    return "".join(stdout_lines)

print(run_cmd("echo hello"))
print(run_cmd("net address"))
print(run_cmd("storage list"))
