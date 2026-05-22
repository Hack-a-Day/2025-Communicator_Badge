import time
import threading
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
        self._prompt = "badge >: " # Added space to match Shell._prompt()

    def _has_shell_prompt(self, text):
        return (
            self._prompt in text
            or "] >: " in text
            or (">: " in text and "badge" in text.lower())
        )

    def _has_repl_prompt(self, text):
        return "\n>>> " in text or text.rstrip().endswith(">>>")

    def _recover_from_repl(self):
        # Ctrl+D requests a soft reboot in MicroPython.
        self.ser.write(b"\x04")
        time.sleep(0.6)
        self.ser.write(b"\r\n")
        return self._read_until_prompt(timeout=3.0)
        
    def connect(self):
        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        time.sleep(1.0) # Increased wait for boot/connect
        self.ser.reset_input_buffer()
        self.ser.write(b"\r\n")
        out = self._read_until_prompt(timeout=2.0)

        if self._has_repl_prompt(out):
            out += self._recover_from_repl()

        if not self._has_shell_prompt(out):
            # Try Ctrl+C to break any running app
            self.ser.write(b"\x03")
            time.sleep(0.2)
            self.ser.write(b"\r\n")
            out += self._read_until_prompt()
            if self._has_repl_prompt(out):
                out += self._recover_from_repl()
            if not self._has_shell_prompt(out):
                # One last try: send 'exit' in case we are in a sub-app that supports it.
                self.ser.write(b"exit\r\n")
                time.sleep(0.5)
                out += self._read_until_prompt()
                if self._has_repl_prompt(out):
                    out += self._recover_from_repl()
                if not self._has_shell_prompt(out):
                    raise TimeoutError(f"Could not synchronize with CLI prompt on {self.port}. Got: {out!r}")
                
    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            
    def _read_until_prompt(self, timeout=None):
        tout = timeout if timeout is not None else self.timeout
        end_time = time.time() + tout
        output = ""
        while time.time() < end_time:
            if self.ser.in_waiting > 0:
                chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='replace')
                output += chunk
                if self._has_shell_prompt(output) or self._has_repl_prompt(output):
                    break
            else:
                time.sleep(0.01)
        return output

    def run_command(self, cmd, timeout=5.0): # Default timeout increased for real hardware
        self.ser.reset_input_buffer()
        # Ensure command is sent cleanly
        self.ser.write(f"{cmd}\r\n".encode('utf-8'))
        output = self._read_until_prompt(timeout)
        
        # Clean up output
        # Remove echo (interleaved chars might happen, but starts-with is usually safe)
        if output.startswith(cmd):
            output = output.split("\r\n", 1)[-1]
        
        # Remove prompt from end
        idx = max(output.rfind(self._prompt), output.rfind("] >: "), output.rfind(">: "))
        if idx != -1:
            output = output[:idx]
            
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
        
        def mock_create_task(coro):
            if hasattr(coro, "close"):
                coro.close() # Silence 'was never awaited' warning
            return MagicMock()
            
        aio.create_task = mock_create_task
        try:
            self.app.start()
        finally:
            aio.create_task = orig_create_task
        
        # Clear startup noise
        self._stdout_lines.clear()
        
    def disconnect(self):
        pass

    def send_raw(self, chars):
        """Send raw characters to the CLI input buffer."""
        for char in chars:
            self._stdin_buf.append(char)

    def run_command(self, cmd, timeout=2.0, max_iters=None):
        # 1. Reset everything (only if cmd is provided)
        if cmd:
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
        # Use both an iteration cap and wall-clock deadline so hangs fail fast.
        iters_limit = max_iters or 5000
        iters = 0
        found_prompt = False
        long_running = False
        target_prompt = "badge >: "
        prompt_tail = ">:"
        deadline = time.time() + max(timeout, 0.5)
        
        def _run_background_once_with_watchdog(timeout_s=0.5, allow_long_running=False):
            err = {}

            def _runner():
                try:
                    self.app.run_background()
                except Exception as ex:
                    err["ex"] = ex

            t = threading.Thread(target=_runner, daemon=True)
            t.start()
            t.join(timeout_s)
            if t.is_alive():
                if allow_long_running:
                    return False
                raise TimeoutError(
                    "CliApp.run_background() appears hung while processing input. "
                    f"stdin_buf={repr(self._stdin_buf[:20])} "
                    f"line_buf={repr(getattr(self.app, '_line_buf', ''))}"
                )
            if "ex" in err:
                raise err["ex"]
            return True

        try:
            while iters < iters_limit:
                if time.time() > deadline:
                    break
                allow_long_running = cmd is None
                watchdog_timeout = max(0.5, timeout) if cmd is not None else 0.5
                completed = _run_background_once_with_watchdog(
                    timeout_s=watchdog_timeout,
                    allow_long_running=allow_long_running
                )
                if not completed:
                    long_running = True
                    break
                iters += 1
                current_output = "".join(self._stdout_lines)
                if (
                    (target_prompt in current_output or prompt_tail in current_output)
                    and not self._stdin_buf
                ):
                    found_prompt = True
                    break
        finally:
            self.app.read_stdin_noblock = orig_read
        
        # 5. Extract output
        output = "".join(self._stdout_lines)
        
        # Clean up output
        if cmd and output.startswith(cmd):
            output = output.split("\r\n", 1)[-1]
        elif cmd and cmd in output:
            output = output.replace(cmd, "", 1).strip("\r\n")
            
        if target_prompt in output:
            idx = output.rfind(target_prompt)
            output = output[:idx]
        elif prompt_tail in output:
            idx = output.rfind(prompt_tail)
            output = output[:idx]
            
        if not found_prompt:
             if long_running:
                 return output.strip()
             if "Error:" in output or "Unknown command:" in output:
                 return output.strip()
             return (
                 "ERROR: Timeout waiting for prompt. "
                 f"cmd={cmd!r} timeout={timeout}s iters={iters} "
                 f"stdin_buf={repr(self._stdin_buf[:20])} "
                 f"line_buf={repr(getattr(self.app, '_line_buf', ''))} "
                 f"output={output!r}"
             )
            
        return output.strip()
