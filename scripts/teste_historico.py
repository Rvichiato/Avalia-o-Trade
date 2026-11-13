"""Teste histórico (walk-forward) do sistema Break & Retest.

A cada hora cheia dentro da sessão, o motor roda SÓ com os candles já fechados
naquele instante (nada do futuro). Cada plano válido é então simulado candle a
candle no 15m, de dois jeitos:
  sistema : rompimento -> reteste -> confirmação -> entra na abertura do candle seguinte
  direto  : entra no fechamento do próprio candle de rompimento (hipótese a testar)
Custos: spread + comissão + deslizamento, descontados em R.
Se stop e alvo são tocados no mesmo candle, conta stop (conservador).

Uso: python scripts/teste_historico.py [ATIVOS...] [--saida testes/AAAA-MM-DD]
"""
import sys, os, json, argparse, math, random
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import sistema as S

C = S.CFG
P = {
    "validade_plano_barras": 16,     # 4h para o rompimento acontecer
    "barras_reteste": 16,            # 4h entre rompimento e confirmação
    "max_barras_posicao": 48,        # 12h no máximo dentro do trade
    "deslizamento_pips": 0.2,
    "intervalo_decisao_min": 60,
    "duplicata_atr": 0.5,
    "bootstrap": 3000,
    "stop_minimo_atr": 0.75,         # stop menor que isso (ou que 3x o custo) não é operável
}
UTC = pd.Timedelta(0)


def sessao_ok(ativo, t_utc):
    """Rompimento só conta em Londres ou Nova York; US500 só no pregão (11h45–18h Brasília)."""
    brt = t_utc + pd.Timedelta(hours=C["fuso_exibicao_horas"])
    h = brt.hour + brt.minute / 60
    if brt.weekday() >= 5:
        return False
    if C["ativos"][ativo]["sessao"] == "indice":
        return 11.75 <= h < 18.0
    return 5.0 <= h < 19.0


def nome_sessao(t_utc):
    brt = t_utc + pd.Timedelta(hours=C["fuso_exibicao_horas"])
    h = brt.hour + brt.minute / 60
    if 10 <= h < 14:
        return "sobreposição Londres+NY"
    if 5 <= h < 10:
        return "Londres"
    if 14 <= h < 19:
        return "Nova York"
    return "fora"


def custo_pips(ativo, preco):
    A = C["ativos"][ativo]
    com = A.get("comissao_usd_por_lote_ida_volta", C["conta"]["comissao_usd_por_lote_ida_volta"])
    vpl = S.valor_pip_lote(ativo, preco)
    return A["spread_pips"] + com / vpl + 2 * P["deslizamento_pips"]


def gerenciar(d15, i0, direcao, entrada, stop, alvo, ativo):
    """Acompanha a posição a partir do candle i0 (inclusive). Retorna (saida, motivo, i_saida)."""
    fim = min(len(d15), i0 + P["max_barras_posicao"])
    for i in range(i0, fim):
        r = d15.iloc[i]
        t = d15.index[i]
        if C["ativos"][ativo]["sessao"] == "indice":
            brt = t + pd.Timedelta(hours=C["fuso_exibicao_horas"])
            if brt.hour + brt.minute / 60 >= 17.75:
                return float(r.o), "fechamento 17h45", i
        bate_stop = r.h >= stop if direcao == "venda" else r.l <= stop
        bate_alvo = (alvo is not None) and (r.l <= alvo if direcao == "venda" else r.h >= alvo)
        if bate_stop:
            return stop, "stop", i
        if bate_alvo:
            return alvo, "alvo", i
    i = fim - 1
    return float(d15.c.iloc[i]), "tempo", i


