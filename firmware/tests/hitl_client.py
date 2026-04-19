import time
import re
import sys
import io
from unittest.mock import MagicMock

try:
    import serial
except ImportError:
    serial = None

class BaseCLIClient:
    """Base interface for CLI interaction."""
    def connect(self): raise NotImplementedError()
    def disconnect(self): raise NotImplementedError()
    def run_command(self, cmd, timeout=2.0): raise NotImplementedError()

class BadgeSerialClient(BaseCLIClient):
    """Manages serial connection to a physical badge."""

    def __init__(self, port, baudrate=115200, timeout=1.0):
        if serial is None:
            raise ImportError("pyserial is required for HITL testing.")
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self._prompt = "badge >:"
        
    def connect(self):
        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        time.sleep(0.5)
        self.ser.reset_input_buffer()
        self.ser.write(b"\r\n")
        out = self._read_until_prompt()
        if self._prompt not in out:
            self.ser.write(b"\x03")
            time.sleep(0.1)
            self.ser.write(b"\r\n")
            out += self._read_until_prompt()
            if self._prompt not in out:
                raise TimeoutError(f"Could not synchronize with CLI prompt on {self.port}")
                
    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            
    def _read_until_prompt(self, timeout=None):
        end_time = time.time() + (timeout if timeout is not None else self.timeout)
        output = ""
        while time.time() < end_time:
            if self.ser.in_waiting > 0:
                chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='replace')
                output += chunk
                if self._prompt in output:
                    break
            else:
                time.sleep(0.01)
        return output

    def run_command(self, cmd, timeout=2.0):
        self.ser.reset_input_buffer()
        self.ser.write(f"{cmd}\r\n".encode('utf-8'))
        output = self._read_until_prompt(timeout)
        output = output.replace(cmd + "\r\n", "", 1)
        if output.endswith(self._prompt):
            output = output[:-len(self._prompt)]
        return output.strip()

class BadgeMockClient(BaseCLIClient):
    """Simulates a serial connection using CliApp and Shell mocks."""

    def __init__(self, badge):
        from apps.cli_app import CliApp
        self.badge = badge
        self._stdin_buf = []
        self._stdout_lines = []
        
        # Mock stdin and stdout objects
        self.mock_stdin = MagicMock()
        self.mock_stdin.read.side_effect = lambda n: self._stdin_buf.pop(0) if self._stdin_buf else ""
        
        self.app = CliApp("CLI", badge, stdin=self.mock_stdin, stdout=MagicMock())
        # Redirect all writes to our list
        self.app.stdout.write = lambda msg: self._stdout_lines.append(msg)
        self.app.shell._write_func = lambda msg: self._stdout_lines.append(msg)
        
        self._prompt_str = "badge >:"
        
    def connect(self):
        from unittest.mock import MagicMock
        try:
            import uasyncio as aio
        except ImportError:
            import asyncio as aio
            
        orig_create_task = aio.create_task
        aio.create_task = MagicMock()
        try:
            self.app.start()
        finally:
            aio.create_task = orig_create_task
        
        # Clear startup noise
        self._stdout_lines.clear()
        
    def disconnect(self):
        pass

    def run_command(self, cmd, timeout=2.0):
        # 1. Reset everything
        self._stdin_buf.clear()
        self._stdout_lines.clear()
        self.app._line_buf = ""
        
        # 2. Queue command
        for char in cmd + "\n":
            self._stdin_buf.append(char)

        # 3. Direct mock of reading
        orig_read = self.app.read_stdin_noblock
        self.app.read_stdin_noblock = MagicMock()
        self.app.read_stdin_noblock.side_effect = lambda: self._stdin_buf.pop(0) if self._stdin_buf else ""
        
        # 4. Run loop until prompt appears
        max_iters = 50000 
        iters = 0
        found_prompt = False
        target_prompt = "badge >: " 
        
        while iters < max_iters:
            self.app.run_background()
            iters += 1
            current_output = "".join(self._stdout_lines)
            if target_prompt in current_output and not self._stdin_buf:
                found_prompt = True
                break
            
        self.app.read_stdin_noblock = orig_read
        
        # 5. Extract output
        output = "".join(self._stdout_lines)
        
        # Clean up output
        echo_cmd = cmd + "\r\n"
        if output.startswith(echo_cmd):
            output = output[len(echo_cmd):]
        elif cmd in output:
            # Fallback if echo was slightly different
            output = output.split("\r\n", 1)[-1]
            
        if target_prompt in output:
            idx = output.rfind(target_prompt)
            output = output[:idx]
            
        if not found_prompt and iters >= max_iters:
             # Check for common error indicators
             if "Error:" in output or "Unknown command:" in output:
                 return output.strip()
             return f"ERROR: Timeout. iters={iters} output={output!r}"
            
        return output.strip()
