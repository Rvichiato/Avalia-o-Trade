# Teste histórico · filtro de tendência · 16/11/2026

**Variante testada:** só planos a favor da tendência do 4H, ou do 1H quando o 4H está lateral (regra do manual). A base é o mesmo robô sem o filtro (correções de sexta já incluídas), rodado nos mesmos dados até 16/11 11h30 (Brasília). As regras ao vivo não mudaram.

| Sistema completo, com custos | Sem filtro | Com filtro |
|---|---|---|
| Trades | 35 | 15 |
| Acerto | 37% | 47% |
| Expectativa | −0,03R | +0,32R |
| Intervalo de 95% | −0,40 a +0,39 | −0,30 a +1,01 |
| Soma | −0,9R | +4,8R |
| Maior queda | 5,5R | 2,7R |
| Mediana | −0,15R | −0,11R |
| Média sem os 2 maiores ganhos | −0,18R | +0,03R |
| Profit factor | 0,95 | 1,82 |

## Leitura honesta
1. **O filtro aponta na direção certa.** Ele tira mais da metade dos trades, deixa a média positiva e corta a queda máxima pela metade. É o mesmo sinal da sexta, e a regra vem do manual: não foi ajustada aos dados.
2. **Ainda não está provado.** O intervalo inclui o zero e, sem os 2 maiores ganhos, a média fica perto de zero. Quase todo o ganho (+4,8R) vem de 6 compras no USDJPY a favor da alta. O EURUSD fica no zero e o US500 teve só 2 trades.
3. **Pistas para depois, não para agora:** Londres foi melhor que Nova York nas duas versões. Na base, zonas foram melhores que linhas. Atravessar o dado americano (8h30 de NY) não mostrou efeito claro.
4. **Correção pendente:** dois trades iguais no EURUSD em 15/09 vieram de duas linhas quase idênticas e foram contados duas vezes.

## Ouro (só estudo, medido em R, sem o limite de US$ 2)
- Sem filtro: 11 trades, −0,13R (intervalo de −0,82 a +0,60). Nove foram compras em rompimento de LTB do 15m com o 4H em baixa ou lateral, e 6 deram stop.
- Com filtro: só 2 trades. Não dá para concluir nada.
- Vendas a favor da queda, como o short de 13/11 em 3.904, saíram só 2 vezes: o robô ainda não enxerga bem as linhas do ouro.
- Entrada direta no rompimento também perde no ouro (46 trades, −0,19R).

## Próximo passo
Aumentar a amostra antes de qualquer outra mudança: o mesmo teste no 1H em 8 meses e, quando chegar, no histórico da Tickmill exportado do MT5. Corrigir a duplicidade de linhas quase iguais.

Arquivos: `base/`, `filtro/`, `ouro_base/`, `ouro_filtro/` (resumo.json, trades.csv, curva.png), `curva_comparada.png`, `relatorio.pdf`.
Comandos: `python scripts/teste_historico.py [--filtro-tendencia] [--estudo] [ATIVOS] --saida <pasta>` e `python scripts/relatorio_comparativo_pdf.py testes/2026-11-16`.
