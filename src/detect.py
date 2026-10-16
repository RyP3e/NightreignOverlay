"""Detecção: filtros baratos (numpy) que decidem SE vale rodar OCR, pré-processamento do recorte
e interpretação do texto lido (dia, sinais, nome de chefe)."""
import difflib
import re
import unicodedata

import numpy as np
from PIL import Image, ImageFilter


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9' ]+", " ", s.replace("’", "'"))
    return re.sub(r"\s+", " ", s).strip()


# ------------------------------------------------------------------ filtros baratos
def _whiteness(arr):
    return arr[::2, ::2, :3].min(axis=2)  # amostra 1/4 dos pixels; texto do jogo é quase branco


def text_present(arr, thr=185, lo=0.002, hi=0.30):
    """Há pixels bem claros suficientes (texto branco) na região?"""
    w = _whiteness(arr)
    f = float((w > thr).mean())
    return lo < f < hi


def bars(arr):
    """Localiza barras de vida de chefe (linha longa laranja/vermelha). Sem OCR, ~1 ms.
    Retorna [(y, x_esquerda)] em pixels do recorte (uma por barra; lutas com 2+ chefes têm várias)."""
    a = arr[::2, ::2].astype(np.int16)
    b, g, r = a[..., 0], a[..., 1], a[..., 2]
    m = (r > 130) & (r - g > 55) & (r - b > 65) & (g < 140)
    ys = np.where(m.mean(axis=1) > 0.22)[0]
    if not len(ys):
        return []
    groups, start, prev = [], int(ys[0]), int(ys[0])
    for y in ys[1:]:
        y = int(y)
        if y - prev > 6:
            groups.append((start, prev))
            start = y
        prev = y
    groups.append((start, prev))
    out = []
    for s0, e0 in groups[:3]:
        x = int(np.argmax(m[s0:e0 + 1].any(axis=0)))
        out.append((s0 * 2, x * 2))
    return out


def bar_present(arr):
    return bool(bars(arr))


def name_strip(arr, y, x):
    """Recorte só da linha do nome, logo acima da barra e alinhada à esquerda dela."""
    h = int(arr.shape[0] * 0.34)
    return arr[max(0, y - h):y + 2, max(0, x - 8):x + int(arr.shape[1] * 0.55)]


# ------------------------------------------------------------------ pré-processamento p/ OCR
def prep_for_ocr(arr, upscale=2.0, delta=22, minv=140):
    """Recorte BGRA -> imagem cinza com texto ESCURO em fundo BRANCO (o que o OCR lê melhor).
    Texto do jogo é claro; isolamos pelo contraste local (funciona em fundo claro e escuro)."""
    g = Image.fromarray(np.ascontiguousarray(arr[..., :3].min(axis=2)))
    if upscale != 1.0:
        g = g.resize((int(g.width * upscale), int(g.height * upscale)), Image.BICUBIC)
    bg = g.filter(ImageFilter.BoxBlur(max(6, int(g.height * 0.08))))
    a = np.asarray(g, dtype=np.int16)
    m = ((a - np.asarray(bg, dtype=np.int16)) > delta) & (a > minv)
    out = np.where(m, 0, 255).astype(np.uint8)
    # moldura branca para o OCR não colar o texto na borda
    return np.pad(out, 8, constant_values=255)


# ------------------------------------------------------------------ interpretação
_DAY_RE = re.compile(r"(?:day|dia|d[a4]y|d1a)\s*([il1|!]{1,4}|[1-3])", re.I)
_DAY_WORD = re.compile(r"\b(day|dia)\b|(day|dia)[il1|!]", re.I)


def parse_day(lines):
    """'DAY II' / 'DIA III' -> 1..3. None = não é banner de dia. 0 = é banner, mas o numeral
    veio ilegível (erro típico de OCR em I/l/1/|)."""
    txt = " ".join(lines).replace("\n", " ")
    t = txt.lower()
    m = _DAY_RE.search(t.replace(" ", "")) or _DAY_RE.search(t)
    if not m:
        return 0 if _DAY_WORD.search(t) else None
    tail = m.group(1)
    n = int(tail) if tail.isdigit() else len(tail)
    return n if n in (1, 2, 3) else 0


def _tok_match(tok, target):
    if tok == target:
        return True
    if len(target) >= 5 and (target in tok or (len(tok) >= 5 and tok in target)):
        return True
    return difflib.SequenceMatcher(None, tok, target).ratio() >= 0.80


def match_signal(lines, signals_cfg):
    """Retorna 1, 2 ou None conforme as palavras-chave (tolerantes a erro de OCR)."""
    toks = norm(" ".join(lines)).split()
    if not toks:
        return None

    def hit(groups):
        for grp in groups:
            if all(any(_tok_match(t, w) for t in toks) for w in grp):
                return True
        return False
    if hit(signals_cfg["s2"]):
        return 2
    if hit(signals_cfg["s1"]):
        return 1
    return None


class BossMatcher:
    def __init__(self, catalog, extras=()):
        names = set()
        for lst in catalog.values():
            names.update(lst)
        names.update(extras or [])
        self.names = {}
        for n in names:
            k = norm(n)
            if len(k) >= 4:
                self.names[k] = n

    def match(self, lines):
        best, best_s = None, 0.0
        for ln in lines:
            l = norm(re.sub(r"\d+", " ", ln))
            if len(l) < 4:
                continue
            toks = l.split()
            for k, orig in self.names.items():
                if k in l:
                    s = 1.0 + len(k) / 100.0
                else:
                    c = len(k.split())
                    s = 0.0
                    for w in {max(1, c - 1), c, c + 1}:
                        for i in range(0, len(toks) - w + 1):
                            cand = " ".join(toks[i:i + w])
                            if 0.7 * len(k) <= len(cand) <= 1.3 * len(k):
                                s = max(s, difflib.SequenceMatcher(None, k, cand).ratio())
                    if s < 0.84:
                        continue
                if s > best_s:
                    best, best_s = orig, s
        return best
