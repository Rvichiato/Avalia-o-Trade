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
    "pivo_seguranca": 2,             # topo/fundo confirmado com 2 candles de cada lado (30 min)
    "max_barras_seguranca": 48,      # limite de tempo na saída pela linha de segurança (muda com --max-barras)
}
UTC = pd.Timedelta(0)
OPC = {"filtro_tendencia": False, "estudo": False, "reteste_rompido": False}  # ligados por --filtro-tendencia / --estudo


def a_favor_da_tendencia(p, tend):
    """Filtro do manual: só a favor do 4H; se o 4H estiver lateral, a favor do 1H;
    com os dois laterais, qualquer direção (igual ao painel ao vivo)."""
    ref = tend["4h"] if tend["4h"] != "lateral" else tend["1h"]
    if ref == "lateral":
        return True
    return p["direcao"] == ("venda" if ref == "baixa" else "compra")


def cruza_dado_eua(t_ent, t_sai):
    """A posição estava aberta às 8h30 de Nova York (horário dos dados americanos) num dia útil?"""
    a = pd.Timestamp(t_ent).tz_convert("America/New_York")
    b = pd.Timestamp(t_sai).tz_convert("America/New_York") + pd.Timedelta(minutes=15)
    d = a.normalize()
    while d <= b:
        x = d + pd.Timedelta(hours=8, minutes=30)
        if d.weekday() < 5 and a <= x < b:
            return True
        d += pd.Timedelta(days=1)
    return False


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


def gerenciar_seguranca(d15, i0, i_a0, direcao, entrada, stop, ativo, a15):
    """Saída pela "linha de segurança" (guia da Tori / nosso Modo B), sem olhar o futuro.
    Compra: a linha liga fundos cada vez mais altos; o 1º ponto é o fundo do reteste (i_a0).
    A cada fundo novo confirmado (2 candles de cada lado) acima da linha, o ponto B anterior vira o
    novo ponto A e a linha fica mais inclinada, desde que nenhum fechamento entre A e B fure a linha.
    Sai no fechamento do candle que fechar além da linha. O stop inicial do plano continua valendo.
    Venda: o espelho, com topos cada vez mais baixos. Retorna (saida, motivo, i_saida)."""
    k = P["pivo_seguranca"]
    fim = min(len(d15), i0 + P["max_barras_seguranca"])
    hs, ls, cs, os_ = d15.h.values, d15.l.values, d15.c.values, d15.o.values
    ext = ls if direcao == "compra" else hs
    melhor = (lambda a, b: a > b) if direcao == "compra" else (lambda a, b: a < b)  # "mais alto" na compra
    A, B = i_a0, None
    tol = 0.1 * a15
    val = lambda i: ext[A] + (ext[B] - ext[A]) * (i - A) / (B - A)
    for i in range(i0, fim):
        t = d15.index[i]
        brt = t + pd.Timedelta(hours=C["fuso_exibicao_horas"])
        if C["ativos"][ativo]["sessao"] == "indice" and brt.hour + brt.minute / 60 >= 17.75:
            return float(os_[i]), "fechamento 17h45", i
        if brt.weekday() == 4 and brt.hour >= 18:
            return float(os_[i]), "fim de semana", i
        # stop inicial (dentro do candle) vem primeiro
        if (direcao == "compra" and ls[i] <= stop) or (direcao == "venda" and hs[i] >= stop):
            return stop, "stop", i
        # linha rompida no fechamento
        if B is not None and i > B:
            v = val(i)
            if (direcao == "compra" and cs[i] < v - tol) or (direcao == "venda" and cs[i] > v + tol):
                return float(cs[i]), "linha de segurança", i
        # novo pivô confirmado agora (o candle j = i - k já tem k candles de cada lado)
        j = i - k
        if j > (B if B is not None else A) and j - k >= 0:
            janela = ext[j - k:j + k + 1]
            e_pivo = ext[j] == (janela.min() if direcao == "compra" else janela.max())
            if e_pivo and melhor(ext[j], ext[B if B is not None else A]):
                nA = B if B is not None else A
                if B is not None and not melhor(ext[j], val(j)):
                    continue  # o fundo novo furou a linha atual: não vira linha mais inclinada
                # nenhum fechamento entre o novo A e o pivô pode furar a linha nova
                linha = ext[nA] + (ext[j] - ext[nA]) * (np.arange(nA, j + 1) - nA) / (j - nA)
                fura = (cs[nA:j + 1] < linha - tol).any() if direcao == "compra" else (cs[nA:j + 1] > linha + tol).any()
                if not fura:
                    A, B = nA, j
    i = fim - 1
    return float(cs[i]), "tempo", i


