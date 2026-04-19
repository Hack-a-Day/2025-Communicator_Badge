"""Tests for the Shell core: dispatch, help, groups, error handling."""

import pytest
from badge_cli.shell import Shell
from tests.mocks.mock_badge import MockBadge


class TestShellDispatch:
    """Test command parsing and dispatch."""

    def test_empty_line_does_nothing(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("")
        assert output.text == ""

    def test_whitespace_only_does_nothing(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("   ")
        assert output.text == ""

    def test_unknown_command(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("xyzzy")
        assert "Unknown command: xyzzy" in output.text

    def test_unknown_command_suggests_help(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("foobar")
        assert "help" in output.text.lower()


class TestHelpCommand:
    """Test the help / ? command."""

    def test_help_lists_commands(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("help")
        lines = output.line_list
        # Should contain at least 'help', 'echo', 'exit', 'version'
        text = output.text
        assert "help" in text
        assert "echo" in text
        assert "exit" in text
        assert "version" in text

    def test_question_mark_is_help_alias(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("?")
        assert "Commands:" in output.text

    def test_help_shows_groups_section(self, shell_and_output):
        """If command groups are registered, help should show them."""
        shell, output = shell_and_output
        # Register a dummy group
        shell.register_group("testgrp", {"sub1": (lambda a: None, "A sub-command")}, "Test group")
        shell.run_command("help")
        assert "testgrp" in output.text
        assert "Command groups" in output.text


class TestEchoCommand:
    """Test the echo command."""

    def test_echo_single_word(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("echo hello")
        assert "hello" in output.text

    def test_echo_multiple_words(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("echo hello world")
        assert "hello world" in output.text

    def test_echo_empty(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("echo")
        # Empty echo should output an empty line (just CRLF)
        assert len(output.lines) >= 1
        assert "\r\n" in output.text


class TestVersionCommand:
    """Test the version command."""

    def test_version_shows_version(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("version")
        assert "v0.1" in output.text

    def test_version_shows_platform(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("version")
        assert "Platform:" in output.text


class TestExitCommand:
    """Test the exit command."""

    def test_exit_raises_keyboard_interrupt(self, shell_and_output):
        shell, output = shell_and_output
        with pytest.raises(KeyboardInterrupt):
            shell.run_command("exit")


class TestGroupDispatch:
    """Test command group routing and sub-help."""

    def setup_method(self):
        self.badge = MockBadge()
        self.output_lines = []
        self.shell = Shell(self.badge, write_func=lambda t: self.output_lines.append(t))
        # Register a test group
        self._sub1_called = False
        self._sub1_args = None

        def sub1_handler(args):
            self._sub1_called = True
            self._sub1_args = args

        self.shell.register_group(
            "testgrp",
            {
                "sub1": (sub1_handler, "First sub-command"),
                "sub2": (lambda a: None, "Second sub-command"),
            },
            "A test group"
        )

    def test_group_dispatches_to_subcommand(self):
        self.shell.run_command("testgrp sub1 arg1 arg2")
        assert self._sub1_called
        assert self._sub1_args == ["arg1", "arg2"]

    def test_group_question_mark_shows_help(self):
        self.shell.run_command("testgrp ?")
        text = "".join(self.output_lines)
        assert "sub1" in text
        assert "sub2" in text
        assert "First sub-command" in text

    def test_group_no_subcmd_shows_help(self):
        self.shell.run_command("testgrp")
        text = "".join(self.output_lines)
        assert "sub1" in text
        assert "sub2" in text

    def test_unknown_subcommand(self):
        self.shell.run_command("testgrp unknown")
        text = "".join(self.output_lines)
        assert "Unknown sub-command" in text

    def test_subcommand_error_is_caught(self):
        def bad_handler(args):
            raise ValueError("test error")
        self.shell.register_group("badgrp", {"crash": (bad_handler, "Will fail")})
        self.shell.run_command("badgrp crash")
        text = "".join(self.output_lines)
        assert "Error:" in text
        assert "test error" in text


class TestTokenSplitting:
    """Test the line tokenizer."""

    def setup_method(self):
        self.badge = MockBadge()
        self.shell = Shell(self.badge)

    def test_simple_split(self):
        tokens = self.shell._split_line("hello world")
        assert tokens == ["hello", "world"]

    def test_quoted_strings(self):
        tokens = self.shell._split_line('echo "hello world"')
        assert tokens == ["echo", "hello world"]

    def test_multiple_spaces(self):
        tokens = self.shell._split_line("a   b   c")
        assert tokens == ["a", "b", "c"]

    def test_empty_string(self):
        tokens = self.shell._split_line("")
        assert tokens == []

    def test_tabs(self):
        tokens = self.shell._split_line("a\tb\tc")
        assert tokens == ["a", "b", "c"]

    def test_mixed_quotes_and_args(self):
        tokens = self.shell._split_line('poll new "Best language?" Python Rust Go')
        assert tokens == ["poll", "new", "Best language?", "Python", "Rust", "Go"]


class TestUptimeCommand:
    """Test the uptime command."""

    def test_uptime_shows_time(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("uptime")
        assert "Uptime:" in output.text


class TestDateCommand:
    """Test the date command."""

    def test_date_shows_date(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("date")
        # Should output a date string like 2026-04-19 or "RTC not available"
        text = output.text
        assert "-" in text or "RTC" in text


class TestNeofetchCommand:
    """Test the neofetch command."""

    def test_neofetch_shows_ascii_art(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("neofetch")
        text = output.text
        assert "| |__" in text  # ASCII art contains this string
        assert "BadgeOS" in text
        assert "ESP32-S3" in text

    def test_neofetch_shows_radio_info(self, shell_and_output):
        shell, output = shell_and_output
        shell.run_command("neofetch")
        assert "SX1262" in output.text


class TestStreamingInterrupt:
    """Test the streaming / Ctrl+C pattern."""

    def test_interrupt_clears_streaming_flag(self, shell):
        shell._streaming = True
        shell.interrupt()
        assert shell._streaming is False


class TestBangCommand:
    """Test the ! alias."""

    def test_bang_dispatches_to_info_device(self, shell_and_output):
        shell, output = shell_and_output
        # ! should try to run "info device". Since info group isn't registered
        # yet in Phase 1, it should say "Unknown command: info"
        shell.run_command("!")
        # At this point, 'info' group isn't registered, so we expect unknown
        assert "Unknown" in output.text or "info" in output.text.lower()


class TestCliApp:
    """Test the CliApp background runner."""

    def test_cli_app_ui_feedback(self):
        from apps.cli_app import CliApp
        from tests.mocks.mock_badge import MockBadge
        
        badge = MockBadge()
        app = CliApp("CLI", badge)
        
        # Test that entering a character triggers UI feedback
        app._handle_cli_input("a")
        
        assert badge.display.cli_active_shown is True
