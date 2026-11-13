"""Motor do sistema Break & Retest: carrega candles, acha linhas de tendência,
níveis horizontais, estado do rompimento/reteste/confirmação e monta planos.

Tudo trabalha sobre os CSVs de dados/ (UTC). Nada aqui decide sozinho se entra:
o resultado é um rascunho estruturado que a análise diária revisa.
"""
import json, os, math
import numpy as np
import pandas as pd

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CFG = json.load(open(os.path.join(RAIZ, "config", "regras.json")))
TF_MIN = {"15m": 15, "1h": 60, "4h": 240}


# ---------------------------------------------------------------- dados
def _ler(ativo, tf):
    df = pd.read_csv(os.path.join(RAIZ, "dados", f"{ativo}_{tf}.csv"), index_col=0)
    df.index = pd.to_datetime(df.index, utc=True)
    df.columns = ["o", "h", "l", "c"]
    return df.sort_index()


def _limpar_picos(df, k):
    """Corta pavios absurdos (dados do Yahoo às vezes trazem um pico isolado)."""
    rng = (df.h - df.l)
    med = rng.rolling(50, min_periods=10).median().bfill()
    corpo_hi = df[["o", "c"]].max(axis=1)
    corpo_lo = df[["o", "c"]].min(axis=1)
    lim = k * med
    df = df.copy()
    df["h"] = np.where(df.h - corpo_hi > lim, corpo_hi + med, df.h)
    df["l"] = np.where(corpo_lo - df.l > lim, corpo_lo - med, df.l)
    viz_l = pd.concat([df.l.shift(1), df.l.shift(-1)], axis=1).min(axis=1)
    viz_h = pd.concat([df.h.shift(1), df.h.shift(-1)], axis=1).max(axis=1)
    k2 = 4 * med
    df["l"] = np.where(viz_l - df.l > k2, np.minimum(corpo_lo, viz_l) - med * 0.5, df.l)
    df["h"] = np.where(df.h - viz_h > k2, np.maximum(corpo_hi, viz_h) + med * 0.5, df.h)
    return df


def ajuste_us500():
    """Diferença futuro (ES) menos índice à vista (SPX), mediana dos 15m em comum
    nos últimos 2 pregões. O US500 da Tickmill segue o à vista."""
    try:
        es, spx = _ler("US500", "15m"), _ler("SPX", "15m")
    except FileNotFoundError:
        return 0.0, "sem dados do índice à vista; níveis do US500 na escala do futuro"
    comum = es.c.to_frame("es").join(spx.c.to_frame("spx"), how="inner").dropna()
    if len(comum) < 5:
        return 0.0, "poucos candles em comum; níveis do US500 na escala do futuro"
    dias = sorted(set(comum.index.date))[-2:]
    sel = comum[[d in dias for d in comum.index.date]]
    off = float((sel.es - sel.spx).median())
    return off, f"futuro {off:+.1f} pontos acima do à vista (mediana de {len(sel)} candles)"


