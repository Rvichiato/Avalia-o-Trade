# Teste histórico com os preços da Tickmill (MT5) · 16/11/2026

**Dados:** M15 exportado do MT5 da Tickmill: EURUSD, USDJPY e US500, de 02/01/2024 a 16/11/2026 12h45 (Brasília). O horário do servidor (GMT+2 no inverno, GMT+3 no verão dos EUA) foi convertido e conferido contra o Yahoo. O 1H e o 4H foram montados a partir do M15. Mesmo robô, mesmos custos e mesmas regras do teste anterior.

| Sistema completo, com custos | Sem filtro | Com filtro de tendência |
|---|---|---|
| Trades | 356 | 128 |
| Acerto | 33% | 39% |
| Expectativa | −0,19R | −0,02R |
| Intervalo de 95% | −0,33 a −0,06 | −0,26 a +0,24 |
| Soma | −68,7R | −3,1R |
| Maior queda | 73,0R | 11,8R |
| Expectativa sem custos | −0,08R | +0,09R |
| Entrada direta (referência) | −0,11R (1.670) | −0,06R (643) |

**Por ano, com filtro:** 2024 −0,06R (54 trades) · 2025 −0,11R (33) · 2026 +0,10R (41).

## Leitura honesta
1. **Sem filtro, o robô perde, e agora com certeza estatística:** o intervalo inteiro fica abaixo de zero.
2. **O filtro de tendência é indispensável, mas não basta.** Ele corta a perda de −0,19R para −0,02R e a queda máxima de 73R para 12R. Antes dos custos fica em +0,09R, mas os custos levam ~0,11R por trade.
3. **O resultado positivo das últimas 12 semanas não se repete em 2024–2025.**
4. **Onde escapa:** só 17% dos trades chegam ao alvo. O stop mediano é de ~14 pips. Os 31 trades em que o 4H estava lateral (e o filtro usou o 1H) deram −0,31R. Só com o 4H definido: 97 trades, +0,07R.
5. **Recortes vistos depois dos dados:** vendas em rompimento de LTA (+0,20R) e a sobreposição Londres+NY (+0,23R) se destacam. São hipóteses para testar, não regras. "Atravessou o dado americano" parece melhor, mas tem viés: quem toma stop rápido nem chega ao dado.
6. **O que isto mede:** é o robô, não as entradas manuais do Rodrigo. O robô ainda desenha linhas diferentes das dele.

## Dados: Yahoo x Tickmill (12 semanas em comum)
- EURUSD: o Yahoo fica **~3,2 pips acima** da Tickmill, de forma estável, e com candles ~17% menores.
- USDJPY: diferença abaixo de 1 pip.
- US500: o futuro fica ~45 pontos acima do CFD, com variação ao longo dos meses (por isso o ajuste pelo SPX).

## Próximo passo (registrado antes de testar)
(a) só operar com o 4H definido; (b) stops mais largos ou descartar trades em que o custo passe de 10% do risco; (c) revisar alvo e saída por tempo. Desenvolver em 2024–2025 e validar só em 2026. Em paralelo, validar as linhas do robô contra os prints do Rodrigo.

Arquivos: `base/`, `filtro/`, `curva_comparada.png`, `relatorio.pdf`. Dados em `dados/mt5/` (importados com `scripts/importar_mt5.py`). Para rodar: `PASTA_DADOS=dados/mt5 python scripts/teste_historico.py [--filtro-tendencia] --saida <pasta>`.
