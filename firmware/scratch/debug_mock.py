import sys
import os

# Add firmware and firmware/badge to path
sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("badge"))

from tests.mocks.mock_badge import MockBadge
from apps.cli_app import CliApp
import io
from unittest.mock import MagicMock

badge = MockBadge()
stdin = io.StringIO()
stdout = io.StringIO()
app = CliApp("CLI", badge, stdin=stdin, stdout=stdout)
app.shell._write_func = stdout.write

# Start app
app.start()
stdout.truncate(0)
stdout.seek(0)

def run_cmd(cmd):
    stdin.truncate(0)
    stdin.seek(0)
    stdout.truncate(0)
    stdout.seek(0)
    app._line_buf = ""
    
    stdin.write(cmd + "\n")
    stdin.seek(0)
    
    # Mock read_stdin_noblock
    orig_read = app.read_stdin_noblock
    app.read_stdin_noblock = MagicMock()
    # We need to simulate the stateful popping
    buf = list(cmd + "\n")
    app.read_stdin_noblock.side_effect = lambda: buf.pop(0) if buf else ""
    
    for _ in range(len(cmd) + 10): # Run enough times
        app.run_background()
        
    app.read_stdin_noblock = orig_read
    return stdout.getvalue()

print("Testing echo...")
print(f"Result: {run_cmd('echo hello')!r}")

print("Testing info device...")
print(f"Result: {run_cmd('info device')!r}")
