"""Thread de leitura. Só trabalha no que a fase atual espera e só nos recortes necessários.

Custo por detector:
  banner  -> a cada ~0,7 s, apenas na espera de um novo dia (e depois que a luta começa)
  sinais  -> a cada ~1 s, apenas na zona livre / círculos (1 recorte pequeno no canto superior direito)
  chefe   -> teste de cor (sem OCR) a cada 0,5 s; OCR do nome só se houver barra de vida na tela
"""
import threading
import time

import capture
import config
import dbg
import detect
import ocr


class Plan:
    """Compartilhado UI -> scanner (atribuições atômicas)."""
    def __init__(self):
        self.wants = {"banner": False, "s1": False, "s2": False, "boss": False}
        self.expected_day = 1
        self.day = 0              # dia atual da timeline
        self.day_age = 0.0        # segundos desde o início do dia atual
        self.alive = True


class Scanner(threading.Thread):
    BANNER_PARAMS = [(22, 140), (30, 170), (14, 120), (40, 190)]

    def __init__(self, cfg, catalog, plan, out_q):
        super().__init__(daemon=True, name="scanner")
        self.banner_try = 0
        self.cfg, self.plan, self.q = cfg, plan, out_q
        self.matcher = detect.BossMatcher(catalog, cfg.get("extra_boss_names"))
        self.due = {"banner": 0.0, "signal": 0.0, "gate": 0.0, "bossocr": 0.0}
        self.pending = {}          # numeral do dia -> (contagem, instante)
        self.cool = {"banner": 0.0, "s1": 0.0, "s2": 0.0}
        self.boss_hits, self.boss_name, self.boss_miss = 0, None, 0

    # ------------------------------------------------------------------
    def run(self):
        try:
            try:
                import winrt.runtime as wr
                wr.init_apartment(wr.ApartmentType.MULTI_THREADED)
            except Exception:
                pass
            engine, msg = ocr.create(self.cfg["ocr_languages"])
            self.q.put(("ocr", engine is not None, msg))
            dbg.log("OCR: %s" % msg)
            if engine is None:
                return
            grab = capture.Grabber(self.cfg)
        except Exception as e:
            self.q.put(("ocr", False, "falha ao iniciar: %s" % e))
            return
        sc = self.cfg["scan"]
        reg = self.cfg["regions"]
        last_src = None
        while self.plan.alive:
            w = self.plan.wants
            if not any(w.values()):
                time.sleep(0.3)
                continue
            now = time.monotonic()
            try:
                if grab.source != last_src:
                    last_src = grab.source
                    dbg.log("captura: %s %s" % (grab.source, grab.area()))
                if w["banner"] and now >= self.due["banner"]:
                    self.due["banner"] = now + sc["banner_interval"]
                    self._banner(grab, engine, reg["banner"], now)
                if (w["s1"] or w["s2"]) and now >= self.due["signal"]:
                    self.due["signal"] = now + sc["signal_interval"]
                    self._signal(grab, engine, reg["signal"], w, now)
                if w["boss"] and now >= self.due["gate"]:
                    self.due["gate"] = now + sc["boss_gate_interval"]
                    self._boss(grab, engine, reg["boss"], now)
            except Exception as e:
                dbg.log("erro no scanner: %r" % (e,))
                time.sleep(1.0)
            time.sleep(0.08)
        grab.close()

    # ------------------------------------------------------------------
    def _banner(self, grab, engine, region, now):
        if now < self.cool["banner"]:
            return
        arr = grab.grab(region)
        if not detect.text_present(arr, thr=190, lo=0.003):
            self.pending.clear()
            return
        # alterna o limiar a cada leitura: fundos claros/escuros/ruidosos pedem ajustes diferentes
        delta, minv = self.BANNER_PARAMS[self.banner_try % len(self.BANNER_PARAMS)]
        self.banner_try += 1
        img = detect.prep_for_ocr(arr, 1.0, delta, minv)
        dbg.save_crop("banner", img)
        lines = engine.read(img, first_only=True)
        n = detect.parse_day(lines)
        dbg.log("banner OCR %r -> %s" % (lines, n))
        if n is None:
            return
        # O texto "DAY/DIA" só aparece no INÍCIO de um dia: se já passou um tempo no dia atual e o
        # numeral veio ilegível (ou repetido), o que está na tela é o próximo dia.
        if self.plan.day >= 1 and self.plan.day_age > 45 and n <= self.plan.day:
            n = self.plan.expected_day
        if n == 0:
            return
        cnt, t = self.pending.get(n, (0, now))
        cnt = cnt + 1 if now - t < 4 else 1
        self.pending = {n: (cnt, now)}
        # leitura que bate com o esperado vale na hora; fora da sequência exige 2 leituras iguais
        if n == self.plan.expected_day or cnt >= 2:
            self.pending.clear()
            self.cool["banner"] = now + 6.0
            self.q.put(("banner", n))

    def _signal(self, grab, engine, region, w, now):
        arr = grab.grab(region)
        if not detect.text_present(arr, thr=170, lo=0.001):
            return
        img = detect.prep_for_ocr(arr, 2.0, 14, 120)
        dbg.save_crop("signal", img)
        lines = engine.read(img, first_only=True)
        k = detect.match_signal(lines, self.cfg["signals"])
        dbg.log("sinal OCR %r -> %s" % (lines, k))
        if k and w.get("s%d" % k) and now >= self.cool["s%d" % k]:
            self.cool["s%d" % k] = now + 8.0
            self.q.put(("signal", k))

    def _boss(self, grab, engine, region, now):
        arr = grab.grab(region)
        bars = detect.bars(arr)
        if not bars:
            self.boss_hits, self.boss_name, self.boss_miss = 0, None, 0
            self.due["bossocr"] = 0.0
            return
        if now < self.due["bossocr"]:
            return
        sc = self.cfg["scan"]
        name = None
        for i, (y, x) in enumerate(bars):
            img = detect.prep_for_ocr(detect.name_strip(arr, y, x), 2.0, 22, 140)
            dbg.save_crop("boss%d" % i, img)
            lines = engine.read(img, first_only=True)
            name = self.matcher.match(lines)
            dbg.log("chefe OCR %r -> %s" % (lines, name))
            if name:
                break
        if name:
            self.boss_miss = 0
            self.boss_hits = self.boss_hits + 1 if name == self.boss_name else 1
            self.boss_name = name
            self.due["bossocr"] = now + 0.8
            if self.boss_hits >= int(sc["boss_confirm"]):
                self.q.put(("boss", name))
                self.boss_hits = 0
        else:
            self.boss_hits, self.boss_name = 0, None
            self.boss_miss += 1       # barra de um chefe de campo/mini-chefe: reduz a frequência
            self.due["bossocr"] = now + min(5.0, sc["boss_ocr_interval"] * (1 + 0.5 * self.boss_miss))
