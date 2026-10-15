from nr_logic import (detect_message, parse_day, Tracker, fmt,
                      EXPLORE, CIRCLE1, CIRCLE2, FINAL, IDLE)

# ---- mensagens ---------------------------------------------------------------
assert detect_message("A maré da Noite se fortalece.") == "circle1"
assert detect_message("A mare da Noite se fortaleee") == "circle1"           # erro de OCR
assert detect_message("A chuva se acumula, pressagiando a maré da Noite") == "circle2"
assert detect_message("A chuva se acumula pressagiando") == "circle2"        # leitura parcial
assert detect_message("The Night's tide grows stronger.") == "circle1"
assert detect_message("Rains gather, portending the tide of Night") == "circle2"
assert detect_message("Rune Arc activated") is None
assert detect_message("Zona livre (2) 03:16") is None
assert detect_message("") is None

# ---- banners de dia ----------------------------------------------------------
assert parse_day(["DIA I"]) == 1
assert parse_day(["DIA II"]) == 2
assert parse_day(["DIA III"]) == 3
assert parse_day(["DIAIII"]) == 3
assert parse_day(["DAY II"]) == 2
assert parse_day(["DAY Ill"]) == 3                                           # l no lugar de I
assert parse_day(["DIA 1"]) == 1
assert parse_day(["DIA 1 / 2"]) is None                                      # HUD, nao e banner
assert parse_day(["Wyrm de Magma"]) is None
assert parse_day(["Dia 2 / 3", "31194"]) is None

# ---- maquina de fases ----------------------------------------------------------
t = [1000.0]
tr = Tracker(clock=lambda: t[0])
assert tr.phase == IDLE
assert tr.msg_signal("circle1") is True                                      # app aberto no meio do dia
tr.reset()

assert tr.day_signal(1) and tr.phase == EXPLORE and tr.day == 1
assert not tr.day_signal(1)                                                  # repeticao imediata
t[0] += 270 + 20                                                             # zerou sem sinal
s = tr.snapshot()
assert s["phase"] == EXPLORE and s["overdue"] and fmt(s["remaining"]) == "-00:20", s

assert tr.msg_signal("circle1") and tr.phase == CIRCLE1
assert not tr.msg_signal("circle1")                                          # mensagem repetida
t[0] += 100
s = tr.snapshot()
assert fmt(s["remaining"]) == "04:20" and "fecha em" in s["sub"]
t[0] += 300                                                                  # passou do tempo, sem sinal
s = tr.snapshot()
assert s["phase"] == CIRCLE1 and s["overdue"] and fmt(s["remaining"]).startswith("-")

assert tr.msg_signal("circle2") and tr.phase == CIRCLE2
t[0] += 200
assert tr.snapshot()["overdue"] and tr.phase == CIRCLE2                      # boss: continua negativo

assert not tr.msg_signal("circle1")                                          # nao volta atras
assert tr.day_signal(2) and tr.phase == EXPLORE and tr.day == 2
t[0] += 60
assert not tr.day_signal(1) and tr.day == 2                                  # leitura falsa de "DIA I"
t[0] += 500
assert tr.msg_signal("circle2") and tr.phase == CIRCLE2                      # pulou o 1o sinal
assert tr.day_signal(3) and tr.phase == FINAL
t[0] += 65
s = tr.snapshot()
assert s["stopwatch"] and fmt(s["elapsed"], up=True) == "01:05"
assert not tr.msg_signal("circle1")                                          # sem circulos no dia 3

assert fmt(0) == "00:00" and fmt(-0.4) == "-00:01" and fmt(61) == "01:01"
print("TODOS OS TESTES PASSARAM")
