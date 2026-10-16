import os
import time

import config

_enabled = False


def enable(flag):
    global _enabled
    _enabled = bool(flag)
    if _enabled:
        os.makedirs(config.path("logs"), exist_ok=True)
        os.makedirs(config.path("debug"), exist_ok=True)


def log(msg):
    if not _enabled:
        return
    try:
        p = config.path("logs", "overlay.log")
        if os.path.exists(p) and os.path.getsize(p) > 512 * 1024:
            os.remove(p)
        with open(p, "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (time.strftime("%H:%M:%S"), msg))
    except Exception:
        pass


def save_crop(name, gray_or_bgra):
    if not _enabled:
        return
    try:
        from PIL import Image
        a = gray_or_bgra
        im = Image.fromarray(a[..., [2, 1, 0]]) if a.ndim == 3 else Image.fromarray(a)
        im.save(config.path("debug", name + ".png"))
    except Exception:
        pass
