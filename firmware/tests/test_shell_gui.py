import pytest
from unittest.mock import MagicMock, patch
from apps.shell_gui import ShellGuiApp
from tests.mocks.mock_badge import MockBadge
import asyncio

@pytest.fixture
def gui_app():
    badge = MockBadge()
    with patch("asyncio.create_task"):
        app = ShellGuiApp("Shell", badge)
        return app, badge

def test_shell_gui_init(gui_app):
    app, badge = gui_app
    assert app.name == "Shell"
    assert app.shell is None

def test_shell_gui_foreground(gui_app):
    app, badge = gui_app
    
    # Mock LvGL calls
    with patch("lvgl.textarea") as mock_ta, \
         patch("lvgl.style_t"), \
         patch("asyncio.create_task"), \
         patch("ui.page.Page.replace_screen"):
        
        app.switch_to_foreground()
        
        assert app.shell is not None
        assert app.page is not None
        mock_ta.assert_called()

def test_shell_gui_command_execution(gui_app):
    app, badge = gui_app
    
    with patch("lvgl.textarea"), \
         patch("lvgl.style_t"), \
         patch("asyncio.create_task"), \
         patch("ui.page.Page.replace_screen"):
        
        app.switch_to_foreground()
        
        # Simulate typing "help" + ENTER
        badge.keyboard.keybuffer.extend(["h", "e", "l", "p", badge.keyboard.ENTER])
        
        # Mock shell.run_command to see if it's called
        # We need to do this BEFORE processing ENTER
        app.shell = MagicMock()
        
        # Run loop
        for _ in range(5):
            app.run_foreground()
        
        app.shell.run_command.assert_called_with("help")
        assert app.current_cmd == ""

def test_shell_gui_backspace(gui_app):
    app, badge = gui_app
    
    with patch("lvgl.textarea") as mock_ta_class, \
         patch("lvgl.style_t"), \
         patch("asyncio.create_task"), \
         patch("ui.page.Page.replace_screen"):
        
        mock_ta = mock_ta_class.return_value
        app.switch_to_foreground()
        
        app.current_cmd = "abc"
        badge.keyboard.keybuffer.append(badge.keyboard.BS)
        
        app.run_foreground()
        
        assert app.current_cmd == "ab"
        mock_ta.del_char.assert_called_once()
