"""Grava os candles recebidos do TradingView (feed da Tickmill) em dados/tv/<ATIVO>_15m.csv (UTC).
Lê o JSON do evento a partir da variável de ambiente CANDLE."""
import json, os, csv, datetime as dt

BASE = os.path.join(os.path.dirname(__file__), "..", "dados", "tv")
NOMES = {"EURUSD": "EURUSD", "USDJPY": "USDJPY", "US500": "US500"}


def main():
    ev = json.loads(os.environ["CANDLE"])
    tf = {"15": "15m", "60": "1h"}.get(str(ev.get("tf")), str(ev.get("tf")))
    os.makedirs(BASE, exist_ok=True)
    for v in ev.get("velas", []):
        sim = v["s"].split(":")[-1]
        ativo = next((n for k, n in NOMES.items() if sim.startswith(k)), None)
        if ativo is None or v.get("t") in (None, "NaN"):
            continue
        hora = dt.datetime.fromtimestamp(int(float(v["t"])) / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        linha = [hora] + [float(v[x]) for x in ("o", "h", "l", "c")]
        caminho = os.path.join(BASE, f"{ativo}_{tf}.csv")
        linhas = {}
        if os.path.exists(caminho):
            with open(caminho) as f:
                r = csv.reader(f); next(r, None)
                linhas = {l[0]: l for l in r}
        linhas[hora] = linha
        with open(caminho, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["hora_utc", "abertura", "maxima", "minima", "fechamento"])
            w.writerows(linhas[k] for k in sorted(linhas))
        print(ativo, tf, hora, linha[1:])


if __name__ == "__main__":
    main()
