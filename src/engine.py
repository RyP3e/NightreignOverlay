"""Máquina de estados do timer. Sem I/O, sem OCR: só lógica (testável)."""
import time

ROMAN = {0: "–", 1: "I", 2: "II", 3: "III"}

# Estágios: key -> (duração em config | None = cronômetro progressivo, é "marco" automático?)
SEQ_DAY12 = ["free", "c1", "c1hold", "c2", "boss"]
SEQ_DAY3 = ["prep", "boss"]


class Timeline:
    def __init__(self, cfg):
        d = cfg["durations"]
        self.dur = {"free": d["free"], "c1": d["circle1_close"], "c1hold": d["circle1_hold"],
                    "c2": d["circle2_close"], "boss": None, "prep": None}
        self.auto = {"c1": bool(cfg.get("auto_milestone", True))}
        self.boss_min_stage = int(cfg.get("boss_min_stage", 3))
        self.reset()

    # ---------- estado ----------
    def reset(self):
        self.day = 0
        self.idx = 0
        self.t0 = self.day_t0 = 0.0
        self.paused_at = None
        self.boss = None
        self.dirty = True

    def seq(self):
        return SEQ_DAY3 if self.day == 3 else SEQ_DAY12

    def key(self):
        return "idle" if self.day == 0 else self.seq()[self.idx]

    def _now(self, now):
        return time.monotonic() if now is None else now

    def elapsed(self, now=None):
        if self.day == 0:
            return 0.0
        ref = self.paused_at if self.paused_at is not None else self._now(now)
        return ref - self.t0

    def remaining(self, now=None):
        d = self.dur.get(self.key())
        return None if d is None else d - self.elapsed(now)

    # ---------- transições ----------
    def day_age(self, now=None):
        return 0.0 if self.day == 0 else self._now(now) - self.day_t0

    def start_day(self, day, now=None):
        self.day, self.idx, self.boss = day, 0, None
        self.t0 = self.day_t0 = self._now(now)
        self.paused_at = None
        self.dirty = True

    def set_stage(self, idx, now=None, carry=0.0):
        self.idx = max(0, min(idx, len(self.seq()) - 1))
        self.t0 = self._now(now) - carry
        if self.paused_at is not None:
            self.paused_at = self._now(now)
        if self.key() != "boss":
            self.boss = None
        self.dirty = True

    def tick(self, now=None):
        """Marcos automáticos por tempo (só 'c1' -> 'c1hold'). Retorna True se mudou."""
        k = self.key()
        if k in self.auto and self.auto[k] and self.paused_at is None:
            over = self.elapsed(now) - self.dur[k]
            if over >= 0:
                self.set_stage(self.idx + 1, now, carry=over)
                return True
        return False

    def toggle_pause(self, now=None):
        if self.day == 0:
            return
        n = self._now(now)
        if self.paused_at is None:
            self.paused_at = n
        else:
            self.t0 += n - self.paused_at
            self.paused_at = None
        self.dirty = True

    def manual_next(self, now=None):
        if self.day == 0:
            self.start_day(1, now)
        elif self.idx + 1 < len(self.seq()):
            self.set_stage(self.idx + 1, now)
        elif self.day < 3:
            self.start_day(self.day + 1, now)

    def manual_prev(self, now=None):
        if self.day == 0:
            return
        if self.idx > 0:
            self.set_stage(self.idx - 1, now)
        elif self.day > 1:
            self.day -= 1
            self.set_stage(len(self.seq()) - 1, now)

    # ---------- eventos vindos do OCR ----------
    def on_banner(self, n, now=None):
        """'DAY n' lido. Aceita sequência normal, início de nova run ou dia pulado."""
        if n not in (1, 2, 3):
            return False
        if n == self.day:
            nova_run = n == 1 and (self.idx > 0 or self.elapsed(now) > 60)
            if not nova_run:
                return False
        elif n < self.day and n != 1:
            return False
        self.start_day(n, now)
        return True

    def expected_banner(self):
        return 1 if self.day == 0 else min(3, self.day + 1)

    def on_signal(self, k, now=None):
        """k=1: 'A maré da Noite se fortalece'; k=2: 'A chuva se acumula...'."""
        if self.day not in (1, 2):
            return False
        key = self.key()
        if k == 1 and key == "free":
            self.set_stage(1, now)
            return True
        if k == 2 and key in ("free", "c1", "c1hold"):
            self.set_stage(3, now)
            return True
        return False

    def boss_allowed(self):
        if self.day == 0:
            return False
        if self.day == 3:
            return self.key() in ("prep",)
        return self.idx >= self.boss_min_stage and self.key() != "boss"

    def on_boss(self, name, now=None):
        if not self.boss_allowed():
            return False
        self.set_stage(len(self.seq()) - 1, now)
        self.boss = name
        return True

    # ---------- o que o scanner precisa procurar agora ----------
    def wants(self):
        k = self.key()
        w = {"banner": False, "s1": False, "s2": False, "boss": False}
        if k == "idle":
            w["banner"] = True
        elif self.day in (1, 2):
            w["banner"] = k in ("c2", "boss")
            w["s1"] = k == "free"
            w["s2"] = k in ("free", "c1", "c1hold")
            w["boss"] = self.boss_allowed()
        else:
            w["banner"] = False
            w["boss"] = self.boss_allowed()
        if self.paused_at is not None:
            return {k2: False for k2 in w}
        return w

    # ---------- exibição ----------
    @staticmethod
    def fmt(sec):
        neg = sec < 0
        s = int(abs(sec))
        if neg and abs(sec) < 1:
            neg = False
        return ("-" if neg else "") + "%02d:%02d" % (s // 60, s % 60)

    def view(self, now=None):
        k = self.key()
        el = self.elapsed(now)
        rem = self.remaining(now)
        if k == "idle":
            timer, neg, prog = "--:--", False, 0.0
        elif rem is None:
            timer, neg, prog = self.fmt(el), False, None
        else:
            timer, neg = self.fmt(rem), rem < 0
            prog = 1.0 if rem <= 0 else max(0.0, min(1.0, el / self.dur[k]))
        return {"day": self.day, "key": k, "timer": timer, "neg": neg, "progress": prog,
                "boss": self.boss, "paused": self.paused_at is not None}
