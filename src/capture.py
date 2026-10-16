"""Captura SÓ dos recortes necessários (nunca a tela inteira) usando mss."""
import time

import numpy as np

import winutil


class Grabber:
    """Deve ser criado e usado na MESMA thread (limitação do mss no Windows)."""

    def __init__(self, cfg):
        import mss
        self.cfg = cfg
        self.sct = mss.mss()
        self._area = None
        self._area_t = 0.0
        self.source = "monitor"

    def area(self):
        """(x, y, w, h) da área onde o jogo é desenhado. Atualizada a cada 4 s."""
        now = time.monotonic()
        if self._area and now - self._area_t < 4.0:
            return self._area
        ov = self.cfg.get("capture_override")
        area = None
        if ov and len(ov) == 4:
            area, self.source = tuple(int(v) for v in ov), "manual"
        if not area:
            r = winutil.find_game_client_rect(self.cfg.get("game_process"))
            if r:
                area, self.source = r, "jogo"
        if not area:
            mons = self.sct.monitors
            m = mons[min(max(1, int(self.cfg.get("monitor", 1))), len(mons) - 1)]
            area, self.source = (m["left"], m["top"], m["width"], m["height"]), "monitor"
        self._area, self._area_t = area, now
        return area

    def grab(self, frac):
        """frac = (esq, topo, dir, base) em fração da área. Retorna array BGRA (h, w, 4)."""
        x, y, w, h = self.area()
        l = x + int(frac[0] * w)
        t = y + int(frac[1] * h)
        rw = max(8, int((frac[2] - frac[0]) * w))
        rh = max(8, int((frac[3] - frac[1]) * h))
        shot = self.sct.grab({"left": l, "top": t, "width": rw, "height": rh})
        return np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)

    def close(self):
        try:
            self.sct.close()
        except Exception:
            pass
