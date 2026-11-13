"""Coleta candles do Yahoo Finance (via yfinance) e salva em dados/<ATIVO>_<tf>.csv (horário UTC).

Ativos: EURUSD, USDJPY, US500 (futuro do S&P 500, ES=F), XAUUSD (futuro do ouro, GC=F).
Tempos: 15m (últimos 30 dias) e 1h (últimos 180 dias). O 4H é montado a partir do 1h.
Só candles fechados são gravados; o candle em formação vai para dados/ultimo.json.
"""
import json, sys, time, os, datetime as dt
import pandas as pd
import yfinance as yf

ATIVOS = {"EURUSD": "EURUSD=X", "USDJPY": "JPY=X", "US500": "ES=F", "XAUUSD": "GC=F"}
TEMPOS = {"15m": ("15m", "30d", 900), "1h": ("60m", "180d", 3600)}
BASE = os.path.join(os.path.dirname(__file__), "..", "dados")

def baixar(simbolo, intervalo, periodo):
    for tentativa in range(3):
        try:
            df = yf.Ticker(simbolo).history(interval=intervalo, period=periodo, prepost=True, auto_adjust=False)
            if len(df):
                return df
            raise RuntimeError("resposta vazia")
        except Exception as e:
            print(f"  {simbolo} {intervalo} tentativa {tentativa+1} falhou: {e}", file=sys.stderr)
            time.sleep(5 * (tentativa + 1))
    raise RuntimeError(f"falha ao baixar {simbolo} {intervalo}")

def main():
    os.makedirs(BASE, exist_ok=True)
    agora = pd.Timestamp.now(tz="UTC")
    ultimo, erros = {}, []
    for nome, simbolo in ATIVOS.items():
        for tf, (intervalo, periodo, seg) in TEMPOS.items():
            try:
                df = baixar(simbolo, intervalo, periodo)
            except Exception as e:
                erros.append(str(e)); continue
            df = df[["Open", "High", "Low", "Close"]].dropna()
            df.index = df.index.tz_convert("UTC")
            fechado = df.index + pd.Timedelta(seconds=seg) <= agora
            if (~fechado).any():
                t = df.index[~fechado][-1]; r = df.loc[t]
                ultimo[f"{nome}_{tf}"] = [t.strftime("%Y-%m-%dT%H:%M:%SZ")] + [round(float(x), 6) for x in r]
            out = df[fechado].round(6)
            out.index = out.index.strftime("%Y-%m-%dT%H:%M:%SZ")
            out.index.name = "hora_utc"
            out.columns = ["abertura", "maxima", "minima", "fechamento"]
            out.to_csv(os.path.join(BASE, f"{nome}_{tf}.csv"))
            print(f"{nome} {tf}: {len(out)} candles fechados, último {out.index[-1]}")
            time.sleep(1)
    with open(os.path.join(BASE, "ultimo.json"), "w") as f:
        json.dump({"coletado_utc": agora.strftime("%Y-%m-%dT%H:%M:%SZ"), "em_formacao": ultimo, "erros": erros}, f, indent=1)
    if len(erros) == len(ATIVOS) * len(TEMPOS):
        sys.exit("nenhum dado coletado")

if __name__ == "__main__":
    main()
