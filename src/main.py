import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config  # noqa: E402
import dbg  # noqa: E402
import winutil  # noqa: E402


def selftest():
    """Usado pelo instalador: confirma que o executável abre e importa tudo. Exit 0 = ok."""
    out = []
    code = 0
    try:
        import json
        import mss  # noqa: F401
        import numpy  # noqa: F401
        import tkinter  # noqa: F401
        from PIL import ImageTk  # noqa: F401
        import capture, detect, engine, hotkeys, ocr, render, scanner, ui  # noqa: F401
        json.load(open(config.path("data", "bosses.json"), encoding="utf-8"))
        out.append("imports ok")
        eng, msg = ocr.create(config.load()["ocr_languages"])
        out.append("OCR: %s" % msg)
    except Exception as e:
        code = 2
        out.append("ERRO: %r" % (e,))
    try:
        os.makedirs(config.path("logs"), exist_ok=True)
        with open(config.path("logs", "selftest.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(out))
    except Exception:
        pass
    print("\n".join(out))
    return code


def main():
    if "--selftest" in sys.argv:
        return selftest()
    cfg = config.load()
    if "--debug" in sys.argv:
        cfg["debug"] = True
    dbg.enable(cfg.get("debug"))
    if not winutil.single_instance():
        return 0
    winutil.set_dpi_aware()
    winutil.lower_priority()
    import ui
    ui.App(cfg).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
