# Plano do sistema Break & Retest

**Propósito:** tornar o modelo vencedor e rentável, com prova estatística, não com impressão. Toda melhoria (dados, código, portal, cérebro) se justifica só se ajudar a medir ou aumentar a expectativa em R.

## Ciclo de melhoria (como o modelo evolui)
1. **Ideia:** vem da pesquisa (estudos e fontes de dados), da revisão diária ou do que o Rodrigo observa no mercado.
2. **Teste no histórico:** roda com custos e sem ver o futuro, comparando com a versão atual. Toda ideia testada fica registrada em `testes/`, inclusive as que falharam (13/11: entrada direta no rompimento descartada).
3. **Validação ao vivo:** o que passou no histórico roda em paralelo nas análises automáticas, medido pela revisão diária.
4. **Decisão:** o Rodrigo aprova antes de virar regra. Uma mudança por vez, para saber o que funcionou.

## Critério de sucesso (do manual)
50 trades com resultado, expectativa acima de +0,2R, profit factor acima de 1,3, drawdown abaixo de 10%, disciplina de 90% ou mais. Para medir uma vantagem de +0,2R com confiança são necessários cerca de 200 trades.

## Decisões de 13/11/2026
1. Análises automáticas em todo dia útil: 05h20 (EURUSD e USDJPY) e 11h45 (US500, EURUSD e USDJPY), sem prints do Rodrigo. Pedidos de imagem a qualquer hora continuam disponíveis.
2. Coleta de candles a cada 5 minutos pelo GitHub Actions (fonte atual: Yahoo).
3. Revisão diária das 18h47 passa a medir o resultado hipotético de cada plano automático; às sextas, revisa também o processo (atraso, falhas, acerto) e propõe até 3 melhorias.
4. Pesquisa avalia fontes de dados toda semana (histórico em `docs/fontes-de-dados.md`).
5. Nenhuma regra muda sem aprovação do Rodrigo. Nada executa ordem sozinho.

## Semana de 16 a 20/11: rodar o que foi construído
- Deixar as rotinas rodarem sem mudanças de regra. Rodrigo opera a conta demo pelos planos e registra tudo na Mesa, inclusive setups vistos e não operados.
- Rodrigo manda um print por dia com as próprias marcações, para comparar com as linhas do robô.
- Sexta 20/11: a revisão semanal traz o primeiro balanço (planos que dispararam, resultado hipotético, atraso dos dados, onde o robô divergiu das marcações).

## Resultado de 16/11 (teste com filtro de tendência)
Com o filtro: 15 trades, +0,32R por trade (intervalo de −0,30 a +1,01), soma de +4,8R, queda máxima de 2,7R. Sem filtro, nos mesmos dados: 35 trades, −0,03R, soma de −0,9R, queda de 5,5R. Na direção certa, mas sem prova: quase tudo vem do USDJPY. Ouro (estudo): 11 trades, −0,13R, quase só compras contra a queda; com filtro, 2 trades. Próximo: ampliar a amostra (1H em 8 meses, histórico do MT5) e corrigir linhas duplicadas. Detalhes em `testes/2026-11-16/`.

## Resultado de 16/11 com os preços da Tickmill (MT5, jan/2024 a nov/2026)
Sem filtro: 356 trades, −0,19R (intervalo inteiro negativo). Com filtro de tendência: 128 trades, −0,02R (−0,26 a +0,24), +0,09R antes dos custos. O filtro é indispensável, mas não basta: os custos (~0,11R por trade) comem a vantagem, e o bom resultado de 2026 não se repete em 2024–2025. Próximos testes (registrados antes): só 4H definido; stop mais largo ou corte por custo; alvo e saída por tempo. Desenvolver em 2024–2025, validar em 2026. Yahoo x Tickmill: EURUSD do Yahoo ~3,2 pips acima (correção proposta, aguarda aprovação). Detalhes em `testes/2026-11-16-mt5/`.

## 23/11 · TradingView Premium
Assinado. Fonte principal passa a ser a Tickmill via TradingView (ponte v2 com 4 ativos, robô com reserva no Yahoo e aviso), mais os indicadores Painel B&R, B&R Nível e B&R Linha para alertas de rompimento → reteste → confirmação no celular. Guia em `tradingview/LEIA-ME.md`. Próximos: ligar a ponte, tapar o histórico de 16/11 em diante com a exportação do gráfico, decidir se as análises de 05h20 e 11h45 voltam a rodar (estão desligadas desde 19/11) e, depois, usar o Deep Backtesting para conferir o teste em Python.

## Pendências com data
- **Hipótese para testar (19/11):** no US500, em 17/11 e 19/11, o alvo antes do primeiro suporte travou a relação abaixo de 1,5R em dias de queda forte (−150 e −260 pts). Testar no histórico da Tickmill, desenvolvendo em 2024–2025 e validando em 2026: com tendência forte no 4H, usar o 2º obstáculo como alvo, ou sair com parte no 1º e deixar o resto andar com stop móvel.
- **Registro (19/11):** o rompimento para cima da LTB grande do ouro em 16/11 (contra o 4H) falhou: topo 3.890 em 17/11, depois −265 dólares. Rompimento contra a tendência só conta depois de fechamento + reteste.
- **Ajuste no robô (17/11):** ele não gera plano de venda/compra no reteste de um nível que JÁ foi rompido (ex.: US500 em 17/11, suporte do 4H em ~7.475 rompido em 16/11, reteste esperado por baixo). Hoje ele só trata o nível como resistência a romper para cima. Corrigir e medir no histórico da Tickmill.
- **TradingView:** decisão adiada para a Black Friday do TradingView em 23/11 (preço melhor). Conferir se o plano tem alertas com webhook antes de assinar.
- **Segunda 16/11:** Rodrigo decide sobre o plano do TradingView (Essential ou acima). Se sim, ligar a ponte (`tradingview/LEIA-ME.md`) e rodar uma semana em paralelo com o Yahoo antes de trocar.
- **Segunda 16/11 (pedido de 14/11):** incluir o XAUUSD no teste histórico só para estudo, em seção separada, sem somar aos ativos operados. Origem: short em 3.904 de 13/11 (reteste de LTA rompida + Fibonacci + topo do canal; alvo antes do suporte teria dado ~2–3R; o dado das 10h30 levou o preço de volta à entrada). Medir em R, porque no ouro o stop típico passa do limite de US$ 2.
- **Pedido de 13/11 (anotado):** relatórios das análises e dos testes em PDF dinâmico e profissional, no tema cyberpunk (mesma identidade visual da amostra do Obsidian): capa, um bloco por ativo com o painel 4H/1H/15m, plano, alertas e situação; versão do teste histórico com curva e tabelas. Gerado automaticamente junto com as análises das 05h20 e 11h45.
- **Depois da validação:** cérebro no Obsidian (repositório privado `cerebro-trade`, amostra visual aprovada em estilo cyberpunk) e portal web.

## Maior alavanca ainda não usada
Testar o motor no histórico: rodar as regras candle a candle nos dados já coletados (6 meses de 1h, 30 a 60 dias de 15m), sem olhar o futuro, com custos, para ter centenas de casos hipotéticos em vez de esperar meses de trades. Não substitui a validação ao vivo, mas mostra cedo se há vantagem e quais filtros ajudam.
