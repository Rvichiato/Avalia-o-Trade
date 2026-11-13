# Fontes de dados: avaliações

Cada avaliação nova entra no topo. Critérios: (1) preço próximo ao da Tickmill, (2) atraso até o candle chegar, (3) resolução do preço, (4) custo e limites, (5) funciona a partir do GitHub Actions sem intervenção.

## 13/11/2026 · avaliação inicial

**Em uso: Yahoo Finance via yfinance** (EURUSD=X, JPY=X, ES=F, ^GSPC, GC=F)
- Grátis, sem chave. O acesso direto à API dava erro 429 a partir do GitHub; via yfinance funciona.
- EURUSD: níveis batem com a Tickmill em 0 a 4 pips, mas o preço anda em degraus de ~1,2 pip (o Yahoo calcula o par a partir do inverso com 4 casas). 19% dos candles de 15m têm abertura igual ao fechamento.
- USDJPY: 3 casas, ok; picos falsos ocasionais (filtrados no código).
- US500: só existe o futuro (ES=F) em 24h; o à vista (^GSPC) só no pregão. O código converte usando a diferença mediana dos 2 últimos pregões (+22,5 pontos em 13/11).
- Atraso medido na primeira coleta: ~4 min depois do fechamento do candle de 15m.

**Candidata 1: Twelve Data, plano gratuito**
- 800 requisições/dia e 8 por minuto; cobre forex. Com só o 15m (o 1h e o 4H saem dele), 3 pares a cada 5 min das 05h às 19h e a cada 15 min no resto do dia ≈ 600 requisições/dia: cabe.
- Precisa de chave gratuita do Rodrigo, guardada como segredo do repositório (TWELVE_DATA_KEY). Nunca vai para o código.
- A testar: resolução do EURUSD (esperado 5 casas), atraso real no plano gratuito (há relatos de 1 a 15 minutos), se índices (S&P 500) entram no plano gratuito.
- Plano de teste: rodar em paralelo ao Yahoo por 1 semana e comparar com os prints da Tickmill.

**Descartada por ora: OANDA (API v20, conta demo)**
- Seria a melhor (preço de corretora, SPX500_USD parecido com o US500 da Tickmill), mas a documentação diz que a API não é oferecida à divisão OANDA Global Markets, que é a que atende residentes de fora dos EUA/UE como o Brasil. Reavaliar se isso mudar.

**Descartadas: Alpha Vantage** (25 requisições/dia, insuficiente), **ExchangeRate-API e similares** (só atualização horária ou diária).
