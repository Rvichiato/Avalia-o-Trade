"""Grava os candles que chegam do TradingView (feed da Tickmill) em dados/tv/<ATIVO>_15m.csv (UTC).

Lê o JSON do evento da variável de ambiente CANDLE (o workflow receber.yml passa o client_payload).
Aceita os dois formatos do indicador:
  v2: {"tf":"15","v":2,"ativos":[{"s":"TICKMILL:EURUSD","b":[[t,o,h,l,c], ...]}, ...]}
  v3 (preço do momento): {"v":3,"agora":{"t":ms,"ativos":[{"s":..,"b":[t,o,h,l,c]}]}} → dados/tv/agora.json
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


def gravar_agora(ev, base=BASE):
    """Preço do momento (v3): candle de 15m ainda aberto de cada ativo. Vai só para dados/tv/agora.json,
    nunca para os CSVs de candles fechados."""
    ag = ev["agora"]
    env = dt.datetime.fromtimestamp(int(float(ag.get("t", 0))) / 1000, dt.timezone.utc)
    ativos = {}
    for a in ag.get("ativos", []):
        ativo = nome_ativo(a.get("s", ""))
        b = a.get("b")
        if not ativo or not b or len(b) != 5 or any(x is None for x in b):
            continue
        t, o, h, l, c = b
        if not (float(l) <= min(float(o), float(c)) and float(h) >= max(float(o), float(c)) and float(l) > 0):
            continue
        seg = int(float(t)) // 1000
        seg -= seg % 900
        ativos[ativo] = dict(candle_abertura_utc=dt.datetime.fromtimestamp(seg, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                             abertura=float(o), maxima=float(h), minima=float(l), preco=float(c))
    if not ativos:
        return {}
    os.makedirs(base, exist_ok=True)
    with open(os.path.join(base, "agora.json"), "w") as f:
        json.dump({"enviado_utc": env.strftime("%Y-%m-%dT%H:%M:%SZ"), "recebido_utc": ev.get("recebido"),
                   "ativos": ativos}, f, ensure_ascii=False, indent=1)
    print("agora", env.strftime("%H:%MZ"), ", ".join(f"{k} {v['preco']}" for k, v in ativos.items()))
    return ativos


def gravar(ev, base=BASE):
    if "agora" in ev:
        return gravar_agora(ev, base)
    tf = {"15": "15m", "60": "1h"}.get(str(ev.get("tf", "15")), str(ev.get("tf")))
    try:
        agora = dt.datetime.fromisoformat(str(ev.get("recebido")).replace("Z", "+00:00"))
    except ValueError:
        agora = dt.datetime.now(dt.timezone.utc)
    os.makedirs(base, exist_ok=True)
    por_ativo = {}
    for ativo, t, o, h, l, c in velas(ev):
        seg = int(float(t)) // 1000
        seg -= seg % 900  # grade de 15 min: a Tickmill às vezes abre os candles em :02/:17/:32/:47
        if dt.datetime.fromtimestamp(seg + 900, dt.timezone.utc) > agora + dt.timedelta(minutes=3):
            continue  # candle ainda em formação (ex.: US500 em :00 quando o gráfico fecha em :02): chega fechado no próximo envio
        hora = dt.datetime.fromtimestamp(seg, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
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
                for l in r:
                    if not l:
                        continue
                    t = dt.datetime.strptime(l[0], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
                    t -= dt.timedelta(minutes=t.minute % 15, seconds=t.second)  # normaliza linhas antigas para a grade
                    k = t.strftime("%Y-%m-%dT%H:%M:%SZ")
                    linhas[k] = [k] + l[1:]
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
