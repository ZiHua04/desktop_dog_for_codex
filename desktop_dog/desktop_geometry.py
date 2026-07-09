from __future__ import annotations

import ctypes
import sys

import pygame


def get_virtual_desktop_rect() -> pygame.Rect:
    """Return the full Windows virtual desktop rect.

    pygame.display.get_desktop_sizes()[0] only describes one display. On multi-monitor
    setups that makes the pet window too small, so dragging feels clipped.
    """

    if sys.platform != "win32":
        size = pygame.display.get_desktop_sizes()[0]
        return pygame.Rect(0, 0, size[0], size[1])

    user32 = ctypes.windll.user32
    left = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    top = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    return pygame.Rect(left, top, width, height)