# ---------------------------------------------------------------- manual "Tori A+" (linha de ação + linha de segurança)
def gerenciar_linha(d15, i0, direcao, stop, ativo, a15, linha, ancora):
    """Segura a posição enquanto a linha de segurança não romper no fechamento.
    linha = (iA, pA, iB, pB) no índice do 15m; ancora = (i, preço) do último fundo (compra) ou topo (venda)
    usado. A cada novo fundo/topo confirmado além da linha, a linha passa a ligar a âncora anterior a ele
    (o ponto B anterior vira o novo ponto A), desde que fique mais inclinada e nenhum fechamento entre os
    dois fure a linha nova. O stop inicial vale dentro do candle."""
    k = P["pivo_seguranca"]
    fim = min(len(d15), i0 + P["max_barras_seguranca"])
    hs, ls, cs, os_ = d15.h.values, d15.l.values, d15.c.values, d15.o.values
    ext = ls if direcao == "compra" else hs
    compra = direcao == "compra"
    iA, pA, iB, pB = linha
    tol = 0.1 * a15
    val = lambda i: pA + (pB - pA) * (i - iA) / (iB - iA)
    incl = lambda: (pB - pA) / (iB - iA)
    for i in range(i0, fim):
        brt = d15.index[i] + pd.Timedelta(hours=C["fuso_exibicao_horas"])
        if C["ativos"][ativo]["sessao"] == "indice" and brt.hour + brt.minute / 60 >= 17.75:
            return float(os_[i]), "fechamento 17h45", i
        if brt.weekday() == 4 and brt.hour >= 18:
            return float(os_[i]), "fim de semana", i
        if (compra and ls[i] <= stop) or (not compra and hs[i] >= stop):
            return stop, "stop", i
        v = val(i)
        if (compra and cs[i] < v - tol) or (not compra and cs[i] > v + tol):
            return float(cs[i]), "linha de segurança", i
        j = i - k
        if j > ancora[0] and j - k >= 0:
            jan = ext[j - k:j + k + 1]
            if ext[j] == (jan.min() if compra else jan.max()) and ((ext[j] > val(j)) if compra else (ext[j] < val(j))):
                nA, npA = ancora
                if j > nA:
                    ninc = (ext[j] - npA) / (j - nA)
                    mais_inclinada = ninc > incl() if compra else ninc < incl()
                    lin = npA + ninc * (np.arange(nA, j + 1) - nA)
                    fura = (cs[nA:j + 1] < lin - tol).any() if compra else (cs[nA:j + 1] > lin + tol).any()
                    if mais_inclinada and not fura:
                        iA, pA, iB, pB = nA, npA, j, float(ext[j])
                ancora = (j, float(ext[j]))
    i = fim - 1
    return float(cs[i]), "tempo", i


def simular_tori(ativo, d15, i_ini, L, Sg, a15, ctx):
    """Linha de ação L rompe no fechamento (na sessão), com a linha oposta Sg (segurança) já formada.
    Entra no fechamento do candle de rompimento; stop logo além da linha de segurança; risco baixo =
    stop até TORI['risco_max_atr'] ATRs do 15m; sai quando a linha de segurança romper."""
    pip = C["ativos"][ativo]["pip"]
    direcao = "venda" if L["tipo"] == "LTA" else "compra"
    compra = direcao == "compra"
    i0 = i_ini - 1
    lv = lambda i: L["valor_agora"] + L["inclinacao_por_hora"] / 4 * (i - i0)
    sv = lambda i: Sg["valor_agora"] + Sg["inclinacao_por_hora"] / 4 * (i - i0)
    tol = 0.1 * a15
    lim = min(len(d15), i_ini + P["validade_plano_barras"])
    cs, hs, ls = d15.c.values, d15.h.values, d15.l.values
    for i in range(i_ini, lim):
        # a linha de segurança rompeu antes da linha de ação: o cenário acabou
        if (compra and cs[i] < sv(i) - tol) or (not compra and cs[i] > sv(i) + tol):
            return None
        rompeu = (cs[i] > lv(i) + tol) if compra else (cs[i] < lv(i) - tol)
        if not rompeu:
            continue
        if not sessao_ok(ativo, d15.index[i]):
            return None
        ent = float(cs[i])
        stop = sv(i) - tol if compra else sv(i) + tol
        risco = (ent - stop) if compra else (stop - ent)
        if risco <= 0:
            return None
        if risco < max(P["stop_minimo_atr"] * a15, 3 * custo_pips(ativo, ent) * pip):
            return dict(modo="tori", ativo=ativo, descartado="stop pequeno demais")
        if risco > TORI["risco_max_atr"] * a15:
            return dict(modo="tori", ativo=ativo, descartado="risco alto (longe da linha de segurança)")
        # âncora inicial: último fundo (compra) ou topo (venda) antes da entrada
        jan = slice(max(0, i - 8), i + 1)
        ia = jan.start + int(np.argmin(ls[jan]) if compra else np.argmax(hs[jan]))
        linha = (i0, Sg["valor_agora"], i0 + 4, Sg["valor_agora"] + Sg["inclinacao_por_hora"])
        sai, mot, j = gerenciar_linha(d15, i + 1, direcao, stop, ativo, a15, linha, (ia, float(ls[ia] if compra else hs[ia])))
        p = dict(direcao=direcao, stop=stop, alvo=None, rr=None,
                 origem=dict(tipo=L["tipo"], tf=L["tf"], toques=L["toques"]))
        reg = _registro("tori", ativo, p, d15, i, i, j, ent, sai, mot, ctx, pip)
        t_ent = d15.index[i]
        reg.update(tf_seguranca=Sg["tf"], toques_seguranca=Sg["toques"], risco_atr=round(risco / a15, 2),
                   idade_linha_h=round((t_ent - pd.Timestamp(L["a_hora"])).total_seconds() / 3600, 1),
                   a_favor_tendencia=a_favor_da_tendencia(dict(direcao=direcao), ctx["tendencia"]))
        return reg
    return None