def simular(ativo, d15, i_ini, p, a15, contexto):
    """Simula um plano a partir do candle i_ini (o primeiro depois da decisão)."""
    pip = C["ativos"][ativo]["pip"]
    direcao = p["direcao"]
    sg = -1 if direcao == "venda" else 1
    nivel0 = p["nivel_de"] if direcao == "venda" else p["nivel_ate"]
    incl = (p["origem"].get("incl_h") or 0) / 4  # por candle de 15m
    tol = 0.1 * a15
    out = []
    funil = {"plano": 1, "rompeu": 0, "retestou": 0, "confirmou": 0}
    fase, i_romp, i = 0, None, i_ini
    lim = min(len(d15), i_ini + P["validade_plano_barras"])
    while i < len(d15):
        r = d15.iloc[i]
        nv = nivel0 + incl * (i - i_ini + 1)
        if fase == 0:
            if i >= lim:
                break
            rompeu = (r.c < nv - tol) if direcao == "venda" else (r.c > nv + tol)
            if rompeu:
                if not sessao_ok(ativo, d15.index[i]):
                    break  # rompimento fora da sessão não conta
                funil["rompeu"] = 1
                fase, i_romp = 1, i
                # modo direto: entra no fechamento do candle de rompimento
                ent = float(r.c)
                risco_d = (p["stop"] - ent) if direcao == "venda" else (ent - p["stop"])
                if risco_d >= max(P["stop_minimo_atr"] * a15, 3 * custo_pips(ativo, ent) * pip):
                    if p["alvo"] is None or (direcao == "venda" and ent > p["alvo"]) or (direcao == "compra" and ent < p["alvo"]):
                        sai, mot, j = gerenciar(d15, i + 1, direcao, ent, p["stop"], p["alvo"], ativo)
                        out.append(_registro("direto", ativo, p, d15, i, i + 1, j, ent, sai, mot, contexto, pip))
            i += 1
            continue
        if i - i_romp > P["barras_reteste"]:
            break
        if fase == 1:
            voltou = (r.c > nv + tol) if direcao == "venda" else (r.c < nv - tol)
            if voltou:
                break  # falso rompimento
            tocou = (r.h >= nv - tol) if direcao == "venda" else (r.l <= nv + tol)
            if tocou:
                funil["retestou"] = 1
                fase = 2
            else:
                i += 1
                continue
        if fase == 2:
            voltou = (r.c > nv + tol) if direcao == "venda" else (r.c < nv - tol)
            if voltou:
                break
            confirma = (r.c < r.o and r.c < nv) if direcao == "venda" else (r.c > r.o and r.c > nv)
            if confirma and i + 1 < len(d15):
                funil["confirmou"] = 1
                ent = float(d15.o.iloc[i + 1])  # deslizamento entra no custo
                risco = (p["stop"] - ent) if direcao == "venda" else (ent - p["stop"])
                if risco <= 0:
                    break
                if risco < max(P["stop_minimo_atr"] * a15, 3 * custo_pips(ativo, ent) * pip):
                    out.append(dict(modo="sistema", ativo=ativo, descartado="stop pequeno demais na entrada"))
                    break
                if p["alvo"] is not None:
                    ganho = (ent - p["alvo"]) if direcao == "venda" else (p["alvo"] - ent)
                    if ganho / risco < C["conta"]["rr_minimo"]:
                        out.append(dict(modo="sistema", ativo=ativo, descartado="R abaixo do mínimo na entrada"))
                        break
                sai, mot, j = gerenciar(d15, i + 1, direcao, ent, p["stop"], p["alvo"], ativo)
                out.append(_registro("sistema", ativo, p, d15, i_romp, i + 1, j, ent, sai, mot, contexto, pip))
                break
        i += 1
    return out, funil


def _registro(modo, ativo, p, d15, i_romp, i_ent, i_sai, ent, sai, mot, ctx, pip):
    direcao = p["direcao"]
    risco = abs(ent - p["stop"])
    bruto = ((ent - sai) if direcao == "venda" else (sai - ent)) / risco if risco > 0 else 0.0
    stop_pips = risco / pip
    liq = bruto - custo_pips(ativo, ent) / stop_pips if stop_pips > 0 else bruto
    o = p["origem"]
    tend4, tend1 = ctx["tendencia"]["4h"], ctx["tendencia"]["1h"]
    a_favor = lambda t: (t == "baixa" and direcao == "venda") or (t == "alta" and direcao == "compra")
    t_ent = d15.index[min(i_ent, len(d15) - 1)]
    return dict(
        modo=modo, ativo=ativo, direcao=direcao,
        origem=o.get("tipo"), origem_tf=o.get("tf") or "+".join(o.get("tempos", [])), toques=o.get("toques"),
        t_plano=ctx["t"], t_rompimento=str(d15.index[i_romp]), t_entrada=str(t_ent), t_saida=str(d15.index[i_sai]),
        sessao=nome_sessao(d15.index[i_romp]),
        entrada=ent, stop=p["stop"], alvo=p["alvo"], saida=sai, motivo=mot,
        stop_pips=round(stop_pips, 1), rr_plano=p["rr"],
        R_bruto=round(bruto, 3), R=round(liq, 3),
        a_favor_4h=a_favor(tend4), a_favor_1h=a_favor(tend1), tend_4h=tend4, tend_1h=tend1,
        barras=int(i_sai - i_ent + 1),
    )


