"""
NIGHTREIGN OVERLAY
Overlay de cronometro das fases do dia para Elden Ring Nightreign.

Nao toca no jogo: apenas captura a tela (como o OBS) e le os textos por OCR.
Funciona com o jogo em PT-BR ou EN.  Use o jogo em "Janela sem bordas".
"""
import json
import os
import sys
import threading
import time
import ctypes
import tkinter as tk

from nr_logic import (Tracker, detect_message, parse_day, fmt, ROMAN,
                      IDLE, EXPLORE, CIRCLE1, CIRCLE2, BOSS, FINAL, FINISHED)

IS_WIN = sys.platform == "win32"


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(app_dir(), "config.json")
LOG_PATH = os.path.join(app_dir(), "nightreign_overlay.log")

DEFAULT_CONFIG = {
    "monitor": 1,                       # 1 = monitor principal
    "window_title": "auto",             # "auto" = janela do jogo, senao tela inteira; ou parte do titulo; "" = tela inteira
    "scan_interval": 0.7,               # segundos entre leituras
    "overlay": {"x": -1, "y": -1, "opacity": 0.93, "scale": 1.0},
    "durations": {"explore": 270, "circle1_close": 180, "a_to_b": 360, "b_to_boss": 180},
    "regions": {                        # fracoes da tela: [esq, topo, dir, base]
        "banner": [0.22, 0.42, 0.78, 0.82],
        "message": [0.50, 0.08, 1.00, 0.32],
    },
    "extra_phrases": {"circle1": [], "circle2": []},
    "hotkeys": {"next_day": "F5", "move": "F6", "next_phase": "F7", "hide": "F8",
                "reset": "F9", "quit": "F10", "debug": "F11"},
}


def deep_merge(base, new):
    out = dict(base)
    for k, v in (new or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config():
    cfg = DEFAULT_CONFIG
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = deep_merge(DEFAULT_CONFIG, json.load(f))
    except FileNotFoundError:
        save_config(cfg)
    except Exception:
        pass
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def log(msg):
    try:
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > 1_000_000:
            os.remove(LOG_PATH)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + msg + "\n")
    except Exception:
        pass


# ----------------------------------------------------------------------------
# Windows helpers
# ----------------------------------------------------------------------------
if IS_WIN:
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetParent.restype = wintypes.HWND
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
    user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]

    def set_dpi_aware():
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass

    def find_window_rect(title, exact):
        found = []
        WNDENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def cb(hwnd, _lp):
            if user32.IsWindowVisible(hwnd) and not user32.IsIconic(hwnd):
                n = user32.GetWindowTextLengthW(hwnd)
                if n:
                    buf = ctypes.create_unicode_buffer(n + 1)
                    user32.GetWindowTextW(hwnd, buf, n + 1)
                    name = buf.value.lower()
                    if (name == title.lower()) if exact else (title.lower() in name):
                        found.append(hwnd)
            return True

        user32.EnumWindows(WNDENUM(cb), 0)
        for hwnd in found:
            rect = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(rect))
            pt = wintypes.POINT(0, 0)
            user32.ClientToScreen(hwnd, ctypes.byref(pt))
            if rect.right > 300 and rect.bottom > 200:
                return {"left": pt.x, "top": pt.y, "width": rect.right, "height": rect.bottom}
        return None

    def key_down(vk):
        return bool(user32.GetAsyncKeyState(vk) & 0x8000)
else:
    def set_dpi_aware():
        pass

    def find_window_rect(title, exact):
        return None

    def key_down(vk):
        return False


def vk_from_name(name):
    name = (name or "").upper().strip()
    if name.startswith("F") and name[1:].isdigit() and 1 <= int(name[1:]) <= 12:
        return 0x70 + int(name[1:]) - 1
    return None


