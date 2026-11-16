"""Relatório comparativo (tema cyberpunk): base x filtro de tendência, mais o ouro em estudo.

Uso: python scripts/relatorio_comparativo_pdf.py testes/2026-11-16
Espera as subpastas base/, filtro/, ouro_base/ e ouro_filtro/ (cada uma com resumo.json e trades.csv)
e o arquivo leitura.json (textos da leitura honesta). Gera curva_comparada.png e relatorio.pdf.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd
from reportlab.lib.utils import ImageReader
from relatorio_pdf import Rel, br, W, H, M, CIANO, MAG, AMAR, VERDE, BRANCO, MUTED, TXT, BORDA, Color


def curva(pasta):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.6), facecolor="#07080f", gridspec_kw={"width_ratios": [2, 1]})
    series = [(axs[0], "base", "sem filtro", "#ff3ec8"), (axs[0], "filtro", "com filtro de tendência", "#00e5ff"),
              (axs[1], "ouro_base", "ouro sem filtro", "#f4ff52"), (axs[1], "ouro_filtro", "ouro com filtro", "#4dffb5")]
    for ax, sub, rot, cor in series:
        d = pd.read_csv(os.path.join(pasta, sub, "trades.csv"))
        d = d[d.modo == "sistema"].sort_values("t_entrada")
        if len(d):
            ax.plot(range(0, len(d) + 1), [0] + list(d.R.cumsum()), color=cor, linewidth=2.2,
                    marker="o", markersize=3, label=f"{rot} ({len(d)} trades)")
    for ax, tit in zip(axs, ("EURUSD · USDJPY · US500", "XAUUSD · só estudo")):
        ax.set_facecolor("#0d0f1c")
        ax.axhline(0, color="#8a93c2", linewidth=0.8)
        ax.set_xlabel("trades, em ordem de entrada", color="#d9e2ff")
        ax.tick_params(colors="#8a93c2")
        for s in ax.spines.values():
            s.set_color("#1f2547")
        ax.grid(color="#141936")
        ax.legend(facecolor="#07080f", edgecolor="#1f2547", labelcolor="#d9e2ff", fontsize=9, loc="upper left")
        ax.set_title(tit, color="#d9e2ff", loc="left", fontsize=11)
    axs[0].set_ylabel("R acumulado, já com custos", color="#d9e2ff")
    fig.tight_layout()
    caminho = os.path.join(pasta, "curva_comparada.png")
    fig.savefig(caminho, dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)
    return caminho


def pct(x):
    return f"{x * 100:.0f}%".replace(".", ",")


def gerar(pasta):
    data = os.path.basename(os.path.normpath(pasta))
    data_br = "/".join(reversed(data.split("-")))
    R = {k: json.load(open(os.path.join(pasta, k, "resumo.json"))) for k in ("base", "filtro", "ouro_base", "ouro_filtro")}
    L = json.load(open(os.path.join(pasta, "leitura.json")))
    img = curva(pasta)
    rel = Rel(os.path.join(pasta, "relatorio.pdf"), "Teste histórico · filtro de tendência",
              data=data_br, pasta=f"testes/{data}")
    c = rel.c
    b, f = R["base"]["sistema"]["geral"], R["filtro"]["sistema"]["geral"]
    ob = R["ouro_base"]["sistema"]["geral"]

    # ============================================================ 1 · capa
    rel.nova("capa", "capa")
    c.setFont("Mono", 10); c.setFillColor(CIANO); c.drawString(M, H - 120, "> RELATÓRIO // VARIANTE COM FILTRO DE TENDÊNCIA")
    c.setFont("Tit", 40); c.setFillColor(BRANCO); c.drawString(M, H - 172, "Filtro de tendência")
    c.setFillColor(MAG); c.drawString(M, H - 218, "no histórico")
    c.setFont("TxtL", 11.5); c.setFillColor(MUTED)
    c.drawString(M, H - 246, "Só planos a favor do 4H (ou do 1H com o 4H lateral) · mesmos dados · com custos")
    rel.caixa(M, H - 340, W - 2 * M, 66, borda=AMAR, brilho=AMAR)
    c.setFont("MonoB", 9); c.setFillColor(AMAR); c.drawString(M + 16, H - 296, "VEREDITO")
    c.setFont("TitM", 12.5); c.setFillColor(BRANCO); c.drawString(M + 16, H - 316, L["veredito"][0])
    c.setFont("Txt", 10); c.setFillColor(TXT); c.drawString(M + 16, H - 332, L["veredito"][1])
    kw = (W - 2 * M - 24) / 3
    rel.kpi(M, H - 465, kw, "sem filtro", br(b["expectativa"]) + "R", MAG,
            f"{b['n']} trades · IC {br(b['ic95'][0])} a {br(b['ic95'][1])}")
    rel.kpi(M + kw + 12, H - 465, kw, "com filtro", br(f["expectativa"]) + "R", CIANO,
            f"{f['n']} trades · IC {br(f['ic95'][0])} a {br(f['ic95'][1])}")
    rel.kpi(M + 2 * (kw + 12), H - 465, kw, "ouro · estudo", br(ob["expectativa"]) + "R", AMAR,
            f"{ob['n']} trades sem filtro · fora da conta")
    c.setFont("Mono", 9); c.setFillColor(MUTED); c.drawString(M, H - 515, "ÍNDICE  (clique para ir)")
    itens = [("01", "Resultado lado a lado", "resultado"), ("02", "De onde vem o ganho", "recortes"),
             ("03", "Ouro · só estudo", "ouro"), ("04", "Leitura honesta e próximo passo", "leitura")]
    yy = H - 543
    for num, nome, chave in itens:
        c.setFont("MonoB", 12); c.setFillColor(CIANO); c.drawString(M, yy, num)
        c.setFont("TitM", 13); c.setFillColor(BRANCO); c.drawString(M + 34, yy, nome)
        c.setStrokeColor(BORDA); c.line(M, yy - 10, W - M, yy - 10)
        c.linkAbsolute(nome, chave, (M, yy - 10, W - M, yy + 16))
        yy -= 36
    c.setFont("Txt", 8.5); c.setFillColor(MUTED)
    c.drawString(M, 60, "Valores em R (múltiplos do risco). IC = intervalo de confiança de 95% por bootstrap.")

    # ============================================================ 2 · resultado
    rel.nova("resultado", "resultado")
    rel.titulo(H - 90, "Resultado lado a lado", "Sistema completo (rompimento + reteste + confirmação), mesmos dados, já com custos")
    ir = ImageReader(img); iw, ih = ir.getSize(); lw = W - 2 * M; lh = lw * ih / iw
    rel.caixa(M - 4, H - 136 - lh - 4, lw + 8, lh + 8, borda=CIANO)
    c.drawImage(ir, M, H - 136 - lh, lw, lh)
    y = H - 160 - lh - 18
    cols = [M, M + 230, M + 370]
    bs, fs = R["base"]["sistema"]["sem_custos"], R["filtro"]["sistema"]["sem_custos"]
    bd, fd = R["base"]["direto"]["geral"], R["filtro"]["direto"]["geral"]
    linhas = [("", "SEM FILTRO", "COM FILTRO"),
              ("Trades", b["n"], f["n"]),
              ("Acerto", pct(b["acerto"]), pct(f["acerto"])),
              ("Expectativa com custos", br(b["expectativa"]) + "R", br(f["expectativa"]) + "R"),
              ("Intervalo de 95%", f"{br(b['ic95'][0])} a {br(b['ic95'][1])}", f"{br(f['ic95'][0])} a {br(f['ic95'][1])}"),
              ("Soma", br(b["soma_R"], 1) + "R", br(f["soma_R"], 1) + "R"),
              ("Maior queda (drawdown)", br(b["drawdown_R"], 1, False) + "R", br(f["drawdown_R"], 1, False) + "R"),
              ("Mediana", br(b["mediana"]) + "R", br(f["mediana"]) + "R"),
              ("Média sem os 2 maiores ganhos", br(b["media_sem_2_maiores"]) + "R", br(f["media_sem_2_maiores"]) + "R"),
              ("Profit factor", br(b["profit_factor"], sinal=False), br(f["profit_factor"], sinal=False)),
              ("Expectativa sem custos", br(bs["expectativa"]) + "R", br(fs["expectativa"]) + "R"),
              ("Entrada direta (referência)", br(bd["expectativa"]) + f"R · {bd['n']}", br(fd["expectativa"]) + f"R · {fd['n']}")]
    for i, (a, x1, x2) in enumerate(linhas):
        if i:
            c.setStrokeColor(BORDA); c.line(M, y + 12, W - M, y + 12)
            c.setFont("Txt", 9.5); c.setFillColor(TXT)
        else:
            c.setFont("MonoB", 8); c.setFillColor(MUTED)
        c.drawString(cols[0], y, str(a))
        c.setFont("MonoB", 9.5 if i else 8)
        c.setFillColor(MAG); c.drawString(cols[1], y, str(x1))
        c.setFillColor(CIANO); c.drawString(cols[2], y, str(x2))
        y -= 20

    # ============================================================ 3 · recortes
    rel.nova("de onde vem o ganho", "recortes")
    rel.titulo(H - 90, "De onde vem o ganho", "Variante com filtro · barras claras = menos de 30 trades (amostra pequena)")
    s = R["filtro"]["sistema"]
    def grp(chave, nomes):
        return [(nomes.get(k, k), v["n"], v["expectativa"]) for k, v in s[chave].items() if v.get("n")]
    y = H - 138
    y = rel.barras(M, y, W - 2 * M, "Ativo", grp("por_ativo", {})) - 14
    y = rel.barras(M, y, W - 2 * M, "Sessão do rompimento", grp("por_sessao", {})) - 14
    y = rel.barras(M, y, W - 2 * M, "O que rompeu", grp("por_origem", {"LTA": "LTA (piso subindo)", "LTB": "LTB (teto caindo)", "resistencia": "resistência", "suporte": "suporte"})) - 14
    y = rel.barras(M, y, W - 2 * M, "Direção", grp("por_direcao", {})) - 14
    y = rel.barras(M, y, W - 2 * M, "Aberta às 8h30 de NY (dado americano)", grp("atravessou_dado_eua", {"True": "atravessou", "False": "não atravessou"})) - 10
    rel.caixa(M, y - 62, W - 2 * M, 58, borda=AMAR)
    rel.paragrafo(M + 12, y - 22, W - 2 * M - 24, L["recortes"], tam=9, cor=AMAR, entre=13)

    # ============================================================ 4 · ouro
    rel.nova("ouro · só estudo", "ouro")
    rel.titulo(H - 90, "Ouro · só estudo", "XAUUSD fora da conta: medido em R, sem o limite de US$ 2")
    so = R["ouro_base"]["sistema"]; of = R["ouro_filtro"]["sistema"]["geral"]; odir = R["ouro_base"]["direto"]["geral"]
    y = H - 140
    cols = [M, M + 230, M + 370]
    linhas = [("", "SEM FILTRO", "COM FILTRO"),
              ("Trades", ob["n"], of["n"]),
              ("Acerto", pct(ob["acerto"]), pct(of["acerto"])),
              ("Expectativa com custos", br(ob["expectativa"]) + "R", br(of["expectativa"]) + "R"),
              ("Intervalo de 95%", f"{br(ob['ic95'][0])} a {br(ob['ic95'][1])}", "amostra pequena demais"),
              ("Entrada direta (referência)", br(odir["expectativa"]) + f"R · {odir['n']}", "")]
    for i, (a, x1, x2) in enumerate(linhas):
        if i:
            c.setStrokeColor(BORDA); c.line(M, y + 12, W - M, y + 12)
            c.setFont("Txt", 9.5); c.setFillColor(TXT)
        else:
            c.setFont("MonoB", 8); c.setFillColor(MUTED)
        c.drawString(cols[0], y, str(a))
        c.setFont("MonoB", 9.5 if i else 8)
        c.setFillColor(AMAR); c.drawString(cols[1], y, str(x1))
        c.setFillColor(VERDE); c.drawString(cols[2], y, str(x2))
        y -= 20
    y -= 12
    s = so
    y = rel.barras(M, y, W - 2 * M, "O que rompeu (sem filtro)", grp("por_origem", {"LTA": "LTA (piso subindo)", "LTB": "LTB (teto caindo)", "resistencia": "resistência", "suporte": "suporte"})) - 14
    y = rel.barras(M, y, W - 2 * M, "Direção (sem filtro)", grp("por_direcao", {})) - 14
    y = rel.barras(M, y, W - 2 * M, "Aberta às 8h30 de NY", grp("atravessou_dado_eua", {"True": "atravessou", "False": "não atravessou"})) - 14
    for cor, tit, txt in L["ouro"]:
        c.setFont("TitM", 10.5); c.setFillColor(cor_de(cor)); c.drawString(M, y, tit)
        y = rel.paragrafo(M, y - 16, W - 2 * M, txt, tam=9, entre=13) - 8

    # ============================================================ 5 · leitura
    rel.nova("leitura honesta", "leitura")
    rel.titulo(H - 90, "Leitura honesta")
    y = H - 128
    for cor, tit, txt in L["blocos"]:
        cc = cor_de(cor)
        alt = 30 + 13 * linhas_de(rel, txt, W - 2 * M - 32)
        rel.caixa(M, y - alt, W - 2 * M, alt - 4, borda=cc)
        c.setFillColor(cc); c.rect(M, y - alt, 4, alt - 4, stroke=0, fill=1)
        c.setFont("TitM", 10.5); c.setFillColor(cc); c.drawString(M + 16, y - 20, tit)
        rel.paragrafo(M + 16, y - 36, W - 2 * M - 32, txt, tam=9, entre=13)
        y -= alt + 8
    y -= 18
    c.setFont("Tit", 14); c.setFillColor(BRANCO); c.drawString(M, y - 8, "Próximo passo")
    alt = 26 + 14 * linhas_de(rel, L["proximo"], W - 2 * M - 32, tam=9.5)
    rel.caixa(M, y - 18 - alt, W - 2 * M, alt, borda=CIANO, brilho=CIANO)
    rel.paragrafo(M + 16, y - 38, W - 2 * M - 32, L["proximo"], tam=9.5, cor=BRANCO, entre=14)
    y -= 40 + alt
    c.setFont("Mono", 8.5); c.setFillColor(MUTED); c.drawString(M, y, "LIMITAÇÕES")
    y -= 16
    for l in L["limitacoes"]:
        c.setFillColor(MAG); c.rect(M, y + 2, 4, 4, stroke=0, fill=1)
        c.setFont("Txt", 8.8); c.setFillColor(TXT); c.drawString(M + 12, y, l); y -= 14
    rel.salvar()
    return os.path.join(pasta, "relatorio.pdf")


def cor_de(nome):
    return {"ciano": CIANO, "mag": MAG, "amar": AMAR, "verde": VERDE}.get(nome, TXT)


def linhas_de(rel, texto, largura, tam=9, fonte="Txt"):
    from reportlab.pdfbase import pdfmetrics
    n, linha = 1, ""
    for p in texto.split():
        t = (linha + " " + p).strip()
        if pdfmetrics.stringWidth(t, fonte, tam) > largura:
            n += 1; linha = p
        else:
            linha = t
    return n


if __name__ == "__main__":
    print(gerar(sys.argv[1] if len(sys.argv) > 1 else "testes/2026-11-16"))