def carregar(ativo, tf, ajuste=0.0):
    base = "1h" if tf == "4h" else tf
    df = _ler(ativo, base)
    df = _limpar_picos(df, CFG["filtro_picos_atr"])
    if ajuste:
        df = df - ajuste
    if tf == "4h":
        off = pd.Timedelta(hours=CFG["abertura_4h_utc"] % 4)
        df = df.resample("4h", offset=off, label="left", closed="left").agg(
            {"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
    return df


def atr(df, n=14):
    pc = df.c.shift()
    tr = pd.concat([df.h - df.l, (df.h - pc).abs(), (df.l - pc).abs()], axis=1).max(axis=1)
    return float(tr.rolling(n).mean().iloc[-1])


# ---------------------------------------------------------------- pivôs
def pivos(serie, k, tipo):
    v = serie.values
    out = []
    for i in range(k, len(v) - k):
        jan = v[i - k:i + k + 1]
        if tipo == "topo" and v[i] == jan.max() and (jan == v[i]).sum() == 1:
            out.append(i)
        if tipo == "fundo" and v[i] == jan.min() and (jan == v[i]).sum() == 1:
            out.append(i)
    # o extremo absoluto da janela também conta, mesmo perto das bordas
    j = int(np.argmax(v) if tipo == "topo" else np.argmin(v))
    if j not in out and k <= j:
        out.append(j)
    return sorted(out)


# ---------------------------------------------------------------- linhas
def linhas(df, tf, ativo):
    """LTB liga topos descendentes; LTA liga fundos ascendentes.
    Uma linha vale se nenhum pavio a atravessa entre os dois pontos de apoio.
    Rompimento = primeiro candle que FECHA além da linha depois do 2º apoio."""
    p = CFG["tempos"][tf]; L = CFG["linhas"]
    d = df.iloc[-p["janela"]:].reset_index()
    a = atr(df); tol = L["tolerancia_atr"] * a
    n = len(d); res = []
    for tipo, col, sinal in (("LTB", "h", -1), ("LTA", "l", +1)):
        v = d[col].values
        piv = pivos(d[col], p["pivo"], "topo" if tipo == "LTB" else "fundo")
        for ia, A in enumerate(piv):
            for B in piv[ia + 1:]:
                if B - A < p["intervalo_min_linha"] or B > n - 3:
                    continue
                if sinal * (v[B] - v[A]) <= 0:  # LTB tem que cair, LTA tem que subir
                    continue
                s = (v[B] - v[A]) / (B - A)
                f = lambda x, A=A, s=s: v[A] + s * (x - A)
                xs = np.arange(A + 1, B)
                if tipo == "LTB" and (v[xs] > f(xs) + tol).any():
                    continue
                if tipo == "LTA" and (v[xs] < f(xs) - tol).any():
                    continue
                # rompimento por fechamento
                rompe = None
                for x in range(B + 1, n):
                    if tipo == "LTB" and d.c.values[x] > f(x) + tol * 0.5:
                        rompe = x; break
                    if tipo == "LTA" and d.c.values[x] < f(x) - tol * 0.5:
                        rompe = x; break
                fim = rompe if rompe is not None else n
                toques = [i for i in piv if A <= i < fim and abs(v[i] - f(i)) <= tol]
                if len(toques) < L["toques_minimos"]:
                    continue
                res.append(dict(tipo=tipo, A=A, B=B, s=s, toques=toques, rompe=rompe,
                                agora=float(f(n - 1)), proximo=float(f(n))))
    # pontuação: mais toques, mais longa, mais recente, mais perto do preço
    preco = d.c.values[-1]
    for r in res:
        dist = abs(r["proximo"] - preco) / a
        idade = (n - 1 - r["toques"][-1]) / n
        r["nota"] = 2 * len(r["toques"]) + (r["B"] - r["A"]) / n * 3 - 0.4 * dist - 2 * idade
    res.sort(key=lambda r: -r["nota"])
    # remove duplicadas (mesma região e inclinação parecida)
    finais = []
    for r in res:
        if any(r["tipo"] == q["tipo"] and abs(r["proximo"] - q["proximo"]) < 0.6 * a
               and (r["rompe"] is None) == (q["rompe"] is None) for q in finais):
            continue
        finais.append(r)
    ativas = [r for r in finais if r["rompe"] is None][:2]
    recentes = [r for r in finais if r["rompe"] is not None
                and n - 1 - r["rompe"] <= L["rompimento_recente_barras"]][:1]
    out = []
    for r in ativas + recentes:
        t = d["hora_utc"] if "hora_utc" in d else d.iloc[:, 0]
        mins = TF_MIN[tf]
        out.append(dict(
            tipo=r["tipo"], tf=tf,
            a_hora=str(t.iloc[r["A"]]), a_preco=float(d[("h" if r["tipo"] == "LTB" else "l")].iloc[r["A"]]),
            b_hora=str(t.iloc[r["B"]]), b_preco=float(d[("h" if r["tipo"] == "LTB" else "l")].iloc[r["B"]]),
            toques=len(r["toques"]),
            toques_idx=[int(i - n) for i in r["toques"]],
            a_idx=int(r["A"] - n), b_idx=int(r["B"] - n),
            inclinacao_por_hora=float(r["s"] * 60 / mins),
            valor_agora=r["agora"], valor_proximo=r["proximo"],
            rompida=r["rompe"] is not None,
            rompe_idx=None if r["rompe"] is None else int(r["rompe"] - n),
            rompe_hora=None if r["rompe"] is None else str(t.iloc[r["rompe"]]),
        ))
    return out


# ---------------------------------------------------------------- níveis
def niveis(df, tf, ativo):
    p = CFG["tempos"][tf]; N = CFG["niveis"]
    d = df.iloc[-p["janela"]:]
    a = atr(df); larg = N["agrupar_atr"] * a
    pts = [(float(d.h.iloc[i]), i, "topo") for i in pivos(d.h, p["pivo"], "topo")]
    pts += [(float(d.l.iloc[i]), i, "fundo") for i in pivos(d.l, p["pivo"], "fundo")]
    pts.sort()
    grupos, atual = [], []
    for pt in pts:
        if atual and pt[0] - atual[0][0] > larg:
            grupos.append(atual); atual = []
        atual.append(pt)
    if atual:
        grupos.append(atual)
    out = []
    n = len(d)
    for g in grupos:
        if len(g) < N["toques_minimos"]:
            continue
        precos = [x[0] for x in g]
        out.append(dict(tf=tf, de=min(precos), ate=max(precos), meio=float(np.median(precos)),
                        toques=len(g), ultimo_idx=int(max(x[1] for x in g) - n),
                        papeis=sorted(set(x[2] for x in g))))
    return out


def redondos(ativo, preco, qtd=2):
    r = CFG["ativos"][ativo]["redondo"]
    base = math.floor(preco / r) * r
    return [round(base - i * r, 6) for i in range(qtd - 1, -1, -1)] + \
           [round(base + (i + 1) * r, 6) for i in range(qtd)]


# ---------------------------------------------------------------- dinheiro
def valor_pip_lote(ativo, preco):
    v = CFG["ativos"][ativo]["valor_pip_lote"]
    return 1000.0 / preco if v == "1000/preco" else float(v)


def dimensionar(ativo, preco, stop_pips):
    c = CFG["conta"]; A = CFG["ativos"][ativo]
    risco = c["capital_usd"] * c["risco_pct"] / 100
    vpl = valor_pip_lote(ativo, preco)
    lote = math.floor(risco / (stop_pips * vpl) * 100) / 100
    com = A.get("comissao_usd_por_lote_ida_volta", c["comissao_usd_por_lote_ida_volta"])
    return dict(risco_usd=risco, lote=max(lote, 0.0), cabe_na_conta=lote >= 0.01,
                risco_real_usd=round(max(lote, 0.01) * stop_pips * vpl, 2),
                custo_comissao_usd=round(max(lote, 0.01) * com, 2))


# ---------------------------------------------------------------- estado do gatilho
def estado_gatilho(df15, nivel, direcao, a15, barras=24, desde=None):
    """Procura nos últimos candles de 15m: rompimento (fechamento além do nível),
    reteste (volta a tocar o nível pelo outro lado) e confirmação (fecha a favor)."""
    ini = -barras if desde is None else max(-barras, desde + 1)
    d = df15.iloc[ini:] if ini < 0 else df15.iloc[0:0]
    tol = 0.1 * a15
    passos = {"rompimento": None, "reteste": None, "confirmacao": None}
    for i, (t, r) in enumerate(d.iterrows()):
        if passos["rompimento"] is None:
            if (direcao == "venda" and r.c < nivel - tol) or (direcao == "compra" and r.c > nivel + tol):
                passos["rompimento"] = str(t)
            continue
        if passos["reteste"] is None:
            if (direcao == "venda" and r.h >= nivel - tol) or (direcao == "compra" and r.l <= nivel + tol):
                passos["reteste"] = str(t)
                if (direcao == "venda" and r.c < r.o and r.c < nivel) or \
                   (direcao == "compra" and r.c > r.o and r.c > nivel):
                    passos["confirmacao"] = str(t); break
            continue
        if (direcao == "venda" and r.c < r.o and r.c < nivel) or (direcao == "compra" and r.c > r.o and r.c > nivel):
            passos["confirmacao"] = str(t); break
        if (direcao == "venda" and r.c > nivel + tol) or (direcao == "compra" and r.c < nivel - tol):
            passos = {"rompimento": None, "reteste": None, "confirmacao": None, "falhou": str(t)}
    if passos.get("confirmacao"):
        depois = df15.loc[df15.index > pd.Timestamp(passos["confirmacao"])]
        volta = depois[(depois.c > nivel + tol) if direcao == "venda" else (depois.c < nivel - tol)]
        if len(volta):
            passos["invalidado_depois"] = str(volta.index[0])
    return passos


# ---------------------------------------------------------------- planos
def planos(ativo, dfs, lin, niv):
    A = CFG["ativos"][ativo]; pip = A["pip"]
    d15 = dfs["15m"]; preco = float(d15.c.iloc[-1])
    a15, a1 = atr(d15), atr(dfs["1h"])
    buf = max(A["spread_pips"] * pip * 2, 0.1 * a15)
    buf_alvo = max(buf, 0.8 * a15)  # alvo fica antes do obstáculo, não em cima dele
    # gatilhos: níveis do 1h/15m perto do preço + linhas ativas do 15m/1h
    zonas = [z for z in niv["1h"] + niv["15m"]
             if abs(z["meio"] - preco) <= CFG["niveis"]["distancia_max_atr_1h"] * a1]
    zonas = [dict(z) for z in zonas]
    # junta zonas sobrepostas de tempos diferentes
    zonas.sort(key=lambda z: z["meio"])
    uni = []
    for z in zonas:
        if uni and z["de"] <= uni[-1]["ate"] + 0.5 * a15:
            u = uni[-1]; u["de"] = min(u["de"], z["de"]); u["ate"] = max(u["ate"], z["ate"])
            u["toques"] += z["toques"]; u["tfs"] = sorted(set(u["tfs"] + [z["tf"]]))
        else:
            uni.append(dict(de=z["de"], ate=z["ate"], toques=z["toques"], tfs=[z["tf"]], ultimo_idx=z["ultimo_idx"]))
            continue
        uni[-1]["ultimo_idx"] = max(uni[-1]["ultimo_idx"], z["ultimo_idx"]) if z["tf"] == "15m" else uni[-1]["ultimo_idx"]
    for u in uni:
        u["meio"] = (u["de"] + u["ate"]) / 2
    uni = [u for u in uni if u["toques"] >= 3 or "1h" in u["tfs"]]
    rd = redondos(ativo, preco, 3)
    alvos_baixo = sorted([u["ate"] for u in uni if u["ate"] < preco] + [x for x in rd if x < preco], reverse=True)
    alvos_cima = sorted([u["de"] for u in uni if u["de"] > preco] + [x for x in rd if x > preco])
    out = []

    def montar(direcao, gatilho_nome, nivel_lo, nivel_hi, origem, desde=None):
        piv_h = [float(d15.h.iloc[i]) for i in pivos(d15.h.iloc[-48:], 2, "topo")]
        piv_l = [float(d15.l.iloc[i]) for i in pivos(d15.l.iloc[-48:], 2, "fundo")]
        if direcao == "venda":
            entrada = nivel_lo - buf
            acima = [x for x in piv_h if x > nivel_hi + 0.5 * a15]
            ref = min(acima) if acima else nivel_hi + 1.5 * a15
            stop = min(max(ref, nivel_hi + 1.5 * a15), nivel_hi + 4 * a15) + buf
            cands = [x for x in alvos_baixo if x + buf_alvo < entrada - 0.5 * a15]
            alvo = cands[0] + buf_alvo if cands else None
        else:
            entrada = nivel_hi + buf
            abaixo = [x for x in piv_l if x < nivel_lo - 0.5 * a15]
            ref = max(abaixo) if abaixo else nivel_lo - 1.5 * a15
            stop = max(min(ref, nivel_lo - 1.5 * a15), nivel_lo - 4 * a15) - buf
            cands = [x for x in alvos_cima if x - buf_alvo > entrada + 0.5 * a15]
            alvo = cands[0] - buf_alvo if cands else None
        stop_p = abs(entrada - stop) / pip
        alvo_p = abs(alvo - entrada) / pip if alvo is not None else None
        rr = alvo_p / stop_p if alvo_p else None
        # Modo A: alvo antes do primeiro obstáculo. O seguinte fica anotado para o Modo B.
        obs_alvo = None
        alvo_estendido = None
        if len(cands) > 1:
            alvo_estendido = cands[1] + (buf_alvo if direcao == "venda" else -buf_alvo)
        if rr is not None and rr < CFG["conta"]["rr_minimo"]:
            obs_alvo = f"primeiro obstáculo em {cands[0]:.{A['casas']}f} deixa só {rr:.1f}R"
        tam = dimensionar(ativo, preco, stop_p)
        nivel_ref = nivel_lo if direcao == "venda" else nivel_hi
        est = estado_gatilho(d15, nivel_ref, direcao, a15, desde=desde)
        out.append(dict(
            direcao=direcao, gatilho=gatilho_nome, origem=origem,
            nivel_de=nivel_lo, nivel_ate=nivel_hi,
            entrada=entrada, stop=stop, alvo=alvo,
            stop_pips=round(stop_p, 1), alvo_pips=None if alvo_p is None else round(alvo_p, 1),
            rr=None if rr is None else round(rr, 2), obs_alvo=obs_alvo,
            alvo_estendido=alvo_estendido,
            distancia_preco_pips=round(abs(preco - nivel_ref) / pip, 1),
            tamanho=tam, estado=est,
            valido=bool(rr and rr >= CFG["conta"]["rr_minimo"] and tam["cabe_na_conta"]),
        ))

    sup = [u for u in uni if u["ate"] < preco]
    res = [u for u in uni if u["de"] > preco]
    if sup:
        s = max(sup, key=lambda u: u["ate"])
        montar("venda", f"rompimento do suporte {s['de']:.{A['casas']}f}–{s['ate']:.{A['casas']}f}",
               s["de"], s["ate"], dict(tipo="suporte", toques=s["toques"], tempos=s["tfs"]), s["ultimo_idx"])
    if res:
        r = min(res, key=lambda u: u["de"])
        montar("compra", f"rompimento da resistência {r['de']:.{A['casas']}f}–{r['ate']:.{A['casas']}f}",
               r["de"], r["ate"], dict(tipo="resistencia", toques=r["toques"], tempos=r["tfs"]), r["ultimo_idx"])
    for l in lin.get("15m", []) + lin.get("1h", []):
        if l["rompida"]:
            continue
        v = l["valor_proximo"]
        if abs(v - preco) > 2 * a1:
            continue
        if l["tipo"] == "LTB" and v > preco:
            montar("compra", f"rompimento da LTB do {l['tf']} (hoje em {v:.{A['casas']}f})",
                   v - 0.1 * a15, v, dict(tipo="LTB", tf=l["tf"], toques=l["toques"], incl_h=l["inclinacao_por_hora"]),
                   l["toques_idx"][-1] if l["tf"] == "15m" else None)
        if l["tipo"] == "LTA" and v < preco:
            montar("venda", f"rompimento da LTA do {l['tf']} (hoje em {v:.{A['casas']}f})",
                   v, v + 0.1 * a15, dict(tipo="LTA", tf=l["tf"], toques=l["toques"], incl_h=l["inclinacao_por_hora"]),
                   l["toques_idx"][-1] if l["tf"] == "15m" else None)
    out.sort(key=lambda p: (not p["valido"], -(p["rr"] or 0)))
    finais = []
    for p in out:
        if any(q["direcao"] == p["direcao"] and abs(q["entrada"] - p["entrada"]) < 0.5 * a15 for q in finais):
            continue
        finais.append(p)
    return finais, uni, rd


# ---------------------------------------------------------------- tudo junto
def analisar(ativo):
    ajuste, nota = (0.0, None)
    if CFG["ativos"][ativo].get("ajuste_futuro"):
        ajuste, nota = ajuste_us500()
    dfs = {tf: carregar(ativo, tf, ajuste) for tf in ("4h", "1h", "15m")}
    return analisar_dfs(ativo, dfs, nota), dfs


def analisar_dfs(ativo, dfs, nota=None):
    """Mesma análise, sobre dataframes já cortados (o teste histórico usa isto
    com os dados cortados no instante simulado, sem ver o futuro)."""
    lin = {tf: linhas(dfs[tf], tf, ativo) for tf in dfs}
    niv = {tf: niveis(dfs[tf], tf, ativo) for tf in dfs}
    pl, zonas, rd = planos(ativo, dfs, lin, niv)
    d15 = dfs["15m"]
    tend = {}
    for tf, df in dfs.items():
        c = df.c.iloc[-60:]
        tend[tf] = "alta" if c.iloc[-1] > c.mean() + 0.3 * atr(df) and c.iloc[-1] > c.iloc[0] else \
                   "baixa" if c.iloc[-1] < c.mean() - 0.3 * atr(df) and c.iloc[-1] < c.iloc[0] else "lateral"
    return dict(
        ativo=ativo, nome=CFG["ativos"][ativo]["nome"],
        ultimo_candle_15m_utc=str(d15.index[-1]), preco=float(d15.c.iloc[-1]),
        ajuste_us500=nota, atr={tf: atr(dfs[tf]) for tf in dfs},
        tendencia=tend, linhas=lin, niveis=niv, zonas=zonas, redondos=rd, planos=pl,
        dia_anterior=_dia_anterior(dfs["1h"]),
    )


def _dia_anterior(d1):
    """Máxima e mínima do dia anterior (dia do forex vira às 19h de Brasília)."""
    t = d1.index - pd.Timedelta(hours=CFG["abertura_4h_utc"])
    dias = sorted(set(t.date))
    if len(dias) < 2:
        return None
    ontem = d1[t.date == dias[-2]]
    return dict(data=str(dias[-2]), maxima=float(ontem.h.max()), minima=float(ontem.l.min()))
