"""Painel por ativo: 4H e 1H em cima, 15m embaixo com área de projeção do plano.
Estilo escuro parecido com o TradingView; horários em Brasília."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import re
import textwrap
import pandas as pd
from sistema import CFG

FUNDO = "#131722"; GRADE = "#1f2433"; TXT = "#d1d4dc"; CINZA = "#8a8f9c"
VERDE = "#26a69a"; VERM = "#ef5350"; AZUL = "#4c9bff"; LARANJA = "#ffa03c"; AMAR = "#ffd700"; TEAL = "#5ac8e6"
FUSO = pd.Timedelta(hours=CFG["fuso_exibicao_horas"])


def _fmt(ativo):
    c = CFG["ativos"][ativo]["casas"]
    return lambda v: f"{v:,.{c}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def br(t):
    """1.1050 -> 1,1050 dentro de textos."""
    return re.sub(r"(\d)\.(\d)", r"\1,\2", t)


def _velas(ax, d):
    x = np.arange(len(d))
    sobe = d.c.values >= d.o.values
    cor = np.where(sobe, VERDE, VERM)
    ax.vlines(x, d.l.values, d.h.values, colors=cor, linewidth=0.8, zorder=2)
    base = np.minimum(d.o.values, d.c.values)
    alt = np.maximum(np.abs(d.c.values - d.o.values), (d.h.values - d.l.values).max() * 0.002)
    ax.bar(x, alt, bottom=base, width=0.65, color=cor, zorder=3, linewidth=0)


def _eixo(ax, d, tf, extra=0):
    ax.set_facecolor(FUNDO)
    for s in ax.spines.values():
        s.set_color(GRADE)
    ax.tick_params(colors=CINZA, labelsize=8)
    ax.yaxis.tick_right()
    ax.grid(color=GRADE, linewidth=0.6)
    n = len(d)
    t = d.index + FUSO
    passo = max(1, n // 7)
    idx = list(range(0, n, passo))
    if tf == "15m":
        lab = [t[i].strftime("%d/%m %Hh") if t[i].hour == 0 or i == 0 else t[i].strftime("%Hh%M") for i in idx]
    else:
        lab = [t[i].strftime("%d/%m") + ("" if tf == "4h" else t[i].strftime(" %Hh")) for i in idx]
    ax.set_xticks(idx)
    ax.set_xticklabels(lab)
    ax.set_xlim(-1, n + extra)


def _linha(ax, l, n_total, n_vis, cor, fim_extra=0):
    """l usa índices negativos relativos ao fim da série."""
    xa, xb = n_vis + l["a_idx"], n_vis + l["b_idx"]
    ya, yb = l["a_preco"], l["b_preco"]
    s = (yb - ya) / (xb - xa)
    x_fim = n_vis - 1 + fim_extra if not l["rompida"] else n_vis + l["rompe_idx"] + 3
    xs = [max(xa, -1), x_fim]
    ys = [ya + s * (xs[0] - xa), ya + s * (x_fim - xa)]
    ax.plot(xs, ys, color=cor, linewidth=1.8 if not l["rompida"] else 1.2,
            linestyle="-" if not l["rompida"] else "--", zorder=4)
    for ti in l["toques_idx"]:
        xt = n_vis + ti
        if xt >= 0:
            ax.scatter([xt], [ya + s * (xt - xa)], s=60, facecolors="none", edgecolors=cor, linewidths=1.4, zorder=5)
    return ys[-1]


def _caixa(ax, linhas, xy=(0.01, 0.98), size=9):
    txt = "\n".join(linhas)
    ax.text(*xy, txt, transform=ax.transAxes, va="top", ha="left", fontsize=size, color=TXT,
            bbox=dict(boxstyle="round,pad=0.45", facecolor="#0e1015", edgecolor="#444a58", alpha=0.93), zorder=10)


def _painel_simples(ax, ativo, d, tf, lin, zonas, titulo):
    F = _fmt(ativo)
    _velas(ax, d)
    _eixo(ax, d, tf)
    n = len(d)
    for l in lin:
        if n + l["a_idx"] < -5 and n + l["b_idx"] < 0:
            continue
        _linha(ax, l, n, n, VERM if l["tipo"] == "LTB" else VERDE)
    lo, hi = d.l.min(), d.h.max()
    for z in zonas:
        if lo <= z["meio"] <= hi:
            ax.axhspan(z["de"], z["ate"], color=TEAL, alpha=0.18, zorder=1)
    ax.set_ylim(lo - (hi - lo) * 0.04, hi + (hi - lo) * 0.18)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: F(v)))
    _titulo(ax, titulo)


def _titulo(ax, linhas):
    """Informações acima do gráfico (nunca por cima das velas)."""
    cab, resto = linhas[0], linhas[1:]
    corpo = "\n".join(textwrap.fill(x, 70) for x in resto)
    ax.set_title(cab + ("\n" + corpo if corpo else ""), loc="left", fontsize=9, color=TXT, pad=8, linespacing=1.4)


def _coluna(ax, linhas, largura=40):
    """Coluna lateral de texto, fora do gráfico."""
    ax.set_facecolor("#0e1015")
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#2a2e39")
    blocos = []
    for x in linhas:
        blocos.append(textwrap.fill(x, largura, subsequent_indent="   ") if x else "")
    ax.text(0.05, 0.97, "\n".join(blocos), transform=ax.transAxes, va="top", ha="left",
            fontsize=9, color=TXT, linespacing=1.45)


def painel(ativo, r, dfs, plano=None, caminho="painel.png", subtitulo=""):
    F = _fmt(ativo); T = CFG["tempos"]
    fig = plt.figure(figsize=(16, 12.5), facecolor="#0e0f13")
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.35], hspace=0.22,
                          left=0.02, right=0.95, top=0.86, bottom=0.04)
    gs_cima = gs[0].subgridspec(1, 2, wspace=0.1)
    gs_baixo = gs[1].subgridspec(1, 2, width_ratios=[3.3, 1], wspace=0.07)
    hora = (pd.Timestamp(r["ultimo_candle_15m_utc"]) + pd.Timedelta(minutes=15) + FUSO)
    fig.text(0.02, 0.972, f"{r['nome']} · {hora.strftime('%d/%m/%Y %Hh%M')} (Brasília) · preço {F(r['preco'])}",
             color=TXT, fontsize=15, fontweight="bold")
    if subtitulo:
        fig.text(0.02, 0.952, subtitulo, color=CINZA, fontsize=10)

    tend = {"alta": "alta", "baixa": "baixa", "lateral": "lateral"}
    for i, tf in enumerate(("4h", "1h")):
        ax = fig.add_subplot(gs_cima[0, i])
        d = dfs[tf].iloc[-T[tf]["mostrar"]:]
        ativas = [l for l in r["linhas"][tf] if not l["rompida"]]
        txt = [f"{tf.upper()} · tendência de {tend[r['tendencia'][tf]]}"]
        for l in r["linhas"][tf]:
            nome = "LTB (teto caindo)" if l["tipo"] == "LTB" else "LTA (piso subindo)"
            if l["rompida"]:
                txt.append(f"{nome} rompida, passava em {F(l['valor_agora'])}")
            else:
                txt.append(f"{nome}: {l['toques']} toques, hoje em {F(l['valor_proximo'])}")
        _painel_simples(ax, ativo, d, tf, r["linhas"][tf], r["zonas"], txt)

    # ---- 15m com projeção
    ax = fig.add_subplot(gs_baixo[0, 0])
    info = fig.add_subplot(gs_baixo[0, 1])
    caixa = []
    d = dfs["15m"].iloc[-T["15m"]["mostrar"]:]
    n = len(d); extra = 56
    _velas(ax, d)
    _eixo(ax, d, "15m", extra)
    ax.axvspan(n - 0.5, n + extra, color="#000000", alpha=0.35, zorder=0)
    for l in r["linhas"]["15m"]:
        cor = VERM if l["tipo"] == "LTB" else VERDE
        _linha(ax, l, n, n, cor, fim_extra=12)
    lo, hi = d.l.min(), d.h.max()
    for z in r["zonas"]:
        ax.axhspan(z["de"], z["ate"], xmax=1, color=TEAL, alpha=0.22, zorder=1)
        ax.text(2, z["ate"], f" {F(z['de'])}–{F(z['ate'])} · {z['toques']} toque{'s' if z['toques'] > 1 else ''}", color=TEAL, fontsize=8, va="bottom", clip_on=True)
    marcas = [] if not plano else [plano["entrada"], plano["stop"]] + ([plano["alvo"]] if plano["alvo"] else [])
    for rd in r["redondos"]:
        if lo - (hi - lo) * 0.3 <= rd <= hi + (hi - lo) * 0.3:
            if any(abs(rd - m) < 0.5 * r["atr"]["15m"] for m in marcas):
                ax.axhline(rd, color=CINZA, linestyle=(0, (4, 4)), linewidth=0.9, zorder=1)
                continue
            ax.axhline(rd, color=CINZA, linestyle=(0, (4, 4)), linewidth=0.9, zorder=1)
            ax.text(n + extra - 1, rd, f"{F(rd)} redondo", color=CINZA, fontsize=8, ha="right", va="bottom", clip_on=True)
    ax.axhline(r["preco"], color="#bbbbbb", linestyle=":", linewidth=0.8)
    ylo, yhi = lo, hi
    if plano:
        p = plano
        x0, x1 = n + 14, n + 32
        risco_lo, risco_hi = sorted([p["entrada"], p["stop"]])
        ax.add_patch(Rectangle((x0, risco_lo), x1 - x0, risco_hi - risco_lo, facecolor=VERM, alpha=0.3, edgecolor=VERM, zorder=6))
        if p["alvo"] is not None:
            g_lo, g_hi = sorted([p["entrada"], p["alvo"]])
            ax.add_patch(Rectangle((x0, g_lo), x1 - x0, g_hi - g_lo, facecolor=VERDE, alpha=0.3, edgecolor=VERDE, zorder=6))
            ylo, yhi = min(ylo, p["alvo"]), max(yhi, p["alvo"])
        ax.plot([x0, x1], [p["entrada"]] * 2, color=AZUL, linewidth=2.2, zorder=7)
        ylo, yhi = min(ylo, p["stop"]), max(yhi, p["stop"])
        A_ = CFG["ativos"][ativo]; un = A_.get("unidade", "pips"); fu = A_.get("fator_unidade", 1)
        un = {"dólares": "dól.", "pontos": "pts"}.get(un, un)
        ax.text(x1 + 0.5, p["stop"], f"Stop {F(p['stop'])} ({p['stop_pips'] * fu:.0f} {un})", color=VERM, fontsize=9, va="center", fontweight="bold")
        ax.text(x1 + 0.5, p["entrada"], f"Entrada {F(p['entrada'])}", color=AZUL, fontsize=9, va="center", fontweight="bold")
        if p["alvo"] is not None:
            ax.text(x1 + 0.5, p["alvo"], f"Alvo {F(p['alvo'])} ({p['rr']:.1f}R)", color=VERDE, fontsize=9, va="center", fontweight="bold")
        # trajetória ilustrativa: rompimento, reteste, confirmação
        nv = p["nivel_de"] if p["direcao"] == "venda" else p["nivel_ate"]
        sg = -1 if p["direcao"] == "venda" else 1
        a15 = r["atr"]["15m"]
        pts = [(n - 1, r["preco"]), (n + 4, nv + sg * 1.2 * a15), (n + 8, nv), (n + 11, nv + sg * 0.6 * a15), (n + 14, p["entrada"])]
        ax.plot(*zip(*pts), color=AMAR, linewidth=1.6, linestyle="--", zorder=6)
        for k, (xx, yy) in enumerate(pts[1:4], 1):
            ax.scatter([xx], [yy], s=110, facecolors="none", edgecolors=AMAR, linewidths=1.6, zorder=7)
            ax.text(xx, yy + sg * 0.5 * a15, str(k), color=AMAR, fontsize=10, ha="center", va="center", fontweight="bold")
        cor = VERM if p["direcao"] == "venda" else VERDE
        e = p["estado"]
        if e.get("confirmacao") and not e.get("invalidado_depois"):
            st = "Situação: rompimento, reteste e confirmação já aconteceram"
        elif e.get("reteste"):
            st = "Situação: rompeu e retestou; falta a confirmação"
        elif e.get("rompimento"):
            st = "Situação: rompeu; aguardando o reteste"
        else:
            st = "Situação: ainda não rompeu"
        lote = p["tamanho"]["lote"]
        caixa = [br(f"Plano: {p['direcao'].upper()} no {p['gatilho']}"),
                 f"1 · Rompimento: candle de 15m fecha {'abaixo' if sg < 0 else 'acima'} de {F(nv)}",
                 f"2 · Reteste: o preço volta a {F(nv)}",
                 f"3 · Confirmação: candle fecha a favor → entra no seguinte",
                 br(f"Lote {lote:.2f} · risco ≈ US$ {p['tamanho']['risco_real_usd']:.2f}") if lote >= 0.01 else
                 f"Stop de {p['stop_pips'] * fu:.0f} {un} não cabe no risco de US$ {p['tamanho']['risco_usd']:.0f}",
                 st]
        if p.get("obs_alvo"):
            caixa.append(br(f"Atenção: {p['obs_alvo']}; abaixo do mínimo de 1,5R"))
        ax.text(n + 1, ylo, "projeção ilustrativa", color="#777", fontsize=8, va="bottom")
    rng = yhi - ylo
    ax.set_ylim(ylo - rng * 0.06, yhi + rng * 0.12)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: F(v)))
    linhas15 = ["15m · operação"]
    for l in r["linhas"]["15m"]:
        nome = "LTB" if l["tipo"] == "LTB" else "LTA"
        if l["rompida"]:
            linhas15.append(f"{nome} rompida")
        else:
            linhas15.append(f"{nome}: {l['toques']} toques, hoje em {F(l['valor_proximo'])}")
    _titulo(ax, [linhas15[0], "  ·  ".join(linhas15[1:])] if len(linhas15) > 1 else linhas15)
    if not caixa:
        caixa = ["Só observar: nenhum plano a favor da tendência do 4H/1H com risco e relação mínima de 1,5R."]
    # cabeçalho do plano em destaque, resto em texto corrido
    _coluna(info, [caixa[0], ""] + caixa[1:4] + [""] + caixa[4:])
    fig.savefig(caminho, dpi=110, facecolor=fig.get_facecolor())
    plt.close(fig)
    return caminho