def rodar(ativo, log=print):
    d15 = S.carregar(ativo, "15m")
    d1 = S.carregar(ativo, "1h")
    d4 = S.carregar(ativo, "4h")
    T = C["tempos"]
    fim15 = d15.index + pd.Timedelta(minutes=15)
    fim1 = d1.index + pd.Timedelta(hours=1)
    fim4 = d4.index + pd.Timedelta(hours=4)
    decisoes = [t for t in fim15 if t.minute == 0 and sessao_ok(ativo, t - pd.Timedelta(minutes=1))]
    trades, funis, descartes = [], [], 0
    ativos_recentes = []  # (t, direcao, nivel) para não repetir o mesmo setup
    for k, t in enumerate(decisoes):
        c15, c1, c4 = d15[fim15 <= t], d1[fim1 <= t], d4[fim4 <= t]
        if len(c15) < T["15m"]["janela"] or len(c1) < T["1h"]["janela"] or len(c4) < T["4h"]["janela"]:
            continue
        try:
            r = S.analisar_dfs(ativo, {"4h": c4, "1h": c1, "15m": c15})
        except Exception as e:  # um instante ruim não derruba o teste
            log(f"  {ativo} {t}: erro na análise ({e})")
            continue
        a15 = r["atr"]["15m"]
        i_ini = len(c15)
        ctx = dict(t=str(t), tendencia=r["tendencia"])
        for p in r["planos"]:
            if not p["valido"]:
                continue
            nivel = p["nivel_de"] if p["direcao"] == "venda" else p["nivel_ate"]
            ativos_recentes = [x for x in ativos_recentes if (t - x[0]) < pd.Timedelta(hours=8)]
            if any(x[1] == p["direcao"] and abs(x[2] - nivel) < P["duplicata_atr"] * a15 for x in ativos_recentes):
                continue
            ativos_recentes.append((t, p["direcao"], nivel))
            res, funil = simular(ativo, d15, i_ini, p, a15, ctx)
            funis.append(funil)
            for x in res:
                if x.get("descartado"):
                    descartes += 1
                else:
                    trades.append(x)
        if k % 50 == 0:
            log(f"  {ativo}: {k}/{len(decisoes)} instantes, {len(trades)} trades simulados")
    return trades, funis, descartes, (str(d15.index[0]), str(d15.index[-1]))


# ---------------------------------------------------------------- estatística
def metricas(R):
    R = np.asarray(R, dtype=float)
    if len(R) == 0:
        return dict(n=0)
    ganhos, perdas = R[R > 0], R[R <= 0]
    curva = np.cumsum(R)
    dd = float((np.maximum.accumulate(curva) - curva).max()) if len(R) else 0.0
    seq, pior = 0, 0
    for x in R:
        seq = seq + 1 if x <= 0 else 0
        pior = max(pior, seq)
    rnd = random.Random(42)
    medias = sorted(sum(rnd.choice(R) for _ in R) / len(R) for _ in range(P["bootstrap"]))
    lo, hi = medias[int(0.025 * len(medias))], medias[int(0.975 * len(medias))]
    return dict(
        n=int(len(R)), acerto=round(float((R > 0).mean()), 3),
        expectativa=round(float(R.mean()), 3), ic95=[round(lo, 3), round(hi, 3)],
        payoff=round(float(ganhos.mean() / -perdas.mean()), 2) if len(ganhos) and len(perdas) and perdas.mean() < 0 else None,
        profit_factor=round(float(ganhos.sum() / -perdas.sum()), 2) if len(perdas) and perdas.sum() < 0 else None,
        soma_R=round(float(R.sum()), 2), drawdown_R=round(dd, 2), pior_sequencia=int(pior),
        mediana=round(float(np.median(R)), 3),
        media_sem_2_maiores=round(float(np.sort(R)[:-2].mean()), 3) if len(R) > 4 else None,
    )


