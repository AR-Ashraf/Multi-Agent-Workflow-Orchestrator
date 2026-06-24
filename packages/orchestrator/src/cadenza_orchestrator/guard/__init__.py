"""Injection guard — screens ALL tool/web output before agents act on it (§9)."""

from .injection import ScreenResult, screen_content

__all__ = ["ScreenResult", "screen_content"]
