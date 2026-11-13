# Avaliação Trade · sistema Break & Retest

Dados de mercado e rotinas da análise diária do sistema Break & Retest (linhas de tendência, rompimento e reteste).

- `dados/`: candles fechados de 15m e 1h (horário UTC), atualizados a cada 5 minutos pelo GitHub Actions. Fonte: Yahoo Finance (EURUSD=X, JPY=X, ES=F, GC=F). Os preços podem diferir de 1 a 2 pips da corretora; os níveis de entrada são conferidos no gráfico da Tickmill antes de operar.
- `scripts/coleta.py`: coleta.
- `scripts/linhas.py`: regras de traçado das LTA/LTB e níveis horizontais.
- `scripts/analise.py`: gera o painel 4H/1H/15m de cada ativo.
- `config/regras.json`: parâmetros do sistema.

Nada de conta, senha ou saldo é guardado aqui.

## Como rodar a análise

```
pip install pandas matplotlib
python scripts/analise.py                # EURUSD, USDJPY e US500
python scripts/analise.py EURUSD         # só um ativo
```

Gera `saida/analise.json` (linhas, níveis, planos e situação do rompimento/reteste/confirmação) e um painel PNG por ativo (4H e 1H em cima, 15m com o plano embaixo).
