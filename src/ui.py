"""Janela do overlay (Tkinter): sem borda, sempre no topo, arrastável, não rouba foco do jogo."""
import json
import queue
import time
import tkinter as tk

from PIL import ImageTk

import config
import dbg
import engine as tl
import hotkeys
import i18n
import render
import scanner
import winutil


class App:
    def __init__(self, cfg):
        self.cfg = cfg
        self.S = i18n.STR.get(cfg.get("ui_language", "pt"), i18n.STR["pt"])
        with open(config.path("data", "bosses.json"), encoding="utf-8") as f:
            catalog = json.load(f)

        self.root = tk.Tk()
        self.root.title("Nightreign Overlay")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        hexkey = "#%02x%02x%02x" % render.KEY
        self.root.configure(bg=hexkey)
        self.root.attributes("-transparentcolor", hexkey)
        try:
            self.root.attributes("-alpha", float(cfg.get("opacity", 0.97)))
        except Exception:
            pass
        try:
            self.root.iconbitmap(config.path("assets", "icon.ico"))
        except Exception:
            pass

        sw, _ = winutil.screen_size()
        self.r = render.Renderer(config.path("assets", "hud.png"), cfg, sw)
        self.label = tk.Label(self.root, bd=0, highlightthickness=0, bg=hexkey, cursor="fleur")
        self.label.pack()
        self._place()

        self.tl = tl.Timeline(cfg)
        self.q = queue.Queue()
        self.plan = scanner.Plan()
        self.ocr_ok, self.ocr_msg = None, ""
        self.hidden = False
        self.scanner = scanner.Scanner(cfg, catalog, self.plan, self.q)
        self.hk = hotkeys.Hotkeys(cfg["hotkeys"], self.q)

        self._drag = None
        for ev, fn in (("<ButtonPress-1>", self._press), ("<B1-Motion>", self._motion),
                       ("<ButtonRelease-1>", self._release), ("<Button-3>", self._menu)):
            self.label.bind(ev, fn)
        self._build_menu()
        self.hwnd = winutil.make_overlay_window(self.root)

    # ---------------- posição ----------------
    def _place(self):
        wx, wy, ww, wh = winutil.work_area()
        pos = self.cfg.get("position")
        if pos and wx - 50 <= pos[0] <= wx + ww - 60 and wy - 20 <= pos[1] <= wy + wh - 40:
            x, y = int(pos[0]), int(pos[1])
        else:  # padrão: canto inferior direito
            m = int(self.cfg.get("margin", 24))
            x, y = wx + ww - self.r.W - m, wy + wh - self.r.H - m
        self.root.geometry("%dx%d+%d+%d" % (self.r.W, self.r.H, x, y))

    def _press(self, e):
        self._drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def _motion(self, e):
        if self._drag:
            self.root.geometry("+%d+%d" % (e.x_root - self._drag[0], e.y_root - self._drag[1]))

    def _release(self, _):
        if self._drag:
            self._drag = None
            self.cfg["position"] = [self.root.winfo_x(), self.root.winfo_y()]
            saved = config.load()
            saved["position"] = self.cfg["position"]
            config.save(saved)

    # ---------------- menu / ações ----------------
    def _build_menu(self):
        S = self.S
        m = tk.Menu(self.root, tearoff=0)
        for key, act in (("menu_pause", "pause"), ("menu_reset", "reset"), ("menu_next", "next"),
                         ("menu_prev", "prev"), ("menu_hide", "toggle")):
            m.add_command(label="%s    [%s]" % (S[key], self.cfg["hotkeys"][act]),
                          command=lambda a=act: self.action(a))
        m.add_separator()
        m.add_command(label="%s    [%s]" % (S["menu_quit"], self.cfg["hotkeys"]["quit"]),
                      command=lambda: self.action("quit"))
        self.menu = m

    def _menu(self, e):
        try:
            self.menu.tk_popup(e.x_root, e.y_root)
        finally:
            self.menu.grab_release()

    def action(self, act):
        t = self.tl
        if act == "pause":
            t.toggle_pause()
        elif act == "reset":
            t.reset()
        elif act == "next":
            t.manual_next()
        elif act == "prev":
            t.manual_prev()
        elif act == "toggle":
            self.hidden = not self.hidden
            (self.root.withdraw if self.hidden else self.root.deiconify)()
            if not self.hidden:
                winutil.keep_on_top(self.hwnd)
        elif act == "quit":
            self.quit()
        self._sync_plan()

    # ---------------- ciclo principal ----------------
    def _sync_plan(self):
        w = self.tl.wants()
        if self.hidden:
            w = {k: False for k in w}
        self.plan.wants = w
        self.plan.expected_day = self.tl.expected_banner()
        self.plan.day = self.tl.day
        self.plan.day_age = self.tl.day_age()

    def _drain(self):
        try:
            while True:
                ev = self.q.get_nowait()
                kind = ev[0]
                if kind == "banner":
                    self.tl.on_banner(ev[1])
                elif kind == "signal":
                    self.tl.on_signal(ev[1])
                elif kind == "boss":
                    self.tl.on_boss(ev[1])
                elif kind == "hk":
                    self.action(ev[1])
                elif kind == "ocr":
                    self.ocr_ok, self.ocr_msg = ev[1], ev[2]
                elif kind == "hotkey_fail":
                    dbg.log("atalhos indisponíveis (em uso por outro app): %s" % ev[1])
        except queue.Empty:
            pass

    def _tick(self):
        try:
            self._drain()
            self.tl.tick()
            self._sync_plan()
            if not self.hidden:
                v = self.tl.view()
                if self.ocr_ok is False:
                    status = "no_ocr"
                elif v["paused"]:
                    status = "paused"
                else:
                    status = "reading"
                img, changed = self.r.render(v, status)
                if changed:
                    self._photo = ImageTk.PhotoImage(img)
                    self.label.configure(image=self._photo)
            now = time.monotonic()
            if now - getattr(self, "_top_t", 0) > 2.0 and not self.hidden:
                self._top_t = now
                winutil.keep_on_top(self.hwnd)
        except Exception as e:  # nunca derruba o overlay
            dbg.log("erro na UI: %r" % (e,))
        if self.plan.alive:
            self.root.after(250, self._tick)

    def quit(self):
        self.plan.alive = False
        try:
            self.hk.stop()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.scanner.start()
        self.hk.start()
        self._sync_plan()
        self._tick()
        self.root.mainloop()
