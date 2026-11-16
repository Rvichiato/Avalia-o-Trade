"""Importa o histórico exportado do MetaTrader 5 (Tickmill) para dados/mt5/.

Uso: python scripts/importar_mt5.py ATIVO arquivo.csv [ATIVO arquivo.csv ...]
O MT5 exporta no horário do servidor da Tickmill: GMT+2 no inverno e GMT+3 no verão,
seguindo o horário de verão dos EUA (equivale ao horário de Nova York + 7h).
Grava <ATIVO>_15m.csv e <ATIVO>_1h.csv em UTC, no mesmo formato da coleta.
"""
import sys, os
import pandas as pd

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SAIDA = os.path.join(RAIZ, "dados", "mt5")


def ler_mt5(caminho):
    d = pd.read_csv(caminho, sep="\t")
    t = pd.to_datetime(d["<DATE>"] + " " + d["<TIME>"], format="%Y.%m.%d %H:%M:%S") - pd.Timedelta(hours=7)
    t = t.dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    df = pd.DataFrame({"abertura": d["<OPEN>"].values, "maxima": d["<HIGH>"].values,
                       "minima": d["<LOW>"].values, "fechamento": d["<CLOSE>"].values,
                       "spread_pontos": d["<SPREAD>"].values}, index=t)
    df = df[df.index.notna()]
    df.index.name = "hora_utc"
    return df[~df.index.duplicated()].sort_index()


def gravar(ativo, df):
    os.makedirs(SAIDA, exist_ok=True)
    fmt = lambda x: x.strftime("%Y-%m-%dT%H:%M:%SZ")
    m15 = df[["abertura", "maxima", "minima", "fechamento"]]
    m15.to_csv(os.path.join(SAIDA, f"{ativo}_15m.csv"), date_format="%Y-%m-%dT%H:%M:%SZ")
    h1 = m15.resample("1h", label="left", closed="left").agg(
        {"abertura": "first", "maxima": "max", "minima": "min", "fechamento": "last"}).dropna()
    h1.to_csv(os.path.join(SAIDA, f"{ativo}_1h.csv"), date_format="%Y-%m-%dT%H:%M:%SZ")
    return len(m15), len(h1), m15.index[0], m15.index[-1]


if __name__ == "__main__":
    args = sys.argv[1:]
    for ativo, arq in zip(args[::2], args[1::2]):
        print(ativo, *gravar(ativo, ler_mt5(arq)))
