# Teste histórico do Break & Retest · 13/11/2026

## O que foi testado
- **Período:** cerca de 11 semanas de candles de 15m. EURUSD e USDJPY desde 23/08/2026, US500 desde 04/09/2026. Para o 1H e o 4H, até 8 meses.
- **Método:**
  - A cada hora cheia da sessão, o motor fez a análise usando só os candles já fechados naquele instante.
  - Cada plano válido (relação de pelo menos 1,5R e stop dentro do risco de US$ 2) foi simulado candle a candle no 15m.
  - O teste comparou duas formas de entrar:
    - **Sistema completo:** rompimento, depois reteste, depois confirmação, com entrada na abertura do candle seguinte.
    - **Entrada direta:** no fechamento do próprio candle de rompimento.
- **Regras aplicadas:**
  - O rompimento só vale em Londres e Nova York; no US500, só no pregão (11h45–18h), com saída até 17h45.
  - O plano vale por 4h, e o reteste mais a confirmação têm até 4h depois do rompimento.
  - A posição fica aberta no máximo 12h.
  - Stops menores que 0,75 da volatilidade do 15m (ou que 3 vezes o custo) foram descartados, por não serem operáveis.
- **Custos:** spread, comissão e deslizamento de 0,2 pip por lado, descontados de cada resultado. Quando stop e alvo são tocados no mesmo candle, conta como stop.

## Resultado

| | Sistema completo | Entrada direta |
|---|---|---|
| Trades | 36 | 140 |
| Acerto | 38,9% | 35,7% |
| Expectativa (com custos) | +0,08R | −0,18R |
| Intervalo de confiança de 95% | −0,40R a +0,57R | −0,39R a +0,05R |
| Mediana | −0,46R | −1,05R |
| Média sem os 2 maiores ganhos | −0,13R | −0,25R |
| Profit factor | 1,13 | 0,73 |
| Expectativa sem custos | +0,21R | −0,06R |
| Pior sequência de perdas | 5 | 10 |

**Funil do sistema:** dos 477 planos, 155 romperam (32%), 74 retestaram, 52 confirmaram e 36 viraram trade. Os outros 16 foram descartados na entrada, por R abaixo do mínimo ou stop pequeno demais.

## Leitura honesta
1. **Entrar direto no rompimento não funciona.** São 140 trades com média negativa, negativa até sem custos, e o intervalo quase todo abaixo de zero. A ideia que surgiu nos três casos de rompimento sem reteste (06, 10 e 11/11) não se sustenta: o reteste filtra boa parte dos rompimentos falsos.
2. **O sistema completo ainda não mostra vantagem.** A média de +0,08R depende de dois trades grandes: sem eles, fica em −0,13R, e a mediana é negativa. Com 36 trades, o intervalo vai de −0,40R a +0,57R, ou seja, não prova vantagem nem a falta dela.
3. **Os custos pesam muito:** cerca de 0,14R por trade, porque o motor coloca stops curtos (mediana de ~8 pips no EURUSD, contra ~18 pips nas análises manuais).
4. **O sinal mais importante, ainda em amostra pequena:** 32 dos 36 trades foram contra a tendência do 4H, porque o motor ainda não aplica esse filtro do manual.
   - A favor do 4H: 4 trades, +1,67R.
   - A favor do 1H: 11 trades, +0,38R, contra −0,06R dos que foram contra.
   - Vendas: 9 trades, −0,30R. Rompimentos de LTA: 7 trades, −0,47R.
   - Tudo isso é amostra pequena e não deve ser tratado como conclusão.

## Limitações
- Só cerca de 11 semanas de 15m (o máximo da fonte gratuita).
- Dados do Yahoo: o EURUSD anda em degraus de ~1,2 pip, e o US500 vem do futuro convertido.
- Sem filtro de notícias e sem limite diário de perdas.
- Sem os filtros do manual além de sessão, relação mínima de R e stop dentro do risco.
- Linhas e níveis do motor ainda em calibração (validação em curso).

## Próximo passo recomendado
Aplicar no motor e no teste os filtros do manual que ficaram de fora, começando pelo alinhamento com a tendência do 4H e do 1H, e testar de novo. A regra já existe no manual: não é ajuste para caber nos dados. Em seguida, aumentar a amostra rodando o mesmo teste no 1H em 8 meses.
