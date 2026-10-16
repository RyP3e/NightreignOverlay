"""Configuração: valores padrão + config.json ao lado do executável."""
import copy, json, os, sys


def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


DEFAULTS = {
    "ui_language": "pt",            # "pt" ou "en" (textos do overlay)
    "scale": 1.0,                   # multiplicador do tamanho do overlay
    "opacity": 0.97,
    "margin": 24,                   # distância das bordas na 1ª abertura (canto inferior direito)
    "position": None,               # [x, y] — salvo automaticamente ao arrastar
    "monitor": 1,                   # monitor capturado quando o jogo não é encontrado
    "game_process": "nightreign.exe",
    "hotkeys": {
        "pause": "F6", "reset": "F7", "next": "F8", "prev": "F9",
        "toggle": "F10", "quit": "F11",
    },
    # Tempos (segundos) de cada dia (dias 1 e 2). O dia 3 é só o chefe final.
    "durations": {"free": 270, "circle1_close": 180, "circle1_hold": 210, "circle2_close": 180},
    "auto_milestone": True,         # "1º círculo fechando" -> "fechado" muda sozinho (marco por tempo)
    "boss_min_stage": 3,            # só aceita barra de chefe depois do sinal do 2º círculo (dias 1-2)
    "scan": {
        "banner_interval": 0.7,     # leitura do "DAY I/II/III"
        "signal_interval": 1.0,     # leitura das mensagens do canto superior direito
        "boss_gate_interval": 0.5,  # teste barato (sem OCR) da barra de vida
        "boss_ocr_interval": 1.5,   # OCR do nome do chefe (só com barra visível)
        "boss_confirm": 2,          # leituras seguidas para confirmar o chefe
    },
    # Regiões lidas (fração da tela: esquerda, topo, direita, base)
    "regions": {
        "banner": [0.36, 0.50, 0.64, 0.63],
        "signal": [0.58, 0.12, 1.00, 0.25],
        "boss":   [0.20, 0.70, 0.80, 0.88],
    },
    "capture_override": None,       # [x, y, largura, altura] para forçar a área capturada
    "ocr_languages": ["pt-BR", "en-US"],
    "extra_boss_names": [],         # nomes extras (veja logs/overlay.log com debug ligado)
    "signals": {
        "s1": [["mare", "fortalece"], ["fortalece"], ["tide", "stronger"], ["tide", "strengthens"],
               ["tide", "grows"], ["tide", "rising"], ["tide", "swells"]],
        "s2": [["chuva", "acumula"], ["pressagiando"], ["chuva", "pressagiando"], ["rain", "gathers"],
               ["rain", "presaging"], ["rain", "portending"], ["rain", "foreshadowing"], ["rain", "heralding"]],
    },
    "debug": False,                 # salva recortes em debug/ e escreve logs/overlay.log
}


def _merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _merge(a[k], v)
        else:
            a[k] = v
    return a


def path(*parts):
    return os.path.join(base_dir(), *parts)


def load():
    cfg = copy.deepcopy(DEFAULTS)
    p = path("config.json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            _merge(cfg, json.load(f))
    except FileNotFoundError:
        save(cfg)
    except Exception:
        pass  # config corrompido: usa padrão sem sobrescrever
    return cfg


def save(cfg):
    try:
        with open(path("config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