# ----------------------------------------------------------------------------
# Leitura da tela (thread)
# ----------------------------------------------------------------------------
class Scanner(threading.Thread):
    def __init__(self, cfg, tracker, lock):
        super().__init__(daemon=True)
        self.cfg, self.tracker, self.lock = cfg, tracker, lock
        self.stop_flag = False
        self.status = "Carregando leitor de texto..."
        self.debug_text = ""
        self.source = "tela"
        self.boss_seen_frames = 0
        self.boss_missing_frames = 0
        self.boss_bar_active = False

    def run(self):
        try:
            import mss
            import numpy as np
            import cv2
            from rapidocr_onnxruntime import RapidOCR
            self.np, self.cv2 = np, cv2
            self.engine = RapidOCR()
        except Exception as e:  # dependencia faltando
            self.status = "ERRO: %s" % e
            log("Falha ao iniciar OCR: %r" % (e,))
            return
        self.status = "Lendo a tela"
        log("Scanner iniciado")
        with mss.mss() as sct:
            while not self.stop_flag:
                t0 = time.time()
                try:
                    self.scan(sct)
                except Exception as e:
                    log("Erro no scan: %r" % (e,))
                    self.status = "Erro de captura (veja o log)"
                time.sleep(max(0.05, float(self.cfg["scan_interval"]) - (time.time() - t0)))

    # --- captura -------------------------------------------------------------
    def area(self, sct):
        wt = self.cfg.get("window_title", "auto")
        rect = None
        if wt == "auto":
            rect = find_window_rect("ELDEN RING NIGHTREIGN", True)
        elif wt:
            rect = find_window_rect(wt, False)
        if rect:
            self.source = "janela"
            return rect
        self.source = "tela"
        idx = min(max(1, int(self.cfg["monitor"])), len(sct.monitors) - 1)
        return sct.monitors[idx]

    def crop(self, img, frac):
        h, w = img.shape[:2]
        l, t, r, b = frac
        return img[int(h * t):int(h * b), int(w * l):int(w * r)]

    def ocr(self, img):
        if img.shape[1] < 1000:
            f = 1000.0 / img.shape[1]
            img = self.cv2.resize(img, None, fx=f, fy=f, interpolation=self.cv2.INTER_CUBIC)
        result, _ = self.engine(img)
        out = []
        for item in (result or []):
            try:
                if float(item[2]) >= 0.35:
                    out.append(str(item[1]))
            except Exception:
                pass
        return out

    def detect_boss_bar(self, shot):
        """Detecta a barra vermelha de chefe por forma/cor na faixa inferior da tela.

        Não depende do nome localizado do chefe: funciona com barras de chefes únicos
        e múltiplos. O catálogo é referência de encontros; a barra é o sinal visual.
        """
        hsv = self.cv2.cvtColor(shot, self.cv2.COLOR_BGR2HSV)
        h, w = hsv.shape[:2]
        y0 = int(h * 0.72)
        roi = hsv[y0:int(h * 0.985), :]
        # Vermelho em HSV ocupa as duas extremidades do canal H.
        low = self.cv2.inRange(roi, self.np.array([0, 95, 65]), self.np.array([12, 255, 255]))
        high = self.cv2.inRange(roi, self.np.array([168, 95, 65]), self.np.array([180, 255, 255]))
        mask = self.cv2.bitwise_or(low, high)
        kernel = self.np.ones((3, 9), self.np.uint8)
        mask = self.cv2.morphologyEx(mask, self.cv2.MORPH_CLOSE, kernel)
        contours, _ = self.cv2.findContours(mask, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)
        min_width = int(w * 0.12)
        for c in contours:
            x, y, cw, ch = self.cv2.boundingRect(c)
            if cw >= min_width and 2 <= ch <= max(18, int(h * 0.025)) and cw / max(ch, 1) >= 8:
                return True
        return False

    def scan(self, sct):
        now = time.time()
        with self.lock:
            day_wait = now - self.tracker.last_day_t < self.tracker.DAY_COOLDOWN
            msg_wait = all(now - v < self.tracker.MSG_COOLDOWN for v in self.tracker.last_msg_t.values())
        area = self.area(sct)
        shot = self.np.array(sct.grab(area))[:, :, :3]  # BGRA -> BGR
        dbg = []

        # Confirmação em vários frames evita falsos positivos por efeitos vermelhos.
        bar_now = self.detect_boss_bar(shot)
        if bar_now:
            self.boss_seen_frames += 1
            self.boss_missing_frames = 0
        else:
            self.boss_missing_frames += 1
            self.boss_seen_frames = 0
        with self.lock:
            if self.boss_seen_frames >= 3 and not self.boss_bar_active:
                self.boss_bar_active = True
                if self.tracker.boss_bar_signal():
                    log("Barra de chefe detectada; fase de combate iniciada")
            # A barra só encerra o Dia III depois de desaparecer de forma estável.
            # Uma pausa curta/segunda barra de uma luta múltipla não conclui a run.
            if self.boss_bar_active and self.boss_missing_frames >= 15:
                if self.tracker.boss_defeated():
                    log("Barra final desapareceu; expedição concluída")
                self.boss_bar_active = False

        if not day_wait:
            lines = self.ocr(self.crop(shot, self.cfg["regions"]["banner"]))
            n = parse_day(lines)
            if lines:
                dbg.append("banner: " + " | ".join(lines)[:80])
            if n:
                with self.lock:
                    if self.tracker.day_signal(n):
                        self.boss_bar_active = False
                        self.boss_seen_frames = self.boss_missing_frames = 0
                        log("DIA %s detectado (texto: %s)" % (ROMAN[n], lines))

        if not msg_wait:
            lines = self.ocr(self.crop(shot, self.cfg["regions"]["message"]))
            text = " ".join(lines)
            if text:
                dbg.append("msg: " + text[:80])
            kind = detect_message(text, self.cfg.get("extra_phrases"))
            if kind:
                with self.lock:
                    if self.tracker.msg_signal(kind):
                        log("Sinal %s detectado (texto: %s)" % (kind, text))
        self.debug_text = "  ".join(dbg)


