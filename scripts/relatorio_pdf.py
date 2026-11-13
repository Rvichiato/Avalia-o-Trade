"""Relatório em PDF (tema cyberpunk) do teste histórico.

Uso: python scripts/relatorio_pdf.py testes/2026-11-13
Gera <pasta>/relatorio.pdf a partir de resumo.json e curva.png.
"""
import sys, os, json
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.utils import ImageReader

GF = "/usr/share/fonts/truetype/google-fonts/"
DJ = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("Tit", GF + "Poppins-Bold.ttf"))
pdfmetrics.registerFont(TTFont("TitM", GF + "Poppins-Medium.ttf"))
pdfmetrics.registerFont(TTFont("Txt", GF + "Poppins-Regular.ttf"))
pdfmetrics.registerFont(TTFont("TxtL", GF + "Poppins-Light.ttf"))
pdfmetrics.registerFont(TTFont("Mono", DJ + "DejaVuSansMono.ttf"))
pdfmetrics.registerFont(TTFont("MonoB", DJ + "DejaVuSansMono-Bold.ttf"))

FUNDO = HexColor("#07080f"); PAINEL = HexColor("#0d0f1c"); BORDA = HexColor("#1f2547")
TXT = HexColor("#d9e2ff"); MUTED = HexColor("#8a93c2"); CIANO = HexColor("#00e5ff")
MAG = HexColor("#ff3ec8"); AMAR = HexColor("#f4ff52"); VERDE = HexColor("#4dffb5"); BRANCO = HexColor("#f2f5ff")
W, H = A4
M = 40


def br(x, casas=2, sinal=True):
    x = x + (1e-9 if x >= 0 else -1e-9)  # arredonda 0,075 para 0,08
    s = f"{x:+.{casas}f}" if sinal else f"{x:.{casas}f}"
    return s.replace(".", ",")


