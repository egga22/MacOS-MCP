"""MacOS automation MCP server built with FastMCP."""

from __future__ import annotations

import base64
import importlib
import io
from types import ModuleType
from typing import List, Optional, Sequence

from fastmcp import FastMCP

_pyautogui_spec = importlib.util.find_spec("pyautogui")
if _pyautogui_spec is not None:
    pyautogui = importlib.import_module("pyautogui")
else:  # pragma: no cover - informative import failure
    pyautogui = None

# Configure PyAutoGUI for predictable behaviour.
if pyautogui is not None:
    pyautogui.FAILSAFE = True  # Move the cursor to the top-left corner to abort.
    pyautogui.PAUSE = 0.05

mcp = FastMCP("MacOS Automation Server")


def _normalize_button(button: str) -> str:
    normalized = button.lower()
    if normalized not in {"left", "right", "middle"}:
        raise ValueError("Button must be 'left', 'right', or 'middle'.")
    return normalized


def _require_pyautogui() -> ModuleType:
    if pyautogui is None:  # pragma: no cover - informative import failure
        raise RuntimeError(
            "pyautogui is required for the MacOS automation MCP server. Install it with 'pip install pyautogui'."
        )
    return pyautogui


@mcp.tool
def get_screenshot(region: Optional[Sequence[int]] = None) -> str:
    """Return a PNG screenshot encoded as a data URL.

    If ``region`` is provided, it must contain ``[x, y, width, height]`` values.
    """

    if region is not None and len(region) != 4:
        raise ValueError("Region must contain exactly four integers: x, y, width, height.")

    module = _require_pyautogui()
    region_tuple = tuple(int(value) for value in region) if region is not None else None
    screenshot = module.screenshot(region=region_tuple)
    buffer = io.BytesIO()
    screenshot.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


@mcp.tool
def move_mouse(x: int, y: int, duration: float = 0.0) -> str:
    """Move the mouse cursor to ``(x, y)`` over ``duration`` seconds."""

    module = _require_pyautogui()
    module.moveTo(x, y, duration=max(0.0, duration))
    return f"Mouse moved to ({x}, {y})."


@mcp.tool
def click(
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    clicks: int = 1,
    interval: float = 0.0,
    duration: float = 0.0,
) -> str:
    """Click the specified mouse button.

    If ``x`` and ``y`` are provided the click occurs at that location.
    """

    module = _require_pyautogui()
    module.click(
        x=x,
        y=y,
        clicks=max(1, clicks),
        interval=max(0.0, interval),
        button=_normalize_button(button),
        duration=max(0.0, duration),
    )
    location = f"({x}, {y})" if x is not None and y is not None else "current position"
    return f"Clicked {button} button {clicks} time(s) at {location}."


@mcp.tool
def press_key(key: str, modifiers: Optional[List[str]] = None) -> str:
    """Press a keyboard key, optionally including modifier keys."""

    module = _require_pyautogui()
    if modifiers:
        sequence = [modifier.lower() for modifier in modifiers] + [key]
        module.hotkey(*sequence)
        pressed = " + ".join(sequence)
    else:
        module.press(key)
        pressed = key
    return f"Pressed {pressed}."


@mcp.tool
def type_text(text: str, interval: float = 0.0, press_enter: bool = False) -> str:
    """Type the provided text with an optional delay between characters."""

    module = _require_pyautogui()
    module.write(text, interval=max(0.0, interval))
    if press_enter:
        module.press("enter")
    return "Typed text successfully." if not press_enter else "Typed text and pressed Enter successfully."


@mcp.tool
def drag_and_drop(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration: float = 0.5,
    button: str = "left",
) -> str:
    """Drag from the start coordinates to the end coordinates using the given mouse button."""

    normalized_button = _normalize_button(button)
    module = _require_pyautogui()
    module.moveTo(start_x, start_y)
    module.mouseDown(button=normalized_button)
    module.moveTo(end_x, end_y, duration=max(0.0, duration))
    module.mouseUp(button=normalized_button)
    return (
        f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y}) using the {normalized_button} button."
    )


if __name__ == "__main__":
    mcp.run()
