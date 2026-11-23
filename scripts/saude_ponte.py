"""Mostra se a ponte do TradingView está entregando os candles da Tickmill em dia.

Uso: python scripts/saude_ponte.py
Para cada ativo: último candle ao vivo recebido, atraso em minutos e a fonte que o robô vai usar
(Tickmill ou Yahoo de reserva, com o motivo). Termina com uma linha de resumo para as rotinas.
"""
import os, sys, json
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import sistema as S


def mercado_aberto(agora):
    """Forex: de domingo 22h a sexta 22h (UTC)."""
    d, h = agora.weekday(), agora.hour
    return not (d == 5 or (d == 4 and h >= 22) or (d == 6 and h < 22))


def main():
    agora = pd.Timestamp.now(tz="UTC")
    aberto = mercado_aberto(agora)
    p = os.path.join(S.RAIZ, "dados", "tv", "ultimo_recebimento.json")
    rec = json.load(open(p)) if os.path.exists(p) else None
    print(f"Agora: {S._brt(agora)} (Brasília) · mercado {'aberto' if aberto else 'fechado'}")
    print(f"Último webhook recebido: {rec['recebido_utc'] if rec else 'nenhum ainda'}")
    problemas = []
    for a in ("EURUSD", "USDJPY", "US500", "XAUUSD"):
        vivo = os.path.join(S.RAIZ, "dados", "tv", f"{a}_15m.csv")
        if os.path.exists(vivo):
            ult = S._ler_csv(vivo).index[-1]
            atraso = int((agora - (ult + pd.Timedelta(minutes=15))).total_seconds() // 60)
            txt = f"último candle {S._brt(ult)}, atraso {atraso} min"
        else:
            atraso, txt = None, "sem candles ao vivo"
        origem, nota = S.fonte(a)
        print(f"  {a:7s} {txt:40s} → {('Tickmill' if origem == 'tickmill' else 'Yahoo (reserva)')}"
              + (f" · {nota}" if origem != "tickmill" and nota else ""))
        if aberto and a != "XAUUSD" and (origem != "tickmill"):
            problemas.append(a)
    if problemas:
        print(f"RESUMO: ATENÇÃO — análise de {', '.join(problemas)} está usando o Yahoo de reserva.")
    else:
        print("RESUMO: ponte em dia" if aberto else "RESUMO: mercado fechado; nada a conferir")


if __name__ == "__main__":
    main()
