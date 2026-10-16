"""Mostra o que o OCR enxerga num print seu. Uso:  Testar_Print.bat "C:\\caminho\\print.png"
Salva os recortes processados em debug\\ para você conferir."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import numpy as np
from PIL import Image
import config, dbg, detect, ocr

dbg.enable(True)
cfg = config.load()
img = Image.open(sys.argv[1]).convert("RGBA")
w, h = img.size
eng, msg = ocr.create(cfg["ocr_languages"])
print("OCR:", msg)
if not eng:
    sys.exit(1)
cat = json.load(open(config.path("data", "bosses.json"), encoding="utf-8"))
bm = detect.BossMatcher(cat, cfg.get("extra_boss_names"))


def crop(k):
    x0, y0, x1, y1 = cfg["regions"][k]
    a = np.array(img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))))
    return a[..., [2, 1, 0, 3]].copy()


b = crop("banner")
for d, m in ((22, 140), (30, 170), (14, 120)):
    g = detect.prep_for_ocr(b, 1.0, d, m); L = eng.read(g, True)
    print("DIA   ", (d, m), L, "->", detect.parse_day(L))
dbg.save_crop("banner", detect.prep_for_ocr(b, 1.0, 22, 140))
s = crop("signal"); g = detect.prep_for_ocr(s, 2.0, 14, 120); dbg.save_crop("signal", g); L = eng.read(g, True)
print("SINAL ", L, "->", detect.match_signal(L, cfg["signals"]))
bo = crop("boss"); bl = detect.bars(bo); print("BARRAS", bl)
for i, (y, x) in enumerate(bl):
    g = detect.prep_for_ocr(detect.name_strip(bo, y, x), 2.0, 22, 140); dbg.save_crop("boss%d" % i, g)
    L = eng.read(g, True); print("CHEFE ", L, "->", bm.match(L))
print("Recortes em:", config.path("debug"))
