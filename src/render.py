"""Desenha o overlay inteiro com Pillow (1 imagem RGB pequena) — redesenha só quando algo muda."""
import os

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

import i18n
from engine import ROMAN

KEY = (1, 2, 3)                      # cor "transparente" da janela
TXT = (206, 216, 232)                # cinza-azulado claro (texto principal)
TXT_DIM = (122, 140, 168)
GLOW = (70, 135, 230)
WARN = (236, 150, 140)
BAR_FILL_A, BAR_FILL_B = (62, 128, 214), (150, 202, 255)

_SERIF_B = ["georgiab.ttf", "cambriab.ttf", "timesbd.ttf", "DejaVuSerif-Bold.ttf"]
_SERIF = ["georgia.ttf", "cambria.ttc", "times.ttf", "DejaVuSerif.ttf"]
_SERIF_I = ["georgiai.ttf", "timesi.ttf", "DejaVuSerif-Italic.ttf", "DejaVuSerif.ttf"]
_fcache = {}


def font(names, size):
    key = (names[0], int(size))
    if key in _fcache:
        return _fcache[key]
    f = None
    for n in names:
        try:
            f = ImageFont.truetype(n, int(size))
            break
        except Exception:
            continue
    _fcache[key] = f or ImageFont.load_default()
    return _fcache[key]


