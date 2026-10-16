"""Gera data/bosses.json a partir do catálogo .txt (uso opcional, para desenvolvedores)."""
import re, json, sys

def split_names(s):
    s = re.sub(r"\((?:apelido|aliases?|alias|expedition/alias)[^)]*\)", lambda m: " | " + m.group(0)[1:-1].split(":",1)[-1].replace(";", "/") , s)
    s = re.sub(r"\(.*?\)", "", s)           # remove observações entre parênteses restantes
    out = []
    for chunk in re.split(r"\||/|→", s):
        chunk = chunk.strip(" .;")
        if not chunk: continue
        for part in re.split(r"\s+&\s+|\s+e\s+(?=[A-ZÁÉÍÓÚ])", chunk):
            part = part.strip(" .;")
            if part: out.append(part)
            if "," in part:
                out.append(part.split(",")[0].strip())
    return out

def main(txt, dst):
    sec = None; data = {"day1": [], "day2": [], "day3": []}
    cur = None
    for raw in open(txt, encoding="utf-8"):
        line = raw.rstrip("\n")
        m = re.match(r"^(DIA|DIA)\s+([123])\s+—", line)
        if m:
            sec = "day" + m.group(2); continue
        if line.startswith("VARIANTES AVANÇADAS") or line.startswith("RESUMO"):
            sec = None
        if sec and re.match(r"^\s*\d\d\.\s+EN:", line):
            cur = {"en": re.sub(r"^\s*\d\d\.\s+EN:\s*", "", line).strip(), "pt": ""}
            data[sec].append(cur)
        elif sec and cur and re.match(r"^\s+PT-BR:", line):
            cur["pt"] = re.sub(r"^\s+PT-BR:\s*", "", line).strip()
    out = {}
    for d, items in data.items():
        names = []
        for it in items:
            for n in split_names(it["en"]) + split_names(it["pt"]):
                if n not in names: names.append(n)
        names = [n for n in names if "(" not in n and n.lower() not in ("balancers", "dreglord")]
        extra = {"day3": ["Áugure", "Maris, Fathom of Night"]}.get(d, [])
        out[d] = names + [e for e in extra if e not in names]
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for d in out: print(d, len(out[d]))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
