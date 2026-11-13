"""Gera a análise do momento: um JSON com tudo e um painel PNG por ativo.

Uso:
  python scripts/analise.py                    # EURUSD, USDJPY e US500
  python scripts/analise.py EURUSD US500       # só os escolhidos
  python scripts/analise.py --saida saida/     # pasta de saída (padrão: saida/)
O plano desenhado é o melhor válido de cada ativo; os outros vão no JSON.
"""
import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(__file__))
import pandas as pd
import sistema as S
import grafico as G


def melhor_plano(r):
    """Só desenha plano a favor da tendência: do 4H, ou do 1H quando o 4H está lateral.
    Sem plano assim, nada é desenhado (o painel diz "só observar")."""
    t4, t1 = r["tendencia"]["4h"], r["tendencia"]["1h"]
    ref = t4 if t4 != "lateral" else t1
    if ref == "lateral":
        cand = [p for p in r["planos"] if p["valido"]]
    else:
        alvo = "venda" if ref == "baixa" else "compra"
        cand = [p for p in r["planos"] if p["direcao"] == alvo]
    if not cand:
        return None
    validos = [p for p in cand if p["valido"]]
    if validos:  # o válido mais perto do preço
        return sorted(validos, key=lambda p: (p["distancia_preco_pips"], -(p["rr"] or 0)))[0]
    return sorted(cand, key=lambda p: -(p["rr"] or 0))[0]  # nenhum vale: mostra o melhor, marcado como inválido


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ativos", nargs="*", default=["EURUSD", "USDJPY", "US500"])
    ap.add_argument("--saida", default=os.path.join(S.RAIZ, "saida"))
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    tudo = {}
    for ativo in a.ativos:
        r, dfs = S.analisar(ativo)
        p = melhor_plano(r)
        r["plano_desenhado"] = p
        hora = (pd.Timestamp(r["ultimo_candle_15m_utc"]) + pd.Timedelta(minutes=15)
                + pd.Timedelta(hours=S.CFG["fuso_exibicao_horas"]))
        nome = f"{ativo.lower()}_{hora.strftime('%Y%m%d_%H%M')}.png"
        sub = r["ajuste_us500"] or ""
        r["imagem"] = G.painel(ativo, r, dfs, p, os.path.join(a.saida, nome), sub)
        tudo[ativo] = r
        print(f"{ativo}: preço {r['preco']}, {len(r['planos'])} planos, imagem {r['imagem']}")
    with open(os.path.join(a.saida, "analise.json"), "w") as f:
        json.dump(tudo, f, indent=1, ensure_ascii=False, default=str)


if __name__ == "__main__":
    main()