TORI = {"risco_max_atr": 2.0}


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
    ja_rompido = p.get("tipo") == "reteste_rompido"
    # invalidação: no nível comum é o próprio nível; no reteste de nível já rompido é o outro lado da zona
    inv0 = (p["nivel_ate"] if direcao == "venda" else p["nivel_de"]) if ja_rompido else nivel0
    if ja_rompido:
        if not OPC.get("reteste_rompido"):
            return out, funil
        funil["rompeu"] = 1
        fase, i_romp = 1, i_ini
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
        nv_inv = inv0 + incl * (i - i_ini + 1)
        if fase == 1:
            voltou = (r.c > nv_inv + tol) if direcao == "venda" else (r.c < nv_inv - tol)
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
            voltou = (r.c > nv_inv + tol) if direcao == "venda" else (r.c < nv_inv - tol)
            if voltou:
                break
            confirma = (r.c < r.o and r.c < nv) if direcao == "venda" else (r.c > r.o and r.c > nv)
            if confirma and ja_rompido and not sessao_ok(ativo, d15.index[i]):
                confirma = False  # nível já rompido: a confirmação é o gatilho e precisa cair na sessão
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
                reg = _registro("sistema", ativo, p, d15, i_romp, i + 1, j, ent, sai, mot, contexto, pip)
                if OPC.get("saida_seguranca"):
                    # mesma operação, saída pela linha de segurança; o resultado do alvo fixo fica guardado ao lado
                    seg = slice(i_romp, i + 1)
                    i_a0 = i_romp + int(np.argmin(d15.l.values[seg]) if direcao == "compra" else np.argmax(d15.h.values[seg]))
                    sai2, mot2, j2 = gerenciar_seguranca(d15, i + 1, i_a0, direcao, ent, p["stop"], ativo, a15)
                    reg2 = _registro("sistema", ativo, p, d15, i_romp, i + 1, j2, ent, sai2, mot2, contexto, pip)
                    reg2.update(R_alvo_fixo=reg["R"], R_bruto_alvo_fixo=reg["R_bruto"], motivo_alvo_fixo=reg["motivo"],
                                barras_alvo_fixo=reg["barras"])
                    reg = reg2
                out.append(reg)
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
        atravessou_dado_eua=cruza_dado_eua(t_ent, d15.index[i_sai]),
        origem_linha=o.get("tipo") in ("LTA", "LTB"),
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
    fim_pos = {}  # manual Tori: hora de saída da última posição por direção
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
        if OPC.get("tori"):
            preco = float(c15.c.iloc[-1])
            ativas = [l for tf in ("15m", "1h", "4h") for l in r["linhas"].get(tf, []) if not l["rompida"]]
            for L in ativas:
                compra = L["tipo"] == "LTB"
                if (compra and L["valor_agora"] <= preco) or (not compra and L["valor_agora"] >= preco):
                    continue  # a linha de ação tem de estar do lado certo do preço
                if OPC["filtro_tendencia"] and not a_favor_da_tendencia(dict(direcao="compra" if compra else "venda"), r["tendencia"]):
                    continue
                if abs(L["valor_agora"] - preco) > 2 * r["atr"]["1h"]:
                    continue
                # linha de segurança: a oposta, já formada, do outro lado do preço, a mais próxima
                opostas = [l for l in ativas if l["tipo"] != L["tipo"] and
                           ((l["valor_agora"] < preco) if compra else (l["valor_agora"] > preco))]
                if not opostas:
                    continue
                Sg = min(opostas, key=lambda l: abs(l["valor_agora"] - preco))
                chave = ("compra" if compra else "venda", round(L["valor_agora"] / max(a15, 1e-9)))
                ativos_recentes = [x for x in ativos_recentes if (t - x[0]) < pd.Timedelta(hours=8)]
                if any(x[1] == chave[0] and abs(x[2] - L["valor_agora"]) < P["duplicata_atr"] * a15 for x in ativos_recentes):
                    continue
                ativos_recentes.append((t, chave[0], L["valor_agora"]))
                reg = simular_tori(ativo, d15, i_ini, L, Sg, a15, ctx)
                if reg is None:
                    continue
                if "descartado" in reg:
                    descartes += 1
                    continue
                # uma posição por direção de cada vez: não abre outra enquanto a anterior está aberta
                if reg["t_entrada"] <= fim_pos.get(reg["direcao"], ""):
                    continue
                fim_pos[reg["direcao"]] = reg["t_saida"]
                trades.append(reg)
            continue
        for p in r["planos"]:
            if OPC["estudo"]:  # estudo: ignora o limite de US$ 2 da conta, mede só em R
                if not (p["rr"] and p["rr"] >= C["conta"]["rr_minimo"]):
                    continue
            elif not p["valido"]:
                continue
            if OPC["filtro_tendencia"] and not a_favor_da_tendencia(p, r["tendencia"]):
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
    res = {"parametros": P, "opcoes": OPC, "periodos": periodos, "descartes_R_na_entrada": descartes}
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
            linha_vs_zona=grupos(d, "origem_linha") if len(d) and "origem_linha" in d else {},
            atravessou_dado_eua=grupos(d, "atravessou_dado_eua") if len(d) and "atravessou_dado_eua" in d else {},
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
    ap.add_argument("--filtro-tendencia", action="store_true", help="só planos a favor do 4H (ou do 1H com 4H lateral)")
    ap.add_argument("--reteste-rompido", action="store_true", help="inclui os planos de reteste de nível já rompido")
    ap.add_argument("--estudo", action="store_true", help="ignora o limite de risco da conta (ex.: ouro), mede em R")
    ap.add_argument("--origem-perna", action="store_true", help="prioriza a linha que nasce na origem da perna")
    ap.add_argument("--linhas-4h", action="store_true", help="3 linhas por tempo gráfico e linhas do 4H também viram gatilho")
    ap.add_argument("--so-linhas", action="store_true", help="só LTA/LTB viram gatilho; zonas ficam só como alvo/obstáculo")
    ap.add_argument("--zona-max", action="store_true", help="zona horizontal com no máximo 1 ATR do 1h de largura")
    ap.add_argument("--tori", action="store_true", help="manual Tori A+: linha de ação rompe com a linha de segurança já formada")
    ap.add_argument("--risco-max-atr", type=float, default=2.0, help="manual Tori: stop até quantos ATR do 15m (risco baixo)")
    ap.add_argument("--saida-seguranca", action="store_true", help="sai pela linha de segurança em vez do alvo fixo (mesmas entradas)")
    ap.add_argument("--max-barras", type=int, default=None, help="limite de candles de 15m dentro da operação na saída pela linha")
    ap.add_argument("--saida", default=os.path.join(S.RAIZ, "testes", pd.Timestamp.now().strftime("%Y-%m-%d")))
    a = ap.parse_args()
    OPC["filtro_tendencia"], OPC["estudo"], OPC["reteste_rompido"] = a.filtro_tendencia, a.estudo, a.reteste_rompido
    OPC.update(origem_perna=a.origem_perna, linhas_4h=a.linhas_4h, so_linhas=a.so_linhas, zona_max=a.zona_max,
               saida_seguranca=a.saida_seguranca, tori=a.tori)
    TORI["risco_max_atr"] = a.risco_max_atr
    if a.tori and not a.max_barras:
        P["max_barras_seguranca"] = 192
    if a.max_barras:
        P["max_barras_seguranca"] = a.max_barras
    if a.origem_perna:
        C["linhas"]["bonus_origem"] = 3
    if a.linhas_4h:
        C["linhas"]["max_ativas"] = 3
        C["linhas"]["gatilho_tfs"] = ["15m", "1h", "4h"]
    if a.so_linhas:
        C["niveis"]["gatilho_zonas"] = False
    if a.zona_max:
        C["niveis"]["largura_max_atr_1h"] = 1.0
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