class Rel:
    def __init__(self, caminho, titulo):
        self.c = canvas.Canvas(caminho, pagesize=A4)
        self.c.setTitle(titulo)
        self.c.setAuthor("Claude · sistema Break & Retest")
        self.c.setSubject("Teste histórico")
        self.pag = 0

    # ------------------------------------------------ base de cada página
    def nova(self, secao, chave=None):
        if self.pag:
            self.c.showPage()
        self.pag += 1
        c = self.c
        c.setFillColor(FUNDO); c.rect(0, 0, W, H, stroke=0, fill=1)
        # grade sutil
        c.setStrokeColor(HexColor("#0e1124")); c.setLineWidth(0.4)
        for x in range(0, int(W), 24):
            c.line(x, 0, x, H)
        for y in range(0, int(H), 24):
            c.line(0, y, W, y)
        # faixa superior
        c.setFillColor(MAG); c.rect(M, H - 34, 7, 7, stroke=0, fill=1)
        c.setFont("MonoB", 8.5); c.setFillColor(CIANO)
        c.drawString(M + 14, H - 33, "CEREBRO-TRADE")
        c.setFont("Mono", 8.5); c.setFillColor(MUTED)
        c.drawString(M + 92, H - 33, f"// {secao}")
        c.drawRightString(W - M, H - 33, "teste histórico · 13/11/2026")
        c.setStrokeColor(BORDA); c.setLineWidth(0.8); c.line(M, H - 42, W - M, H - 42)
        # rodapé
        c.line(M, 34, W - M, 34)
        c.setFont("Mono", 7.5); c.setFillColor(MUTED)
        c.drawString(M, 22, "github.com/Rvichiato/Avalia-o-Trade · testes/2026-11-13")
        c.linkURL("https://github.com/Rvichiato/Avalia-o-Trade/tree/main/testes/2026-11-13",
                  (M, 18, M + 260, 30), relative=0)
        c.setFillColor(CIANO); c.drawRightString(W - M, 22, f"{self.pag:02d}")
        if chave:
            c.bookmarkPage(chave)
            c.addOutlineEntry(secao, chave, level=0)

    def titulo(self, y, texto, sub=None, cor=BRANCO, tam=24):
        c = self.c
        c.setFont("Tit", tam); c.setFillColor(cor); c.drawString(M, y, texto)
        tw = pdfmetrics.stringWidth(texto, "Tit", tam)
        c.setFillColor(MAG); c.drawString(M + tw + 4, y, "_")
        if sub:
            c.setFont("TxtL", 10.5); c.setFillColor(MUTED); c.drawString(M, y - 18, sub)

    def caixa(self, x, y, w, h, borda=BORDA, fundo=PAINEL, brilho=None):
        c = self.c
        if brilho:
            for i, a in enumerate((0.05, 0.08, 0.12)):
                c.setStrokeColor(Color(brilho.red, brilho.green, brilho.blue, alpha=a))
                c.setLineWidth(6 - 2 * i); c.rect(x, y, w, h, stroke=1, fill=0)
        c.setFillColor(fundo); c.setStrokeColor(borda); c.setLineWidth(0.9)
        c.rect(x, y, w, h, stroke=1, fill=1)

    def paragrafo(self, x, y, largura, texto, fonte="Txt", tam=9.5, cor=TXT, entre=14):
        c = self.c; c.setFont(fonte, tam); c.setFillColor(cor)
        palavras = texto.split(); linha = ""
        for p in palavras:
            t = (linha + " " + p).strip()
            if pdfmetrics.stringWidth(t, fonte, tam) > largura:
                c.drawString(x, y, linha); y -= entre; linha = p
            else:
                linha = t
        if linha:
            c.drawString(x, y, linha); y -= entre
        return y

    def kpi(self, x, y, w, rotulo, valor, cor, nota):
        self.caixa(x, y, w, 92, borda=cor, brilho=cor)
        c = self.c
        c.setFont("Mono", 7.5); c.setFillColor(MUTED); c.drawString(x + 12, y + 74, rotulo.upper())
        c.setFont("Tit", 27); c.setFillColor(cor); c.drawString(x + 12, y + 38, valor)
        c.setFont("Txt", 8); c.setFillColor(MUTED); c.drawString(x + 12, y + 16, nota)

    def barras(self, x, y, w, titulo, grupos, escala=2.0):
        """Barras horizontais em torno de zero. grupos: [(rotulo, n, expectativa)]."""
        c = self.c
        c.setFont("TitM", 10.5); c.setFillColor(BRANCO); c.drawString(x, y, titulo)
        y -= 18
        x0 = x + 150; meia = (w - 150 - 70) / 2; zero = x0 + meia
        c.setStrokeColor(BORDA); c.setLineWidth(0.8)
        c.line(zero, y + 10, zero, y - 20 * len(grupos) + 6)
        for rot, n, e in grupos:
            c.setFont("Txt", 8.5); c.setFillColor(TXT); c.drawString(x, y - 2, rot)
            c.setFont("Mono", 7.5); c.setFillColor(MUTED); c.drawString(x + 112, y - 2, f"n={n}")
            comp = max(-1, min(1, e / escala)) * meia
            cor = CIANO if e >= 0 else MAG
            c.setFillColor(Color(cor.red, cor.green, cor.blue, alpha=0.85 if n >= 30 else 0.45))
            c.rect(min(zero, zero + comp), y - 4, abs(comp), 11, stroke=0, fill=1)
            c.setFont("MonoB", 8); c.setFillColor(cor)
            c.drawString(x0 + 2 * meia + 8, y - 2, br(e) + "R")
            y -= 20
        return y

    def salvar(self):
        self.c.showPage(); self.c.save()


