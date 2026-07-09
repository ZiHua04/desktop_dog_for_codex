from __future__ import annotations

import ctypes
import sys
from collections.abc import Callable
from ctypes import wintypes

import pygame


class DesktopPetWindow:
    """把 pygame 窗口改造成桌宠窗口。

    这个类只处理操作系统窗口特性：
    1. 用颜色键让背景透明；
    2. 让窗口保持置顶；
    3. 在狗之外返回 HTTRANSPARENT，让点击交给背后的应用。

    注意：不要动态开启 WS_EX_TRANSPARENT。它会让整个窗口直接跳过鼠标事件，
    很容易导致 pygame 收不到 MOUSEBUTTONDOWN，于是狗就拖不动了。
    """

    def __init__(self, screen: pygame.Surface, transparent_color: tuple[int, int, int]) -> None:
        self.screen = screen
        self.transparent_color = transparent_color
        self._hit_test: Callable[[tuple[int, int]], bool] = lambda _pos: False
        self._enabled = sys.platform == "win32"
        self._hwnd: int | None = None
        self._old_wnd_proc: int | None = None
        self._wnd_proc_ref = None

        if self._enabled:
            self._setup_windows_window()

    def set_hit_test(self, hit_test: Callable[[tuple[int, int]], bool]) -> None:
        """设置点击区域判断函数。

        hit_test 返回 True 表示当前位置属于狗，窗口接收鼠标事件；
        返回 False 表示当前位置是透明背景，点击透传给背后的应用。
        """

        self._hit_test = hit_test

    def clear(self) -> None:
        """用透明色清屏。经过颜色键处理后，这个背景在桌面上不可见。"""

        self.screen.fill(self.transparent_color)

    def close(self) -> None:
        """退出前还原窗口过程，避免 Python 回调销毁后 Windows 继续调用。"""

        if not self._enabled or self._hwnd is None or self._old_wnd_proc is None:
            return

        _set_window_long_ptr(self._hwnd, GWLP_WNDPROC, self._old_wnd_proc)
        self._old_wnd_proc = None
        self._wnd_proc_ref = None

    def _setup_windows_window(self) -> None:
        info = pygame.display.get_wm_info()
        self._hwnd = info.get("window")
        if self._hwnd is None:
            self._enabled = False
            return

        self._make_layered_transparent()
        self._make_topmost_tool_window()
        self._install_hit_test_hook()

    def _make_layered_transparent(self) -> None:
        assert self._hwnd is not None

        style = _get_window_long_ptr(self._hwnd, GWL_EXSTYLE)
        style = (style | WS_EX_LAYERED) & ~WS_EX_APPWINDOW
        _set_window_long_ptr(self._hwnd, GWL_EXSTYLE, style)

        r, g, b = self.transparent_color
        color_key = r | (g << 8) | (b << 16)
        user32.SetLayeredWindowAttributes(self._hwnd, color_key, 0, LWA_COLORKEY)

    def _make_topmost_tool_window(self) -> None:
        assert self._hwnd is not None

        style = _get_window_long_ptr(self._hwnd, GWL_EXSTYLE)
        style = (style | WS_EX_TOOLWINDOW | WS_EX_LAYERED) & ~WS_EX_APPWINDOW
        _set_window_long_ptr(self._hwnd, GWL_EXSTYLE, style)

        user32.SetWindowPos(
            self._hwnd,
            HWND_TOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )

    def set_topmost(self, enabled: bool) -> None:
        if not self._enabled or self._hwnd is None:
            return

        user32.SetWindowPos(
            self._hwnd,
            HWND_TOPMOST if enabled else HWND_NOTOPMOST,
            0,
            0,
            0,
            0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_FRAMECHANGED,
        )

    def _install_hit_test_hook(self) -> None:
        assert self._hwnd is not None

        def wnd_proc(hwnd: int, msg: int, w_param: int, l_param: int) -> int:
            if msg == WM_NCHITTEST:
                pos = _screen_point_to_client(hwnd, l_param)
                if self._hit_test(pos):
                    return HTCLIENT
                return HTTRANSPARENT

            assert self._old_wnd_proc is not None
            return user32.CallWindowProcW(self._old_wnd_proc, hwnd, msg, w_param, l_param)

        self._wnd_proc_ref = WNDPROC(wnd_proc)
        self._old_wnd_proc = _set_window_long_ptr(
            self._hwnd,
            GWLP_WNDPROC,
            ctypes.cast(self._wnd_proc_ref, ctypes.c_void_p).value,
        )


def _screen_point_to_client(hwnd: int, l_param: int) -> tuple[int, int]:
    # lParam 里低 16 位是屏幕 x，高 16 位是屏幕 y，都要按有符号数解释。
    x = ctypes.c_short(l_param & 0xFFFF).value
    y = ctypes.c_short((l_param >> 16) & 0xFFFF).value
    point = wintypes.POINT(x, y)
    user32.ScreenToClient(hwnd, ctypes.byref(point))
    return point.x, point.y


def _get_window_long_ptr(hwnd: int, index: int) -> int:
    return int(GetWindowLongPtrW(hwnd, index))


def _set_window_long_ptr(hwnd: int, index: int, value: int) -> int:
    return int(SetWindowLongPtrW(hwnd, index, value))


user32 = ctypes.windll.user32 if sys.platform == "win32" else None

GWLP_WNDPROC = -4
GWL_EXSTYLE = -20

WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000

LWA_COLORKEY = 0x00000001

HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020

WM_NCHITTEST = 0x0084
HTCLIENT = 1
HTTRANSPARENT = -1

if sys.platform == "win32":
    LONG_PTR = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
    LRESULT = LONG_PTR
    WPARAM = ctypes.c_uint64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_uint
    LPARAM = LONG_PTR

    WNDPROC = ctypes.WINFUNCTYPE(
        LRESULT,
        wintypes.HWND,
        wintypes.UINT,
        WPARAM,
        LPARAM,
    )

    GetWindowLongPtrW = user32.GetWindowLongPtrW
    GetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int)
    GetWindowLongPtrW.restype = LONG_PTR

    SetWindowLongPtrW = user32.SetWindowLongPtrW
    SetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int, LONG_PTR)
    SetWindowLongPtrW.restype = LONG_PTR

    user32.SetLayeredWindowAttributes.argtypes = (
        wintypes.HWND,
        wintypes.COLORREF,
        wintypes.BYTE,
        wintypes.DWORD,
    )
    user32.SetLayeredWindowAttributes.restype = wintypes.BOOL

    user32.SetWindowPos.argtypes = (
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    )
    user32.SetWindowPos.restype = wintypes.BOOL

    user32.CallWindowProcW.argtypes = (
        LONG_PTR,
        wintypes.HWND,
        wintypes.UINT,
        WPARAM,
        LPARAM,
    )
    user32.CallWindowProcW.restype = LRESULT

    user32.ScreenToClient.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.POINT))
    user32.ScreenToClient.restype = wintypes.BOOL
