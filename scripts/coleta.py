"""Coleta candles do Yahoo Finance e salva em dados/<ATIVO>_<tf>.csv (horário UTC).

Ativos: EURUSD, USDJPY, US500 (futuro do S&P 500, ES=F), XAUUSD (futuro do ouro, GC=F).
Tempos: 15m (últimos 30 dias) e 1h (últimos 180 dias). O 4H é montado a partir do 1h.
Só candles fechados são gravados; o candle em formação vai para dados/ultimo.json.
"""
import json, sys, time, csv, os, datetime as dt
import urllib.request

ATIVOS = {"EURUSD": "EURUSD=X", "USDJPY": "JPY=X", "US500": "ES=F", "XAUUSD": "GC=F"}
TEMPOS = {"15m": ("15m", "30d", 900), "1h": ("60m", "180d", 3600)}
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
BASE = os.path.join(os.path.dirname(__file__), "..", "dados")

def baixar(simbolo, intervalo, periodo):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}"
           f"?interval={intervalo}&range={periodo}&includePrePost=true")
    for tentativa in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)["chart"]["result"][0]
        except Exception as e:
            print(f"  tentativa {tentativa+1} falhou: {e}", file=sys.stderr)
            time.sleep(3 * (tentativa + 1))
    raise RuntimeError(f"falha ao baixar {simbolo} {intervalo}")

def main():
    agora = int(time.time())
    ultimo, erros = {}, []
    for nome, simbolo in ATIVOS.items():
        for tf, (intervalo, periodo, seg) in TEMPOS.items():
            try:
                res = baixar(simbolo, intervalo, periodo)
            except Exception as e:
                erros.append(str(e)); continue
            ts = res.get("timestamp") or []
            q = res["indicators"]["quote"][0]
            linhas = []
            for i, t in enumerate(ts):
                o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
                if None in (o, h, l, c):
                    continue
                fechado = t + seg <= agora
                reg = [dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                       round(o, 6), round(h, 6), round(l, 6), round(c, 6)]
                if fechado:
                    linhas.append(reg)
                else:
                    ultimo[f"{nome}_{tf}"] = reg
            caminho = os.path.join(BASE, f"{nome}_{tf}.csv")
            with open(caminho, "w", newline="") as f:
                w = csv.writer(f); w.writerow(["hora_utc", "abertura", "maxima", "minima", "fechamento"]); w.writerows(linhas)
            print(f"{nome} {tf}: {len(linhas)} candles fechados")
    with open(os.path.join(BASE, "ultimo.json"), "w") as f:
        json.dump({"coletado_utc": dt.datetime.fromtimestamp(agora, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "em_formacao": ultimo, "erros": erros}, f, indent=1)
    if len(erros) == len(ATIVOS) * len(TEMPOS):
        sys.exit("nenhum dado coletado")

if __name__ == "__main__":
    main()