def gerar(pasta):
    r = json.load(open(os.path.join(pasta, "resumo.json")))
    s, d = r["sistema"], r["direto"]
    sg, dg = s["geral"], d["geral"]
    rel = Rel(os.path.join(pasta, "relatorio.pdf"), "Teste histórico · Break & Retest")
    c = rel.c

    # ============================================================ 1 · capa
    rel.nova("capa", "capa")
    c.setFont("Mono", 10); c.setFillColor(CIANO); c.drawString(M, H - 120, "> RELATÓRIO // TESTE HISTÓRICO")
    c.setFont("Tit", 44); c.setFillColor(BRANCO)
    c.drawString(M, H - 175, "Break & Retest")
    c.setFillColor(MAG); c.drawString(M, H - 225, "no histórico")
    c.setFont("TxtL", 12); c.setFillColor(MUTED)
    c.drawString(M, H - 255, "EURUSD · USDJPY · US500 · ~11 semanas de candles de 15m · com custos")
    # veredito
    rel.caixa(M, H - 345, W - 2 * M, 62, borda=AMAR, brilho=AMAR)
    c.setFont("MonoB", 9); c.setFillColor(AMAR); c.drawString(M + 16, H - 305, "VEREDITO")
    c.setFont("TitM", 13); c.setFillColor(BRANCO)
    c.drawString(M + 16, H - 326, "Entrada direta perde. Sistema completo: vantagem ainda não provada.")
    # KPIs
    kw = (W - 2 * M - 24) / 3
    rel.kpi(M, H - 470, kw, "sistema completo", br(sg["expectativa"]) + "R", CIANO,
            f"{sg['n']} trades · IC {br(sg['ic95'][0])} a {br(sg['ic95'][1])}")
    rel.kpi(M + kw + 12, H - 470, kw, "entrada direta", br(dg["expectativa"]) + "R", MAG,
            f"{dg['n']} trades · IC {br(dg['ic95'][0])} a {br(dg['ic95'][1])}")
    rel.kpi(M + 2 * (kw + 12), H - 470, kw, "a favor do 4H", br(s["a_favor_tendencia_4h"]["True"]["expectativa"]) + "R",
            AMAR, f"só {s['a_favor_tendencia_4h']['True']['n']} trades · amostra pequena")
    # índice clicável
    c.setFont("Mono", 9); c.setFillColor(MUTED); c.drawString(M, H - 520, "ÍNDICE  (clique para ir)")
    itens = [("01", "Resultado e curva", "resultado"), ("02", "Onde está o sinal", "recortes"),
             ("03", "Leitura honesta e próximo passo", "leitura")]
    yy = H - 548
    for num, nome, chave in itens:
        c.setFont("MonoB", 12); c.setFillColor(CIANO); c.drawString(M, yy, num)
        c.setFont("TitM", 13); c.setFillColor(BRANCO); c.drawString(M + 34, yy, nome)
        c.setStrokeColor(BORDA); c.line(M, yy - 10, W - M, yy - 10)
        c.linkAbsolute(nome, chave, (M, yy - 10, W - M, yy + 16))
        yy -= 38
    c.setFont("Txt", 8.5); c.setFillColor(MUTED)
    c.drawString(M, 60, "Valores em R (múltiplos do risco). IC = intervalo de confiança de 95% por bootstrap.")

    # ============================================================ 2 · resultado
    rel.nova("resultado", "resultado")
    rel.titulo(H - 90, "Resultado", "Sistema completo contra entrada direta no rompimento, já com custos")
    img = ImageReader(os.path.join(pasta, "curva.png"))
    iw, ih = img.getSize(); lw = W - 2 * M; lh = lw * ih / iw
    rel.caixa(M - 4, H - 140 - lh - 4, lw + 8, lh + 8, borda=CIANO)
    c.drawImage(img, M, H - 140 - lh, lw, lh)
    # tabela
    y = H - 160 - lh - 22
    cols = [M, M + 210, M + 350]
    linhas = [("", "SISTEMA", "DIRETA"),
              ("Trades", sg["n"], dg["n"]),
              ("Acerto", f"{sg['acerto']*100:.1f}%".replace(".", ","), f"{dg['acerto']*100:.1f}%".replace(".", ",")),
              ("Expectativa com custos", br(sg["expectativa"]) + "R", br(dg["expectativa"]) + "R"),
              ("Intervalo de 95%", f"{br(sg['ic95'][0])} a {br(sg['ic95'][1])}", f"{br(dg['ic95'][0])} a {br(dg['ic95'][1])}"),
              ("Mediana", br(sg["mediana"]) + "R", br(dg["mediana"]) + "R"),
              ("Média sem os 2 maiores ganhos", br(sg["media_sem_2_maiores"]) + "R", br(dg["media_sem_2_maiores"]) + "R"),
              ("Profit factor", br(sg["profit_factor"], sinal=False), br(dg["profit_factor"], sinal=False)),
              ("Expectativa sem custos", br(s["sem_custos"]["expectativa"]) + "R", br(d["sem_custos"]["expectativa"]) + "R"),
              ("Pior sequência de perdas", sg["pior_sequencia"], dg["pior_sequencia"])]
    for i, (a, b, e) in enumerate(linhas):
        if i == 0:
            c.setFont("MonoB", 8); c.setFillColor(MUTED)
        else:
            c.setStrokeColor(BORDA); c.line(M, y + 12, W - M, y + 12)
            c.setFont("Txt", 9.5); c.setFillColor(TXT)
        c.drawString(cols[0], y, str(a))
        c.setFont("MonoB" if i else "MonoB", 9.5 if i else 8)
        c.setFillColor(CIANO if i else CIANO); c.drawString(cols[1], y, str(b))
        c.setFillColor(MAG if i else MAG); c.drawString(cols[2], y, str(e))
        y -= 21
    # funil
    f = r["funil"]; y -= 14
    c.setFont("TitM", 10.5); c.setFillColor(BRANCO); c.drawString(M, y, "Funil do sistema")
    y -= 22
    etapas = [("planos", f["plano"]), ("romperam", f["rompeu"]), ("retestaram", f["retestou"]),
              ("confirmaram", f["confirmou"]), ("viraram trade", sg["n"])]
    larg = W - 2 * M - 170
    for nome, v in etapas:
        c.setFont("Txt", 8.5); c.setFillColor(TXT); c.drawString(M, y, nome)
        wv = larg * v / f["plano"]
        c.setFillColor(Color(CIANO.red, CIANO.green, CIANO.blue, alpha=0.35 + 0.5 * v / f["plano"]))
        c.rect(M + 90, y - 3, wv, 11, stroke=0, fill=1)
        c.setFont("MonoB", 8.5); c.setFillColor(CIANO); c.drawString(M + 96 + wv, y - 1, f"{v}  ({v / f['plano'] * 100:.0f}%)".replace(".", ","))
        y -= 18

    # ============================================================ 3 · recortes
    rel.nova("onde está o sinal", "recortes")
    rel.titulo(H - 90, "Onde está o sinal", "Sistema completo por recorte · barras claras = menos de 30 trades (amostra pequena)")
    def grp(chave, nomes):
        g = s[chave]
        return [(nomes.get(k, k), v["n"], v["expectativa"]) for k, v in g.items() if v.get("n")]
    y = H - 140
    y = rel.barras(M, y, W - 2 * M, "Tendência do 4H", grp("a_favor_tendencia_4h", {"True": "a favor", "False": "contra"})) - 16
    y = rel.barras(M, y, W - 2 * M, "Tendência do 1H", grp("a_favor_tendencia_1h", {"True": "a favor", "False": "contra"})) - 16
    y = rel.barras(M, y, W - 2 * M, "Direção", grp("por_direcao", {})) - 16
    y = rel.barras(M, y, W - 2 * M, "O que rompeu", grp("por_origem", {"LTA": "LTA (piso subindo)", "LTB": "LTB (teto caindo)", "resistencia": "resistência", "suporte": "suporte"})) - 16
    y = rel.barras(M, y, W - 2 * M, "Sessão do rompimento", grp("por_sessao", {})) - 16
    y = rel.barras(M, y, W - 2 * M, "Ativo", grp("por_ativo", {})) - 10
    rel.caixa(M, y - 58, W - 2 * M, 54, borda=AMAR)
    rel.paragrafo(M + 12, y - 22, W - 2 * M - 24,
                  "Nenhum recorte chega a 30 trades. O padrão mais coerente com o manual é a tendência: 32 dos 36 trades foram contra o 4H, porque o robô ainda não aplica esse filtro.",
                  tam=9, cor=AMAR)

    # ============================================================ 4 · leitura
    rel.nova("leitura honesta", "leitura")
    rel.titulo(H - 90, "Leitura honesta")
    blocos = [
        (MAG, "1 · Entrada direta no rompimento: não funciona",
         f"{dg['n']} trades, média de {br(dg['expectativa'])}R, negativa até sem custos. O reteste é o que filtra os rompimentos falsos: só 32% dos planos rompem e menos da metade retesta e confirma."),
        (CIANO, "2 · Sistema completo: inconclusivo",
         f"Média de {br(sg['expectativa'])}R puxada por 2 ganhos grandes; sem eles, {br(sg['media_sem_2_maiores'])}R, e a mediana é negativa. Com {sg['n']} trades, o intervalo de {br(sg['ic95'][0])} a {br(sg['ic95'][1])}R não prova vantagem nem a falta dela."),
        (AMAR, "3 · Custos pesam ~0,14R por trade",
         "O robô coloca stops curtos (mediana de ~8 pips no EURUSD, contra ~18 pips nas análises manuais). Stop curto deixa o custo proporcionalmente maior."),
        (VERDE, "4 · Sinal a confirmar: tendência",
         "A favor do 4H: 4 trades, +1,67R. A favor do 1H: 11 trades, +0,38R, contra −0,06R dos que foram contra. Amostra pequena, mas na direção da regra do manual."),
    ]
    y = H - 130
    for cor, tit, txt in blocos:
        rel.caixa(M, y - 70, W - 2 * M, 66, borda=cor)
        c.setFillColor(cor); c.rect(M, y - 70, 4, 66, stroke=0, fill=1)
        c.setFont("TitM", 11); c.setFillColor(cor); c.drawString(M + 16, y - 20, tit)
        rel.paragrafo(M + 16, y - 38, W - 2 * M - 32, txt, tam=9, entre=13)
        y -= 84
    c.setFont("Tit", 15); c.setFillColor(BRANCO); c.drawString(M, y - 10, "Próximo passo")
    rel.caixa(M, y - 96, W - 2 * M, 72, borda=CIANO, brilho=CIANO)
    rel.paragrafo(M + 16, y - 46, W - 2 * M - 32,
                  "Aplicar no robô e no teste os filtros do manual que ficaram de fora, começando pelo alinhamento com a tendência do 4H e do 1H, e testar de novo. Depois, ampliar para 8 meses usando o 1H. A regra já existe no manual: não é ajuste para caber nos dados.",
                  tam=9.5, cor=BRANCO, entre=14)
    y -= 122
    c.setFont("Mono", 8.5); c.setFillColor(MUTED); c.drawString(M, y, "LIMITAÇÕES")
    lims = ["~11 semanas de 15m (máximo da fonte gratuita)",
            "Dados do Yahoo: EURUSD em degraus de ~1,2 pip; US500 convertido do futuro",
            "Sem filtro de notícias e sem limite diário de perdas",
            "Sem os filtros do manual além de sessão, relação mínima de R e stop dentro do risco",
            "Linhas e níveis do robô ainda em calibração (validação em curso)"]
    y -= 16
    for l in lims:
        c.setFillColor(MAG); c.rect(M, y + 2, 4, 4, stroke=0, fill=1)
        c.setFont("Txt", 9); c.setFillColor(TXT); c.drawString(M + 12, y, l); y -= 15
    rel.salvar()
    return os.path.join(pasta, "relatorio.pdf")


if __name__ == "__main__":
    print(gerar(sys.argv[1] if len(sys.argv) > 1 else "testes/2026-11-13"))
