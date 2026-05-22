import time
import threading
import re
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


class GenericSerialCLIClient(BaseCLIClient):
    """Simple serial CLI client for non-badge devices (e.g., Flipper Zero)."""

    def __init__(self, port, baudrate=115200, timeout=1.0, prompt_hint=">:"):
        if serial is None:
            raise ImportError("pyserial is required for HITL testing.")
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.prompt_hint = prompt_hint
        self.ser = None

    def _strip_ansi(self, text):
        return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)

    def _has_prompt(self, text):
        if not text:
            return False
        return self.prompt_hint in text

    def _read_until_prompt(self, timeout=None):
        tout = timeout if timeout is not None else self.timeout
        end_time = time.time() + tout
        output = ""
        saw_prompt = False
        last_rx = time.time()

        while time.time() < end_time:
            if self.ser.in_waiting > 0:
                chunk = self.ser.read(self.ser.in_waiting).decode("utf-8", errors="replace")
                output += chunk
                last_rx = time.time()
                if self._has_prompt(output):
                    saw_prompt = True
            else:
                if saw_prompt and (time.time() - last_rx) > 0.15:
                    break
                time.sleep(0.01)

        return output

    def _read_for(self, duration):
        end_time = time.time() + max(0.0, duration)
        output = ""
        while time.time() < end_time:
            if self.ser.in_waiting > 0:
                chunk = self.ser.read(self.ser.in_waiting).decode("utf-8", errors="replace")
                output += chunk
            else:
                time.sleep(0.01)
        return output

    def connect(self):
        self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        time.sleep(0.6)
        self.ser.reset_input_buffer()
        self.ser.write(b"\r\n")
        self._read_until_prompt(timeout=2.0)

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def send_raw(self, chars):
        if isinstance(chars, str):
            chars = chars.encode("utf-8", errors="ignore")
        self.ser.write(chars)

    def run_command(self, cmd, timeout=4.0, max_iters=None):
        if cmd is not None:
            self.ser.reset_input_buffer()
            self.ser.write(f"{cmd}\r\n".encode("utf-8"))
        output = self._read_until_prompt(timeout=timeout)
        output = self._strip_ansi(output)
        if cmd and output.startswith(cmd):
            output = output.split("\r\n", 1)[-1]
        idx = output.rfind(self.prompt_hint)
        if idx != -1:
            output = output[:idx]
        return output.strip()

    def run_command_interrupt(self, cmd, run_seconds=1.0, timeout=4.0, interrupt_char="\x03"):
        """Run an interactive/streaming command, interrupt it, and capture output."""
        self.ser.reset_input_buffer()
        self.ser.write(f"{cmd}\r\n".encode("utf-8"))
        output = self._read_for(run_seconds)
        self.send_raw(interrupt_char)
        output += self._read_until_prompt(timeout=timeout)
        output = self._strip_ansi(output)
        if output.startswith(cmd):
            output = output.split("\r\n", 1)[-1]
        idx = output.rfind(self.prompt_hint)
        if idx != -1:
            output = output[:idx]
        return output.strip()


class FlipperSerialClient(GenericSerialCLIClient):
    """Serial client for Flipper Zero CLI/UART console integration."""

    def __init__(self, port, baudrate=115200, timeout=1.0, prompt_hint=">:"):
        super().__init__(port=port, baudrate=baudrate, timeout=timeout, prompt_hint=prompt_hint)

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
        self._ready_marker = "CLI_READY"

    def _has_shell_prompt(self, text):
        return (
            self._prompt in text
            or "] >: " in text
            or (">: " in text and "badge" in text.lower())
        )

    def _has_ready_marker(self, text):
        return self._ready_marker in text

    def _has_startup_banner(self, text):
        low = text.lower()
        return "type 'help' or '?' for a list of commands" in low

    def _strip_ansi(self, text):
        return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)

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
        # Give firmware time to finish app startup and emit the ready marker.
        out = self._read_until_prompt(timeout=10.0)

        if self._has_ready_marker(out) and self._has_shell_prompt(out):
            return

        # One extra non-destructive nudge before any interrupt recovery.
        self.ser.write(b"\r\n")
        out += self._read_until_prompt(timeout=3.0)
        if self._has_ready_marker(out) and self._has_shell_prompt(out):
            return
        if self._has_shell_prompt(out):
            return

        if self._has_repl_prompt(out):
            out += self._recover_from_repl()
            if self._has_ready_marker(out) and self._has_shell_prompt(out):
                return
            if self._has_shell_prompt(out):
                return

        if not self._has_shell_prompt(out):
            # Try Ctrl+C to break any running app
            self.ser.write(b"\x03")
            time.sleep(0.2)
            self.ser.write(b"\r\n")
            out += self._read_until_prompt()
            if self._has_repl_prompt(out):
                out += self._recover_from_repl()
            if not self._has_shell_prompt(out):
                # Final non-destructive retry.
                self.ser.write(b"\r\n")
                out += self._read_until_prompt(timeout=2.0)
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
        saw_prompt = False
        last_rx = time.time()

        while time.time() < end_time:
            if self.ser.in_waiting > 0:
                chunk = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='replace')
                output += chunk
                last_rx = time.time()
                if self._has_shell_prompt(output) or self._has_repl_prompt(output):
                    saw_prompt = True
            else:
                # Once we've seen a prompt, wait briefly for line tail to settle.
                if saw_prompt and (time.time() - last_rx) > 0.15:
                    break
                time.sleep(0.01)

        return output

    def send_raw(self, chars):
        if isinstance(chars, str):
            chars = chars.encode("utf-8", errors="ignore")
        self.ser.write(chars)

    def run_command(self, cmd, timeout=5.0, max_iters=None): # max_iters kept for interface compatibility
        if cmd is not None:
            self.ser.reset_input_buffer()
        # Ensure command is sent cleanly unless caller already queued raw input.
        if cmd is not None:
            self.ser.write(f"{cmd}\r\n".encode('utf-8'))
        output = self._read_until_prompt(timeout)
        clean = self._strip_ansi(output)

        # If we captured a startup banner or only a bare prompt, retry command once.
        stripped = clean.strip()
        needs_retry = (
            cmd is not None
            and (
                self._has_startup_banner(clean)
                or not stripped
                or (stripped.endswith("] >:") and stripped.count("\n") <= 1)
            )
        )
        if needs_retry:
            self.ser.reset_input_buffer()
            self.ser.write(f"{cmd}\r\n".encode('utf-8'))
            output = self._read_until_prompt(timeout=max(1.0, timeout))
            clean = self._strip_ansi(output)
        
        # Clean up output
        # Remove echo (interleaved chars might happen, but starts-with is usually safe)
        if cmd is not None and clean.startswith(cmd):
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
