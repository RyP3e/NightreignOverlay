"""Utilidades Windows via ctypes (sem dependências extras). Tudo é opcional/tolerante a falhas."""
import ctypes
import os
import sys

IS_WIN = sys.platform == "win32"
if IS_WIN:
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32


def set_dpi_aware():
    if not IS_WIN:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def lower_priority():
    """Prioridade abaixo do normal: o overlay nunca disputa CPU com o jogo."""
    if not IS_WIN:
        return
    try:
        kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), 0x00004000)  # BELOW_NORMAL
    except Exception:
        pass


def single_instance(name="Local\\NightreignOverlay"):
    if not IS_WIN:
        return True
    try:
        h = kernel32.CreateMutexW(None, False, name)
        return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return True


def screen_size():
    if not IS_WIN:
        return 1920, 1080
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def make_overlay_window(tk_root):
    """Não rouba foco, não aparece na barra de tarefas/Alt-Tab, fica sempre por cima."""
    if not IS_WIN:
        return None
    try:
        tk_root.update_idletasks()
        hwnd = user32.GetParent(tk_root.winfo_id()) or tk_root.winfo_id()
        GWL_EXSTYLE = -20
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex |= 0x08000000 | 0x00000080  # WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
        return hwnd
    except Exception:
        return None


def keep_on_top(hwnd):
    if not (IS_WIN and hwnd):
        return
    try:
        # HWND_TOPMOST=-1; SWP_NOMOVE|NOSIZE|NOACTIVATE|SHOWWINDOW = 0x2|0x1|0x10|0x40
        user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010 | 0x0040)
    except Exception:
        pass


def find_game_client_rect(process_name):
    """Retângulo (x, y, w, h) da área de cliente da janela do jogo, ou None."""
    if not IS_WIN or not process_name:
        return None
    target = process_name.lower()
    found = []

    EnumProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, _):
        try:
            if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            h = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return True
            buf = ctypes.create_unicode_buffer(520)
            size = wintypes.DWORD(520)
            ok = kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
            kernel32.CloseHandle(h)
            if ok and os.path.basename(buf.value).lower() == target:
                rc = wintypes.RECT()
                user32.GetClientRect(hwnd, ctypes.byref(rc))
                pt = wintypes.POINT(0, 0)
                user32.ClientToScreen(hwnd, ctypes.byref(pt))
                w, h2 = rc.right - rc.left, rc.bottom - rc.top
                if w > 300 and h2 > 200:
                    found.append((pt.x, pt.y, w, h2))
        except Exception:
            pass
        return True

    try:
        user32.EnumWindows(EnumProc(cb), 0)
    except Exception:
        return None
    return found[0] if found else None


def work_area():
    """Área útil da tela (sem a barra de tarefas): (x, y, w, h)."""
    if IS_WIN:
        try:
            rc = wintypes.RECT()
            if user32.SystemParametersInfoW(48, 0, ctypes.byref(rc), 0):  # SPI_GETWORKAREA
                return rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top
        except Exception:
            pass
    w, h = screen_size()
    return 0, 0, w, h