class Renderer:
    # posições relativas ao quadro (calibradas no conceito da imagem 8)
    def __init__(self, hud_path, cfg, screen_w):
        self.cfg = cfg
        self.S = i18n.STR.get(cfg.get("ui_language", "pt"), i18n.STR["pt"])
        hud = Image.open(hud_path).convert("RGBA")
        W = int(max(300, min(900, screen_w * 0.235 * float(cfg.get("scale", 1.0)))))
        H = round(hud.height * W / hud.width)
        self.W, self.H = W, H
        self.frame = hud.resize((W, H), Image.LANCZOS)
        a = np.asarray(self.frame.getchannel("A"))
        self.keymask = Image.fromarray(((a < 40) * 255).astype(np.uint8))
        dark = Image.new("RGBA", (W, H), (7, 10, 18, 255))
        self.base = Image.alpha_composite(dark, self.frame)
        self._last = None
        self._img = None
        self._build_static()

    # ---------- camadas ----------
    def _glow(self, layer, xy, text, f, fill, glow=GLOW, anchor="mm", blur=None, strength=0.75):
        d = ImageDraw.Draw(layer)
        tmp = Image.new("L", layer.size, 0)
        ImageDraw.Draw(tmp).text(xy, text, font=f, fill=255, anchor=anchor)
        bbox = tmp.getbbox()
        if bbox:
            pad = int(f.size * 0.5)
            box = (max(0, bbox[0] - pad), max(0, bbox[1] - pad),
                   min(layer.width, bbox[2] + pad), min(layer.height, bbox[3] + pad))
            g = tmp.crop(box).filter(ImageFilter.GaussianBlur(blur or max(2, f.size * 0.09)))
            g = g.point(lambda v: min(255, int(v * strength * 1.6)))
            layer.paste(Image.new("RGBA", g.size, glow + (0,)), box[:2], g)
        d.text(xy, text, font=f, fill=fill + (255,), anchor=anchor)

    def _spaced(self, d, cx, cy, text, f, fill, gap):
        w = sum(d.textlength(c, font=f) for c in text) + gap * (len(text) - 1)
        x = cx - w / 2
        for c in text:
            d.text((x, cy), c, font=f, fill=fill, anchor="lm")
            x += d.textlength(c, font=f) + gap

    def _build_static(self):
        W, H = self.W, self.H
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)
        self.p = {  # posições
            "title_y": H * 0.105, "day_x": W * 0.075, "day_y": H * 0.285,
            "dia_cx": (W * 0.80, W * 0.866, W * 0.934), "dia_y": H * 0.285,
            "timer_x": W * 0.5, "timer_y": H * 0.50, "label_y": H * 0.675, "keys_y": H * 0.755,
            "bar": (W * 0.082, H * 0.835, W * 0.918, H * 0.872), "status_y": H * 0.925,
        }
        p = self.p
        ft = font(_SERIF, H * 0.062)
        self._glow(L, (W / 2, p["title_y"]), "", ft, TXT)
        self._spaced(d, W / 2, p["title_y"], "NIGHTREIGN OVERLAY", ft, TXT, H * 0.012)
        keys = self.S["keys"].format(**{k: v.upper() for k, v in self.cfg["hotkeys"].items()})
        fk = font(_SERIF, H * 0.037)
        while fk.size > 8 and d.textlength(keys, font=fk) > W * 0.82:
            fk = font(_SERIF, fk.size - 1)
        d.text((W / 2, p["keys_y"]), keys, font=fk, fill=TXT_DIM + (255,), anchor="mm")
        x0, y0, x1, y1 = p["bar"]
        d.rounded_rectangle((x0, y0, x1, y1), radius=(y1 - y0) / 2, fill=(10, 15, 26, 255),
                            outline=(70, 92, 128, 255), width=1)
        self.static = Image.alpha_composite(self.base, L)

    def _diamond(self, d, cx, cy, r, filled):
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        if filled:
            d.polygon(pts, fill=(95, 165, 245, 255), outline=(200, 225, 255, 255))
        else:
            d.polygon(pts, fill=(8, 12, 22, 255), outline=(150, 168, 196, 255))

    # ---------- quadro dinâmico ----------
    def render(self, v, status):
        sig = (v["day"], v["key"], v["timer"], v["neg"], v["boss"], v["paused"], status,
               None if v["progress"] is None else int(v["progress"] * 200))
        if sig == self._last and self._img is not None:
            return self._img, False
        self._last = sig
        W, H, p, S = self.W, self.H, self.p, self.S
        L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(L)

        # "DIA I"
        day = v["day"]
        txt = "%s %s" % (S["day"], ROMAN[day])
        fd = font(_SERIF_B, H * 0.115)
        self._glow(L, (p["day_x"], p["day_y"]), txt, fd, TXT if day else TXT_DIM, anchor="lm", strength=0.5)
        r = H * 0.036
        for i, cx in enumerate(p["dia_cx"]):
            self._diamond(d, cx, p["dia_y"], r, i < day)

        # timer
        ftm = font(_SERIF_B, H * 0.215)
        col = WARN if v["neg"] else (TXT if v["day"] else TXT_DIM)
        glow = (200, 90, 80) if v["neg"] else GLOW
        self._glow(L, (p["timer_x"], p["timer_y"]), v["timer"], ftm, col, glow=glow, strength=0.8)

        # rótulo da fase
        key = v["key"]
        if key == "idle":
            label = S["idle_label"]
        elif key == "boss":
            base = S["boss_final"] if day == 3 else S["boss"]
            label = base + (": " + v["boss"] if v["boss"] else "")
        else:
            label = S[key]
        fl = font(_SERIF_I, H * 0.062)
        while fl.size > 9 and d.textlength(label, font=fl) > W * 0.84:
            fl = font(_SERIF_I, fl.size - 1)
        d.text((W / 2, p["label_y"]), label, font=fl, fill=TXT + (255,), anchor="mm")

        # barra de progresso
        x0, y0, x1, y1 = p["bar"]
        prog = v["progress"]
        inner0, inner1 = x0 + 3, x1 - 3
        if prog is None:
            if key != "idle":
                d.rounded_rectangle((inner0, y0 + 3, inner1, y1 - 3), radius=(y1 - y0) / 2 - 3,
                                    fill=(38, 58, 92, 255))
        elif prog > 0.005:
            xe = inner0 + (inner1 - inner0) * prog
            fill_col = (150, 70, 66, 255) if v["neg"] else None
            bar = Image.new("RGBA", (max(2, int(xe - inner0)), max(2, int(y1 - y0 - 6))))
            bd = ImageDraw.Draw(bar)
            for xx in range(bar.width):
                t = xx / max(1, bar.width - 1)
                c = tuple(int(BAR_FILL_A[i] + (BAR_FILL_B[i] - BAR_FILL_A[i]) * t) for i in range(3))
                bd.line([(xx, 0), (xx, bar.height)], fill=(fill_col[:3] if fill_col else c) + (255,))
            m = Image.new("L", bar.size, 0)
            ImageDraw.Draw(m).rounded_rectangle((0, 0, bar.width - 1, bar.height - 1),
                                                radius=bar.height / 2, fill=255)
            L.paste(bar, (int(inner0), int(y0 + 3)), m)

        # status
        fs = font(_SERIF_I, H * 0.050)
        st = S[status] if status in S else status
        sx = W * 0.085
        self._diamond(d, sx, p["status_y"], H * 0.021, status == "reading")
        d.text((sx + H * 0.04, p["status_y"]), st, font=fs, fill=TXT + (255,), anchor="lm")

        rgb = Image.alpha_composite(self.static, L).convert("RGB")
        rgb.paste(KEY, (0, 0), self.keymask)
        self._img = rgb
        return rgb, True
