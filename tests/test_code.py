# Framework: pytest + unittest.mock
# These tests target the MacOS automation MCP server functions in code.py.
# They mock pyautogui and stub FastMCP, focusing on behaviors added/changed in the diff.

import builtins
import base64
import io
import sys
import types
from pathlib import Path
from unittest import mock
import importlib.util
import pytest

CODE_PATH = Path(__file__).resolve().parents[1] / "code.py"

# If the target module isn't present (e.g., partial checkout), skip gracefully.

if not CODE_PATH.is_file():
    pytest.skip("code.py not found at repository root; tests require the PR-changed file.", allow_module_level=True)

class FastMCPStub:
    def __init__(self, *_args, **_kwargs): pass
    def tool(self, fn): return fn
    def run(self): pass

def _make_pyautogui_fake():
    fake = types.SimpleNamespace()
    fake.FAILSAFE = None
    fake.PAUSE = None
    fake.screenshot = mock.Mock(name="screenshot")
    fake.moveTo = mock.Mock(name="moveTo")
    fake.click = mock.Mock(name="click")
    fake.press = mock.Mock(name="press")
    fake.hotkey = mock.Mock(name="hotkey")
    fake.write = mock.Mock(name="write")
    fake.mouseDown = mock.Mock(name="mouseDown")
    fake.mouseUp = mock.Mock(name="mouseUp")
    return fake

def _load_module_with_stubs(module_name="macos_automation_test"):
    # Ensure clean slate

    for key in [module_name, "pyautogui", "fastmcp"]:
        sys.modules.pop(key, None)

    fake_pyautogui = _make_pyautogui_fake()
    sys.modules["pyautogui"] = fake_pyautogui
    sys.modules["fastmcp"] = types.SimpleNamespace(FastMCP=FastMCPStub)

    spec = importlib.util.spec_from_file_location(module_name, str(CODE_PATH))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod, fake_pyautogui

@pytest.fixture()
def module_and_pyautogui():
    mod, fake = _load_module_with_stubs()
    try:
        yield mod, fake
    finally:
        for key in ["pyautogui", "fastmcp", "macos_automation_test"]:
            sys.modules.pop(key, None)

def test_pyautogui_configuration_set_on_import(module_and_pyautogui):
    mod, fake = module_and_pyautogui
    assert fake.FAILSAFE is True
    assert fake.PAUSE == 0.05

def test_normalize_button_valid_cases(module_and_pyautogui):
    mod, _ = module_and_pyautogui
    assert mod._normalize_button("left") == "left"
    assert mod._normalize_button("RIGHT") == "right"
    assert mod._normalize_button("Middle") == "middle"

@pytest.mark.parametrize("bad", ["", "primary", "LEFTCLICK", "l3ft", "None"])
def test_normalize_button_invalid_raises(module_and_pyautogui, bad):
    mod, _ = module_and_pyautogui
    with pytest.raises(ValueError, match="Button must be 'left', 'right', or 'middle'\\."):
        mod._normalize_button(bad)

def test_get_screenshot_fullscreen_encodes_data_url(module_and_pyautogui):
    mod, fake = module_and_pyautogui

    class FakeImage:
        def __init__(self, data=b"\x89PNG\r\nTESTDATA"): self.data = data
        def save(self, buf, format="PNG"):
            assert isinstance(buf, io.BytesIO)
            assert format == "PNG"
            buf.write(self.data)

    fake.screenshot.return_value = FakeImage()
    data_url = mod.get_screenshot()
    assert data_url.startswith("data:image/png;base64,")
    payload = data_url.split(",", 1)[1]
    assert base64.b64decode(payload) == b"\x89PNG\r\nTESTDATA"
    fake.screenshot.assert_called_once_with(region=None)

def test_get_screenshot_with_region_and_type_casting(module_and_pyautogui):
    mod, fake = module_and_pyautogui

    class Img:
        def save(self, buf, format="PNG"):
            _ = format
            buf.write(b"X")

    fake.screenshot.return_value = Img()
    data_url = mod.get_screenshot(region=["10", "20", "300", "400"])
    assert data_url.startswith("data:image/png;base64,")
    fake.screenshot.assert_called_once_with(region=(10, 20, 300, 400))

@pytest.mark.parametrize("bad_region", [[], [1,2,3], [1,2,3,4,5]])
def test_get_screenshot_bad_region_raises(module_and_pyautogui, bad_region):
    mod, _ = module_and_pyautogui
    with pytest.raises(ValueError, match="Region must contain exactly four integers"):
        mod.get_screenshot(region=bad_region)

