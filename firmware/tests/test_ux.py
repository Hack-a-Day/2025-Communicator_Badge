from badge_cli.shell import Shell, Colors
from tests.mocks.mock_badge import MockBadge
import sys
from unittest.mock import MagicMock

# Mock gc for environments without mem_free (like CPython tests)
if not hasattr(sys.modules.get('gc'), 'mem_free'):
    mock_gc = MagicMock()
    mock_gc.mem_free.return_value = 100000
    mock_gc.mem_alloc.return_value = 20000
    sys.modules['gc'] = mock_gc

def test_storage_cd_pwd(shell_and_output, tmp_path):
    shell, output = shell_and_output
    
    # Create a test directory structure
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "file.txt").write_text("hello")
    
    # Default CWD should be /
    shell.run_command("storage pwd")
    assert "/" in output.text
    output.clear()
    
    # CD into absolute path
    shell.run_command(f"storage cd {tmp_path}")
    shell.run_command("storage pwd")
    assert str(tmp_path).replace("\\", "/") in output.text.replace("\\", "/")
    output.clear()
    
    # CD into relative path
    shell.run_command("storage cd subdir")
    assert shell.cwd.replace("\\", "/").endswith("subdir")
    
    # List in current dir
    shell.run_command("storage list")
    assert "file.txt" in output.text

def test_tab_completion_commands(shell_and_output):
    shell, output = shell_and_output
    
    # Complete "lo" -> should give ["lora", "log", "loader"]
    matches = shell.complete("lo")
    assert "lora" in matches
    assert "log" in matches
    assert "loader" in matches

def test_tab_completion_files(shell_and_output, tmp_path):
    shell, output = shell_and_output
    
    # Create files
    (tmp_path / "test_alpha.txt").write_text("a")
    (tmp_path / "test_beta.txt").write_text("b")
    
    shell.cwd = str(tmp_path).replace("\\", "/")
    
    # Complete "storage read test_"
    matches = shell.complete("storage read test_")
    assert any("test_alpha.txt" in m for m in matches)
    assert any("test_beta.txt" in m for m in matches)

def test_info_top(shell_and_output):
    shell, output = shell_and_output
    
    # Mock streaming flag to exit immediately
    import threading, time
    def interrupter():
        time.sleep(0.2)
        shell.interrupt()
    
    t = threading.Thread(target=interrupter)
    t.start()
    
    shell.run_command("info top")
    t.join()
    
    assert "System Monitor" in output.text
    assert "Heap Used" in output.text
    assert "Stopped" in output.text

def test_ansi_colors_in_output(shell_and_output):
    shell, output = shell_and_output
    
    shell.run_command("info device")
    # Check if any ANSI escape codes are present
    assert "\x1b[" in output.text
    assert Colors.END in output.text

def test_colorized_prompt(shell_and_output):
    shell, output = shell_and_output
    shell._prompt()
    assert Colors.GREEN in output.text
    assert Colors.CYAN in output.text
