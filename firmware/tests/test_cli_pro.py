import pytest
import time
import os

def test_cli_history(hitl_badge):
    """Test command history navigation."""
    # 1. Run some commands
    hitl_badge.run_command("echo cmd1")
    hitl_badge.run_command("echo cmd2")
    
    # 2. Check history command
    out = hitl_badge.run_command("history")
    assert "echo cmd1" in out
    assert "echo cmd2" in out

def test_cli_completion(hitl_badge):
    """Test Tab completion."""
    # Send "lor" + Tab
    hitl_badge.send_raw("lor\t")
    # Process it
    out = hitl_badge.run_command(None, max_iters=100)
    # When completed, the line is redrawn. "badge >: lora" should be in out.
    assert "lora" in out

def test_cli_batch_script(hitl_badge):
    """Test running a batch script from flash."""
    script_name = "test.cli"
    
    # 1. Write script to flash line by line
    hitl_badge.run_command(f"storage write {script_name} echo hello")
    hitl_badge.run_command(f"storage append {script_name} echo world")
    
    # 2. Run batch script
    out = hitl_badge.run_command(f"batch {script_name}")
    assert "hello" in out
    assert "world" in out

def test_cli_rf_scan(hitl_badge):
    """Test Sub-GHz scanner (waterfall)."""
    # Start scan
    hitl_badge.send_raw("subghz scan\n")
    # Run for a bit (now non-blocking because of check_interrupt)
    out = hitl_badge.run_command(None, max_iters=100)
    assert "Starting Sub-GHz Scanner" in out
    
    # Send Ctrl+C to stop
    hitl_badge.send_raw("\x03")
    out = hitl_badge.run_command(None, max_iters=200)
    assert "Scanner stopped" in out

def test_cli_rf_record_play(hitl_badge):
    """Test recording and playing back RF signals."""
    # Start recording
    hitl_badge.send_raw("subghz record 915.0 test.ook\n")
    # Run for 50 iters
    hitl_badge.run_command(None, max_iters=50)
    
    # Stop recording
    hitl_badge.send_raw("\x03")
    hitl_badge.run_command(None, max_iters=100)
    
    # Verify file exists
    out = hitl_badge.run_command("storage list")
    assert "test.ook" in out
    
    # Play back
    out = hitl_badge.run_command("subghz play 915.0 test.ook")
    assert "Playback complete" in out
