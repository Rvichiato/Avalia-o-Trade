"""Importa a exportação de dados do gráfico do TradingView (menu do gráfico → "Exportar dados do gráfico").

Uso: python scripts/importar_tv.py arquivo.csv [arquivo2.csv ...]
     python scripts/importar_tv.py --ativo US500 arquivo.csv

O ativo é reconhecido pelo nome do arquivo (ex.: "TICKMILL_EURUSD, 15_abc12.csv"); se não der,
use --ativo. Aceita a coluna de tempo em UNIX (segundos) ou em data ISO com fuso.
Só candles de 15 minutos. Grava em dados/tv/export/<ATIVO>_15m.csv (UTC), juntando com o que já existe.
O robô usa esses candles para tapar o período entre o histórico do MT5 e o início da ponte ao vivo.
"""
import sys, os, re
import pandas as pd

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SAIDA = os.path.join(RAIZ, "dados", "tv", "export")
ATIVOS = ("EURUSD", "USDJPY", "US500", "XAUUSD")


def ler_export(caminho):
    d = pd.read_csv(caminho)
    cols = {c.lower().strip(): c for c in d.columns}
    tcol = cols.get("time") or cols.get("tempo") or d.columns[0]
    t = d[tcol]
    if pd.api.types.is_numeric_dtype(t):
        idx = pd.to_datetime(t.astype("int64"), unit="s", utc=True)
    else:
        idx = pd.to_datetime(t, utc=True)
    pega = lambda nome: d[cols[nome]].astype(float).values
    df = pd.DataFrame({"abertura": pega("open"), "maxima": pega("high"), "minima": pega("low"),
                       "fechamento": pega("close")}, index=idx)
    df.index.name = "hora_utc"
    # o último candle da exportação ainda estava em formação: fica de fora
    df = df.sort_index().iloc[:-1]
    # a Tickmill no TradingView às vezes abre os candles em :02/:17/:32/:47 (começo da semana);
    # tudo vai para a grade de 15 min (:00/:15/:30/:45), a mesma do MT5 e do robô
    df.index = df.index.floor("15min")
    df = df[~df.index.duplicated(keep="last")]
    passo = df.index.to_series().diff().dropna().median()
    if passo != pd.Timedelta(minutes=15):
        raise SystemExit(f"{caminho}: os candles não são de 15 minutos (passo {passo}). Exporte o gráfico em 15m.")
    return df


def ativo_do_nome(caminho):
    nome = os.path.basename(caminho).upper()
    return next((a for a in ATIVOS if re.search(rf"(^|[^A-Z]){a}", nome)), None)


def gravar(ativo, df):
    os.makedirs(SAIDA, exist_ok=True)
    caminho = os.path.join(SAIDA, f"{ativo}_15m.csv")
    if os.path.exists(caminho):
        antigo = pd.read_csv(caminho, index_col=0)
        antigo.index = pd.to_datetime(antigo.index, utc=True)
        df = pd.concat([antigo, df])
        df = df[~df.index.duplicated(keep="last")].sort_index()
    df.to_csv(caminho, date_format="%Y-%m-%dT%H:%M:%SZ")
    return len(df), df.index[0], df.index[-1]


if __name__ == "__main__":
    args, forcado = sys.argv[1:], None
    if args[:1] == ["--ativo"]:
        forcado, args = args[1].upper(), args[2:]
    for arq in args:
        ativo = forcado or ativo_do_nome(arq)
        if not ativo:
            raise SystemExit(f"não reconheci o ativo em {arq}: use --ativo")
        print(ativo, *gravar(ativo, ler_export(arq)))
