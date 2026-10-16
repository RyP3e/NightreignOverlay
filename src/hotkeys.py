"""Atalhos globais via RegisterHotKey (não precisa de admin nem de bibliotecas extras)."""
import ctypes
import threading

import winutil

VK = {"F%d" % i: 0x6F + i for i in range(1, 25)}
VK.update({chr(c): c for c in range(ord("A"), ord("Z") + 1)})
VK.update({str(i): 0x30 + i for i in range(10)})
VK.update({"INSERT": 0x2D, "DELETE": 0x2E, "HOME": 0x24, "END": 0x23, "PAGEUP": 0x21, "PAGEDOWN": 0x22,
           "PAUSE": 0x13, "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27})
MODS = {"ALT": 1, "CTRL": 2, "CONTROL": 2, "SHIFT": 4, "WIN": 8}


def parse(spec):
    mods, vk = 0x4000, None  # MOD_NOREPEAT
    for part in spec.upper().replace(" ", "").split("+"):
        if part in MODS:
            mods |= MODS[part]
        elif part in VK:
            vk = VK[part]
    return (mods, vk) if vk else None


class Hotkeys(threading.Thread):
    def __init__(self, mapping, out_q):
        super().__init__(daemon=True, name="hotkeys")
        self.mapping, self.q = mapping, out_q
        self.tid = None
        self.failed = []

    def run(self):
        if not winutil.IS_WIN:
            return
        u32 = ctypes.windll.user32
        k32 = ctypes.windll.kernel32
        self.tid = k32.GetCurrentThreadId()
        ids = {}
        for i, (action, spec) in enumerate(self.mapping.items(), start=1):
            p = parse(spec)
            if p and u32.RegisterHotKey(None, i, p[0], p[1]):
                ids[i] = action
            else:
                self.failed.append(spec)
        if self.failed:
            self.q.put(("hotkey_fail", ", ".join(self.failed)))
        from ctypes import wintypes
        msg = wintypes.MSG()
        while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == 0x0312 and msg.wParam in ids:  # WM_HOTKEY
                self.q.put(("hk", ids[msg.wParam]))
        for i in ids:
            u32.UnregisterHotKey(None, i)

    def stop(self):
        if self.tid and winutil.IS_WIN:
            ctypes.windll.user32.PostThreadMessageW(self.tid, 0x0012, 0, 0)  # WM_QUIT
