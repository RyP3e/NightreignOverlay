"""
Nightreign Overlay - logica pura (sem UI, sem OCR).

Contem:
  * normalizacao e reconhecimento de texto (PT-BR e EN) para os sinais do jogo
  * maquina de fases (Dia 1/2/3, zona livre, 1o circulo, 2o circulo)

Regra principal: as fases SO mudam quando o sinal correspondente e detectado.
Se o cronometro zerar antes do sinal, ele continua contando NEGATIVO.
"""
import difflib
import re
import time
import unicodedata

# ----------------------------------------------------------------------------
# Duracoes padrao (segundos). Podem ser alteradas no config.json.
# ----------------------------------------------------------------------------
DEFAULT_DURATIONS = {
    "explore": 270,        # inicio do dia -> 1o circulo comecar a fechar (4:30)
    "circle1_close": 180,  # tempo que o 1o circulo leva para fechar
    "a_to_b": 360,         # sinal do 1o circulo -> sinal do 2o circulo
    "b_to_boss": 180,      # sinal do 2o circulo -> circulo fechado / Chefe da Noite
}

# Estados
IDLE, EXPLORE, CIRCLE1, CIRCLE2, FINAL = "idle", "explore", "circle1", "circle2", "final"

ROMAN = {1: "I", 2: "II", 3: "III"}

# ----------------------------------------------------------------------------
# Reconhecimento de texto
# ----------------------------------------------------------------------------
# Frases normalizadas (minusculas, sem acento, sem pontuacao).
PHRASES = {
    "circle2": [
        "rains gather portending the tide of night",
        "a chuva se acumula pressagiando a mare da noite",
    ],
    "circle1": [
        "the nights tide grows stronger",
        "the nights tide strengthens",
        "a mare da noite se fortalece",
    ],
}
# Fragmentos curtos e distintivos (ajudam quando o OCR le so parte da frase).
KEYS = {
    "circle2": ["rains gather", "portending", "chuva se acumula", "pressagiando"],
    "circle1": ["tide grows stronger", "noite se fortalece"],
}
DAY_WORDS = ["dia", "day", "jour", "tag", "giorno", "dag", "dzien"]