def test_move_mouse_clamps_negative_duration(module_and_pyautogui):
    mod, fake = module_and_pyautogui
    msg = mod.move_mouse(100, 200, duration=-5.0)
    assert msg == "Mouse moved to (100, 200)."
    fake.moveTo.assert_called_once_with(100, 200, duration=0.0)

def test_click_defaults_current_position_and_clamping(module_and_pyautogui):
    mod, fake = module_and_pyautogui
    msg = mod.click(clicks=0, interval=-1.5, duration=-2.0)
    assert msg == "Clicked left button 0 time(s) at current position."
    fake.click.assert_called_once_with(
        x=None, y=None, clicks=1, interval=0.0, button="left", duration=0.0
    )

def test_click_with_coordinates_and_right_button(module_and_pyautogui):
    mod, fake = module_and_pyautogui
    msg = mod.click(x=10, y=20, button="RIGHT", clicks=2, interval=0.1, duration=0.2)
    assert msg == "Clicked RIGHT button 2 time(s) at (10, 20)."
    fake.click.assert_called_once_with(
        x=10, y=20, clicks=2, interval=0.1, button="right", duration=0.2
    )

def test_click_invalid_button_bubbles_error(module_and_pyautogui):
    mod, _ = module_and_pyautogui
    with pytest.raises(ValueError):
        mod.click(button="invalid")

def test_press_key_without_modifiers(module_and_pyautogui):
    mod, fake = module_and_pyautogui
    msg = mod.press_key("enter")
    assert msg == "Pressed enter."
    fake.press.assert_called_once_with("enter")
    fake.hotkey.assert_not_called()

def test_press_key_with_modifiers_lowercased_sequence(module_and_pyautogui):
    mod, fake = module_and_pyautogui
    msg = mod.press_key("k", modifiers=["CTRL", "Alt"])
    assert msg == "Pressed ctrl + alt + k."
    fake.hotkey.assert_called_once_with("ctrl", "alt", "k")
    fake.press.assert_not_called()

def test_type_text_simple_and_with_enter(module_and_pyautogui):
    mod, fake = module_and_pyautogui
    msg = mod.type_text("Hello", interval=0.0, press_enter=False)
    assert msg == "Typed text successfully."
    fake.write.assert_called_with("Hello", interval=0.0)
    fake.press.assert_not_called()

    fake.write.reset_mock()
    fake.press.reset_mock()

    msg2 = mod.type_text("World", interval=-0.5, press_enter=True)
    assert msg2 == "Typed text and pressed Enter successfully."
    fake.write.assert_called_with("World", interval=0.0)
    fake.press.assert_called_once_with("enter")

def test_drag_and_drop_happy_path_and_clamping(module_and_pyautogui):
    mod, fake = module_and_pyautogui
    msg = mod.drag_and_drop(0, 1, 100, 200, duration=-1.0, button="Middle")
    assert msg == "Dragged from (0, 1) to (100, 200) using the middle button."
    fake.moveTo.assert_any_call(0, 1)
    fake.mouseDown.assert_called_once_with(button="middle")
    fake.moveTo.assert_any_call(100, 200, duration=0.0)
    fake.mouseUp.assert_called_once_with(button="middle")

def test_drag_and_drop_invalid_button_raises(module_and_pyautogui):
    mod, _ = module_and_pyautogui
    with pytest.raises(ValueError):
        mod.drag_and_drop(0, 0, 1, 1, button="bad")

def test_pyautogui_import_failure_message_is_informative(monkeypatch):
    # Force ImportError for pyautogui during module execution
    sys.modules.pop("pyautogui", None)

    def failing_import(name, *args, **kwargs):
        if name == "pyautogui":
            raise ModuleNotFoundError
        return original_import(name, *args, **kwargs)

    original_import = builtins.__import__
    try:
        monkeypatch.setattr(builtins, "__import__", failing_import)
        # Stub FastMCP so 'from fastmcp import FastMCP' succeeds
        sys.modules["fastmcp"] = types.SimpleNamespace(FastMCP=FastMCPStub)
        mod_name = "macos_automation_import_fail"
        spec = importlib.util.spec_from_file_location(mod_name, str(CODE_PATH))
        mod = importlib.util.module_from_spec(spec)
        with pytest.raises(ImportError, match="pyautogui is required.*pip install pyautogui"):
            spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    finally:
        monkeypatch.setattr(builtins, "__import__", original_import)
        sys.modules.pop("fastmcp", None)