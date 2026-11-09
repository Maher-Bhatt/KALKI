"""The pet's own window: truly see-through, with no box around it.

WebView2 can't draw on a see-through background on Windows, so the pet isn't drawn by
it. The page still decides what the pet looks like, and sends each frame here. This is a
plain Windows layered window, which gets real transparency for every pixel: the desktop
shows around the pet, and clicks on empty pixels reach whatever is behind it.
"""

import base64
import ctypes
import sys
import threading
from typing import Callable, Optional, Tuple

SPRITE_SIZE = 32
CSS_SCALE = 3  # Each sprite pixel is 3 by 3 at normal display scaling.
EDGE_MARGIN = 20
DRAG_THRESHOLD = 4


def frame_to_bgra(rgba: bytes, size: int, scale: int) -> bytes:
    """Enlarge an RGBA frame into the premultiplied BGRA that Windows expects.

    Pixels are enlarged as whole blocks, so the pixel art stays sharp.
    """
    if len(rgba) != size * size * 4:
        raise ValueError("frame is the wrong size")
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            at = (y * size + x) * 4
            red, green, blue, alpha = rgba[at:at + 4]
            if alpha == 0:
                pixel = b"\0\0\0\0"
            else:
                pixel = bytes((blue * alpha // 255, green * alpha // 255, red * alpha // 255, alpha))
            row += pixel * scale
        rows.append(bytes(row) * scale)
    return b"".join(rows)


def scale_for_dpi(dpi: int) -> int:
    """Whole numbers only: a fractional scale would blur or unevenly size the pixels."""
    return max(1, round(CSS_SCALE * dpi / 96))


def card_position(pet: Tuple[int, int, int, int], card_size: Tuple[int, int],
                  work: Tuple[int, int, int, int], gap: int = 6) -> Tuple[int, int]:
    """Where the card goes: above the pet, or below it if there's no room, always on screen."""
    width, height = card_size
    x = min(pet[2] - width, work[2] - width)
    x = max(work[0], x)
    y = pet[1] - height - gap
    if y < work[1]:
        y = min(pet[3] + gap, work[3] - height)
    return x, max(work[1], y)


def use_real_pixels() -> None:
    """Make this thread work in real screen pixels, so sizes and positions agree on
    scaled displays and the pet isn't stretched and blurred by Windows."""
    try:
        function = ctypes.windll.user32.SetThreadDpiAwarenessContext
        function.argtypes = (ctypes.c_void_p,)
        function.restype = ctypes.c_void_p
        function(ctypes.c_void_p(-4))  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    except (AttributeError, OSError):
        pass  # Older Windows: it still works, just less sharply.


class PetWindow:
    """A small always-on-top window showing the frames it's given. Windows only."""

    WM_DESTROY = 0x0002
    WM_MOUSEMOVE = 0x0200
    WM_LBUTTONDOWN = 0x0201
    WM_LBUTTONUP = 0x0202
    WM_APP_PAINT = 0x8001

    def __init__(self, on_click: Callable[[], None], on_moved: Optional[Callable[[], None]] = None):
        self.on_click = on_click
        self.on_moved = on_moved
        self.hwnd = 0
        self.scale = CSS_SCALE
        self._frame: Optional[bytes] = None
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._press = None
        self._dragging = False
        self._bits = None
        self._mem_dc = None
        self._proc = None

    def start(self) -> bool:
        if sys.platform != "win32":
            return False
        threading.Thread(target=self._run, daemon=True, name="kalki-pet-window").start()
        return self._ready.wait(5) and bool(self.hwnd)

    def show(self, rgba_base64: str) -> bool:
        """Show a frame. Painting happens on the window's own thread."""
        if not self.hwnd:
            return False
        rgba = base64.b64decode(rgba_base64)
        with self._lock:
            self._frame = rgba
        ctypes.windll.user32.PostMessageW(self.hwnd, self.WM_APP_PAINT, 0, 0)
        return True

    def rect(self) -> Tuple[int, int, int, int]:
        from ctypes import wintypes
        rect = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
        return rect.left, rect.top, rect.right, rect.bottom

    @staticmethod
    def work_area() -> Tuple[int, int, int, int]:
        from ctypes import wintypes
        rect = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA
        return rect.left, rect.top, rect.right, rect.bottom

    def _run(self):
        from ctypes import wintypes
        use_real_pixels()
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        kernel32 = ctypes.windll.kernel32

        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        user32.DefWindowProcW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        user32.DefWindowProcW.restype = LRESULT
        user32.CreateWindowExW.restype = wintypes.HWND
        user32.CreateWindowExW.argtypes = (
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID)
        user32.LoadCursorW.restype = wintypes.HANDLE
        user32.LoadCursorW.argtypes = (wintypes.HINSTANCE, wintypes.LPVOID)
        user32.GetDC.restype = wintypes.HDC
        user32.GetDC.argtypes = (wintypes.HWND,)
        user32.ReleaseDC.argtypes = (wintypes.HWND, wintypes.HDC)
        user32.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        user32.SetCapture.argtypes = (wintypes.HWND,)
        user32.GetCursorPos.argtypes = (ctypes.POINTER(wintypes.POINT),)
        user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
        user32.SetWindowPos.argtypes = (wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_int, wintypes.UINT)
        gdi32.CreateCompatibleDC.restype = wintypes.HDC
        gdi32.CreateCompatibleDC.argtypes = (wintypes.HDC,)
        gdi32.SelectObject.argtypes = (wintypes.HDC, wintypes.HANDLE)
        gdi32.SelectObject.restype = wintypes.HANDLE
        gdi32.CreateDIBSection.restype = wintypes.HANDLE
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                        ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HANDLE),
                        ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HANDLE),
                        ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                        ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                        ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                        ("biClrImportant", wintypes.DWORD)]

        class BLENDFUNCTION(ctypes.Structure):
            _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                        ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]

        def cursor():
            point = wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(point))
            return point.x, point.y

        def paint():
            with self._lock:
                rgba, self._frame = self._frame, None
            if rgba is None or self._bits is None:
                return
            side = SPRITE_SIZE * self.scale
            pixels = frame_to_bgra(rgba, SPRITE_SIZE, self.scale)
            ctypes.memmove(self._bits, pixels, len(pixels))
            size = wintypes.SIZE(side, side)
            origin = wintypes.POINT(0, 0)
            blend = BLENDFUNCTION(0, 0, 255, 1)  # AC_SRC_OVER, per-pixel alpha
            screen = user32.GetDC(None)
            user32.UpdateLayeredWindow(
                wintypes.HWND(self.hwnd), screen, None, ctypes.byref(size), self._mem_dc,
                ctypes.byref(origin), 0, ctypes.byref(blend), 2)  # ULW_ALPHA
            user32.ReleaseDC(None, screen)

        def wndproc(hwnd, message, wparam, lparam):
            if message == self.WM_APP_PAINT:
                paint()
                return 0
            if message == self.WM_LBUTTONDOWN:
                user32.SetCapture(hwnd)
                left, top, _, _ = self.rect()
                self._press = (*cursor(), left, top)
                self._dragging = False
                return 0
            if message == self.WM_MOUSEMOVE and self._press:
                x, y = cursor()
                start_x, start_y, left, top = self._press
                if self._dragging or abs(x - start_x) > DRAG_THRESHOLD or abs(y - start_y) > DRAG_THRESHOLD:
                    self._dragging = True
                    # SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE
                    user32.SetWindowPos(hwnd, None, left + x - start_x, top + y - start_y, 0, 0, 0x0001 | 0x0004 | 0x0010)
                return 0
            if message == self.WM_LBUTTONUP and self._press:
                user32.ReleaseCapture()
                self._press = None
                callback = self.on_moved if self._dragging else self.on_click
                if callback:
                    threading.Thread(target=callback, daemon=True).start()
                return 0
            if message == self.WM_DESTROY:
                user32.PostQuitMessage(0)
                return 0
            return user32.DefWindowProcW(hwnd, message, wparam, lparam)

        self._proc = WNDPROC(wndproc)
        instance = kernel32.GetModuleHandleW(None)
        window_class = WNDCLASSW()
        window_class.lpfnWndProc = self._proc
        window_class.hInstance = instance
        window_class.hCursor = user32.LoadCursorW(None, ctypes.c_void_p(32649))  # IDC_HAND
        window_class.lpszClassName = "KalkiPetWindow"
        user32.RegisterClassW(ctypes.byref(window_class))

        dpi = 96
        try:
            dpi = user32.GetDpiForSystem() or 96
        except AttributeError:
            pass
        self.scale = scale_for_dpi(dpi)
        side = SPRITE_SIZE * self.scale
        area = self.work_area()
        margin = EDGE_MARGIN * dpi // 96

        # WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_TOPMOST | WS_EX_NOACTIVATE, WS_POPUP
        hwnd = user32.CreateWindowExW(
            0x00080000 | 0x00000080 | 0x00000008 | 0x08000000, "KalkiPetWindow", "KALKI Pet", 0x80000000,
            area[2] - side - margin, area[3] - side - margin, side, side, None, None, instance, None)
        if not hwnd:
            self._ready.set()
            return

        info = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), side, -side, 1, 32, 0, 0, 0, 0, 0, 0)
        bits = ctypes.c_void_p()
        screen = user32.GetDC(None)
        self._mem_dc = gdi32.CreateCompatibleDC(screen)
        bitmap = gdi32.CreateDIBSection(screen, ctypes.byref(info), 0, ctypes.byref(bits), None, 0)
        gdi32.SelectObject(self._mem_dc, bitmap)
        user32.ReleaseDC(None, screen)
        self._bits = bits
        self.hwnd = hwnd
        user32.ShowWindow(wintypes.HWND(hwnd), 8)  # SW_SHOWNA
        self._ready.set()

        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