# ----------------------------------------------------------------------------
# Overlay (visual inspirado em Elden Ring: preto, cinza e azul escuro)
# ----------------------------------------------------------------------------
BG = "#0a0d13"
EDGE = "#2c3849"
EDGE_IN = "#171f2c"
ACCENT = "#5b86c7"
ACCENT_DIM = "#27405f"
SILVER = "#cfd6e1"
DIM = "#6a7686"
RED = "#c05a55"
FONT_SERIF = "Palatino Linotype"
W, H = 360, 224


class App:
    def __init__(self):
        set_dpi_aware()
        self.cfg = load_config()
        self.lock = threading.Lock()
        self.tracker = Tracker(self.cfg["durations"])
        self.scanner = Scanner(self.cfg, self.tracker, self.lock)
        self.visible, self.move_mode, self.debug = True, False, False
        self.prev_keys = {}
        self.drag = (0, 0)
        self.sc = float(self.cfg["overlay"].get("scale", 1.0))

        self.root = tk.Tk()
        self.root.title("NRO")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", float(self.cfg["overlay"]["opacity"]))
        self.root.configure(bg=BG)
        w, h = int(W * self.sc), int(H * self.sc)
        x, y = int(self.cfg["overlay"].get("x", -1)), int(self.cfg["overlay"].get("y", -1))
        if x < 0 or y < 0:
            x = max(0, self.root.winfo_screenwidth() - w - 24)
            y = max(0, self.root.winfo_screenheight() - h - 48)
            self.cfg["overlay"]["x"], self.cfg["overlay"]["y"] = x, y
            save_config(self.cfg)
        self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))
        self.cv = tk.Canvas(self.root, width=w, height=h, bg=BG, highlightthickness=0)
        self.cv.pack()
        self.root.update_idletasks()
        self.hwnd = None
        if IS_WIN:
            self.hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            try:  # o overlay nao aparece na captura -> nao le a si mesmo
                user32.SetWindowDisplayAffinity(self.hwnd, 0x11)
            except Exception:
                pass
            self.set_click_through(True)
        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.scanner.start()
        self.tick()
        self.root.mainloop()

    # --- janela ----------------------------------------------------------------
    def set_click_through(self, on):
        if not IS_WIN or not self.hwnd:
            return
        style = user32.GetWindowLongW(self.hwnd, -20)
        base = 0x00080000 | 0x00000080 | 0x08000000  # LAYERED | TOOLWINDOW | NOACTIVATE
        style = style | base
        style = (style | 0x20) if on else (style & ~0x20)
        user32.SetWindowLongW(self.hwnd, -20, style)

    def on_press(self, e):
        self.drag = (e.x_root - self.root.winfo_x(), e.y_root - self.root.winfo_y())

    def on_drag(self, e):
        if self.move_mode:
            self.root.geometry("+%d+%d" % (e.x_root - self.drag[0], e.y_root - self.drag[1]))

    def toggle_move(self):
        self.move_mode = not self.move_mode
        self.set_click_through(not self.move_mode)
        if not self.move_mode:
            self.cfg["overlay"]["x"], self.cfg["overlay"]["y"] = self.root.winfo_x(), self.root.winfo_y()
            save_config(self.cfg)

    # --- atalhos ---------------------------------------------------------------
    def poll_keys(self):
        for action, name in self.cfg["hotkeys"].items():
            vk = vk_from_name(name)
            if vk is None:
                continue
            down = key_down(vk)
            if down and not self.prev_keys.get(action):
                self.do_action(action)
            self.prev_keys[action] = down

    def do_action(self, action):
        if action == "quit":
            self.scanner.stop_flag = True
            self.root.destroy()
            os._exit(0)
        with self.lock:
            if action == "next_day":
                self.tracker.force_next_day()
            elif action == "next_phase":
                self.tracker.force_next_phase()
            elif action == "reset":
                self.tracker.reset()
        if action == "move":
            self.toggle_move()
        elif action == "hide":
            self.visible = not self.visible
            (self.root.deiconify if self.visible else self.root.withdraw)()
        elif action == "debug":
            self.debug = not self.debug

    # --- desenho ---------------------------------------------------------------
    def diamond(self, x, y, r, fill, outline=""):
        s = self.sc
        self.cv.create_polygon(x, y - r * s, x + r * s, y, x, y + r * s, x - r * s, y,
                               fill=fill, outline=outline, tags="dyn")

    def text(self, x, y, s, size, color, anchor="center", weight="normal", font=FONT_SERIF, slant="roman"):
        self.cv.create_text(x * self.sc, y * self.sc, text=s, anchor=anchor, fill=color,
                            font=(font, max(6, int(size * self.sc)), weight, slant), tags="dyn")

    def draw(self, snap):
        sc = self.sc
        cv = self.cv
        cv.delete("dyn")
        w, h = W * sc, H * sc
        # moldura
        cv.create_rectangle(1, 1, w - 2, h - 2, outline=EDGE if not self.move_mode else ACCENT, width=2, tags="dyn")
        cv.create_rectangle(6 * sc, 6 * sc, w - 6 * sc, h - 6 * sc, outline=EDGE_IN, tags="dyn")
        # cantos
        for cx, cy in ((6, 6), (W - 6, 6), (6, H - 6), (W - 6, H - 6)):
            self.diamond(cx * sc, cy * sc, 3.5, ACCENT_DIM)
        # titulo
        self.text(W / 2, 19, "N I G H T R E I G N   O V E R L A Y", 8, DIM)
        cv.create_line(30 * sc, 32 * sc, W / 2 * sc - 10 * sc, 32 * sc, fill=EDGE, tags="dyn")
        cv.create_line(W / 2 * sc + 10 * sc, 32 * sc, (W - 30) * sc, 32 * sc, fill=EDGE, tags="dyn")
        self.diamond(W / 2 * sc, 32 * sc, 3.5, ACCENT)

        # dia + pips
        day = snap["day"]
        dtxt = ("DIA " + ROMAN[day]) if day in ROMAN else "DIA —"
        self.text(24, 56, dtxt, 19, SILVER, anchor="w", weight="bold")
        for i in range(3):
            filled = day >= i + 1
            self.diamond((W - 70 + i * 22) * sc, 56 * sc, 6, ACCENT if filled else "", ACCENT if filled else EDGE)

        # cronometro
        overdue = snap["overdue"]
        if snap["phase"] == IDLE:
            ttxt, tcol = "--:--", DIM
        elif snap["stopwatch"]:
            ttxt, tcol = fmt(snap["elapsed"], up=True), SILVER
        else:
            ttxt = fmt(snap["remaining"])
            tcol = RED if overdue else (ACCENT if snap["remaining"] <= 30 else SILVER)
        self.text(W / 2, 102, ttxt, 38, tcol, weight="bold")

        # fase
        label = snap["label"]
        if snap["next"] and snap["phase"] != IDLE:
            label += "  →  " + snap["next"]
        self.text(W / 2, 138, label, 11, SILVER, slant="italic")
        self.text(W / 2, 156, snap["sub"] or " ", 9, RED if overdue else DIM)

        # barra de progresso
        x0, x1, y = 24 * sc, (W - 24) * sc, 170 * sc
        cv.create_rectangle(x0, y, x1, y + 4 * sc, fill=EDGE_IN, outline="", tags="dyn")
        if snap["total"]:
            frac = min(1.0, max(0.0, snap["elapsed"] / snap["total"]))
            cv.create_rectangle(x0, y, x0 + (x1 - x0) * frac, y + 4 * sc,
                                fill=RED if overdue else ACCENT, outline="", tags="dyn")

        # atalhos compactos sempre visíveis
        self.text(W / 2, 188, "F5 Dia  •  F6 Mover  •  F7 Fase  •  F8 Ocultar", 7, DIM, font="Segoe UI")
        self.text(W / 2, 199, "F9 Resetar  •  F10 Fechar  •  F11 Depuração", 7, DIM, font="Segoe UI")

        # rodape
        status = self.scanner.status
        if self.move_mode:
            status = "Modo mover: arraste e aperte %s" % self.cfg["hotkeys"]["move"]
        elif self.debug:
            status = self.scanner.debug_text or "(sem texto lido)"
        dot = ACCENT if "Lendo" in self.scanner.status else RED
        cv.create_oval(14 * sc, 211 * sc, 19 * sc, 216 * sc, fill=dot, outline="", tags="dyn")
        self.text(24, 214, status[:58], 7, DIM, anchor="w", font="Segoe UI")

    def tick(self):
        try:
            self.poll_keys()
            with self.lock:
                snap = self.tracker.snapshot()
            if self.visible:
                self.draw(snap)
        except Exception as e:
            log("Erro UI: %r" % (e,))
        self.root.after(150, self.tick)


if __name__ == "__main__":
    App()