def _strip_accents(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def norm_text(s):
    s = _strip_accents(s).lower()
    for ch in ("'", "’", "`", "´"):
        s = s.replace(ch, "")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def best_ratio(text, phrase):
    """Melhor similaridade (0..1) de `phrase` dentro de `text` (janela deslizante)."""
    if not text or not phrase:
        return 0.0
    n = len(phrase)
    if len(text) <= n + 2:
        return difflib.SequenceMatcher(None, text, phrase).ratio()
    best = 0.0
    for size in (n - 2, n, n + 2):
        if size <= 0:
            continue
        for i in range(0, max(1, len(text) - size + 1)):
            r = difflib.SequenceMatcher(None, text[i:i + size], phrase).ratio()
            if r > best:
                best = r
                if best >= 0.98:
                    return best
    return best


def detect_message(raw_text, extra_phrases=None):
    """Retorna 'circle1', 'circle2' ou None a partir do texto lido no canto superior direito."""
    t = norm_text(raw_text)
    if len(t) < 8:
        return None
    phrases = {k: list(v) for k, v in PHRASES.items()}
    keys = {k: list(v) for k, v in KEYS.items()}
    for kind, items in (extra_phrases or {}).items():
        if kind in phrases:
            phrases[kind] += [norm_text(x) for x in items]
    # circle2 primeiro: a frase dele tambem cita "a mare da noite".
    for kind in ("circle2", "circle1"):
        for p in phrases[kind]:
            if best_ratio(t, p) >= 0.72:
                return kind
        for k in keys[kind]:
            if best_ratio(t, k) >= 0.82:
                return kind
    return None


def parse_day(lines):
    """
    Procura 'DIA I / DIA II / DIA III' (ou 'DAY I/II/III') nas linhas lidas.
    Retorna 1, 2, 3 ou None.  Ignora o HUD 'DIA 1 / 2'.
    """
    for raw in lines:
        if "/" in raw:  # HUD "DIA 1 / 2"
            continue
        t = norm_text(raw).replace(" ", "")
        if not t:
            continue
        # I / l / 1 / | / ! costumam ser confundidos pelo OCR
        t = t.replace("l", "i").replace("1", "i")
        m = re.match(r"^([a-z0]{2,6}?)(i{1,3}|[23])$", t)
        if not m:
            continue
        word, num = m.group(1).replace("0", "o"), m.group(2)
        ok = any(difflib.SequenceMatcher(None, word, w).ratio() >= 0.66 for w in DAY_WORDS)
        if not ok:
            continue
        return int(num) if num in ("2", "3") else len(num)
    return None


# ----------------------------------------------------------------------------
# Maquina de fases
# ----------------------------------------------------------------------------
class Tracker:
    DAY_COOLDOWN = 40.0
    MSG_COOLDOWN = 25.0

    def __init__(self, durations=None, clock=time.time):
        self.dur = dict(DEFAULT_DURATIONS)
        if durations:
            self.dur.update({k: float(v) for k, v in durations.items() if k in self.dur})
        self.clock = clock
        self.reset()

    def reset(self):
        self.day = 0
        self.phase = IDLE
        self.t0 = self.clock()
        self.last_day_t = -1e9
        self.last_msg_t = {"circle1": -1e9, "circle2": -1e9}
        self.last_event = ""

    # -- sinais -------------------------------------------------------------
    def day_signal(self, n, now=None):
        now = self.clock() if now is None else now
        if now - self.last_day_t < self.DAY_COOLDOWN:
            return False
        accept = n > self.day or (n == 1 and self.day >= 1 and now - self.t0 > 120)
        if not accept:
            return False
        self.day = n
        self.phase = FINAL if n == 3 else EXPLORE
        self.t0 = now
        self.last_day_t = now
        self.last_event = "Dia %s detectado" % ROMAN[n]
        return True

    def msg_signal(self, kind, now=None):
        now = self.clock() if now is None else now
        if kind not in self.last_msg_t or now - self.last_msg_t[kind] < self.MSG_COOLDOWN:
            return False
        if self.day == 3 or self.phase == FINAL:
            return False
        if kind == "circle1" and self.phase in (IDLE, EXPLORE):
            self.phase = CIRCLE1
            self.last_event = "1o circulo comecou a fechar"
        elif kind == "circle2" and self.phase in (IDLE, EXPLORE, CIRCLE1):
            self.phase = CIRCLE2
            self.last_event = "2o circulo comecou a fechar"
        else:
            return False
        self.t0 = now
        self.last_msg_t[kind] = now
        return True

    # -- manual (hotkeys) -----------------------------------------------------
    def force_next_phase(self, now=None):
        now = self.clock() if now is None else now
        order = {IDLE: CIRCLE1, EXPLORE: CIRCLE1, CIRCLE1: CIRCLE2}
        if self.phase in order:
            self.phase = order[self.phase]
            self.t0 = now
            self.last_event = "fase avancada manualmente"

    def force_next_day(self, now=None):
        now = self.clock() if now is None else now
        n = 1 if self.day >= 3 else self.day + 1
        self.day = n
        self.phase = FINAL if n == 3 else EXPLORE
        self.t0 = now
        self.last_event = "dia avancado manualmente"

    # -- leitura para a UI ----------------------------------------------------
    def snapshot(self, now=None):
        now = self.clock() if now is None else now
        el = max(0.0, now - self.t0)
        d = self.dur
        s = {"day": self.day, "phase": self.phase, "elapsed": el,
             "remaining": None, "total": None, "label": "", "next": "",
             "sub": "", "overdue": False, "stopwatch": False}
        if self.phase == IDLE:
            s.update(label="Aguardando sinal do dia...", next="Dia I")
        elif self.phase == EXPLORE:
            s.update(label="Zona livre", next="1º círculo", total=d["explore"])
        elif self.phase == CIRCLE1:
            s.update(label="1º círculo fechando", next="2º círculo", total=d["a_to_b"])
            close_left = d["circle1_close"] - el
            s["sub"] = ("Círculo fecha em %s" % fmt(close_left)) if close_left > 0 \
                else "Círculo fechado • aguardando o 2º"
        elif self.phase == CIRCLE2:
            s.update(label="2º círculo fechando", next="Chefe da Noite", total=d["b_to_boss"])
        elif self.phase == FINAL:
            s.update(label="Chefe final", next="", stopwatch=True,
                     sub="Cronômetro do Dia III")
        if s["total"] is not None:
            s["remaining"] = s["total"] - el
            s["overdue"] = s["remaining"] < 0
            if s["overdue"] and self.phase != CIRCLE1:
                s["sub"] = "Sinal ainda não detectado"
            if s["overdue"] and self.phase == CIRCLE1:
                s["sub"] = "Aguardando sinal do 2º círculo"
        return s


def fmt(seconds, up=False):
    """mm:ss; negativo recebe '-'. `up=True` (cronometro) arredonda para baixo."""
    import math
    neg = seconds < 0
    sec = int(abs(seconds)) if up else int(math.ceil(abs(seconds)))
    out = "%02d:%02d" % (sec // 60, sec % 60)
    return ("-" + out) if neg else out