def grupos(df, col):
    out = {}
    for k, g in df.groupby(col, dropna=False):
        out[str(k)] = metricas(g.R.values)
    return out


def relatorio(df, funis, descartes, periodos, pasta):
    res = {"parametros": P, "periodos": periodos, "descartes_R_na_entrada": descartes}
    f = pd.DataFrame(funis)
    res["funil"] = {k: int(f[k].sum()) for k in f.columns} if len(f) else {}
    for modo in ("sistema", "direto"):
        d = df[df.modo == modo] if len(df) else df
        res[modo] = dict(
            geral=metricas(d.R.values) if len(d) else dict(n=0),
            sem_custos=metricas(d.R_bruto.values) if len(d) else dict(n=0),
            por_ativo=grupos(d, "ativo") if len(d) else {},
            por_direcao=grupos(d, "direcao") if len(d) else {},
            por_origem=grupos(d, "origem") if len(d) else {},
            por_sessao=grupos(d, "sessao") if len(d) else {},
            a_favor_tendencia_4h=grupos(d, "a_favor_4h") if len(d) else {},
            a_favor_tendencia_1h=grupos(d, "a_favor_1h") if len(d) else {},
            por_saida=d.motivo.value_counts().to_dict() if len(d) else {},
        )
    json.dump(res, open(os.path.join(pasta, "resumo.json"), "w"), indent=1, ensure_ascii=False, default=str)
    _grafico(df, pasta)
    return res


def _grafico(df, pasta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 5), facecolor="#131722")
    ax.set_facecolor("#131722")
    cores = {"sistema": "#4c9bff", "direto": "#ffa03c"}
    rotulo = {"sistema": "rompimento + reteste + confirmação", "direto": "entrada direta no rompimento"}
    for modo in ("sistema", "direto"):
        d = df[df.modo == modo].sort_values("t_entrada") if len(df) else df
        if len(d):
            ax.plot(range(1, len(d) + 1), d.R.cumsum().values, color=cores[modo], linewidth=2,
                    label=f"{rotulo[modo]} ({len(d)} trades)")
    ax.axhline(0, color="#8a8f9c", linewidth=0.8)
    ax.set_xlabel("trades, em ordem de entrada", color="#d1d4dc")
    ax.set_ylabel("R acumulado, já com custos", color="#d1d4dc")
    ax.tick_params(colors="#8a8f9c")
    for s in ax.spines.values():
        s.set_color("#2a2e39")
    ax.grid(color="#1f2433")
    ax.legend(facecolor="#0e1015", edgecolor="#444a58", labelcolor="#d1d4dc")
    ax.set_title("Teste histórico do Break & Retest", color="#d1d4dc", loc="left", fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(pasta, "curva.png"), dpi=110, facecolor=fig.get_facecolor())
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ativos", nargs="*", default=["EURUSD", "USDJPY", "US500"])
    ap.add_argument("--saida", default=os.path.join(S.RAIZ, "testes", pd.Timestamp.now().strftime("%Y-%m-%d")))
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    todos, funis, desc, per = [], [], 0, {}
    for ativo in a.ativos:
        print(f"{ativo}: começando")
        tr, fu, de, pe = rodar(ativo)
        todos += tr; funis += fu; desc += de; per[ativo] = pe
        print(f"{ativo}: {len(tr)} trades simulados, {len(fu)} planos")
    df = pd.DataFrame(todos)
    df.to_csv(os.path.join(a.saida, "trades.csv"), index=False)
    res = relatorio(df, funis, desc, per, a.saida)
    print(json.dumps({m: res[m]["geral"] for m in ("sistema", "direto")}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
