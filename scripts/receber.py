"""Grava os candles que chegam do TradingView (feed da Tickmill) em dados/tv/<ATIVO>_15m.csv (UTC).

Lê o JSON do evento da variável de ambiente CANDLE (o workflow receber.yml passa o client_payload).
Aceita os dois formatos do indicador:
  v2: {"tf":"15","v":2,"ativos":[{"s":"TICKMILL:EURUSD","b":[[t,o,h,l,c], ...]}, ...]}
  v1: {"tf":"15","velas":[{"s":"TICKMILL:EURUSD","t":..,"o":..,"h":..,"l":..,"c":..}, ...]}
Cada candle é gravado pela hora de abertura; se o mesmo candle chegar de novo,
a versão mais nova substitui a anterior (corrige candles que mudaram depois do fechamento).
Também grava dados/tv/ultimo_recebimento.json para o monitor de saúde da ponte.
"""
import json, os, csv, datetime as dt

BASE = os.path.join(os.path.dirname(__file__), "..", "dados", "tv")
ATIVOS = ("EURUSD", "USDJPY", "US500", "XAUUSD")
CAB = ["hora_utc", "abertura", "maxima", "minima", "fechamento"]


def nome_ativo(simbolo):
    s = simbolo.split(":")[-1].upper()
    return next((a for a in ATIVOS if s.startswith(a)), None)


def velas(ev):
    """Devolve [(ativo, t_ms, o, h, l, c)] dos dois formatos."""
    out = []
    for a in ev.get("ativos", []):
        ativo = nome_ativo(a.get("s", ""))
        for b in a.get("b", []) if ativo else []:
            if len(b) == 5 and all(x is not None for x in b):
                out.append((ativo, *b))
    for v in ev.get("velas", []):
        ativo = nome_ativo(v.get("s", ""))
        if ativo and all(v.get(x) not in (None, "NaN") for x in ("t", "o", "h", "l", "c")):
            out.append((ativo, v["t"], v["o"], v["h"], v["l"], v["c"]))
    return out


def gravar(ev, base=BASE):
    tf = {"15": "15m", "60": "1h"}.get(str(ev.get("tf", "15")), str(ev.get("tf")))
    os.makedirs(base, exist_ok=True)
    por_ativo = {}
    for ativo, t, o, h, l, c in velas(ev):
        hora = dt.datetime.fromtimestamp(int(float(t)) / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        o, h, l, c = (float(x) for x in (o, h, l, c))
        if not (l <= min(o, c) and h >= max(o, c) and l > 0):
            continue  # candle incoerente: ignora
        por_ativo.setdefault(ativo, {})[hora] = [hora, o, h, l, c]
    resumo = {}
    for ativo, novas in por_ativo.items():
        caminho = os.path.join(base, f"{ativo}_{tf}.csv")
        linhas = {}
        if os.path.exists(caminho):
            with open(caminho) as f:
                r = csv.reader(f); next(r, None)
                linhas = {l[0]: l for l in r if l}
        linhas.update(novas)
        with open(caminho, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(CAB)
            w.writerows(linhas[k] for k in sorted(linhas))
        resumo[ativo] = max(novas)
        print(ativo, tf, ", ".join(sorted(novas)))
    with open(os.path.join(base, "ultimo_recebimento.json"), "w") as f:
        json.dump({"recebido_utc": ev.get("recebido") or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                   "ultimo_candle_por_ativo": resumo}, f, ensure_ascii=False, indent=1)
    return resumo


if __name__ == "__main__":
    gravar(json.loads(os.environ["CANDLE"]))
